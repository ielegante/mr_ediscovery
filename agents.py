# ABOUTME: Map-reduce EIA extraction pipeline — PDF extraction, agents, orchestration.
# ABOUTME: Splits PDFs into batches, extracts structured data (map), consolidates (reduce).

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from collections.abc import Callable
from dataclasses import asdict
from functools import cache
from pathlib import Path
from typing import TypeVar

import logfire
import pymupdf
from pydantic_ai import Agent

logfire.configure()
logfire.instrument_pydantic_ai()

from models import (
    BatchExtraction,
    ConsolidatedReport,
    ImpactAssessment,
    MitigationMeasure,
    SpeciesRecord,
)
from prompts import MAP_SYSTEM_PROMPT, REDUCE_SYSTEM_PROMPT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# --- Configuration (override via environment or .env file) ---

MODEL = os.environ.get("MODEL", "gateway/anthropic:claude-sonnet-4-5")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", "5"))
PAGE_BREAK = "\n\n--- PAGE BREAK ---\n\n"
MIN_TEXT_LENGTH = 50  # batches with less text than this are considered empty

# --- PDF extraction ---


def extract_pages(pdf_path: str | Path) -> list[str]:
    """Extract text from each page of a PDF using pymupdf."""
    doc = pymupdf.open(str(pdf_path))
    pages = [page.get_text() for page in doc]
    doc.close()
    log.info("Extracted %d pages from %s", len(pages), Path(pdf_path).name)
    return pages


def make_batches(
    pages: list[str], batch_size: int = BATCH_SIZE
) -> list[tuple[int, int, str]]:
    """Group pages into batches. Returns list of (start_page, end_page, combined_text)."""
    batches = []
    for i in range(0, len(pages), batch_size):
        chunk = pages[i : i + batch_size]
        start = i + 1  # 1-indexed page numbers
        end = i + len(chunk)
        text = PAGE_BREAK.join(chunk)
        if len(text.strip()) >= MIN_TEXT_LENGTH:
            batches.append((start, end, text))
    log.info("Created %d batches of ~%d pages", len(batches), batch_size)
    return batches


# --- Agents (lazy-initialized to avoid requiring API key at import time) ---


@cache
def get_map_agent() -> Agent[None, BatchExtraction]:
    return Agent(MODEL, output_type=BatchExtraction, system_prompt=MAP_SYSTEM_PROMPT)


@cache
def get_reduce_agent() -> Agent[None, ConsolidatedReport]:
    return Agent(MODEL, output_type=ConsolidatedReport, system_prompt=REDUCE_SYSTEM_PROMPT)


# --- Map phase ---


async def run_map(
    batch_id: int,
    page_start: int,
    page_end: int,
    text: str,
    source: str,
    semaphore: asyncio.Semaphore,
) -> BatchExtraction:
    """Run the map agent on one batch with concurrency control."""
    async with semaphore:
        log.info("MAP batch %d (pages %d-%d, %s)", batch_id, page_start, page_end, source)
        result = await get_map_agent().run(text)
        extraction = result.output
        extraction.batch_id = batch_id
        extraction.page_start = page_start
        extraction.page_end = page_end
        extraction.source_document = source
        log.info(
            "MAP batch %d done: %d species, %d impacts, %d mitigations",
            batch_id,
            len(extraction.species),
            len(extraction.impacts),
            len(extraction.mitigations),
        )
        return extraction


# --- Aggregation (pure Python, no LLM) ---

CONSERVATION_SIGNIFICANT = {"cr", "en", "vu", "critically endangered", "endangered", "vulnerable"}

T = TypeVar("T")


def _deduplicate(items: list[T], key_fn: Callable[[T], tuple]) -> list[T]:
    """Deduplicate a list using a key function, preserving first occurrence."""
    seen: dict[tuple, T] = {}
    for item in items:
        key = key_fn(item)
        if key not in seen:
            seen[key] = item
    return list(seen.values())


def _species_key(s: SpeciesRecord) -> tuple[str, str]:
    return (s.name.lower().strip(), s.site.lower().strip())


def _impact_key(i: ImpactAssessment) -> tuple[str, str, str]:
    return (
        i.environmental_parameter.lower().strip(),
        i.site.lower().strip(),
        i.description[:80].lower().strip(),
    )


