"""
Adherence Analytics and Clinical Reporting Engine for GoldenCare.
Calculates adherence KPIs, time-drift variances, diurnal patterns,
and exports clinical records for healthcare providers.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from db.database import (
    get_adherence_history,
    get_vitals,
)


@st.cache_data(ttl=300)
def compute_adherence_timeseries(patient_id: int = 1, days: int = 14) -> pd.DataFrame:
    """
    Construct a daily time-series DataFrame of scheduled vs taken doses.
    """
    history = get_adherence_history(patient_id, days=days)
    if not history:
        # Return empty structured dataframe
        return pd.DataFrame(columns=["date", "scheduled", "taken", "missed", "rate"])

    df = pd.DataFrame(history)
    df["date"] = pd.to_datetime(df["scheduled_date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])
    if df.empty:
        return pd.DataFrame(columns=["date", "scheduled", "taken", "missed", "rate"])

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


@st.cache_data(ttl=300)
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
            except (ValueError, TypeError, KeyError):
                continue

    return pd.DataFrame(records)


@st.cache_data(ttl=300)
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
    Generate an exportable comprehensive CSV dossier combining medication adherence
    records, schedule time-drift, and vital sign telemetry for clinical review.
    """
    history = get_adherence_history(patient_id, days=days)
    vitals = get_vitals(patient_id, limit=100)

    lines = [
        "# ========================================================",
        "# GOLDENCARE CLINICAL ADHERENCE & VITALS DOSSIER",
        f"# Export Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# Patient ID: {patient_id} | Reporting Window: Past {days} Days",
        "# ========================================================",
        "",
        "--- SECTION 1: MEDICATION ADHERENCE & TIME-DRIFT TELEMETRY ---",
    ]

    if history:
        enriched_history = []
        for h in history:
            drift = ""
            if h.get("status") == "TAKEN" and h.get("taken_at") and h.get("scheduled_time"):
                try:
                    s_dt = datetime.strptime(f"{h['scheduled_date']} {h['scheduled_time']}", "%Y-%m-%d %H:%M")
                    t_dt = datetime.strptime(str(h["taken_at"])[:19], "%Y-%m-%d %H:%M:%S")
                    drift = str(int((t_dt - s_dt).total_seconds() / 60))
                except (ValueError, TypeError, KeyError):
                    pass
            enriched_history.append({
                "scheduled_date": h.get("scheduled_date"),
                "scheduled_time": h.get("scheduled_time"),
                "time_of_day": h.get("time_of_day"),
                "medication_name": h.get("medication_name"),
                "dosage": h.get("dosage"),
                "status": h.get("status"),
                "taken_at": h.get("taken_at") or "N/A",
                "drift_minutes": drift or "0",
                "recorded_by": h.get("recorded_by", "patient"),
                "log_notes": h.get("log_notes", ""),
            })
        df_hist = pd.DataFrame(enriched_history)
        lines.append(df_hist.to_csv(index=False).strip())
    else:
        lines.append("No medication adherence records found for this period.")

    lines.extend([
        "",
        "--- SECTION 2: LONGITUDINAL BIOMETRIC & VITAL SIGNS TELEMETRY ---",
    ])

    if vitals:
        vitals_formatted = []
        for v in vitals:
            vitals_formatted.append({
                "recorded_date": v.get("recorded_date"),
                "recorded_time": v.get("recorded_time"),
                "systolic_bp": v.get("systolic_bp"),
                "diastolic_bp": v.get("diastolic_bp"),
                "blood_glucose": v.get("blood_glucose"),
                "heart_rate": v.get("heart_rate"),
                "weight_kg": v.get("weight_kg"),
                "mood": v.get("mood"),
                "is_abnormal": "YES" if v.get("is_abnormal") == 1 else "NO",
                "notes": v.get("notes", ""),
            })
        df_vit = pd.DataFrame(vitals_formatted)
        lines.append(df_vit.to_csv(index=False).strip())
    else:
        lines.append("No vital sign records found for this period.")

    return "\n".join(lines)
