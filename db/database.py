"""
Database management module for GoldenCare Platform.
Provides SQLite connection management, schema initialization, auto-seeding,
and type-safe queries for users, medications, adherence logs, appointments,
vitals, and proactive alert logs.
"""

from __future__ import annotations

import hmac
import os
import sqlite3
import streamlit as st
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple

# Database path resolution: supports environment variable or default relative path
DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "carecompanion.db")
DB_PATH = os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)


@st.cache_resource(ttl=3600)
def get_db_pool_manager() -> Dict[str, Any]:
    """
    Cached database resource manager using st.cache_resource.
    Ensures single-instance connection configuration and prevent memory leaks.
    """
    ensure_db_dir()
    return {"db_path": DB_PATH, "status": "active", "engine": "sqlite3_wal"}


def ensure_db_dir() -> None:
    """Ensure the target directory for the SQLite database exists."""
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)


@contextmanager
def get_db_connection():
    """
    Context manager for SQLite database connections.
    Enables WAL mode and foreign key constraints for robust concurrency.
    """
    ensure_db_dir()
    conn = sqlite3.connect(DB_PATH, timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db() -> None:
    """Initialize all relational database tables."""
    ensure_db_dir()
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL CHECK(role IN ('elderly', 'caretaker', 'admin')),
                name TEXT NOT NULL,
                passcode TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                emergency_contact_name TEXT,
                emergency_contact_phone TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Medications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                dosage TEXT NOT NULL,
                frequency TEXT NOT NULL,
                time_of_day TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                pill_color TEXT DEFAULT '#2563EB',
                pill_shape TEXT DEFAULT 'Tablet',
                instructions TEXT,
                stock_remaining INTEGER DEFAULT 30,
                refill_threshold INTEGER DEFAULT 5,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)

        # Adherence logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS adherence_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medication_id INTEGER NOT NULL,
                patient_id INTEGER NOT NULL,
                scheduled_date TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                taken_at TIMESTAMP,
                status TEXT NOT NULL CHECK(status IN ('TAKEN', 'MISSED', 'PENDING', 'SKIPPED')),
                notes TEXT,
                recorded_by TEXT DEFAULT 'elderly',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (medication_id) REFERENCES medications (id) ON DELETE CASCADE,
                FOREIGN KEY (patient_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE (medication_id, scheduled_date, scheduled_time)
            );
        """)

        # Appointments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                doctor_name TEXT NOT NULL,
                clinic_address TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                transport_required INTEGER DEFAULT 0,
                prep_notes TEXT,
                status TEXT DEFAULT 'SCHEDULED' CHECK(status IN ('SCHEDULED', 'COMPLETED', 'CANCELLED')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)

        # Vitals logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vitals_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                recorded_date TEXT NOT NULL,
                recorded_time TEXT NOT NULL,
                systolic_bp INTEGER,
                diastolic_bp INTEGER,
                blood_glucose REAL,
                heart_rate INTEGER,
                weight_kg REAL,
                mood TEXT DEFAULT 'Good',
                notes TEXT,
                is_abnormal INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)

        # Alert logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                medication_id INTEGER,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL CHECK(severity IN ('INFO', 'WARNING', 'CRITICAL')),
                message TEXT NOT NULL,
                recipient_email TEXT,
                delivery_status TEXT NOT NULL CHECK(delivery_status IN ('SENT', 'LOGGED', 'FAILED')),
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (medication_id) REFERENCES medications (id) ON DELETE SET NULL
            );
        """)

        # Drug interactions knowledge base
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drug_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drug_a TEXT NOT NULL,
                drug_b TEXT NOT NULL,
                severity TEXT NOT NULL CHECK(severity IN ('High', 'Moderate', 'Minor')),
                description TEXT NOT NULL,
                recommendation TEXT NOT NULL
            );
        """)

        # Indexing for query acceleration
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_adherence_patient_date ON adherence_logs(patient_id, scheduled_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_meds_patient ON medications(patient_id, is_active);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_patient ON alert_logs(patient_id, sent_at);")


def seed_initial_data() -> None:
    """Populate database with rich realistic clinical seed data if tables are empty."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if users already seeded
        cursor.execute("SELECT COUNT(*) as cnt FROM users;")
        if cursor.fetchone()["cnt"] > 0:
            return  # Already populated

        # 1. Insert Users
        cursor.execute("""
            INSERT INTO users (role, name, passcode, phone, email, emergency_contact_name, emergency_contact_phone, notes)
            VALUES 
            ('elderly', 'Eleanor Vance', '1234', '+1 (555) 234-5678', 'eleanor.vance@example.org', 'Sarah Vance (Daughter)', '+1 (555) 987-6543', 'Mild hypertension, Type 2 diabetes managed with diet & oral meds. Prefers voice prompts.'),
            ('caretaker', 'Sarah Vance', '8888', '+1 (555) 987-6543', 'sarah.vance@example.org', 'Dr. Robert Chen', '+1 (555) 345-6789', 'Primary caretaker and daughter. Receives instant escalation email alerts.')
        """)

        cursor.execute("SELECT id FROM users WHERE role = 'elderly' LIMIT 1;")
        elderly_id = cursor.fetchone()["id"]

        # 2. Insert Medications
        medications_data = [
            (elderly_id, "Lisinopril", "10mg", "Daily", "Morning", "08:00", "#2563EB", "Tablet", "Take 1 tablet with a full glass of water every morning for blood pressure.", 45, 7, 1),
            (elderly_id, "Metformin", "500mg", "Twice Daily", "Morning", "08:00", "#10B981", "Round", "Take with morning meal to reduce gastrointestinal discomfort.", 38, 10, 1),
            (elderly_id, "Calcium + Vitamin D3", "600mg", "Daily", "Afternoon", "13:00", "#F59E0B", "Oval", "Take after lunch for bone density and fracture prevention.", 60, 10, 1),
            (elderly_id, "Metformin (Evening)", "500mg", "Twice Daily", "Evening", "19:00", "#10B981", "Round", "Take with dinner.", 38, 10, 1),
            (elderly_id, "Atorvastatin", "20mg", "Daily", "Bedtime", "21:00", "#8B5CF6", "Capsule", "Take before sleeping for lipid control.", 28, 5, 1),
            (elderly_id, "Baby Aspirin", "81mg", "Daily", "Morning", "08:00", "#EC4899", "Round", "Cardiovascular cardioprotection regimen.", 50, 10, 1),
        ]

        cursor.executemany("""
            INSERT INTO medications (patient_id, name, dosage, frequency, time_of_day, scheduled_time, pill_color, pill_shape, instructions, stock_remaining, refill_threshold, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, medications_data)

        # Retrieve medication IDs
        cursor.execute("SELECT id, name, scheduled_time FROM medications WHERE patient_id = ?", (elderly_id,))
        med_rows = cursor.fetchall()
        med_dict = {row["name"]: (row["id"], row["scheduled_time"]) for row in med_rows}

        # 3. Populate 14 days of realistic adherence logs
        today = date.today()
        adherence_entries = []

        for day_offset in range(14, 0, -1):
            past_date = today - timedelta(days=day_offset)
            date_str = past_date.isoformat()

            for med_name, (m_id, m_time) in med_dict.items():
                # Realistic adherence simulation: 92% adherence
                # Specific intentional patterns:
                # 3 days ago missed Evening Metformin
                # 8 days ago missed Afternoon Calcium
                if day_offset == 3 and "Evening" in med_name:
                    status = "MISSED"
                    taken_at = None
                    notes = "Automated escalation: Dose missed by >60 min."
                elif day_offset == 8 and "Calcium" in med_name:
                    status = "MISSED"
                    taken_at = None
                    notes = "Automated alert sent to caretaker."
                else:
                    status = "TAKEN"
                    # Time drift: taken within 5-25 minutes of scheduled time
                    h, m = map(int, m_time.split(":"))
                    taken_dt = datetime(past_date.year, past_date.month, past_date.day, h, m) + timedelta(minutes=(day_offset * 3) % 22)
                    taken_at = taken_dt.strftime("%Y-%m-%d %H:%M:%S")
                    notes = "Confirmed on Elderly Touch Portal."

                adherence_entries.append((m_id, elderly_id, date_str, m_time, taken_at, status, notes, "elderly"))

        # Add Today's entries
        today_str = today.isoformat()
        current_hour = datetime.now().hour

        for med_name, (m_id, m_time) in med_dict.items():
            h, m = map(int, m_time.split(":"))
            if h < current_hour:
                status = "TAKEN"
                taken_dt = datetime(today.year, today.month, today.day, h, m) + timedelta(minutes=8)
                taken_at = taken_dt.strftime("%Y-%m-%d %H:%M:%S")
                notes = "Taken on schedule"
            else:
                status = "PENDING"
                taken_at = None
                notes = "Scheduled"

            adherence_entries.append((m_id, elderly_id, today_str, m_time, taken_at, status, notes, "elderly"))

        cursor.executemany("""
            INSERT OR REPLACE INTO adherence_logs (medication_id, patient_id, scheduled_date, scheduled_time, taken_at, status, notes, recorded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, adherence_entries)

        # 4. Insert Appointments
        appointments_data = [
            (elderly_id, "Cardiology Follow-Up & ECG", "Dr. Robert Chen", "Metro Cardiology Pavilion, Suite 402", (today + timedelta(days=2)).isoformat(), "10:30", 1, "Bring past 14-day blood pressure logs. Fasting not required.", "SCHEDULED"),
            (elderly_id, "Comprehensive Diabetic Eye Exam", "Dr. Lisa Wong", "St. Luke Ophthalmology Center", (today + timedelta(days=7)).isoformat(), "14:15", 1, "Dilating drops will be administered. Sunglasses recommended for ride home.", "SCHEDULED"),
            (elderly_id, "Geriatric Wellness & Lab Panel", "Dr. Marcus Hayes", "Community Health Center", (today - timedelta(days=25)).isoformat(), "09:00", 0, "HbA1c was 6.8%. Lipid panel reviewed.", "COMPLETED"),
        ]

        cursor.executemany("""
            INSERT INTO appointments (patient_id, title, doctor_name, clinic_address, appointment_date, appointment_time, transport_required, prep_notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, appointments_data)

        # 5. Insert 7 Days of Vitals
        vitals_data = []
        for i in range(7, -1, -1):
            v_date = (today - timedelta(days=i)).isoformat()
            # Systolic 122-138, Diastolic 74-84, Glucose 104-128
            systolic = 124 + ((i * 4) % 15)
            diastolic = 76 + ((i * 3) % 9)
            glucose = 108.5 + ((i * 5) % 18)
            pulse = 68 + ((i * 2) % 10)
            weight = 64.2 - (i * 0.05)
            mood = "Great" if i in (0, 1, 4) else "Good"
            is_abnormal = 1 if systolic > 140 or glucose > 140 else 0
            vitals_data.append((elderly_id, v_date, "08:15", systolic, diastolic, glucose, pulse, round(weight, 1), mood, "Morning routine reading", is_abnormal))

        cursor.executemany("""
            INSERT INTO vitals_logs (patient_id, recorded_date, recorded_time, systolic_bp, diastolic_bp, blood_glucose, heart_rate, weight_kg, mood, notes, is_abnormal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, vitals_data)

        # 6. Insert Preloaded Drug-Drug Interactions
        interactions_data = [
            ("Aspirin", "Warfarin", "High", "Co-administration significantly potentiates anticoagulant action, elevating major hemorrhage risk.", "Avoid combination unless strictly monitored by a hematologist with routine INR checks."),
            ("Lisinopril", "Spironolactone", "High", "Concomitant use of ACE inhibitors and potassium-sparing diuretics may precipitate severe hyperkalemia.", "Monitor serum potassium and renal panel closely within 1-2 weeks."),
            ("Metformin", "Furosemide", "Moderate", "Furosemide may increase peak blood and plasma levels of Metformin without altering renal clearance.", "Monitor blood glucose and watch for signs of lactic acidosis."),
            ("Atorvastatin", "Clarithromycin", "High", "Potent CYP3A4 inhibition elevates statin concentrations, increasing risk of rhabdomyolysis.", "Withhold Atorvastatin during short-course Clarithromycin or substitute Azithromycin."),
            ("Lisinopril", "Ibuprofen", "Moderate", "NSAIDs blunt the antihypertensive effect of ACE inhibitors and may impair renal function in elderly.", "Use Acetaminophen for acute analgesia instead of NSAIDs."),
            ("Calcium", "Levothyroxine", "Moderate", "Calcium carbonate binds levothyroxine in the gut, sharply reducing absorption.", "Separate administration by at least 4 hours."),
            ("Baby Aspirin", "Ibuprofen", "Moderate", "Ibuprofen may competitively interfere with Aspirin's irreversible platelet COX-1 inhibition.", "Take immediate-release Aspirin at least 30 minutes before or 8 hours after Ibuprofen."),
        ]

        cursor.executemany("""
            INSERT INTO drug_interactions (drug_a, drug_b, severity, description, recommendation)
            VALUES (?, ?, ?, ?, ?)
        """, interactions_data)

        # 7. Insert Initial Seed Alert Logs
        alerts_data = [
            (elderly_id, None, "SYSTEM_READY", "INFO", "GoldenCare Platform initialized and patient Eleanor Vance synchronized.", "sarah.vance@example.org", "SENT"),
            (elderly_id, None, "MISSED_DOSE", "WARNING", "Missed Dose Escalation: Evening Metformin 500mg was not marked taken within grace period.", "sarah.vance@example.org", "SENT"),
            (elderly_id, None, "REFILL_ALERT", "INFO", "Stock Alert: Atorvastatin 20mg has 5 days of doses remaining.", "sarah.vance@example.org", "SENT"),
        ]

        cursor.executemany("""
            INSERT INTO alert_logs (patient_id, medication_id, alert_type, severity, message, recipient_email, delivery_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, alerts_data)


# --- User & Auth Operations ---

def get_users() -> List[Dict[str, Any]]:
    """Retrieve all users in the system."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY id ASC;")
        return [dict(row) for row in cursor.fetchall()]


def get_patient(patient_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Retrieve elderly patient record by ID or first available."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if patient_id:
            cursor.execute("SELECT * FROM users WHERE id = ? AND role = 'elderly';", (patient_id,))
        else:
            cursor.execute("SELECT * FROM users WHERE role = 'elderly' LIMIT 1;")
        row = cursor.fetchone()
        return dict(row) if row else None


def verify_user_passcode(role: str, passcode: Any) -> Optional[Dict[str, Any]]:
    """Verify role and passcode combination using constant-time comparison."""
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
    """Update passcode for specified user."""
    if new_passcode is None:
        return False
    pin_str = str(new_passcode).strip()
    if not pin_str:
        return False
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET passcode = ? WHERE id = ?;", (pin_str, user_id))
        return cursor.rowcount > 0


# --- Medication CRUD Operations ---

def get_medications(patient_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
    """Retrieve medications for a patient."""
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
    """Insert a new medication schedule and create today's adherence log entry."""
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
    """Update existing medication specifications."""
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
    """Soft delete or permanent remove medication."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM medications WHERE id = ?;", (med_id,))
        return cursor.rowcount > 0


# --- Adherence & Dose Tracking ---

def get_todays_doses(patient_id: int, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve all doses scheduled for a given date (defaults to today)
    with combined medication details. Ensures all active medications have
    a corresponding log entry.
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
    Mark dose status (TAKEN, MISSED, SKIPPED, PENDING).
    Decrements medication stock when marked TAKEN.
    Returns True if updated, False otherwise (including on constraint failure).
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


def reconcile_past_doses(patient_id: Optional[int] = None) -> int:
    """
    Reconcile historical adherence records:
    Any unconfirmed 'PENDING' dose from a past calendar day (scheduled_date < today)
    is automatically transitioned to 'MISSED' status.
    Returns the count of updated doses.
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


def get_adherence_history(patient_id: int, days: int = 14) -> List[Dict[str, Any]]:
    """Retrieve adherence records for the past N days."""
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
    """Calculate adherence metrics: total scheduled, taken, missed, percentage, streak."""
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


# --- Appointments CRUD Operations ---

def get_appointments(patient_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve appointments for a patient."""
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
    """Insert a new clinical appointment."""
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
    """Update status of appointment (SCHEDULED, COMPLETED, CANCELLED)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE appointments SET status = ? WHERE id = ?;", (status, appointment_id))
        return cursor.rowcount > 0


# --- Vitals Logs Operations ---

def get_vitals(patient_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieve vitals logged for a patient in descending date order."""
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
    Log a set of vital signs and flag if abnormal.
    Abnormal criteria: Systolic > 140 or < 90, Diastolic > 90, Glucose > 140 or < 70, Pulse > 100 or < 55.
    If abnormal, automatically registers an alert entry in alert_logs.
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


# --- Alert System Operations ---

def get_alerts(patient_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve logged alerts."""
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
    """Record an alert log entry."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alert_logs (
                patient_id, medication_id, alert_type, severity,
                message, recipient_email, delivery_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (patient_id, medication_id, alert_type, severity, message, recipient_email, delivery_status))
        return cursor.lastrowid


# --- Drug-Drug Interactions ---

def get_drug_interactions() -> List[Dict[str, Any]]:
    """Retrieve full catalog of known drug-drug interactions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drug_interactions ORDER BY severity ASC;")
        return [dict(row) for row in cursor.fetchall()]


def check_drug_interactions(drug_names: List[str]) -> List[Dict[str, Any]]:
    """
    Check if any pair among the provided list of drug names has an active interaction warning.
    Case-insensitive substring matching for active ingredients.
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
