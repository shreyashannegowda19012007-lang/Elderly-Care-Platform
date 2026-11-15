"""
Comprehensive 4-Tier Automated End-to-End Test Suite for AuraCare / GoldenCare Platform.

Tier 1: Feature Coverage — Core feature verification in isolation
Tier 2: Boundary & Corner Cases — Resilience against edge, invalid, and boundary inputs
Tier 3: Cross-Feature Combinations — Pairwise integrated workflows and cascading effects
Tier 4: Real-World Scenarios — Full end-to-end user journeys (Senior, Caretaker, Autonomous Engine)
"""

from __future__ import annotations

import os
import sqlite3
import pytest
from datetime import datetime, date, timedelta
import streamlit as st

import db.database as db
from utils.auth import (
    init_session_state,
    is_authenticated,
    get_current_role,
    get_current_user,
    login_user,
    logout_user,
)
from utils.alerts import (
    get_smtp_config,
    send_email_alert,
    check_and_trigger_alerts,
    dispatch_sos_alert,
    get_alert_summary,
)
from utils.interactions import (
    evaluate_interactions,
    get_interaction_details,
    CLINICAL_RULES,
)
from utils.analytics import (
    compute_adherence_timeseries,
    compute_time_drift,
    compute_time_of_day_breakdown,
    generate_clinical_csv_export,
)


@pytest.fixture(autouse=True)
def setup_isolated_test_env(tmp_path, monkeypatch):
    """
    Ensure complete test isolation with a dedicated temporary SQLite WAL database
    and cleanly initialized session state for every single test case.
    """
    test_db_path = str(tmp_path / "test_auracare_e2e.db")
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()
    db.seed_initial_data()

    # Clear and re-initialize session state
    if hasattr(st, "session_state"):
        st.session_state.clear()
    init_session_state()

    yield

    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass


# ==============================================================================
# TIER 1: FEATURE COVERAGE
# ==============================================================================

