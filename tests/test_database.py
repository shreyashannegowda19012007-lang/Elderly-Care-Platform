"""
Unit and integration tests for database operations and schema integrity.
"""

import os
from datetime import date

import pytest

import db.database as db


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Use an isolated temporary SQLite database for testing."""
    test_db_path = str(tmp_path / "test_carecompanion.db")
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()
    db.seed_initial_data()
    yield
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except OSError:
            pass


def test_seed_data_integrity():
    """Verify default patients, caretakers, and medications are seeded."""
    users = db.get_users()
    assert len(users) >= 2
    roles = {u["role"] for u in users}
    assert "elderly" in roles
    assert "caretaker" in roles

    patient = db.get_patient()
    assert patient is not None
    assert "Eleanor" in patient["name"]

    meds = db.get_medications(patient["id"])
    assert len(meds) >= 5
    med_names = [m["name"] for m in meds]
    assert any("Lisinopril" in name for name in med_names)


def test_passcode_verification():
    """Verify correct and incorrect PIN checks."""
    user = db.verify_user_passcode("elderly", "1234")
    assert user is not None
    assert user["role"] == "elderly"

    caretaker = db.verify_user_passcode("caretaker", "8888")
    assert caretaker is not None
    assert caretaker["role"] == "caretaker"

    invalid = db.verify_user_passcode("elderly", "9999")
    assert invalid is None

    wrong_role = db.verify_user_passcode("caretaker", "1234")
    assert wrong_role is None


def test_add_and_update_medication():
    """Verify adding, updating, and inventory tracking for medications."""
    patient = db.get_patient()
    p_id = patient["id"]

    new_id = db.add_medication(
        patient_id=p_id,
        name="Vitamin C",
        dosage="500mg",
        frequency="Daily",
        time_of_day="Morning",
        scheduled_time="09:00",
        pill_color="#F59E0B",
        pill_shape="Tablet",
        instructions="Take with breakfast",
        stock_remaining=30,
        refill_threshold=5,
    )
    assert new_id > 0

    meds = db.get_medications(p_id)
    added = next((m for m in meds if m["id"] == new_id), None)
    assert added is not None
    assert added["name"] == "Vitamin C"
    assert added["stock_remaining"] == 30

    # Today's dose slot was automatically generated
    doses = db.get_todays_doses(p_id)
    dose_slot = next((d for d in doses if d["medication_id"] == new_id), None)
    assert dose_slot is not None
    assert dose_slot["status"] == "PENDING"

    # Mark dose as taken and verify inventory decrements
    success = db.mark_dose_status(dose_slot["log_id"], "TAKEN", recorded_by="elderly")
    assert success is True

    # Check updated medication stock
    updated_meds = db.get_medications(p_id)
    updated_added = next((m for m in updated_meds if m["id"] == new_id), None)
    assert updated_added["stock_remaining"] == 29


def test_adherence_statistics():
    """Verify adherence metrics computation."""
    patient = db.get_patient()
    p_id = patient["id"]

    stats = db.get_adherence_stats(p_id, days=14)
    assert stats["total_doses"] > 0
    assert stats["taken_count"] > 0
    assert 0 <= stats["adherence_rate"] <= 100.0


def test_appointments_and_vitals():
    """Verify appointment scheduling and abnormal vitals flagging."""
    patient = db.get_patient()
    p_id = patient["id"]

    # Appointment
    apt_id = db.add_appointment(
        patient_id=p_id,
        title="Dental Checkup",
        doctor_name="Dr. Smith",
        clinic_address="123 Dental Way",
        appointment_date=(date.today()).isoformat(),
        appointment_time="14:00",
        transport_required=True,
        prep_notes="Routine cleaning",
    )
    assert apt_id > 0

    apts = db.get_appointments(p_id, status="SCHEDULED")
    assert any(a["id"] == apt_id for a in apts)

    # Vitals - Normal
    v_norm = db.add_vitals(
        patient_id=p_id,
        recorded_date=date.today().isoformat(),
        recorded_time="08:00",
        systolic_bp=120,
        diastolic_bp=80,
        blood_glucose=100.0,
        heart_rate=70,
        weight_kg=65.0,
        mood="Great",
    )
    vitals_list = db.get_vitals(p_id)
    norm_entry = next((v for v in vitals_list if v["id"] == v_norm), None)
    assert norm_entry["is_abnormal"] == 0

    # Vitals - Abnormal
    v_abn = db.add_vitals(
        patient_id=p_id,
        recorded_date=date.today().isoformat(),
        recorded_time="16:00",
        systolic_bp=165,  # High!
        diastolic_bp=95,
        blood_glucose=180.0,
        heart_rate=105,
        weight_kg=65.0,
        mood="Dizzy",
    )
    vitals_list2 = db.get_vitals(p_id)
    abn_entry = next((v for v in vitals_list2 if v["id"] == v_abn), None)
    assert abn_entry["is_abnormal"] == 1

    # Verify abnormal vitals logged to alert center
    alerts = db.get_alerts(p_id)
    v_alert = next((a for a in alerts if a["alert_type"] == "ABNORMAL_VITALS"), None)
    assert v_alert is not None
    assert "Systolic BP 165" in v_alert["message"]


def test_reconcile_past_doses():
    """Verify unconfirmed past doses are transitioned to MISSED status."""
    from datetime import timedelta
    patient = db.get_patient()
    p_id = patient["id"]
    meds = db.get_medications(p_id)
    m_id = meds[0]["id"]

    past_date = (date.today() - timedelta(days=2)).isoformat()
    with db.get_db_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO adherence_logs (
                medication_id, patient_id, scheduled_date, scheduled_time, status, notes, recorded_by
            ) VALUES (?, ?, ?, '10:00', 'PENDING', 'Old unconfirmed', 'system');
        """, (m_id, p_id, past_date))

    count = db.reconcile_past_doses(p_id)
    assert count >= 1

    history = db.get_adherence_history(p_id, days=5)
    old_dose = next((h for h in history if h["scheduled_date"] == past_date and h["medication_id"] == m_id and h["scheduled_time"] == "10:00"), None)
    assert old_dose is not None
    assert old_dose["status"] == "MISSED"


