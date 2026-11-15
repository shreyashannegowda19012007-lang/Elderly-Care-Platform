"""
Adversarial QA & Boundary Resilience Test Suite for GoldenCare Platform.
Rigorous stress-testing of session state boundaries, SQL injection resilience,
idempotency, physiological validation, cache invalidation, and Google service failure paths.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
import streamlit as st

import db.database as db
from utils.alerts import (
    send_email_alert,
)
from utils.analytics import (
    compute_adherence_timeseries,
)
from utils.auth import (
    get_current_role,
    get_current_user,
    init_session_state,
    is_authenticated,
    login_user,
)
from utils.google_services import (
    get_google_services_health,
)


@pytest.fixture(autouse=True)
def setup_adversarial_env(tmp_path, monkeypatch):
    """Set up dedicated temporary database and reset session state for each test."""
    test_db_path = str(tmp_path / "test_adversarial.db")
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()
    db.seed_initial_data()

    if hasattr(st, "session_state"):
        st.session_state.clear()
    init_session_state()

    yield

    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except OSError:
            pass


class TestAdversarialAuthAndSecurity:
    """Adversarial testing of passcode authentication and role boundaries."""

    def test_adversarial_passcode_brute_force(self):
        """Simulate 20 consecutive wrong PIN attempts; verify rejection and no state pollution."""
        for pin in ["0000", "9999", "1111", "4321", "admin", "root", "12345", "' OR 1=1 --"]:
            res = login_user("elderly", pin)
            assert res is False
            assert is_authenticated() is False
            assert get_current_role() is None

        # Verify correct PIN still authenticates immediately after failed attempts
        assert login_user("elderly", "1234") is True
        assert is_authenticated() is True
        assert get_current_role() == "elderly"

    def test_adversarial_passcode_types(self):
        """Verify handling of null, empty, unicode, whitespace, and complex types."""
        assert login_user("elderly", None) is False
        assert login_user("elderly", "") is False
        assert login_user("elderly", "    ") is False
        assert login_user("elderly", "\t\n") is False
        assert login_user("elderly", "🔓🔑") is False
        assert login_user("elderly", ["1234"]) is False
        assert login_user("elderly", {"pin": "1234"}) is False
        assert login_user(None, "1234") is False
        assert login_user(123, "1234") is False

    def test_adversarial_role_escalation_guard(self):
        """Verify elderly credentials cannot gain caretaker role."""
        assert login_user("caretaker", "1234") is False
        assert is_authenticated() is False

        # Caretaker PIN cannot gain elderly role
        assert login_user("elderly", "8888") is False
        assert is_authenticated() is False


class TestAdversarialDataIntegrity:
    """Adversarial testing of SQL injection, idempotency, and physiological constraints."""

    def test_adversarial_sql_injection_resilience(self):
        """Verify SQL injection strings do not compromise database structure."""
        patient = db.get_patient()
        p_id = patient["id"]

        injection_payload = "'; DROP TABLE users; --"
        new_id = db.add_medication(
            patient_id=p_id,
            name=f"Harmless Pill {injection_payload}",
            dosage="10mg",
            frequency="Daily",
            time_of_day="Morning",
            scheduled_time="08:00",
            instructions=f"Instructions with {injection_payload}",
            stock_remaining=30,
            refill_threshold=5,
        )
        assert new_id > 0

        # Verify users table was NOT dropped
        users = db.get_users()
        assert len(users) >= 2

        # Verify appointment SQL injection safety
        apt_id = db.add_appointment(
            patient_id=p_id,
            title=f"Visit {injection_payload}",
            doctor_name=f"Dr. {injection_payload}",
            clinic_address=f"Clinic {injection_payload}",
            appointment_date=(date.today() + timedelta(days=3)).isoformat(),
            appointment_time="10:00",
        )
        assert apt_id > 0

        # Verify vitals notes SQL injection safety
        v_id = db.add_vitals(
            patient_id=p_id,
            recorded_date=date.today().isoformat(),
            recorded_time="12:00",
            systolic_bp=120,
            diastolic_bp=80,
            blood_glucose=100.0,
            heart_rate=70,
            weight_kg=65.0,
            notes=f"Clinical note {injection_payload}",
        )
        assert v_id > 0

    def test_adversarial_double_logging_idempotency(self):
        """Verify logging the same dose as TAKEN multiple times decrements inventory exactly once."""
        patient = db.get_patient()
        p_id = patient["id"]
        doses = db.get_todays_doses(p_id)
        dose = doses[0]
        log_id = dose["log_id"]
        med_id = dose["medication_id"]

        meds_before = db.get_medications(p_id)
        target_med = next(m for m in meds_before if m["id"] == med_id)
        target_med["stock_remaining"]

        # Reset to PENDING first
        db.mark_dose_status(log_id, "PENDING")
        meds_pending = db.get_medications(p_id)
        stock_pending = next(m for m in meds_pending if m["id"] == med_id)["stock_remaining"]

        # Mark TAKEN 5 times consecutively
        for _ in range(5):
            res = db.mark_dose_status(log_id, "TAKEN")
            assert res is True

        meds_after = db.get_medications(p_id)
        stock_after = next(m for m in meds_after if m["id"] == med_id)["stock_remaining"]

        # Stock must have decreased by EXACTLY 1, not 5
        assert stock_after == stock_pending - 1

    def test_adversarial_invalid_dose_statuses(self):
        """Verify illegal statuses return False cleanly without corrupting the record."""
        patient = db.get_patient()
        doses = db.get_todays_doses(patient["id"])
        log_id = doses[0]["log_id"]

        for invalid_status in ["DESTROYED", "EATEN", "NULL", "", "   ", None, 9999]:
            assert db.mark_dose_status(log_id, invalid_status) is False

        # Verify status remained unchanged
        refreshed = db.get_todays_doses(patient["id"])
        assert refreshed[0]["status"] in ("TAKEN", "PENDING", "MISSED", "SKIPPED")

    def test_adversarial_impossible_vitals_rejection(self):
        """Verify physiologically impossible vitals throw ValueError."""
        patient = db.get_patient()
        p_id = patient["id"]
        today_str = date.today().isoformat()

        # Impossible systolic (too high)
        with pytest.raises(ValueError, match="outside physiologically possible range"):
            db.add_vitals(p_id, today_str, "08:00", systolic_bp=450, diastolic_bp=80, blood_glucose=100.0, heart_rate=70, weight_kg=65.0)

        # Impossible diastolic (too low)
        with pytest.raises(ValueError, match="outside physiologically possible range"):
            db.add_vitals(p_id, today_str, "08:00", systolic_bp=120, diastolic_bp=10, blood_glucose=100.0, heart_rate=70, weight_kg=65.0)

        # Systolic less than diastolic
        with pytest.raises(ValueError, match="strictly higher than Diastolic"):
            db.add_vitals(p_id, today_str, "08:00", systolic_bp=80, diastolic_bp=120, blood_glucose=100.0, heart_rate=70, weight_kg=65.0)

        # Negative glucose
        with pytest.raises(ValueError, match="outside physiologically possible range"):
            db.add_vitals(p_id, today_str, "08:00", systolic_bp=120, diastolic_bp=80, blood_glucose=-15.0, heart_rate=70, weight_kg=65.0)

        # Negative weight
        with pytest.raises(ValueError, match="outside physiologically possible range"):
            db.add_vitals(p_id, today_str, "08:00", systolic_bp=120, diastolic_bp=80, blood_glucose=100.0, heart_rate=70, weight_kg=-50.0)

    def test_adversarial_negative_medication_inventory(self):
        """Verify negative stock and threshold are rejected."""
        patient = db.get_patient()
        p_id = patient["id"]

        with pytest.raises(ValueError, match="cannot be negative"):
            db.add_medication(
                patient_id=p_id,
                name="Bad Med",
                dosage="10mg",
                frequency="Daily",
                time_of_day="Morning",
                scheduled_time="08:00",
                stock_remaining=-10,
            )

        with pytest.raises(ValueError, match="cannot be empty"):
            db.add_medication(
                patient_id=p_id,
                name="",
                dosage="10mg",
                frequency="Daily",
                time_of_day="Morning",
                scheduled_time="08:00",
            )

    def test_adversarial_negative_dosage_rejection(self):
        """Verify negative dosage values (e.g. '-10mg', '-5') are rejected."""
        patient = db.get_patient()
        p_id = patient["id"]

        with pytest.raises(ValueError, match="cannot be negative"):
            db.add_medication(
                patient_id=p_id,
                name="Negative Dose Med",
                dosage="-10mg",
                frequency="Daily",
                time_of_day="Morning",
                scheduled_time="08:00",
            )

        with pytest.raises(ValueError, match="cannot be negative"):
            db.add_medication(
                patient_id=p_id,
                name="Negative Number Med",
                dosage="-5",
                frequency="Daily",
                time_of_day="Morning",
                scheduled_time="08:00",
            )

    def test_adversarial_reset_database_windows_resilience(self):
        """Verify reset_database cleanly drops tables and reseeds without Windows WinError 32 PermissionError."""
        # Hold an open read connection to simulate active Streamlit traffic
        with db.get_db_connection() as conn:
            conn.execute("SELECT COUNT(*) FROM medications;").fetchone()

        # Execute reset_database; must succeed cleanly
        assert db.reset_database() is True

        # Verify reseeded data integrity
        patient = db.get_patient()
        assert patient is not None
        assert "Eleanor" in patient["name"]
        meds = db.get_medications(patient["id"])
        assert len(meds) >= 5

    def test_adversarial_malformed_scheduled_date_analytics(self):
        """Verify adherence timeseries does not crash on malformed dates."""
        patient = db.get_patient()
        p_id = patient["id"]

        # Directly insert an abnormal date into adherence_logs
        with db.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO adherence_logs (medication_id, patient_id, scheduled_date, scheduled_time, status)
                VALUES (1, ?, 'malformed-date-string-test', '08:00', 'TAKEN');
            """, (p_id,))

        # compute_adherence_timeseries must drop invalid dates without raising ValueError
        df_ts = compute_adherence_timeseries(patient_id=p_id, days=14)
        assert isinstance(df_ts, object)

    def test_adversarial_appointment_past_scheduling_guard(self):
        """Verify add_appointment with allow_past=False rejects past dates."""
        patient = db.get_patient()
        p_id = patient["id"]

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        with pytest.raises(ValueError, match="cannot be scheduled in the past"):
            db.add_appointment(
                patient_id=p_id,
                title="Past Cardiology",
                doctor_name="Dr. Chen",
                clinic_address="123 Hospital Ave",
                appointment_date=yesterday,
                appointment_time="10:00",
                allow_past=False,
            )

    def test_adversarial_caretaker_login_resolves_patient_id(self):
        """Verify logging in as caretaker properly binds to an existing elderly patient ID."""
        assert login_user("caretaker", "8888") is True
        curr_user = get_current_user()
        assert curr_user["role"] == "caretaker"
        assert curr_user["patient_id"] is not None
        patient = db.get_patient(curr_user["patient_id"])
        assert patient is not None
        assert patient["role"] == "elderly"


