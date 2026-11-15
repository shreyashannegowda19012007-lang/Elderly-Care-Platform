"""
Domain-specific CRUD and query operations for GoldenCare Platform.
Encapsulates all SQL interactions for users, medications, adherence logs,
clinical appointments, vitals telemetry, alerts, and drug interactions.
"""

from __future__ import annotations

import hmac
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .database import get_db_connection


# ==========================================
# 1. User & Passcode Authentication Operations
# ==========================================

def get_users() -> List[Dict[str, Any]]:
    """
    Retrieve all users registered in the system.

    Returns:
        List of user dictionaries ordered by ID.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY id ASC;")
        return [dict(row) for row in cursor.fetchall()]


def get_patient(patient_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve an elderly patient record by ID or return the primary active senior.

    Args:
        patient_id: Optional user ID of the patient. If None, returns first senior found.

    Returns:
        User dictionary if found, otherwise None.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if patient_id:
            cursor.execute("SELECT * FROM users WHERE id = ? AND role = 'elderly';", (patient_id,))
        else:
            cursor.execute("SELECT * FROM users WHERE role = 'elderly' LIMIT 1;")
        row = cursor.fetchone()
        return dict(row) if row else None


def verify_user_passcode(role: str, passcode: Any) -> Optional[Dict[str, Any]]:
    """
    Verify a role and passcode combination using constant-time comparison.

    Args:
        role: Active role ('elderly', 'caretaker', 'admin').
        passcode: 4-digit numeric PIN string or convertible value.

    Returns:
        User dictionary if valid, otherwise None.
    """
    if passcode is None or not isinstance(role, str):
        return None
    provided_pin = str(passcode).strip()
    if not provided_pin:
        return None

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE role = ?;", (role.strip(),))
        rows = cursor.fetchall()
        for row in rows:
            expected_pin = str(row["passcode"]).strip() if row["passcode"] is not None else ""
            if hmac.compare_digest(provided_pin, expected_pin):
                return dict(row)
        return None


def update_user_passcode(user_id: int, new_passcode: Any) -> bool:
    """
    Update the passcode PIN for a specified user.

    Args:
        user_id: ID of the user.
        new_passcode: New 4-digit PIN string or convertible value.

    Returns:
        True if updated successfully, False otherwise.
    """
    if new_passcode is None:
        return False
    pin_str = str(new_passcode).strip()
    if not pin_str:
        return False
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET passcode = ? WHERE id = ?;", (pin_str, user_id))
        return cursor.rowcount > 0


# ==========================================
# 2. Medication Regimen & Inventory Operations
# ==========================================

def get_medications(patient_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieve prescribed medications for a patient.

    Args:
        patient_id: ID of the patient.
        active_only: If True, only returns medications with is_active = 1.

    Returns:
        List of medication dictionaries ordered by scheduled time.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute("""
                SELECT * FROM medications 
                WHERE patient_id = ? AND is_active = 1 
                ORDER BY scheduled_time ASC;
            """, (patient_id,))
        else:
            cursor.execute("""
                SELECT * FROM medications 
                WHERE patient_id = ? 
                ORDER BY is_active DESC, scheduled_time ASC;
            """, (patient_id,))
        return [dict(row) for row in cursor.fetchall()]


def add_medication(
    patient_id: int,
    name: str,
    dosage: str,
    frequency: str,
    time_of_day: str,
    scheduled_time: str,
    pill_color: str = "#2563EB",
    pill_shape: str = "Tablet",
    instructions: str = "",
    stock_remaining: int = 30,
    refill_threshold: int = 5,
) -> int:
    """
    Insert a new medication schedule and create today's adherence log entry.

    Args:
        patient_id: Patient user ID.
        name: Name of medication (e.g. Lisinopril).
        dosage: Dosage string (e.g. 10mg).
        frequency: Frequency (e.g. Daily).
        time_of_day: Period (Morning, Afternoon, Evening, Bedtime).
        scheduled_time: Time in HH:MM format.
        pill_color: Hex color string.
        pill_shape: Physical shape string (Tablet, Capsule, Round, Oval).
        instructions: Patient instructions.
        stock_remaining: Pill inventory count.
        refill_threshold: Threshold to trigger refill warning.

    Returns:
        Inserted medication ID.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO medications (
                patient_id, name, dosage, frequency, time_of_day, scheduled_time,
                pill_color, pill_shape, instructions, stock_remaining, refill_threshold, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
        """, (
            patient_id, name.strip(), dosage.strip(), frequency.strip(),
            time_of_day.strip(), scheduled_time.strip(), pill_color,
            pill_shape, instructions.strip(), stock_remaining, refill_threshold
        ))
        med_id = cursor.lastrowid

        # Automatically insert today's pending slot
        today_str = date.today().isoformat()
        cursor.execute("""
            INSERT OR IGNORE INTO adherence_logs (
                medication_id, patient_id, scheduled_date, scheduled_time, status, notes, recorded_by
            ) VALUES (?, ?, ?, ?, 'PENDING', 'Newly scheduled', 'system');
        """, (med_id, patient_id, today_str, scheduled_time.strip()))

        return med_id


def update_medication(
    med_id: int,
    name: str,
    dosage: str,
    frequency: str,
    time_of_day: str,
    scheduled_time: str,
    pill_color: str,
    pill_shape: str,
    instructions: str,
    stock_remaining: int,
    refill_threshold: int,
    is_active: int = 1,
) -> bool:
    """
    Update existing medication specifications and regimen details.

    Args:
        med_id: ID of medication to update.
        ...: Updated parameters.

    Returns:
        True if updated, False otherwise.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE medications SET
                name = ?, dosage = ?, frequency = ?, time_of_day = ?,
                scheduled_time = ?, pill_color = ?, pill_shape = ?,
                instructions = ?, stock_remaining = ?, refill_threshold = ?,
                is_active = ?
            WHERE id = ?;
        """, (
            name.strip(), dosage.strip(), frequency.strip(), time_of_day.strip(),
            scheduled_time.strip(), pill_color, pill_shape, instructions.strip(),
            stock_remaining, refill_threshold, is_active, med_id
        ))
        return cursor.rowcount > 0


def delete_medication(med_id: int) -> bool:
    """
    Delete a medication and cascade its adherence records.

    Args:
        med_id: Medication ID to delete.

    Returns:
        True if deleted, False otherwise.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM medications WHERE id = ?;", (med_id,))
        return cursor.rowcount > 0


# ==========================================
# 3. Adherence Logging & Telemetry Operations
# ==========================================

def reconcile_past_doses(patient_id: Optional[int] = None) -> int:
    """
    Reconcile historical adherence records:
    Any unconfirmed 'PENDING' dose from a past calendar day (scheduled_date < today)
    is automatically transitioned to 'MISSED' status.

    Args:
        patient_id: Optional ID of the patient to scope reconciliation to.

    Returns:
        The count of updated doses.
    """
    today_str = date.today().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if patient_id:
            cursor.execute("""
                UPDATE adherence_logs
                SET status = 'MISSED',
                    notes = 'Auto-escalation: past unconfirmed dose'
                WHERE patient_id = ? AND scheduled_date < ? AND status = 'PENDING';
            """, (patient_id, today_str))
        else:
            cursor.execute("""
                UPDATE adherence_logs
                SET status = 'MISSED',
                    notes = 'Auto-escalation: past unconfirmed dose'
                WHERE scheduled_date < ? AND status = 'PENDING';
            """, (today_str,))
        return cursor.rowcount


def get_todays_doses(patient_id: int, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve all doses scheduled for a given date (defaults to today)
    with combined medication details. Ensures all active medications have
    a corresponding log entry.

    Args:
        patient_id: ID of the patient.
        date_str: ISO date string (YYYY-MM-DD). Defaults to current date.

    Returns:
        List of combined dose dictionaries with medication and adherence status.
    """
    if not date_str:
        date_str = date.today().isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Ensure active medications have log entries for this date
        cursor.execute("""
            SELECT id, scheduled_time FROM medications 
            WHERE patient_id = ? AND is_active = 1;
        """, (patient_id,))
        active_meds = cursor.fetchall()

        for med in active_meds:
            cursor.execute("""
                INSERT OR IGNORE INTO adherence_logs (
                    medication_id, patient_id, scheduled_date, scheduled_time, status, notes, recorded_by
                ) VALUES (?, ?, ?, ?, 'PENDING', 'Daily schedule generated', 'system');
            """, (med["id"], patient_id, date_str, med["scheduled_time"]))

        # Retrieve combined schedule
        cursor.execute("""
            SELECT 
                l.id as log_id,
                l.scheduled_date,
                l.scheduled_time,
                l.taken_at,
                l.status,
                l.notes as log_notes,
                l.recorded_by,
                m.id as medication_id,
                m.name as medication_name,
                m.dosage,
                m.frequency,
                m.time_of_day,
                m.pill_color,
                m.pill_shape,
                m.instructions,
                m.stock_remaining,
                m.refill_threshold
            FROM adherence_logs l
            JOIN medications m ON l.medication_id = m.id
            WHERE l.patient_id = ? AND l.scheduled_date = ?
            ORDER BY l.scheduled_time ASC, m.name ASC;
        """, (patient_id, date_str))

        return [dict(row) for row in cursor.fetchall()]


def mark_dose_status(
    log_id: int,
    status: str,
    recorded_by: str = "elderly",
    notes: Optional[str] = None,
) -> bool:
    """
    Mark dose intake status (TAKEN, MISSED, SKIPPED, PENDING).
    Automatically decrements medication inventory when marked TAKEN.

    Args:
        log_id: Adherence log ID.
        status: New status ('TAKEN', 'MISSED', 'PENDING', 'SKIPPED').
        recorded_by: Actor ('elderly', 'caretaker', 'system').
        notes: Optional care or observation notes.

    Returns:
        True if updated, False otherwise (including on constraint failure).
    """
    if not isinstance(status, str):
        return False
    norm_status = status.upper().strip()
    if norm_status not in {"TAKEN", "MISSED", "PENDING", "SKIPPED"}:
        return False

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if norm_status == "TAKEN" else None

            cursor.execute("SELECT medication_id, status as prev_status FROM adherence_logs WHERE id = ?;", (log_id,))
            row = cursor.fetchone()
            if not row:
                return False

            med_id = row["medication_id"]
            prev_status = row["prev_status"]

            cursor.execute("""
                UPDATE adherence_logs SET
                    status = ?,
                    taken_at = ?,
                    recorded_by = ?,
                    notes = COALESCE(?, notes)
                WHERE id = ?;
            """, (norm_status, now_str, recorded_by, notes, log_id))

            # Adjust inventory
            if norm_status == "TAKEN" and prev_status != "TAKEN":
                cursor.execute("UPDATE medications SET stock_remaining = MAX(0, stock_remaining - 1) WHERE id = ?;", (med_id,))
            elif prev_status == "TAKEN" and norm_status != "TAKEN":
                cursor.execute("UPDATE medications SET stock_remaining = stock_remaining + 1 WHERE id = ?;", (med_id,))

            return True
    except (sqlite3.IntegrityError, sqlite3.OperationalError, sqlite3.DatabaseError):
        return False
    except Exception:
        return False


def log_adherence(
    medication_id: int,
    date_str: str,
    time_str: str,
    status: str,
    notes: str = "",
    recorded_by: str = "elderly",
) -> bool:
    """
    Record or update adherence log entry for a medication slot.
    Logs dose adherence cleanly to adherence_logs table and decrements
    medication stock if status is 'TAKEN'/'taken'.

    Args:
        medication_id: ID of the medication.
        date_str: Date string (YYYY-MM-DD).
        time_str: Scheduled time (HH:MM).
        status: Dose status ('TAKEN', 'MISSED', 'PENDING', 'SKIPPED').
        notes: Optional observation or care notes.
        recorded_by: Actor ('elderly', 'caretaker', 'system').

    Returns:
        True on successful logging/update, False on error or constraint failure.
    """
    if not isinstance(status, str):
        return False
    norm_status = status.upper().strip()
    if norm_status not in {"TAKEN", "MISSED", "PENDING", "SKIPPED"}:
        return False
    if not isinstance(date_str, str) or not str(date_str).strip():
        return False
    if not isinstance(time_str, str) or not str(time_str).strip():
        return False

    clean_date = str(date_str).strip()
    clean_time = str(time_str).strip()

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Retrieve patient_id for the given medication
            cursor.execute("SELECT patient_id FROM medications WHERE id = ?;", (medication_id,))
            med_row = cursor.fetchone()
            if not med_row:
                return False
            patient_id = med_row["patient_id"]

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if norm_status == "TAKEN" else None

            # Check if an adherence log already exists for this slot
            cursor.execute(
                "SELECT id, status FROM adherence_logs WHERE medication_id = ? AND scheduled_date = ? AND scheduled_time = ?;",
                (medication_id, clean_date, clean_time),
            )
            existing = cursor.fetchone()
            prev_status = existing["status"] if existing else None

            if existing:
                cursor.execute("""
                    UPDATE adherence_logs SET
                        status = ?,
                        taken_at = COALESCE(?, taken_at),
                        recorded_by = ?,
                        notes = ?
                    WHERE id = ?;
                """, (norm_status, now_str, recorded_by, notes, existing["id"]))
            else:
                cursor.execute("""
                    INSERT INTO adherence_logs (
                        medication_id, patient_id, scheduled_date, scheduled_time, taken_at, status, notes, recorded_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (medication_id, patient_id, clean_date, clean_time, now_str, norm_status, notes, recorded_by))

            # Adjust medication stock if status transitions to/from TAKEN
            if norm_status == "TAKEN" and prev_status != "TAKEN":
                cursor.execute("UPDATE medications SET stock_remaining = MAX(0, stock_remaining - 1) WHERE id = ?;", (medication_id,))
            elif prev_status == "TAKEN" and norm_status != "TAKEN":
                cursor.execute("UPDATE medications SET stock_remaining = stock_remaining + 1 WHERE id = ?;", (medication_id,))

            return True
    except (sqlite3.IntegrityError, sqlite3.OperationalError, sqlite3.DatabaseError):
        return False
    except Exception:
        return False


# Contract alias
record_dose_adherence = log_adherence


def get_adherence_history(patient_id: int, days: int = 14) -> List[Dict[str, Any]]:
    """
    Retrieve historical adherence logs for the past N days.
    Automatically triggers past dose reconciliation.

    Args:
        patient_id: ID of the patient.
        days: Number of historical days to inspect (default 14).

    Returns:
        List of historical adherence records ordered chronologically.
    """
    reconcile_past_doses(patient_id)
    start_date = (date.today() - timedelta(days=days)).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                l.id as log_id,
                l.scheduled_date,
                l.scheduled_time,
                l.taken_at,
                l.status,
                l.notes as log_notes,
                l.recorded_by,
                m.id as medication_id,
                m.name as medication_name,
                m.dosage,
                m.time_of_day,
                m.stock_remaining
            FROM adherence_logs l
            JOIN medications m ON l.medication_id = m.id
            WHERE l.patient_id = ? AND l.scheduled_date >= ?
            ORDER BY l.scheduled_date ASC, l.scheduled_time ASC;
        """, (patient_id, start_date))
        return [dict(row) for row in cursor.fetchall()]


def get_adherence_stats(patient_id: int, days: int = 7) -> Dict[str, Any]:
    """
    Calculate comprehensive adherence metrics: compliance rate, streak days, total doses.
    Automatically triggers past dose reconciliation.

    Args:
        patient_id: ID of the patient.
        days: Historical window in days (default 7).

    Returns:
        Dictionary of compliance metrics:
            - total_doses: int
            - taken_count: int
            - missed_count: int
            - skipped_count: int
            - pending_count: int
            - adherence_rate: float (percentage 0.0 - 100.0)
            - streak_days: int
            - period_days: int
    """
    reconcile_past_doses(patient_id)
    start_date = (date.today() - timedelta(days=days)).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_doses,
                SUM(CASE WHEN status = 'TAKEN' THEN 1 ELSE 0 END) as taken_count,
                SUM(CASE WHEN status = 'MISSED' THEN 1 ELSE 0 END) as missed_count,
                SUM(CASE WHEN status = 'SKIPPED' THEN 1 ELSE 0 END) as skipped_count,
                SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending_count
            FROM adherence_logs
            WHERE patient_id = ? AND scheduled_date >= ?;
        """, (patient_id, start_date))
        res = cursor.fetchone()
        total = res["total_doses"] or 0
        taken = res["taken_count"] or 0
        missed = res["missed_count"] or 0
        skipped = res["skipped_count"] or 0
        pending = res["pending_count"] or 0

        # Adherence percentage ignores pending upcoming doses
        eligible = taken + missed + skipped
        adherence_rate = round((taken / eligible * 100), 1) if eligible > 0 else 100.0

        # Calculate consecutive days with 100% adherence (Streak)
        cursor.execute("""
            SELECT scheduled_date,
                   SUM(CASE WHEN status = 'TAKEN' THEN 1 ELSE 0 END) as taken_doses,
                   SUM(CASE WHEN status = 'MISSED' THEN 1 ELSE 0 END) as missed_doses
            FROM adherence_logs
            WHERE patient_id = ? AND scheduled_date <= ?
            GROUP BY scheduled_date
            ORDER BY scheduled_date DESC
            LIMIT 30;
        """, (patient_id, date.today().isoformat()))

        daily_rows = cursor.fetchall()
        streak = 0
        for r in daily_rows:
            if r["missed_doses"] == 0 and r["taken_doses"] > 0:
                streak += 1
            else:
                break

        return {
            "total_doses": total,
            "taken_count": taken,
            "missed_count": missed,
            "skipped_count": skipped,
            "pending_count": pending,
            "adherence_rate": adherence_rate,
            "streak_days": streak,
            "period_days": days,
        }


def get_adherence_summary(patient_id: int, days: int = 7) -> Dict[str, Any]:
    """
    Calculate comprehensive adherence summary over the specified day window.
    Returns adherence rate (percentage), streak count, total doses, taken doses,
    and missed doses.

    Args:
        patient_id: ID of the patient.
        days: Window in days (default 7).

    Returns:
        Dictionary containing adherence metrics:
            - adherence_rate: float
            - streak_count: int
            - total_doses: int
            - taken_doses: int
            - missed_doses: int
    """
    stats = get_adherence_stats(patient_id, days=days)
    return {
        "adherence_rate": stats["adherence_rate"],
        "compliance_rate": stats["adherence_rate"],
        "streak_count": stats["streak_days"],
        "streak_days": stats["streak_days"],
        "total_doses": stats["total_doses"],
        "taken_doses": stats["taken_count"],
        "taken_count": stats["taken_count"],
        "missed_doses": stats["missed_count"],
        "missed_count": stats["missed_count"],
        "skipped_doses": stats["skipped_count"],
        "skipped_count": stats["skipped_count"],
        "pending_doses": stats["pending_count"],
        "pending_count": stats["pending_count"],
        "period_days": stats["period_days"],
    }


# ==========================================
# 4. Clinical Appointments Operations
# ==========================================

def get_appointments(patient_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve clinical appointments for a patient.

    Args:
        patient_id: Patient ID.
        status: Optional status filter ('SCHEDULED', 'COMPLETED', 'CANCELLED').

    Returns:
        List of appointment dictionaries ordered by date and time.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute("""
                SELECT * FROM appointments 
                WHERE patient_id = ? AND status = ?
                ORDER BY appointment_date ASC, appointment_time ASC;
            """, (patient_id, status))
        else:
            cursor.execute("""
                SELECT * FROM appointments 
                WHERE patient_id = ?
                ORDER BY appointment_date ASC, appointment_time ASC;
            """, (patient_id,))
        return [dict(row) for row in cursor.fetchall()]


def add_appointment(
    patient_id: int,
    title: str,
    doctor_name: str,
    clinic_address: str,
    appointment_date: str,
    appointment_time: str,
    transport_required: bool = False,
    prep_notes: str = "",
) -> int:
    """
    Schedule a new clinical appointment.

    Args:
        patient_id: Patient ID.
        title: Consultation purpose.
        doctor_name: Attending physician.
        clinic_address: Location or clinic address.
        appointment_date: Date (YYYY-MM-DD).
        appointment_time: Time (HH:MM).
        transport_required: Whether patient requires caregiver transport assistance.
        prep_notes: Patient preparation instructions.

    Returns:
        Inserted appointment ID.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO appointments (
                patient_id, title, doctor_name, clinic_address,
                appointment_date, appointment_time, transport_required, prep_notes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'SCHEDULED');
        """, (
            patient_id, title.strip(), doctor_name.strip(), clinic_address.strip(),
            appointment_date.strip(), appointment_time.strip(), 1 if transport_required else 0,
            prep_notes.strip()
        ))
        return cursor.lastrowid


def update_appointment_status(appointment_id: int, status: str) -> bool:
    """
    Update appointment status (SCHEDULED, COMPLETED, CANCELLED).

    Args:
        appointment_id: ID of appointment.
        status: New status string.

    Returns:
        True if updated, False otherwise.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE appointments SET status = ? WHERE id = ?;", (status, appointment_id))
        return cursor.rowcount > 0


# ==========================================
# 5. Physiological Vitals Telemetry Operations
# ==========================================

def get_vitals(patient_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Retrieve logged vital signs in descending chronological order.

    Args:
        patient_id: Patient ID.
        limit: Maximum number of records to return (default 30).

    Returns:
        List of vitals dictionaries.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM vitals_logs
            WHERE patient_id = ?
            ORDER BY recorded_date DESC, recorded_time DESC
            LIMIT ?;
        """, (patient_id, limit))
        return [dict(row) for row in cursor.fetchall()]


