"""
Database module for GoldenCare Platform.
Cleanly re-exports connection lifecycle managers, domain queries,
and strongly-typed data models.
"""

from __future__ import annotations

# 1. Connection lifecycle & schema operations
from .database import (
    DB_PATH,
    DEFAULT_DB_DIR,
    DEFAULT_DB_PATH,
    ensure_db_dir,
    get_db_connection,
    init_db,
    seed_initial_data,
    reconcile_past_doses,
    reset_database,
)

# 2. Domain Models & TypedDicts
from .models import (
    AdherenceLog,
    AdherenceLogDict,
    Alert,
    AlertDict,
    AlertLog,
    Appointment,
    AppointmentDict,
    DrugInteraction,
    DrugInteractionDict,
    Medication,
    MedicationDict,
    User,
    UserDict,
    VitalsLog,
    VitalsLogDict,
)

# 3. Domain CRUD Query Operations
from .queries import (
    add_alert,
    add_appointment,
    add_medication,
    add_vitals,
    check_drug_interactions,
    delete_medication,
    get_adherence_history,
    get_adherence_stats,
    get_adherence_summary,
    get_alerts,
    get_appointments,
    get_drug_interactions,
    get_medications,
    get_patient,
    get_todays_doses,
    get_users,
    get_vitals,
    log_adherence,
    mark_dose_status,
    reconcile_past_doses,
    record_dose_adherence,
    update_appointment_status,
    update_medication,
    update_user_passcode,
    verify_user_passcode,
)

__all__ = [
    # Connection & Lifecycle
    "DB_PATH",
    "DEFAULT_DB_DIR",
    "DEFAULT_DB_PATH",
    "ensure_db_dir",
    "get_db_connection",
    "init_db",
    "seed_initial_data",
    "reconcile_past_doses",
    "reset_database",
    # Models
    "User",
    "Medication",
    "AdherenceLog",
    "Appointment",
    "VitalsLog",
    "Alert",
    "AlertLog",
    "DrugInteraction",
    "UserDict",
    "MedicationDict",
    "AdherenceLogDict",
    "AppointmentDict",
    "VitalsLogDict",
    "AlertDict",
    "DrugInteractionDict",
    # Queries
    "get_users",
    "get_patient",
    "verify_user_passcode",
    "update_user_passcode",
    "get_medications",
    "add_medication",
    "update_medication",
    "delete_medication",
    "reconcile_past_doses",
    "get_todays_doses",
    "mark_dose_status",
    "log_adherence",
    "record_dose_adherence",
    "get_adherence_history",
    "get_adherence_stats",
    "get_adherence_summary",
    "get_appointments",
    "add_appointment",
    "update_appointment_status",
    "get_vitals",
    "add_vitals",
    "get_alerts",
    "add_alert",
    "get_drug_interactions",
    "check_drug_interactions",
]
