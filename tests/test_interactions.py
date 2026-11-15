"""
Unit tests for pharmacological drug-drug interaction safety engine.
"""

import pytest

import db.database as db
from utils.interactions import evaluate_interactions, get_interaction_details


@pytest.fixture(autouse=True)
def setup_test_interactions(tmp_path, monkeypatch):
    """Set up database."""
    test_db_path = str(tmp_path / "test_interactions.db")
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()
    db.seed_initial_data()


def test_known_high_risk_interaction():
    """Verify Aspirin + Warfarin triggers High risk warning."""
    warnings = evaluate_interactions(["Aspirin", "Warfarin"])
    assert len(warnings) == 1
    assert warnings[0]["severity"] == "High"
    assert "hemorrhage" in warnings[0]["description"].lower()


def test_proposed_drug_interaction():
    """Verify adding a new drug flags conflict against existing regimen."""
    existing_meds = ["Lisinopril", "Metformin", "Atorvastatin"]
    warnings = evaluate_interactions(existing_meds, proposed_drug="Spironolactone")
    assert len(warnings) >= 1
    assert any("hyperkalemia" in w["description"].lower() for w in warnings)


def test_safe_drug_combinations():
    """Verify benign combinations produce zero warnings."""
    safe_meds = ["Paracetamol", "Vitamin C", "Omega 3"]
    warnings = evaluate_interactions(safe_meds)
    assert len(warnings) == 0


def test_interaction_details_formatting():
    """Verify formatted Markdown output."""
    sample = {
        "severity": "High",
        "description": "Risk of bleeding",
        "recommendation": "Avoid combination",
    }
    details = get_interaction_details(sample)
    assert "[HIGH RISK]" in details
    assert "Risk of bleeding" in details


def test_ddi_none_and_non_string_resilience():
    """Verify DDI engine safely handles None, empty, and non-string inputs."""
    # List containing None and empty elements
    warnings = evaluate_interactions([None, "Aspirin", "Warfarin"], proposed_drug=None)
    assert len(warnings) == 1
    assert warnings[0]["severity"] == "High"

    # Single drug with proposed_drug=None
    assert evaluate_interactions(["Aspirin"], proposed_drug=None) == []

    # Non-string elements in current_medications
    warnings_kw = evaluate_interactions(current_medications=[None, "", "   ", 12345, "Aspirin", "Warfarin"])
    assert len(warnings_kw) == 1

    # Empty list and proposed_drug empty
    assert evaluate_interactions([], proposed_drug="") == []
    assert evaluate_interactions([], proposed_drug=None) == []
    assert evaluate_interactions(None, proposed_drug=None) == []


def test_ddi_substring_false_positive_prevention():
    """Verify token boundary checks prevent arbitrary substring false positives."""
    # 'Sin' should NOT trigger 'Lisinopril'
    warnings = evaluate_interactions(["Sin", "Spironolactone"])
    assert len(warnings) == 0

    # 'In' should NOT trigger 'Aspirin' or 'Warfarin'
    warnings_in = evaluate_interactions(["In", "Warfarin"])
    assert len(warnings_in) == 0


def test_ddi_token_and_boundary_matching():
    """Verify real-world prescription strings with dosage and tokens match correctly."""
    # Brand/dosage token matching
    warnings_dosage = evaluate_interactions(["Lisinopril 10mg", "Spironolactone 25mg"])
    assert len(warnings_dosage) == 1
    assert any("hyperkalemia" in w["description"].lower() for w in warnings_dosage)

    # Multi-word matching (Baby Aspirin vs Ibuprofen)
    warnings_multi = evaluate_interactions(["Baby Aspirin", "Ibuprofen"])
    assert len(warnings_multi) == 1

    # Identical drugs do not trigger conflict against themselves
    assert evaluate_interactions(["Aspirin", "Aspirin"]) == []