def add_vitals(
    patient_id: int,
    recorded_date: str,
    recorded_time: str,
    systolic_bp: Optional[int],
    diastolic_bp: Optional[int],
    blood_glucose: Optional[float],
    heart_rate: Optional[int],
    weight_kg: Optional[float],
    mood: str = "Good",
    notes: str = "",
) -> int:
    """
    Log physiological vitals and evaluate clinical abnormality flags.
    Abnormal thresholds: Systolic > 140 or < 90, Diastolic > 90, Glucose > 140 or < 70, Pulse > 100 or < 55.
    If abnormal, automatically registers an alert entry in alert_logs.

    Args:
        patient_id: Patient ID.
        recorded_date: Date string (YYYY-MM-DD).
        recorded_time: Time string (HH:MM).
        systolic_bp: Systolic blood pressure (mmHg).
        diastolic_bp: Diastolic blood pressure (mmHg).
        blood_glucose: Blood glucose (mg/dL).
        heart_rate: Pulse (bpm).
        weight_kg: Body weight (kg).
        mood: Subjective mood rating.
        notes: Clinical notes.

    Returns:
        Inserted vitals record ID.
    """
    is_abnormal = 0
    abnormal_reasons = []

    if systolic_bp and (systolic_bp > 140 or systolic_bp < 90):
        is_abnormal = 1
        abnormal_reasons.append(f"Systolic BP {systolic_bp} mmHg")
    if diastolic_bp and (diastolic_bp > 90 or diastolic_bp < 60):
        is_abnormal = 1
        abnormal_reasons.append(f"Diastolic BP {diastolic_bp} mmHg")
    if blood_glucose and (blood_glucose > 140.0 or blood_glucose < 70.0):
        is_abnormal = 1
        abnormal_reasons.append(f"Blood Glucose {blood_glucose} mg/dL")
    if heart_rate and (heart_rate > 100 or heart_rate < 55):
        is_abnormal = 1
        abnormal_reasons.append(f"Heart Rate {heart_rate} BPM")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vitals_logs (
                patient_id, recorded_date, recorded_time, systolic_bp, diastolic_bp,
                blood_glucose, heart_rate, weight_kg, mood, notes, is_abnormal
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            patient_id, recorded_date, recorded_time, systolic_bp, diastolic_bp,
            blood_glucose, heart_rate, weight_kg, mood, notes.strip(), is_abnormal
        ))
        vitals_id = cursor.lastrowid

        # Register alert if readings breach physiological safety thresholds
        if is_abnormal:
            reasons_str = ", ".join(abnormal_reasons)
            alert_msg = f"Abnormal Vitals Logged: {reasons_str} at {recorded_time}."
            cursor.execute("SELECT email FROM users WHERE role = 'caretaker' LIMIT 1;")
            c_row = cursor.fetchone()
            c_email = c_row["email"] if c_row and c_row["email"] else "caretaker@example.org"

            cursor.execute("""
                INSERT INTO alert_logs (
                    patient_id, medication_id, alert_type, severity,
                    message, recipient_email, delivery_status
                ) VALUES (?, NULL, 'ABNORMAL_VITALS', 'WARNING', ?, ?, 'LOGGED');
            """, (patient_id, alert_msg, c_email))

        return vitals_id


