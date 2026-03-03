# ABOUTME: Test fixtures for EIA extraction pipeline.
# ABOUTME: Provides reusable test data following datasette-enrichments patterns.

from __future__ import annotations

import pytest

from models import (
    BaselineFinding,
    BatchExtraction,
    ImpactAssessment,
    LegislationReference,
    MitigationMeasure,
    SpeciesRecord,
)


@pytest.fixture
def pangolin():
    return SpeciesRecord(
        name="Sunda Pangolin",
        taxonomic_group="mammals",
        conservation_status="CR",
        site="CleanTech Park",
        origin="native",
    )


@pytest.fixture
def bulbul():
    return SpeciesRecord(
        name="Straw-headed Bulbul",
        taxonomic_group="avifauna",
        conservation_status="EN",
        site="Bahar",
        origin="native",
    )


@pytest.fixture
def common_species():
    return SpeciesRecord(
        name="Common Palm Civet",
        taxonomic_group="mammals",
        conservation_status="LC",
        site="CleanTech Park",
        origin="native",
    )


@pytest.fixture
def major_impact():
    return ImpactAssessment(
        environmental_parameter="biodiversity",
        site="CleanTech Park",
        impact_significance="Major",
        description="Loss of foraging habitat for pangolin populations",
    )


@pytest.fixture
def moderate_impact():
    return ImpactAssessment(
        environmental_parameter="noise",
        site="Residential",
        impact_significance="Moderate",
        description="Construction noise exceeding ambient levels",
    )


@pytest.fixture
def minor_impact():
    return ImpactAssessment(
        environmental_parameter="air quality",
        site="Residential",
        impact_significance="Minor",
        description="Dust from earthworks during construction",
    )


@pytest.fixture
def mitigation():
    return MitigationMeasure(
        environmental_parameter="biodiversity",
        measure="Wildlife corridor preservation along western boundary",
        phase="construction",
        responsible_party="Contractor",
    )


@pytest.fixture
def batch_with_species(pangolin, common_species, major_impact, mitigation):
    return BatchExtraction(
        batch_id=0,
        page_start=1,
        page_end=10,
        source_document="report.pdf",
        species=[pangolin, common_species],
        impacts=[major_impact],
        mitigations=[mitigation],
    )


@pytest.fixture
def batch_with_duplicates(pangolin, bulbul, moderate_impact, minor_impact):
    """Second batch with one duplicate species (pangolin) and new data."""
    return BatchExtraction(
        batch_id=1,
        page_start=11,
        page_end=20,
        source_document="report.pdf",
        species=[pangolin, bulbul],
        impacts=[moderate_impact, minor_impact],
    )


@pytest.fixture
def empty_batch():
    return BatchExtraction(batch_id=2, page_start=21, page_end=30)


@pytest.fixture
def batch_with_only_baselines():
    return BatchExtraction(
        batch_id=3,
        page_start=31,
        page_end=40,
        baselines=[BaselineFinding(parameter="PM2.5", site="Bahar", value="12 µg/m³")],
    )
