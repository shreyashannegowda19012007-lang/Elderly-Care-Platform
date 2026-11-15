"""
Adherence Analytics and Clinical Reporting Engine for GoldenCare.
Calculates adherence KPIs, time-drift variances, diurnal patterns,
and exports clinical records for healthcare providers.
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from db.database import get_adherence_history, get_adherence_stats, get_medications, get_vitals


def compute_adherence_timeseries(patient_id: int = 1, days: int = 14) -> pd.DataFrame:
    """
    Construct a daily time-series DataFrame of scheduled vs taken doses.
    """
    history = get_adherence_history(patient_id, days=days)
    if not history:
        # Return empty structured dataframe
        return pd.DataFrame(columns=["date", "scheduled", "taken", "missed", "rate"])

    df = pd.DataFrame(history)
    df["date"] = pd.to_datetime(df["scheduled_date"]).dt.date

    grouped = df.groupby("date").agg(
        total=("status", "count"),
        taken=("status", lambda s: (s == "TAKEN").sum()),
        missed=("status", lambda s: (s == "MISSED").sum()),
        pending=("status", lambda s: (s == "PENDING").sum()),
    ).reset_index()

    # Calculate daily adherence % (completed doses vs eligible)
    grouped["eligible"] = grouped["taken"] + grouped["missed"]
    grouped["rate"] = grouped.apply(
        lambda r: round((r["taken"] / r["eligible"] * 100), 1) if r["eligible"] > 0 else 100.0,
        axis=1
    )
    return grouped.sort_values("date")


def compute_time_drift(patient_id: int = 1, days: int = 14) -> pd.DataFrame:
    """
    Compute delay/early variance between scheduled time and actual taken_at time in minutes.
    """
    history = get_adherence_history(patient_id, days=days)
    records = []

    for item in history:
        if item["status"] == "TAKEN" and item["taken_at"]:
            try:
                # Parse scheduled datetime
                sched_dt = datetime.strptime(f"{item['scheduled_date']} {item['scheduled_time']}", "%Y-%m-%d %H:%M")
                taken_dt = datetime.strptime(str(item["taken_at"])[:19], "%Y-%m-%d %H:%M:%S")
                drift_minutes = int((taken_dt - sched_dt).total_seconds() / 60)
                records.append({
                    "date": item["scheduled_date"],
                    "medication": item["medication_name"],
                    "time_of_day": item["time_of_day"],
                    "scheduled_time": item["scheduled_time"],
                    "taken_at": item["taken_at"],
                    "drift_minutes": drift_minutes,
                })
            except Exception:
                continue

    return pd.DataFrame(records)


def compute_time_of_day_breakdown(patient_id: int = 1, days: int = 14) -> pd.DataFrame:
    """
    Analyze adherence rates across Morning, Afternoon, Evening, and Bedtime slots.
    """
    history = get_adherence_history(patient_id, days=days)
    if not history:
        return pd.DataFrame(columns=["time_of_day", "taken", "missed", "rate"])

    df = pd.DataFrame(history)
    grouped = df.groupby("time_of_day").agg(
        taken=("status", lambda s: (s == "TAKEN").sum()),
        missed=("status", lambda s: (s == "MISSED").sum()),
    ).reset_index()

    grouped["total"] = grouped["taken"] + grouped["missed"]
    grouped["rate"] = grouped.apply(
        lambda r: round((r["taken"] / r["total"] * 100), 1) if r["total"] > 0 else 100.0,
        axis=1
    )
    return grouped


def generate_clinical_csv_export(patient_id: int = 1, days: int = 30) -> str:
    """
    Generate an exportable CSV dataset combining adherence and vitals records
    suitable for sharing with physicians.
    """
    history = get_adherence_history(patient_id, days=days)
    df = pd.DataFrame(history)
    if df.empty:
        return "No data recorded."
    return df.to_csv(index=False)
