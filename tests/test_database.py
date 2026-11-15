"""
Unit and integration tests for database operations and schema integrity.
"""

import os
import pytest
from datetime import date
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
        except Exception:
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
