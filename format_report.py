# ABOUTME: Converts consolidated_report.json to a formatted markdown document.
# ABOUTME: Produces tables for species, impacts, and mitigations with summary stats.

from __future__ import annotations

import json
import sys
from pathlib import Path

CONSERVATION_SIGNIFICANT_CODES = {"cr", "en", "vu", "nt"}
CONSERVATION_SIGNIFICANT_NAMES = {"critically endangered", "endangered", "vulnerable", "near threatened"}


def _is_significant(status: str) -> bool:
    """Match conservation codes and full names in statuses like 'VU (National)', 'CR (National), CR (Global)'."""
    lowered = status.lower()
    if any(name in lowered for name in CONSERVATION_SIGNIFICANT_NAMES):
        return True
    tokens = set(lowered.replace(",", " ").replace("(", " ").replace(")", " ").split())
    return bool(tokens & CONSERVATION_SIGNIFICANT_CODES)


def _escape_md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def format_report(data: dict) -> str:
    lines: list[str] = []
    w = lines.append

    w("# EIA Consolidated Report")
    w("")
    w("**CleanTech Park (Site A) & Bahar Industrial Estates (Site B), Singapore**")
    w("")

    # --- Stats ---
    w("## Summary Statistics")
    w("")
    w(f"| Metric | Value |")
    w(f"|---|---|")
    w(f"| Total species recorded | {data['total_species']} |")
    w(f"| Conservation-significant species | {data['total_species_conservation_significant']} |")
    w(f"| Major impacts | {data['impacts_major']} |")
    w(f"| Moderate impacts | {data['impacts_moderate']} |")
    w(f"| Minor impacts | {data['impacts_minor']} |")
    w(f"| Negligible impacts | {data['impacts_negligible']} |")
    w(f"| Mitigation measures | {len(data['mitigations'])} |")
    w(f"| Pages processed | {data['total_pages_processed']} |")
    w(f"| Batches processed | {data['total_batches_processed']} |")
    w("")

    # --- Executive Summary ---
    w("## Executive Summary")
    w("")
    w(data["executive_summary"])
    w("")

    # --- Conclusion & Recommendations ---
    w("## Conclusion & Recommendations")
    w("")
    w(data["conclusion"])
    w("")

    # --- Key Findings ---
    key_findings = data.get("key_findings", [])
    if key_findings:
        w("## Key Findings")
        w("")

        findings_by_category: dict[str, list] = {}
        for f in key_findings:
            cat = f["category"] or "General"
            findings_by_category.setdefault(cat, []).append(f)

        for cat in sorted(findings_by_category):
            findings = findings_by_category[cat]
            w(f"### {cat}")
            w("")
            for f in findings:
                site_tag = f" *({f['site']})*" if f["site"] else ""
                w(f"- {_escape_md(f['finding'])}{site_tag}")
                if f["significance"]:
                    w(f"  - **Significance**: {_escape_md(f['significance'])}")
            w("")

    # --- Species ---
    significant = [s for s in data["species"] if _is_significant(s["conservation_status"])]
    other = [s for s in data["species"] if not _is_significant(s["conservation_status"])]

    w("## Species Records")
    w("")

    if significant:
        w("### Conservation-Significant Species")
        w("")
        w("| Species | Group | Family | Status | Site | Origin | Habitat |")
        w("|---|---|---|---|---|---|---|")
        for s in sorted(significant, key=lambda x: x["name"]):
            w(f"| {_escape_md(s['name'])} | {s['taxonomic_group']} | {s['family']} "
              f"| **{_escape_md(s['conservation_status'])}** | {s['site']} "
              f"| {s['origin']} | {s['habitat']} |")
        w("")

    if other:
        w("### Other Species")
        w("")
        w("<details>")
        w(f"<summary>{len(other)} species (click to expand)</summary>")
        w("")
        w("| Species | Group | Family | Status | Site | Origin |")
        w("|---|---|---|---|---|---|")
        for s in sorted(other, key=lambda x: x["name"]):
            w(f"| {_escape_md(s['name'])} | {s['taxonomic_group']} | {s['family']} "
              f"| {_escape_md(s['conservation_status'])} | {s['site']} | {s['origin']} |")
        w("")
        w("</details>")
        w("")

    # --- Impacts ---
    w("## Impact Assessments")
    w("")

    impacts_by_severity: dict[str, list] = {}
    for i in data["impacts"]:
        level = i["impact_significance"] or "Unclassified"
        impacts_by_severity.setdefault(level, []).append(i)

    # Sort: major first, then moderate, minor, negligible, then anything else
    severity_order = ["Major", "Moderate", "Minor", "Negligible"]
    ordered_keys = [k for k in severity_order if k in impacts_by_severity]
    ordered_keys += [k for k in sorted(impacts_by_severity) if k not in ordered_keys]

    for level in ordered_keys:
        impacts = impacts_by_severity[level]
        w(f"### {level} ({len(impacts)})")
        w("")
        w("| Parameter | Receptor | Site | Residual | Description |")
        w("|---|---|---|---|---|")
        for i in impacts:
            desc = _escape_md(i["description"][:120])
            if len(i["description"]) > 120:
                desc += "..."
            w(f"| {_escape_md(i['environmental_parameter'])} | {i['receptor_type']} "
              f"| {i['site']} | {_escape_md(i['residual_significance'])} | {desc} |")
        w("")

    # --- Mitigations ---
    w("## Mitigation Measures")
    w("")

    mitigations_by_param: dict[str, list] = {}
    for m in data["mitigations"]:
        param = m["environmental_parameter"] or "General"
        mitigations_by_param.setdefault(param, []).append(m)

    for param in sorted(mitigations_by_param):
        measures = mitigations_by_param[param]
        w(f"### {param} ({len(measures)})")
        w("")
        w("| Measure | Phase | Responsible Party |")
        w("|---|---|---|")
        for m in measures:
            measure_text = _escape_md(m["measure"][:200])
            if len(m["measure"]) > 200:
                measure_text += "..."
            w(f"| {measure_text} | {m['phase']} | {m['responsible_party']} |")
        w("")

    return "\n".join(lines)


if __name__ == "__main__":
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("consolidated_report.json")
    output_path = input_path.with_suffix(".md")

    with open(input_path) as f:
        data = json.load(f)

    md = format_report(data)
    output_path.write_text(md)
    print(f"Written to {output_path} ({len(md)} chars)")
