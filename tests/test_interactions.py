"""
Unit tests for pharmacological drug-drug interaction safety engine.
"""

import pytest
from utils.interactions import evaluate_interactions, get_interaction_details
import db.database as db


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
    assert "🔴" in details
    assert "Risk of bleeding" in details
