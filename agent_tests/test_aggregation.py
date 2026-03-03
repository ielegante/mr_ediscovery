# ABOUTME: Tests for the aggregation (deduplication + counting) logic.
# ABOUTME: Verifies species dedup, impact counting, mitigation merging, and edge cases.

import pytest

from agents import (
    _deduplicate,
    _impact_key,
    _is_conservation_significant,
    _mitigation_key,
    _species_key,
    aggregate,
)
from models import (
    BatchExtraction,
    ImpactAssessment,
    MitigationMeasure,
    SpeciesRecord,
)


# --- Deduplication ---


def test_dedup_removes_duplicate_species(batch_with_species, batch_with_duplicates):
    result = aggregate([batch_with_species, batch_with_duplicates])
    names = [s["name"] for s in result["species"]]
    assert names.count("Sunda Pangolin") == 1


def test_dedup_keeps_unique_species(batch_with_species, batch_with_duplicates):
    result = aggregate([batch_with_species, batch_with_duplicates])
    names = [s["name"] for s in result["species"]]
    assert "Common Palm Civet" in names
    assert "Straw-headed Bulbul" in names
    assert len(names) == 3


def test_dedup_preserves_first_occurrence():
    s1 = SpeciesRecord(name="Test Species", site="Site A", conservation_status="CR")
    s2 = SpeciesRecord(name="Test Species", site="Site A", conservation_status="EN")
    result = _deduplicate([s1, s2], _species_key)
    assert len(result) == 1
    assert result[0].conservation_status == "CR"


def test_dedup_case_insensitive():
    s1 = SpeciesRecord(name="Sunda Pangolin", site="CTP")
    s2 = SpeciesRecord(name="sunda pangolin", site="ctp")
    result = _deduplicate([s1, s2], _species_key)
    assert len(result) == 1


def test_dedup_different_sites_are_distinct():
    s1 = SpeciesRecord(name="Sunda Pangolin", site="CleanTech Park")
    s2 = SpeciesRecord(name="Sunda Pangolin", site="Bahar")
    result = _deduplicate([s1, s2], _species_key)
    assert len(result) == 2


def test_dedup_impacts_by_parameter_site_description():
    i1 = ImpactAssessment(
        environmental_parameter="noise", site="Residential", description="Construction noise"
    )
    i2 = ImpactAssessment(
        environmental_parameter="noise", site="Residential", description="Construction noise"
    )
    i3 = ImpactAssessment(
        environmental_parameter="noise", site="Commercial", description="Construction noise"
    )
    result = _deduplicate([i1, i2, i3], _impact_key)
    assert len(result) == 2


def test_dedup_mitigations_by_parameter_and_measure():
    m1 = MitigationMeasure(
        environmental_parameter="biodiversity", measure="Wildlife corridor"
    )
    m2 = MitigationMeasure(
        environmental_parameter="biodiversity", measure="Wildlife corridor"
    )
    m3 = MitigationMeasure(
        environmental_parameter="biodiversity", measure="Tree transplanting"
    )
    result = _deduplicate([m1, m2, m3], _mitigation_key)
    assert len(result) == 2


def test_dedup_empty_list():
    result = _deduplicate([], _species_key)
    assert result == []


# --- Conservation significance counting ---


@pytest.mark.parametrize("status", [
    "CR", "EN", "VU", "NT", "cr", "Critically Endangered", "endangered", "near threatened",
    "VU (National)", "CR (National), CR (Global)", "EN (National), VU (Global)",
    "NT (National), EN (Global)",
])
def test_conservation_significant_statuses(status):
    assert _is_conservation_significant(status)


@pytest.mark.parametrize("status", ["LC", "DD", "NE", "", "Least Concern", "Data Deficient"])
def test_conservation_non_significant_statuses(status):
    assert not _is_conservation_significant(status)


def test_aggregate_counts_conservation_significant(batch_with_species, batch_with_duplicates):
    result = aggregate([batch_with_species, batch_with_duplicates])
    # CR (pangolin, deduped to 1) + EN (bulbul) = 2 significant
    assert result["total_species_conservation_significant"] == 2


# --- Impact severity counting ---


def test_aggregate_counts_impact_severity(batch_with_species, batch_with_duplicates):
    result = aggregate([batch_with_species, batch_with_duplicates])
    assert result["impacts_major"] == 1
    assert result["impacts_moderate"] == 1
    assert result["impacts_minor"] == 1
    assert result["impacts_negligible"] == 0


def test_aggregate_uncategorized_severity_not_counted():
    """Impacts with non-standard severity levels don't inflate any counter."""
    ext = BatchExtraction(
        batch_id=0,
        page_start=1,
        page_end=10,
        impacts=[
            ImpactAssessment(
                environmental_parameter="test",
                impact_significance="significant",
                description="Non-standard severity",
            )
        ],
    )
    result = aggregate([ext])
    assert result["impacts_major"] == 0
    assert result["impacts_moderate"] == 0
    assert result["impacts_minor"] == 0
    assert result["impacts_negligible"] == 0


# --- Page counting ---


def test_aggregate_total_pages(batch_with_species, batch_with_duplicates):
    result = aggregate([batch_with_species, batch_with_duplicates])
    assert result["total_pages_processed"] == 20


def test_aggregate_batch_count(batch_with_species, batch_with_duplicates, empty_batch):
    result = aggregate([batch_with_species, batch_with_duplicates, empty_batch])
    assert result["total_batches_processed"] == 3


# --- Edge cases ---


def test_aggregate_empty_extractions():
    result = aggregate([])
    assert result["total_species"] == 0
    assert result["total_pages_processed"] == 0
    assert result["total_batches_processed"] == 0
    assert result["species"] == []


def test_aggregate_single_batch(batch_with_species):
    result = aggregate([batch_with_species])
    assert result["total_species"] == 2
    assert result["total_batches_processed"] == 1