def _mitigation_key(m: MitigationMeasure) -> tuple[str, str]:
    return (
        m.environmental_parameter.lower().strip(),
        m.measure[:80].lower().strip(),
    )


def aggregate(extractions: list[BatchExtraction]) -> dict:
    """Deduplicate and count across all batch extractions. Returns data for reduce agent."""
    all_species = [s for ext in extractions for s in ext.species]
    all_impacts = [i for ext in extractions for i in ext.impacts]
    all_mitigations = [m for ext in extractions for m in ext.mitigations]

    species = _deduplicate(all_species, _species_key)
    impacts = _deduplicate(all_impacts, _impact_key)
    mitigations = _deduplicate(all_mitigations, _mitigation_key)

    total_pages = sum(ext.page_end - ext.page_start + 1 for ext in extractions)

    conservation_significant = sum(
        1
        for s in species
        if s.conservation_status.lower().strip() in CONSERVATION_SIGNIFICANT
    )

    significance_counts = {"major": 0, "moderate": 0, "minor": 0, "negligible": 0}
    for i in impacts:
        level = i.impact_significance.lower().strip()
        if level in significance_counts:
            significance_counts[level] += 1

    return {
        "species": [asdict(s) for s in species],
        "impacts": [asdict(i) for i in impacts],
        "mitigations": [asdict(m) for m in mitigations],
        "total_species": len(species),
        "total_species_conservation_significant": conservation_significant,
        "impacts_major": significance_counts["major"],
        "impacts_moderate": significance_counts["moderate"],
        "impacts_minor": significance_counts["minor"],
        "impacts_negligible": significance_counts["negligible"],
        "total_batches_processed": len(extractions),
        "total_pages_processed": total_pages,
    }


# --- Reduce phase ---


async def run_reduce(aggregated: dict) -> ConsolidatedReport:
    """Run the reduce agent on pre-aggregated data."""
    prompt = json.dumps(aggregated, indent=2)
    log.info(
        "REDUCE: %d species, %d impacts, %d mitigations",
        aggregated["total_species"],
        len(aggregated["impacts"]),
        len(aggregated["mitigations"]),
    )
    result = await get_reduce_agent().run(prompt)
    return result.output


# --- Main ---


async def main() -> None:
    pdf_dir = Path(os.environ.get("PDF_DIR", "."))
    output_dir = Path(os.environ.get("OUTPUT_DIR", "."))
    output_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        log.error("No PDFs found in %s", pdf_dir)
        sys.exit(1)
    log.info("Found %d PDFs: %s", len(pdfs), [p.name for p in pdfs])

    # Extract text from all PDFs
    all_batches: list[tuple[int, int, str, str]] = []  # (start, end, text, source)
    for pdf in pdfs:
        pages = extract_pages(pdf)
        batches = make_batches(pages)
        for start, end, text in batches:
            all_batches.append((start, end, text, pdf.name))

    log.info("Total batches across all PDFs: %d", len(all_batches))

    # Map phase — concurrent with semaphore
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    tasks = [
        run_map(i, start, end, text, source, semaphore)
        for i, (start, end, text, source) in enumerate(all_batches)
    ]
    extractions = await asyncio.gather(*tasks)

    # Filter extractions with no structured data
    extractions = [
        e
        for e in extractions
        if e.species or e.impacts or e.mitigations or e.baselines
    ]
    log.info("Non-empty extractions: %d", len(extractions))

    # Aggregate in Python
    aggregated = aggregate(extractions)

    # Reduce phase
    report = await run_reduce(aggregated)

    # Write output
    output_path = output_dir / "consolidated_report.json"
    output_path.write_text(json.dumps(asdict(report), indent=2))
    log.info("Report written to %s", output_path)
    log.info(
        "Summary: %d species (%d conservation-significant), "
        "%d impacts (major=%d, moderate=%d, minor=%d, negligible=%d)",
        report.total_species,
        report.total_species_conservation_significant,
        report.impacts_major,
        report.impacts_moderate,
        report.impacts_minor,
        report.impacts_negligible,
    )


if __name__ == "__main__":
    asyncio.run(main())
