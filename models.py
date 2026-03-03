# ABOUTME: Dataclasses for map-reduce EIA structured extraction.
# ABOUTME: Shared building blocks, batch (map) output, and consolidated (reduce) output.

from __future__ import annotations

from dataclasses import dataclass, field


# --- Shared building blocks (used in both map and reduce outputs) ---


@dataclass
class SpeciesRecord:
    """A species observed or referenced in the EIA."""

    name: str
    taxonomic_group: str = ""
    family: str = ""
    origin: str = ""  # native, exotic, etc.
    conservation_status: str = ""  # e.g. CR, EN, VU, NT, LC
    site: str = ""
    habitat: str = ""


@dataclass
class ImpactAssessment:
    """An assessed environmental impact."""

    environmental_parameter: str  # e.g. air quality, noise, biodiversity
    receptor_type: str = ""
    site: str = ""
    impact_significance: str = ""  # major, moderate, minor, negligible
    residual_significance: str = ""
    description: str = ""


@dataclass
class MitigationMeasure:
    """A proposed mitigation measure."""

    environmental_parameter: str
    measure: str = ""
    phase: str = ""  # construction, operation
    responsible_party: str = ""


@dataclass
class BaselineFinding:
    """A baseline environmental measurement or observation."""

    parameter: str
    site: str = ""
    description: str = ""
    value: str = ""


@dataclass
class LegislationReference:
    """A referenced law, regulation, or standard."""

    name: str
    jurisdiction: str = ""
    relevance: str = ""


@dataclass
class KeyFinding:
    """A qualitative or spatial finding that doesn't fit structured tables."""

    category: str  # e.g. ecological connectivity, cumulative impact, landscape context
    finding: str = ""
    site: str = ""
    significance: str = ""  # why this matters


# --- Map output (one per batch) ---


@dataclass
class BatchExtraction:
    """Structured data extracted from one batch of EIA pages."""

    batch_id: int = 0
    page_start: int = 0
    page_end: int = 0
    source_document: str = ""
    section_titles: list[str] = field(default_factory=list)
    summary: str = ""
    species: list[SpeciesRecord] = field(default_factory=list)
    impacts: list[ImpactAssessment] = field(default_factory=list)
    mitigations: list[MitigationMeasure] = field(default_factory=list)
    baselines: list[BaselineFinding] = field(default_factory=list)
    legislation: list[LegislationReference] = field(default_factory=list)
    key_findings: list[KeyFinding] = field(default_factory=list)


# --- Reduce output (consolidated across all batches) ---


@dataclass
class ConsolidatedReport:
    """Final consolidated report merging all batch extractions."""

    executive_summary: str = ""
    conclusion: str = ""
    species: list[SpeciesRecord] = field(default_factory=list)
    impacts: list[ImpactAssessment] = field(default_factory=list)
    mitigations: list[MitigationMeasure] = field(default_factory=list)
    key_findings: list[KeyFinding] = field(default_factory=list)
    total_species: int = 0
    total_species_conservation_significant: int = 0
    impacts_major: int = 0
    impacts_moderate: int = 0
    impacts_minor: int = 0
    impacts_negligible: int = 0
    total_batches_processed: int = 0
    total_pages_processed: int = 0