def test_models_instantiation_and_serialization():
    """Verify dataclass domain models from db.models instantiate and serialize accurately."""
    from db.models import (
        AdherenceLog,
        Alert,
        AlertLog,
        Appointment,
        DrugInteraction,
        Medication,
        User,
        VitalsLog,
    )

    # User model
    u = User(name="Test User", role="elderly", passcode="1234", phone="555-0100")
    u_dict = u.to_dict()
    assert u_dict["name"] == "Test User"
    assert u_dict["role"] == "elderly"
    u_recreated = User.from_dict(u_dict)
    assert u_recreated.name == u.name

    # Medication model
    m = Medication(
        patient_id=1,
        name="Lisinopril",
        dosage="10mg",
        frequency="Daily",
        time_of_day="Morning",
        scheduled_time="08:00",
        stock_remaining=30,
    )
    m_dict = m.to_dict()
    assert m_dict["name"] == "Lisinopril"
    m_recreated = Medication.from_dict(m_dict)
    assert m_recreated.dosage == "10mg"

    # AdherenceLog model
    a = AdherenceLog(
        medication_id=1,
        patient_id=1,
        scheduled_date="2026-11-15",
        scheduled_time="08:00",
        status="TAKEN",
    )
    assert a.to_dict()["status"] == "TAKEN"
    assert AdherenceLog.from_dict(a.to_dict()).status == "TAKEN"

    # Appointment model
    apt = Appointment(
        patient_id=1,
        title="Cardiology Visit",
        doctor_name="Dr. Chen",
        clinic_address="100 Metro Way",
        appointment_date="2026-11-20",
        appointment_time="10:00",
    )
    assert apt.to_dict()["doctor_name"] == "Dr. Chen"
    assert Appointment.from_dict(apt.to_dict()).clinic_address == "100 Metro Way"

    # VitalsLog model
    v = VitalsLog(
        patient_id=1,
        recorded_date="2026-11-15",
        recorded_time="09:00",
        systolic_bp=120,
        diastolic_bp=80,
    )
    assert v.to_dict()["systolic_bp"] == 120
    assert VitalsLog.from_dict(v.to_dict()).diastolic_bp == 80

    # Alert / AlertLog model
    alt = Alert(
        patient_id=1,
        alert_type="MISSED_DOSE",
        severity="WARNING",
        message="Missed scheduled dose",
    )
    assert alt.to_dict()["severity"] == "WARNING"
    assert AlertLog == Alert

    # DrugInteraction model
    di = DrugInteraction(
        drug_a="Aspirin",
        drug_b="Warfarin",
        severity="High",
        description="Bleeding risk",
        recommendation="Monitor INR",
    )
    assert di.to_dict()["severity"] == "High"
    assert DrugInteraction.from_dict(di.to_dict()).drug_b == "Warfarin"


