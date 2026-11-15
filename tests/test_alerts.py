"""
Unit tests for proactive alert triggers, email simulation, and escalation logic.
"""

from datetime import datetime, timedelta

import pytest

import db.database as db
from utils.alerts import (
    check_and_trigger_alerts,
    dispatch_sos_alert,
    get_alert_summary,
    get_smtp_config,
    send_email_alert,
)


@pytest.fixture(autouse=True)
def setup_test_alerts(tmp_path, monkeypatch):
    """Set up database in isolated tmp_path."""
    test_db_path = str(tmp_path / "test_alerts.db")
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()
    db.seed_initial_data()


def test_smtp_config_fallback():
    """Verify fallback when SMTP is unconfigured."""
    config = get_smtp_config()
    assert isinstance(config, dict)
    assert "is_configured" in config


def test_send_email_alert_sandbox():
    """Verify alert logging works even without active SMTP server."""
    res = send_email_alert(
        recipient_email="test.caretaker@example.com",
        subject="Test Unit Alert",
        body_html="<p>Test</p>",
        alert_type="TEST_UNIT",
        severity="INFO",
        patient_id=1,
    )
    assert res["success"] is True
    assert res["status"] in ("SENT", "LOGGED")

    alerts = db.get_alerts(patient_id=1)
    test_entry = next((a for a in alerts if a["alert_type"] == "TEST_UNIT"), None)
    assert test_entry is not None
    assert test_entry["recipient_email"] == "test.caretaker@example.com"


def test_sos_alert_dispatch():
    """Verify emergency SOS dispatch creates critical alert log."""
    res = dispatch_sos_alert(patient_id=1, notes="Test SOS Press")
    assert res["success"] is True

    summary = get_alert_summary(patient_id=1)
    assert summary["critical"] >= 1


def test_proactive_overdue_check():
    """Verify overdue dose detection marks dose missed and triggers alert."""
    patient = db.get_patient()
    p_id = patient["id"]

    # Insert a dose that was scheduled 2 hours ago today with PENDING status
    past_time = (datetime.now() - timedelta(hours=2)).strftime("%H:%M")
    m_id = db.add_medication(
        patient_id=p_id,
        name="Delayed Med",
        dosage="25mg",
        frequency="Daily",
        time_of_day="Morning",
        scheduled_time=past_time,
        pill_color="#EF4444",
        pill_shape="Tablet",
        stock_remaining=2,  # Also low stock!
        refill_threshold=5,
    )

    triggered = check_and_trigger_alerts(patient_id=p_id, force_check=True)
    assert len(triggered) >= 1

    # Verify dose was marked MISSED in database
    doses = db.get_todays_doses(p_id)
    delayed_dose = next((d for d in doses if d["medication_id"] == m_id), None)
    assert delayed_dose is not None
    assert delayed_dose["status"] == "MISSED"