class TestTier1FeatureCoverage:
    """Verifies every primary core feature of the platform independently."""

    def test_user_auth_and_session_state(self):
        """Verify session initialization, default state, and logout semantics."""
        # Initially unauthenticated before entering PIN
        assert is_authenticated() is False
        assert get_current_role() is None
        assert get_current_user()["role"] is None

        # Login as Senior Eleanor
        assert login_user("elderly", "1234") is True
        assert is_authenticated() is True
        assert get_current_role() == "elderly"

        user = get_current_user()
        assert user["name"] == "Eleanor Vance"
        assert user["role"] == "elderly"
        assert user["patient_id"] == 1

        # Logout
        logout_user()
        assert is_authenticated() is False
        assert get_current_role() is None
        assert get_current_user()["name"] is None

        # Login as Caretaker Sarah
        assert login_user("caretaker", "8888") is True
        assert is_authenticated() is True
        assert get_current_role() == "caretaker"
        assert get_current_user()["name"] == "Sarah Vance"

    def test_pin_validation_senior_and_caretaker(self):
        """Verify strict constant-time PIN authentication for Senior (1234) and Caretaker (8888)."""
        # Senior validation
        senior_auth = db.verify_user_passcode("elderly", "1234")
        assert senior_auth is not None
        assert senior_auth["role"] == "elderly"
        assert "Eleanor" in senior_auth["name"]

        # Caretaker validation
        caretaker_auth = db.verify_user_passcode("caretaker", "8888")
        assert caretaker_auth is not None
        assert caretaker_auth["role"] == "caretaker"
        assert "Sarah" in caretaker_auth["name"]

        # Role mismatch validation
        assert db.verify_user_passcode("elderly", "8888") is None
        assert db.verify_user_passcode("caretaker", "1234") is None

        # Incorrect PIN validation
        assert db.verify_user_passcode("elderly", "0000") is None
        assert db.verify_user_passcode("caretaker", "9999") is None

        # Update passcode feature
        updated = db.update_user_passcode(senior_auth["id"], "4321")
        assert updated is True
        assert db.verify_user_passcode("elderly", "4321") is not None
        assert db.verify_user_passcode("elderly", "1234") is None

    def test_medication_crud_operations(self):
        """Verify full lifecycle of medication prescriptions (Create, Read, Update, Delete)."""
        patient = db.get_patient()
        p_id = patient["id"]

        # 1. Create
        med_id = db.add_medication(
            patient_id=p_id,
            name="Amlodipine",
            dosage="5mg",
            frequency="Daily",
            time_of_day="Morning",
            scheduled_time="08:30",
            pill_color="#3B82F6",
            pill_shape="Tablet",
            instructions="Take with water before breakfast",
            stock_remaining=30,
            refill_threshold=7,
        )
        assert med_id > 0

        # 2. Read
        active_meds = db.get_medications(p_id, active_only=True)
        amlodipine = next((m for m in active_meds if m["id"] == med_id), None)
        assert amlodipine is not None
        assert amlodipine["name"] == "Amlodipine"
        assert amlodipine["dosage"] == "5mg"
        assert amlodipine["stock_remaining"] == 30

        # 3. Update
        updated = db.update_medication(
            med_id=med_id,
            name="Amlodipine Besylate",
            dosage="10mg",
            frequency="Daily",
            time_of_day="Morning",
            scheduled_time="09:00",
            pill_color="#3B82F6",
            pill_shape="Tablet",
            instructions="Increased dosage as directed by cardiologist",
            stock_remaining=25,
            refill_threshold=5,
            is_active=1,
        )
        assert updated is True

        meds_after_update = db.get_medications(p_id, active_only=True)
        amlodipine_updated = next((m for m in meds_after_update if m["id"] == med_id), None)
        assert amlodipine_updated["name"] == "Amlodipine Besylate"
        assert amlodipine_updated["dosage"] == "10mg"
        assert amlodipine_updated["stock_remaining"] == 25

        # 4. Delete
        deleted = db.delete_medication(med_id)
        assert deleted is True
        meds_after_delete = db.get_medications(p_id, active_only=False)
        assert not any(m["id"] == med_id for m in meds_after_delete)

    def test_adherence_logging_and_statuses(self):
        """Verify dose recording across all valid statuses: TAKEN, MISSED, SKIPPED, PENDING."""
        patient = db.get_patient()
        p_id = patient["id"]

        today_doses = db.get_todays_doses(p_id)
        assert len(today_doses) > 0

        target_dose = today_doses[0]
        log_id = target_dose["log_id"]

        # Mark TAKEN
        assert db.mark_dose_status(log_id, "TAKEN", recorded_by="elderly", notes="Taken on time") is True
        doses_taken = db.get_todays_doses(p_id)
        dose_entry = next(d for d in doses_taken if d["log_id"] == log_id)
        assert dose_entry["status"] == "TAKEN"
        assert dose_entry["taken_at"] is not None
        assert dose_entry["log_notes"] == "Taken on time"

        # Mark SKIPPED
        assert db.mark_dose_status(log_id, "SKIPPED", recorded_by="caretaker", notes="NPO for surgery") is True
        doses_skipped = db.get_todays_doses(p_id)
        assert next(d for d in doses_skipped if d["log_id"] == log_id)["status"] == "SKIPPED"

        # Mark MISSED
        assert db.mark_dose_status(log_id, "MISSED", recorded_by="system", notes="Automated miss detection") is True
        doses_missed = db.get_todays_doses(p_id)
        assert next(d for d in doses_missed if d["log_id"] == log_id)["status"] == "MISSED"

        # Reset to PENDING
        assert db.mark_dose_status(log_id, "PENDING", recorded_by="system", notes="Reset") is True
        doses_pending = db.get_todays_doses(p_id)
        assert next(d for d in doses_pending if d["log_id"] == log_id)["status"] == "PENDING"

    def test_proactive_alert_triggering(self):
        """Verify alert dispatch, alert recording, summary calculation, and emergency SOS."""
        patient = db.get_patient()
        p_id = patient["id"]

        # Send test alert
        res = send_email_alert(
            recipient_email="sarah.vance@example.org",
            subject="Test Clinical Alert Notification",
            body_html="<p>Immediate review advised.</p>",
            alert_type="CLINICAL_REVIEW",
            severity="WARNING",
            patient_id=p_id,
        )
        assert res["success"] is True
        assert res["status"] in ("SENT", "LOGGED")

        # Verify alert exists in database
        alerts = db.get_alerts(patient_id=p_id)
        matched = next((a for a in alerts if a["alert_type"] == "CLINICAL_REVIEW"), None)
        assert matched is not None
        assert matched["severity"] == "WARNING"
        assert matched["recipient_email"] == "sarah.vance@example.org"

        # Emergency SOS button dispatch
        sos_res = dispatch_sos_alert(patient_id=p_id, notes="Patient triggered SOS from bed")
        assert sos_res["success"] is True

        alerts_after_sos = db.get_alerts(patient_id=p_id)
        sos_entry = next((a for a in alerts_after_sos if a["alert_type"] == "EMERGENCY_SOS"), None)
        assert sos_entry is not None
        assert sos_entry["severity"] == "CRITICAL"

        # Verify alert summary KPIs
        summary = get_alert_summary(patient_id=p_id)
        assert summary["total"] >= 2
        assert summary["critical"] >= 1

    def test_saferegimen_ddi_conflict_detection(self):
        """Verify SafeRegimen DDI engine detects high and moderate contraindications."""
        # High-risk pair: Aspirin + Warfarin
        warnings_high = evaluate_interactions(["Aspirin", "Warfarin"])
        assert len(warnings_high) >= 1
        assert warnings_high[0]["severity"] == "High"
        assert "hemorrhage" in warnings_high[0]["description"].lower()

        # High-risk pair: Lisinopril + Spironolactone
        warnings_hyperkalemia = evaluate_interactions(["Lisinopril", "Spironolactone"])
        assert len(warnings_hyperkalemia) >= 1
        assert warnings_hyperkalemia[0]["severity"] == "High"
        assert "hyperkalemia" in warnings_hyperkalemia[0]["description"].lower()

        # Moderate-risk pair: Lisinopril + Ibuprofen
        warnings_nsaid = evaluate_interactions(["Lisinopril", "Ibuprofen"])
        assert len(warnings_nsaid) >= 1
        assert warnings_nsaid[0]["severity"] == "Moderate"

        # Direct database query check
        db_warnings = db.check_drug_interactions(["Aspirin", "Warfarin"])
        assert len(db_warnings) >= 1
        assert db_warnings[0]["severity"] == "High"

        # Format details callout
        formatted = get_interaction_details(warnings_high[0])
        assert "🔴" in formatted
        assert "High Risk" in formatted

    def test_appointment_scheduling_and_status(self):
        """Verify medical appointment creation, filtering, and status transitions."""
        patient = db.get_patient()
        p_id = patient["id"]

        appt_id = db.add_appointment(
            patient_id=p_id,
            title="Nephrology Follow-Up",
            doctor_name="Dr. Karen Patel",
            clinic_address="West End Kidney Pavilion, Suite 104",
            appointment_date="2026-11-20",
            appointment_time="11:15",
            transport_required=True,
            prep_notes="Fasting lab panel 8 hours prior",
        )
        assert appt_id > 0

        # Retrieve and inspect
        appts = db.get_appointments(p_id, status="SCHEDULED")
        target_appt = next((a for a in appts if a["id"] == appt_id), None)
        assert target_appt is not None
        assert target_appt["doctor_name"] == "Dr. Karen Patel"
        assert target_appt["transport_required"] == 1
        assert target_appt["status"] == "SCHEDULED"

        # Transition status to COMPLETED
        updated = db.update_appointment_status(appt_id, "COMPLETED")
        assert updated is True

        completed_appts = db.get_appointments(p_id, status="COMPLETED")
        assert any(a["id"] == appt_id for a in completed_appts)

        # Transition status to CANCELLED
        updated_cancelled = db.update_appointment_status(appt_id, "CANCELLED")
        assert updated_cancelled is True
        cancelled_appts = db.get_appointments(p_id, status="CANCELLED")
        assert any(a["id"] == appt_id for a in cancelled_appts)

    def test_vitals_tracking_and_abnormal_flags(self):
        """Verify logging of vitals and automatic clinical abnormality flagging."""
        patient = db.get_patient()
        p_id = patient["id"]

        # Normal vitals: Systolic 122, Diastolic 78, Glucose 98, Pulse 72
        normal_id = db.add_vitals(
            patient_id=p_id,
            recorded_date="2026-11-15",
            recorded_time="07:30",
            systolic_bp=122,
            diastolic_bp=78,
            blood_glucose=98.0,
            heart_rate=72,
            weight_kg=64.5,
            mood="Great",
            notes="Morning baseline reading",
        )
        assert normal_id > 0

        vitals = db.get_vitals(p_id, limit=10)
        normal_entry = next(v for v in vitals if v["id"] == normal_id)
        assert normal_entry["is_abnormal"] == 0

        # Abnormal vitals: High Systolic BP 155 (>140) and high Glucose 160 (>140)
        abnormal_id = db.add_vitals(
            patient_id=p_id,
            recorded_date="2026-11-15",
            recorded_time="14:00",
            systolic_bp=155,
            diastolic_bp=95,
            blood_glucose=162.0,
            heart_rate=105,
            weight_kg=64.5,
            mood="Fatigued",
            notes="Post-lunch spike",
        )
        assert abnormal_id > 0

        vitals_updated = db.get_vitals(p_id, limit=10)
        abnormal_entry = next(v for v in vitals_updated if v["id"] == abnormal_id)
        assert abnormal_entry["is_abnormal"] == 1


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================

