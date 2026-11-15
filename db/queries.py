"""
Domain-specific CRUD and query operations for GoldenCare Platform.
Encapsulates and provides type-safe queries for users, medications, adherence logs,
clinical appointments, vitals telemetry, alerts, and drug interactions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .database import (
    get_users,
    get_patient,
    verify_user_passcode,
    update_user_passcode,
    get_medications,
    add_medication,
    update_medication,
    delete_medication,
    get_todays_doses,
    mark_dose_status,
    log_adherence,
    record_dose_adherence,
    reconcile_past_doses,
    get_adherence_history,
    get_adherence_stats,
    get_adherence_summary,
    get_appointments,
    add_appointment,
    update_appointment_status,
    get_vitals,
    add_vitals,
    get_alerts,
    add_alert,
    get_drug_interactions,
    check_drug_interactions,
    reset_database,
)

__all__ = [
    "get_users",
    "get_patient",
    "verify_user_passcode",
    "update_user_passcode",
    "get_medications",
    "add_medication",
    "update_medication",
    "delete_medication",
    "get_todays_doses",
    "mark_dose_status",
    "log_adherence",
    "record_dose_adherence",
    "reconcile_past_doses",
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
    "reset_database",
]