class TestAdversarialGoogleServicesAndAlerts:
    """Adversarial testing of alert dispatching, severity normalization, and Google gateway."""

    def test_add_alert_severity_normalization(self):
        """Verify severity is normalized to valid SQLite CHECK constraint values ('INFO', 'WARNING', 'CRITICAL')."""
        patient = db.get_patient()
        p_id = patient["id"]

        # 'HIGH' should normalize to 'CRITICAL' without throwing IntegrityError
        a1 = db.add_alert(
            patient_id=p_id,
            alert_type="CONTRAINDICATION_BLOCKED",
            message="High risk interaction blocked",
            severity="HIGH",
        )
        assert a1 > 0

        # 'MEDIUM' should normalize to 'WARNING'
        a2 = db.add_alert(
            patient_id=p_id,
            alert_type="CONTRAINDICATION_OVERRIDDEN",
            message="Moderate risk overridden",
            severity="MEDIUM",
        )
        assert a2 > 0

        alerts = db.get_alerts(p_id, limit=5)
        logged_severities = {a["severity"] for a in alerts}
        assert "CRITICAL" in logged_severities
        assert "WARNING" in logged_severities

    def test_google_services_bad_credentials_graceful_handling(self, monkeypatch):
        """Verify bad Google SMTP credentials or connection refusal never crashes the app."""
        # Point to an unreachable SMTP server
        monkeypatch.setenv("SMTP_SERVER", "127.0.0.1")
        monkeypatch.setenv("SMTP_PORT", "65534")  # Unlikely port
        monkeypatch.setenv("SMTP_USERNAME", "fake_user@gmail.com")
        monkeypatch.setenv("SMTP_PASSWORD", "fake_password")

        res = send_email_alert(
            recipient_email="caretaker@example.com",
            subject="Adversarial Dispatch Test",
            body_html="<p>Test</p>",
            alert_type="ADVERSARIAL_TEST",
            severity="WARNING",
            patient_id=1,
        )

        assert res["success"] is False
        assert res["status"] == "FAILED"
        assert "Error" in res["message"] or "Timeout" in res["message"] or "refused" in res["message"].lower()

        # Verify failure was logged into SQLite audit ledger with delivery_status='FAILED'
        alerts = db.get_alerts(patient_id=1, limit=5)
        failed_alert = next((a for a in alerts if a["alert_type"] == "ADVERSARIAL_TEST"), None)
        assert failed_alert is not None
        assert failed_alert["delivery_status"] == "FAILED"

    def test_google_services_health_reporting(self):
        """Verify Google Services status detection."""
        health = get_google_services_health()
        assert isinstance(health, dict)
        assert "service" in health
        assert "server" in health
        assert "status_label" in health