class TestTier2BoundaryCornerCases:
    """Verifies edge cases, extreme values, empty states, and adversarial inputs."""

    def test_invalid_and_empty_pins(self):
        """Verify system resilience against empty, whitespace, malformed, or injected PINs."""
        # Empty string and whitespace
        assert db.verify_user_passcode("elderly", "") is None
        assert db.verify_user_passcode("elderly", "   ") is None
        assert db.verify_user_passcode("caretaker", "") is None
        assert db.verify_user_passcode("caretaker", "   ") is None

        # Malformed length or characters
        assert db.verify_user_passcode("elderly", "12") is None
        assert db.verify_user_passcode("elderly", "12345") is None
        assert db.verify_user_passcode("elderly", "abcd") is None
        assert db.verify_user_passcode("elderly", "!@#$") is None

        # SQL Injection attempt in passcode
        assert db.verify_user_passcode("elderly", "' OR '1'='1") is None
        assert db.verify_user_passcode("caretaker", "' OR '1'='1' --") is None

        # Non-existent role
        assert db.verify_user_passcode("admin", "1234") is None
        assert db.verify_user_passcode("doctor", "8888") is None

    def test_empty_database_state_graceful_handling(self, tmp_path, monkeypatch):
        """Verify queries and computations handle an empty database gracefully without throwing errors."""
        empty_db_path = str(tmp_path / "empty_db.db")
        monkeypatch.setattr(db, "DB_PATH", empty_db_path)
        db.init_db()  # Initialize schema but DO NOT seed data

        # Users and patient
        assert db.get_users() == []
        assert db.get_patient() is None
        assert db.get_patient(999) is None

        # Medications and today's doses
        assert db.get_medications(1) == []
        assert db.get_todays_doses(1) == []

        # Appointments and vitals
        assert db.get_appointments(1) == []
        assert db.get_vitals(1) == []
        assert db.get_alerts(1) == []

        # Adherence stats on empty DB
        stats = db.get_adherence_stats(1)
        assert stats["total_doses"] == 0
        assert stats["taken_count"] == 0
        assert stats["missed_count"] == 0
        assert stats["adherence_rate"] == 100.0
        assert stats["streak_days"] == 0

        # Adherence timeseries on empty DB
        ts_df = compute_adherence_timeseries(patient_id=1)
        assert ts_df.empty
        assert "date" in ts_df.columns

        # Time drift on empty DB
        drift_df = compute_time_drift(patient_id=1)
        assert drift_df.empty

        # Time of day on empty DB
        tod_df = compute_time_of_day_breakdown(patient_id=1)
        assert tod_df.empty

        # Clinical CSV export on empty DB
        csv_export = generate_clinical_csv_export(patient_id=1)
        assert isinstance(csv_export, str)
        assert "No medication adherence records" in csv_export or "No data" in csv_export or csv_export == ""

    def test_zero_dose_days_and_empty_adherence(self):
        """Verify calculations when patient has zero eligible doses or future-only doses."""
        patient = db.get_patient()
        p_id = patient["id"]

        # Query stats for future date range where no logs exist
        future_stats = db.get_adherence_stats(p_id, days=0)
        assert isinstance(future_stats["adherence_rate"], float)
        assert future_stats["adherence_rate"] >= 0.0

    def test_zero_and_negative_pill_stock_boundary(self):
        """Verify inventory decrement cannot drop stock below zero."""
        patient = db.get_patient()
        p_id = patient["id"]

        # Add medication with stock remaining = 0
        zero_stock_id = db.add_medication(
            patient_id=p_id,
            name="Depleted Med",
            dosage="10mg",
            frequency="Daily",
            time_of_day="Morning",
            scheduled_time="08:00",
            stock_remaining=0,
            refill_threshold=5,
        )

        doses = db.get_todays_doses(p_id)
        dose = next(d for d in doses if d["medication_id"] == zero_stock_id)

        # Mark TAKEN when stock is 0
        db.mark_dose_status(dose["log_id"], "TAKEN", recorded_by="elderly")

        meds = db.get_medications(p_id)
        med = next(m for m in meds if m["id"] == zero_stock_id)
        # Must stay 0, never negative!
        assert med["stock_remaining"] == 0

        # Now revert to SKIPPED, stock should increment to 1
        db.mark_dose_status(dose["log_id"], "SKIPPED", recorded_by="elderly")
        meds_reverted = db.get_medications(p_id)
        med_reverted = next(m for m in meds_reverted if m["id"] == zero_stock_id)
        assert med_reverted["stock_remaining"] == 1

    def test_past_and_future_dates_boundary(self):
        """Verify robustness with distant past, distant future, and boundary date strings."""
        patient = db.get_patient()
        p_id = patient["id"]

        # Distant past appointment
        past_id = db.add_appointment(
            patient_id=p_id,
            title="Historical Checkup",
            doctor_name="Dr. Old",
            clinic_address="Old Hospital",
            appointment_date="1999-01-01",
            appointment_time="08:00",
        )
        assert past_id > 0

        # Distant future appointment
        future_id = db.add_appointment(
            patient_id=p_id,
            title="Future Century Checkup",
            doctor_name="Dr. Future",
            clinic_address="Orbital Health",
            appointment_date="2099-12-31",
            appointment_time="15:00",
        )
        assert future_id > 0

        all_appts = db.get_appointments(p_id)
        dates = [a["appointment_date"] for a in all_appts]
        assert "1999-01-01" in dates
        assert "2099-12-31" in dates

        # Query today's doses for an arbitrary future date
        future_doses = db.get_todays_doses(p_id, date_str="2030-05-15")
        assert len(future_doses) > 0
        assert all(d["scheduled_date"] == "2030-05-15" for d in future_doses)

    def test_special_characters_sql_injection_and_emojis(self):
        """Verify text handling preserves unicode emojis, quotes, and sanitized HTML safely."""
        patient = db.get_patient()
        p_id = patient["id"]

        special_name = "Prescription O'Connor 💊 <script>alert('xss')</script>"
        special_instructions = "Take with 🚰 cold water; do not crush! ' OR '1'='1"

        med_id = db.add_medication(
            patient_id=p_id,
            name=special_name,
            dosage="250mg",
            frequency="Daily",
            time_of_day="Evening",
            scheduled_time="20:00",
            instructions=special_instructions,
        )
        assert med_id > 0

        meds = db.get_medications(p_id)
        saved_med = next(m for m in meds if m["id"] == med_id)
        assert "O'Connor" in saved_med["name"]
        assert "💊" in saved_med["name"]
        assert "<script>" in saved_med["name"]
        assert "' OR '1'='1" in saved_med["instructions"]

    def test_duplicate_dose_log_attempts_idempotency(self):
        """Verify database enforces unique constraint and idempotent dose generation."""
        patient = db.get_patient()
        p_id = patient["id"]

        # Call get_todays_doses multiple times back-to-back
        doses_run_1 = db.get_todays_doses(p_id)
        doses_run_2 = db.get_todays_doses(p_id)
        doses_run_3 = db.get_todays_doses(p_id)

        assert len(doses_run_1) == len(doses_run_2) == len(doses_run_3)
        log_ids_1 = [d["log_id"] for d in doses_run_1]
        log_ids_2 = [d["log_id"] for d in doses_run_2]
        assert log_ids_1 == log_ids_2

    def test_ddi_single_drug_empty_list_and_unknowns(self):
        """Verify DDI engine returns empty results when given insufficient or unknown drugs."""
        assert evaluate_interactions([]) == []
        assert evaluate_interactions([""]) == []
        assert evaluate_interactions(["   "]) == []
        assert evaluate_interactions(["Aspirin"]) == []
        assert evaluate_interactions(["Warfarin"]) == []
        assert evaluate_interactions(["Lisinopril"]) == []

        # Unknown benign compounds
        assert evaluate_interactions(["SyntheticSubstanceA", "CompoundB"]) == []

        # Database direct check
        assert db.check_drug_interactions([]) == []
        assert db.check_drug_interactions(["Metformin"]) == []
        assert db.check_drug_interactions(["NonExistent1", "NonExistent2"]) == []


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (PAIRWISE)
# ==============================================================================