# ==========================================
# 6. Proactive Alerts & Audit Log Operations
# ==========================================

def get_alerts(patient_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieve alert logs for audit inspection and review.

    Args:
        patient_id: Optional patient filter.
        limit: Max records to return (default 50).

    Returns:
        List of alert dictionaries ordered by sent_at DESC.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if patient_id:
            cursor.execute("""
                SELECT * FROM alert_logs
                WHERE patient_id = ?
                ORDER BY sent_at DESC
                LIMIT ?;
            """, (patient_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM alert_logs
                ORDER BY sent_at DESC
                LIMIT ?;
            """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def add_alert(
    patient_id: int,
    medication_id: Optional[int],
    alert_type: str,
    severity: str,
    message: str,
    recipient_email: Optional[str],
    delivery_status: str = "SENT",
) -> int:
    """
    Record an alert notification entry in the persistent audit log.

    Args:
        patient_id: Patient ID.
        medication_id: Associated medication ID (optional).
        alert_type: Type of alert (MISSED_DOSE, REFILL_ALERT, EMERGENCY_SOS, ABNORMAL_VITALS).
        severity: Alert severity (INFO, WARNING, CRITICAL).
        message: Alert description.
        recipient_email: Recipient destination.
        delivery_status: Status ('SENT', 'LOGGED', 'FAILED').

    Returns:
        Inserted alert log ID.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alert_logs (
                patient_id, medication_id, alert_type, severity,
                message, recipient_email, delivery_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (patient_id, medication_id, alert_type, severity, message, recipient_email, delivery_status))
        return cursor.lastrowid


# ==========================================
# 7. Drug-Drug Interactions Catalog
# ==========================================

def get_drug_interactions() -> List[Dict[str, Any]]:
    """
    Retrieve the full clinical catalog of known drug-drug interactions.

    Returns:
        List of interaction dictionaries.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drug_interactions ORDER BY severity ASC;")
        return [dict(row) for row in cursor.fetchall()]


def check_drug_interactions(drug_names: List[str]) -> List[Dict[str, Any]]:
    """
    Check if any pair among the provided list of drug names has an active interaction warning.
    Performs case-insensitive bidirectional substring matching for active pharmacological agents.

    Args:
        drug_names: List of drug or medication names.

    Returns:
        List of matching interaction rule dictionaries.
    """
    if len(drug_names) < 2:
        return []

    interactions = get_drug_interactions()
    found_warnings = []
    clean_names = [d.strip().lower() for d in drug_names if d.strip()]

    for rule in interactions:
        rule_a = rule["drug_a"].lower()
        rule_b = rule["drug_b"].lower()

        match_a = any(rule_a in name or name in rule_a for name in clean_names)
        match_b = any(rule_b in name or name in rule_b for name in clean_names)

        if match_a and match_b:
            found_warnings.append(rule)

    return found_warnings
