# ABOUTME: Tests for EIA dataclass models.
# ABOUTME: Verifies construction, defaults, and serialization.

from dataclasses import asdict

from models import (
    BatchExtraction,
    ConsolidatedReport,
    ImpactAssessment,
    SpeciesRecord,
)


def test_species_record_required_field():
    s = SpeciesRecord(name="Sunda Pangolin")
    assert s.name == "Sunda Pangolin"
    assert s.conservation_status == ""
    assert s.site == ""


def test_species_record_all_fields():
    s = SpeciesRecord(
        name="Sunda Pangolin",
        taxonomic_group="mammals",
        family="Manidae",
        origin="native",
        conservation_status="CR",
        site="CleanTech Park",
        habitat="secondary forest",
    )
    d = asdict(s)
    assert d["name"] == "Sunda Pangolin"
    assert d["family"] == "Manidae"
    assert d["habitat"] == "secondary forest"


def test_batch_extraction_defaults_to_empty_lists():
    b = BatchExtraction()
    assert b.species == []
    assert b.impacts == []
    assert b.mitigations == []
    assert b.baselines == []
    assert b.legislation == []
    assert b.section_titles == []


def test_batch_extraction_lists_are_independent():
    """Each instance gets its own list (no shared default_factory bug)."""
    b1 = BatchExtraction()
    b2 = BatchExtraction()
    b1.species.append(SpeciesRecord(name="test"))
    assert b2.species == []


def test_consolidated_report_defaults():
    r = ConsolidatedReport()
    assert r.total_species == 0
    assert r.executive_summary == ""
    assert r.species == []


def test_impact_assessment_serialization():
    i = ImpactAssessment(
        environmental_parameter="noise",
        impact_significance="Major",
        description="Construction noise",
    )
    d = asdict(i)
    assert d["environmental_parameter"] == "noise"
    assert d["impact_significance"] == "Major"
    assert d["receptor_type"] == ""