def test_modular_queries_and_init_exports():
    """Verify db package __init__.py cleanly re-exports all models and queries for full backward compatibility."""
    import db as db_pkg
    import db.queries as db_q

    # Verify query functions exist in db.queries
    assert callable(db_q.get_patient)
    assert callable(db_q.get_medications)
    assert callable(db_q.get_adherence_stats)
    assert callable(db_q.reconcile_past_doses)
    assert callable(db_q.add_vitals)

    # Verify query functions and models are re-exported by db root
    assert hasattr(db_pkg, "get_patient")
    assert hasattr(db_pkg, "get_medications")
    assert hasattr(db_pkg, "get_db_connection")
    assert hasattr(db_pkg, "init_db")
    assert hasattr(db_pkg, "log_adherence")
    assert hasattr(db_pkg, "record_dose_adherence")
    assert hasattr(db_pkg, "get_adherence_summary")
    assert hasattr(db_q, "log_adherence")
    assert hasattr(db_q, "record_dose_adherence")
    assert hasattr(db_q, "get_adherence_summary")
    assert hasattr(db, "log_adherence")
    assert hasattr(db, "record_dose_adherence")
    assert hasattr(db, "get_adherence_summary")
    assert hasattr(db_pkg, "User")
    assert hasattr(db_pkg, "Medication")
    assert hasattr(db_pkg, "AdherenceLog")
    assert hasattr(db_pkg, "Appointment")
    assert hasattr(db_pkg, "VitalsLog")
    assert hasattr(db_pkg, "Alert")
    assert hasattr(db_pkg, "DrugInteraction")


def test_log_adherence_contract_and_inventory():
    """Verify log_adherence contract, stock decrement, and get_adherence_summary metrics."""
    patient = db.get_patient()
    p_id = patient["id"]
    meds = db.get_medications(p_id)
    med = meds[0]
    med_id = med["id"]
    initial_stock = med["stock_remaining"]

    # Log a dose as TAKEN (lowercase to test case-insensitivity)
    date_str = date.today().isoformat()
    time_str = "12:00"
    result = db.log_adherence(
        medication_id=med_id,
        date_str=date_str,
        time_str=time_str,
        status="taken",
        notes="Taken with water",
    )
    assert result is True

    # Verify inventory was decremented
    updated_meds = db.get_medications(p_id)
    updated_med = next(m for m in updated_meds if m["id"] == med_id)
    assert updated_med["stock_remaining"] == initial_stock - 1

    # Verify get_adherence_summary calculation
    summary = db.get_adherence_summary(patient_id=p_id, days=7)
    assert "adherence_rate" in summary
    assert "streak_count" in summary
    assert "total_doses" in summary
    assert "taken_doses" in summary
    assert "missed_doses" in summary
    assert summary["total_doses"] > 0
    assert summary["taken_doses"] >= 1

    # Verify record_dose_adherence alias works identically
    alias_res = db.record_dose_adherence(
        medication_id=med_id,
        date_str=date_str,
        time_str="18:00",
        status="SKIPPED",
        notes="Doctor instructed skip",
    )
    assert alias_res is True


def test_invalid_status_and_sqlite_integrity_resilience():
    """Verify mark_dose_status and log_adherence catch IntegrityError cleanly and return False."""
    patient = db.get_patient()
    doses = db.get_todays_doses(patient["id"])
    valid_log_id = doses[0]["log_id"]

    # Invalid status strings should return False cleanly without raising IntegrityError
    assert db.mark_dose_status(valid_log_id, "INVALID_STATUS") is False
    assert db.mark_dose_status(valid_log_id, None) is False
    assert db.mark_dose_status(valid_log_id, 12345) is False

    # Invalid log IDs should return False
    assert db.mark_dose_status(-1, "TAKEN") is False
    assert db.mark_dose_status(999999, "TAKEN") is False

    # Invalid log_adherence parameters should return False
    assert db.log_adherence(medication_id=999999, date_str="2026-11-15", time_str="08:00", status="TAKEN") is False
    assert db.log_adherence(medication_id=doses[0]["medication_id"], date_str="2026-11-15", time_str="08:00", status="INVALID") is False
    assert db.log_adherence(medication_id=doses[0]["medication_id"], date_str="", time_str="08:00", status="TAKEN") is False
    assert db.log_adherence(medication_id=doses[0]["medication_id"], date_str="2026-11-15", time_str="08:00", status=None) is False


def test_auth_constant_time_passcode_verification():
    """Verify constant-time PIN comparison and type resilience."""
    # String and int pins
    assert db.verify_user_passcode("elderly", "1234") is not None
    assert db.verify_user_passcode("elderly", 1234) is not None
    assert db.verify_user_passcode("caretaker", "8888") is not None
    assert db.verify_user_passcode("caretaker", 8888) is not None

    # Whitespace padding
    assert db.verify_user_passcode("elderly", "  1234  ") is not None

    # None and invalid inputs
    assert db.verify_user_passcode("elderly", None) is None
    assert db.verify_user_passcode(None, "1234") is None
    assert db.verify_user_passcode("elderly", "") is None
    assert db.verify_user_passcode("elderly", "   ") is None
    assert db.verify_user_passcode("invalid_role", "1234") is None

    # update_user_passcode with None
    assert db.update_user_passcode(1, None) is False
    assert db.update_user_passcode(1, "") is False