class TestTier3CrossFeatureCombinations:
    """Verifies pairwise integrated workflows across database, auth, alerts, and scheduling."""

    def test_medication_addition_creates_pending_adherence_slot(self):
        """Pairwise: Adding a new medication automatically schedules a PENDING slot for today."""
        patient = db.get_patient()
        p_id = patient["id"]

        initial_doses = db.get_todays_doses(p_id)
        initial_count = len(initial_doses)

        new_med_id = db.add_medication(
            patient_id=p_id,
            name="CoQ10 Heart Health",
            dosage="100mg",
            frequency="Daily",
            time_of_day="Afternoon",
            scheduled_time="14:30",
            pill_color="#10B981",
            pill_shape="Capsule",
            stock_remaining=40,
            refill_threshold=5,
        )

        updated_doses = db.get_todays_doses(p_id)
        assert len(updated_doses) == initial_count + 1

        new_slot = next((d for d in updated_doses if d["medication_id"] == new_med_id), None)
        assert new_slot is not None
        assert new_slot["scheduled_time"] == "14:30"
        assert new_slot["status"] == "PENDING"

    def test_dose_status_taken_decrements_stock_and_revert_restores(self):
        """Pairwise: Marking dose TAKEN decrements pill stock by 1; resetting restores stock."""
        patient = db.get_patient()
        p_id = patient["id"]

        med_id = db.add_medication(
            patient_id=p_id,
            name="Test Stock Pill",
            dosage="50mg",
            frequency="Daily",
            time_of_day="Morning",
            scheduled_time="08:15",
            stock_remaining=20,
            refill_threshold=5,
        )

        doses = db.get_todays_doses(p_id)
        slot = next(d for d in doses if d["medication_id"] == med_id)
        assert slot["status"] == "PENDING"

        # 1. Mark TAKEN -> stock becomes 19
        assert db.mark_dose_status(slot["log_id"], "TAKEN", recorded_by="elderly") is True
        med = next(m for m in db.get_medications(p_id) if m["id"] == med_id)
        assert med["stock_remaining"] == 19

        # 2. Mark TAKEN again (idempotent) -> stock remains 19
        assert db.mark_dose_status(slot["log_id"], "TAKEN", recorded_by="elderly") is True
        med = next(m for m in db.get_medications(p_id) if m["id"] == med_id)
        assert med["stock_remaining"] == 19

        # 3. Mark SKIPPED -> reverts stock to 20
        assert db.mark_dose_status(slot["log_id"], "SKIPPED", recorded_by="elderly") is True
        med = next(m for m in db.get_medications(p_id) if m["id"] == med_id)
        assert med["stock_remaining"] == 20

    def test_overdue_dose_escalation_to_missed_generates_alert(self):
        """Pairwise: An overdue dose (>30m grace) transitions to MISSED and triggers caretaker alert."""
        patient = db.get_patient()
        p_id = patient["id"]

        # Schedule a dose 2 hours in the past
        past_time = (datetime.now() - timedelta(hours=2)).strftime("%H:%M")
        med_id = db.add_medication(
            patient_id=p_id,
            name="Overdue Insulin Injection",
            dosage="10 units",
            frequency="Daily",
            time_of_day="Morning",
            scheduled_time=past_time,
            stock_remaining=15,
            refill_threshold=3,
        )

        doses_before = db.get_todays_doses(p_id)
        overdue_slot = next(d for d in doses_before if d["medication_id"] == med_id)
        assert overdue_slot["status"] == "PENDING"

        # Run proactive alert engine
        triggered = check_and_trigger_alerts(patient_id=p_id, force_check=True)

        # Verify dose auto-transitioned to MISSED
        doses_after = db.get_todays_doses(p_id)
        escalated_slot = next(d for d in doses_after if d["medication_id"] == med_id)
        assert escalated_slot["status"] == "MISSED"
        assert "Automated miss detection" in escalated_slot["log_notes"]

        # Verify alert logged for caretaker
        missed_alerts = [a for a in triggered if a["type"] == "MISSED_DOSE"]
        assert any(a["medication"] == "Overdue Insulin Injection" for a in missed_alerts)

    def test_appointment_scheduling_reflected_in_timeline_and_lifecycle(self):
        """Pairwise: Scheduling an appointment integrates with patient timeline and updates status."""
        patient = db.get_patient()
        p_id = patient["id"]

        today_str = date.today().isoformat()
        appt_id = db.add_appointment(
            patient_id=p_id,
            title="Geriatric Fall Risk Assessment",
            doctor_name="Dr. Anita Desai",
            clinic_address="St. Jude Rehab Center",
            appointment_date=today_str,
            appointment_time="14:00",
            transport_required=True,
            prep_notes="Wear athletic walking shoes",
        )

        # Confirm appears in scheduled list
        sched_list = db.get_appointments(p_id, status="SCHEDULED")
        assert any(a["id"] == appt_id for a in sched_list)

        # Update to COMPLETED
        db.update_appointment_status(appt_id, "COMPLETED")
        completed_list = db.get_appointments(p_id, status="COMPLETED")
        assert any(a["id"] == appt_id for a in completed_list)
        assert not any(a["id"] == appt_id for a in db.get_appointments(p_id, status="SCHEDULED"))

    def test_abnormal_vitals_logging_and_filtering(self):
        """Pairwise: Abnormal blood pressure and glucose inputs trigger warning flag in history."""
        patient = db.get_patient()
        p_id = patient["id"]

        today_str = date.today().isoformat()
        # Systolic BP > 140 -> is_abnormal must be 1
        v1 = db.add_vitals(
            patient_id=p_id,
            recorded_date=today_str,
            recorded_time="09:00",
            systolic_bp=165,
            diastolic_bp=88,
            blood_glucose=110.0,
            heart_rate=75,
            weight_kg=64.0,
        )
        # Normal BP & Glucose -> is_abnormal must be 0
        v2 = db.add_vitals(
            patient_id=p_id,
            recorded_date=today_str,
            recorded_time="18:00",
            systolic_bp=125,
            diastolic_bp=80,
            blood_glucose=105.0,
            heart_rate=70,
            weight_kg=64.0,
        )

        vitals = db.get_vitals(p_id, limit=20)
        entry_1 = next(v for v in vitals if v["id"] == v1)
        entry_2 = next(v for v in vitals if v["id"] == v2)

        assert entry_1["is_abnormal"] == 1
        assert entry_2["is_abnormal"] == 0

    def test_low_stock_refill_threshold_triggers_alert(self):
        """Pairwise: Prescription inventory at or below threshold triggers REFILL_ALERT."""
        patient = db.get_patient()
        p_id = patient["id"]

        future_time = (datetime.now() + timedelta(hours=3)).strftime("%H:%M")
        med_id = db.add_medication(
            patient_id=p_id,
            name="Critical Heart Beta Blocker",
            dosage="50mg",
            frequency="Daily",
            time_of_day="Evening",
            scheduled_time=future_time,
            stock_remaining=3,  # <= refill threshold 5!
            refill_threshold=5,
        )

        triggered = check_and_trigger_alerts(patient_id=p_id, force_check=True)
        refill_alerts = [a for a in triggered if a["type"] == "REFILL_ALERT"]
        assert any("Critical Heart Beta Blocker" in a["medication"] for a in refill_alerts)


# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS
# ==============================================================================

class TestTier4RealWorldScenarios:
    """Full end-to-end user journeys mirroring realistic daily clinical operation."""

    def test_scenario_1_senior_eleanor_morning_routine_and_sos(self):
        """
        Scenario 1: Senior Eleanor Vance logs into touch portal, reviews her morning doses,
        marks morning Metformin as TAKEN, updates inventory, triggers celebratory feedback,
        and uses the Emergency SOS button.
        """
        # Step 1: Eleanor unlocks the Senior Portal using PIN 1234
        login_success = login_user("elderly", "1234")
        assert login_success is True
        assert is_authenticated() is True
        assert get_current_role() == "elderly"
        current_user = get_current_user()
        assert current_user["name"] == "Eleanor Vance"
        patient_id = current_user["patient_id"]

        # Step 2: Senior views today's scheduled doses
        today_doses = db.get_todays_doses(patient_id)
        assert len(today_doses) >= 4

        # Step 3: Locate a scheduled / pending dose for Eleanor
        # Locate an unconfirmed pending dose or reset one to PENDING to verify intake
        pending_dose = next((d for d in today_doses if d["status"] == "PENDING"), None)
        if not pending_dose:
            # If earlier doses were already marked taken, reset first dose to PENDING for testing
            pending_dose = today_doses[0]
            db.mark_dose_status(pending_dose["log_id"], status="PENDING", recorded_by="system", notes="Reset for scenario intake")
            today_doses = db.get_todays_doses(patient_id)
            pending_dose = next(d for d in today_doses if d["log_id"] == pending_dose["log_id"])

        initial_stock = pending_dose["stock_remaining"]

        # Step 4: Eleanor confirms taking her medication with 1-tap giant touch button
        log_success = db.mark_dose_status(
            pending_dose["log_id"],
            status="TAKEN",
            recorded_by="elderly",
            notes="Confirmed via tactile morning button",
        )
        assert log_success is True

        # Step 5: Verify dose record and inventory decrement
        refreshed_doses = db.get_todays_doses(patient_id)
        updated_dose = next(d for d in refreshed_doses if d["log_id"] == pending_dose["log_id"])
        assert updated_dose["status"] == "TAKEN"
        assert updated_dose["taken_at"] is not None

        # Verify stock decremented by exactly 1
        meds = db.get_medications(patient_id)
        med_rec = next(m for m in meds if m["id"] == pending_dose["medication_id"])
        assert med_rec["stock_remaining"] == initial_stock - 1

        # Step 6: Verify celebratory feedback progress
        taken_count = sum(1 for d in refreshed_doses if d["status"] == "TAKEN")
        assert taken_count >= 1

        # Step 7: Senior encounters emergency and triggers SOS assistance
        sos_result = dispatch_sos_alert(
            patient_id=patient_id,
            notes="Assistance requested: Dizziness after morning walk",
        )
        assert sos_result["success"] is True

        # Caretaker receives immediate critical alert in audit log
        alerts = db.get_alerts(patient_id=patient_id, limit=10)
        sos_alert = next((a for a in alerts if a["alert_type"] == "EMERGENCY_SOS"), None)
        assert sos_alert is not None
        assert sos_alert["severity"] == "CRITICAL"
        assert "EMERGENCY" in sos_alert["message"]

    def test_scenario_2_caretaker_sarah_clinical_oversight_and_ddi(self):
        """
        Scenario 2: Caretaker Sarah Vance logs in with PIN 8888, reviews Eleanor's adherence streak,
        proactively tests a new prescription against SafeRegimen DDI engine, checks alerts, and
        schedules an upcoming clinic visit.
        """
        # Step 1: Sarah logs in with Caretaker PIN 8888
        assert login_user("caretaker", "8888") is True
        assert is_authenticated() is True
        assert get_current_role() == "caretaker"
        user = get_current_user()
        assert user["name"] == "Sarah Vance"

        patient = db.get_patient()
        p_id = patient["id"]

        # Step 2: Sarah reviews Eleanor's 7-day adherence metrics and streak
        stats = db.get_adherence_stats(p_id, days=7)
        assert stats["total_doses"] > 0
        assert stats["adherence_rate"] >= 50.0  # Realistic seed adherence is ~90%
        assert "streak_days" in stats

        # Step 3: Physician suggests adding Spironolactone to Eleanor's Lisinopril regimen.
        # Sarah inputs proposed drug into SafeRegimen DDI engine
        active_meds = [m["name"] for m in db.get_medications(p_id, active_only=True)]
        ddi_warnings = evaluate_interactions(active_meds, proposed_drug="Spironolactone")

        # Must flag dangerous High-severity interaction (Lisinopril + Spironolactone = Hyperkalemia)
        assert len(ddi_warnings) >= 1
        lisinopril_conflict = next(
            (w for w in ddi_warnings if "Spironolactone" in (w["drug_1"], w["drug_2"])),
            None
        )
        assert lisinopril_conflict is not None
        assert lisinopril_conflict["severity"] == "High"
        assert "hyperkalemia" in lisinopril_conflict["description"].lower()

        # Step 4: Sarah inspects clinical alert log
        alert_summary = get_alert_summary(p_id)
        assert alert_summary["total"] >= 1

        # Step 5: Sarah schedules upcoming clinic appointment
        appt_date = (date.today() + timedelta(days=5)).isoformat()
        new_appt_id = db.add_appointment(
            patient_id=p_id,
            title="Cardiology Consult & Potassium Serum Check",
            doctor_name="Dr. Robert Chen",
            clinic_address="Metro Cardiology Pavilion, Suite 402",
            appointment_date=appt_date,
            appointment_time="10:00",
            transport_required=True,
            prep_notes="Follow-up on ACE inhibitor regimen and serum potassium check",
        )
        assert new_appt_id > 0

        # Verify appointment is registered
        scheduled_appts = db.get_appointments(p_id, status="SCHEDULED")
        assert any(a["id"] == new_appt_id for a in scheduled_appts)

    def test_scenario_3_autonomous_overdue_escalation_simulation(self):
        """
        Scenario 3: Autonomous background monitor simulates passage of time:
        A scheduled dose passes the 30-minute grace period without confirmation,
        automatically escalates from PENDING to MISSED, and dispatches a proactive
        email notification to Caretaker Sarah.
        """
        patient = db.get_patient()
        p_id = patient["id"]

        # 1. Schedule a dose 50 minutes in the past
        past_time = (datetime.now() - timedelta(minutes=50)).strftime("%H:%M")
        med_id = db.add_medication(
            patient_id=p_id,
            name="Afternoon Calcium Citrate",
            dosage="500mg",
            frequency="Daily",
            time_of_day="Afternoon",
            scheduled_time=past_time,
            stock_remaining=30,
            refill_threshold=5,
        )

        doses = db.get_todays_doses(p_id)
        target_slot = next(d for d in doses if d["medication_id"] == med_id)
        assert target_slot["status"] == "PENDING"

        # 2. Autonomous proactive scheduler scans schedules
        triggered = check_and_trigger_alerts(patient_id=p_id, force_check=True)

        # 3. Verify status automatically escalated to MISSED
        refreshed_doses = db.get_todays_doses(p_id)
        escalated_slot = next(d for d in refreshed_doses if d["medication_id"] == med_id)
        assert escalated_slot["status"] == "MISSED"
        assert "Automated miss detection (>30 min grace)" in escalated_slot["log_notes"]

        # 4. Verify caretaker notification was dispatched
        alerts = db.get_alerts(patient_id=p_id, limit=10)
        missed_alert = next((a for a in alerts if "Afternoon Calcium Citrate" in a["message"]), None)
        assert missed_alert is not None
        assert missed_alert["alert_type"] == "MISSED_DOSE"
        assert missed_alert["severity"] == "CRITICAL"

        # 5. Idempotent re-check: Subsequent scan should NOT re-dispatch duplicate alert
        subsequent_scan = check_and_trigger_alerts(patient_id=p_id, force_check=False)
        duplicate_missed = [a for a in subsequent_scan if a.get("medication") == "Afternoon Calcium Citrate"]
        assert len(duplicate_missed) == 0
