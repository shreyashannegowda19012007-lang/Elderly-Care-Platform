"""
Unit tests for adherence analytics, timeseries computation, and clinical export.
"""

import pandas as pd
import pytest

import db.database as db
from utils.analytics import (
    compute_adherence_timeseries,
    compute_time_drift,
    compute_time_of_day_breakdown,
    generate_clinical_csv_export,
)


@pytest.fixture(autouse=True)
def setup_test_analytics(tmp_path, monkeypatch):
    """Set up database with 14-day history."""
    test_db_path = str(tmp_path / "test_analytics.db")
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()
    db.seed_initial_data()


def test_adherence_timeseries_structure():
    """Verify daily timeseries DataFrame output."""
    df = compute_adherence_timeseries(patient_id=1, days=14)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "date" in df.columns
    assert "taken" in df.columns
    assert "rate" in df.columns


def test_time_drift_analysis():
    """Verify time drift minutes computation."""
    df_drift = compute_time_drift(patient_id=1, days=14)
    assert isinstance(df_drift, pd.DataFrame)
    if not df_drift.empty:
        assert "drift_minutes" in df_drift.columns
        assert "medication" in df_drift.columns


def test_time_of_day_breakdown():
    """Verify morning vs evening diurnal breakdown."""
    df_tod = compute_time_of_day_breakdown(patient_id=1, days=14)
    assert isinstance(df_tod, pd.DataFrame)
    assert "time_of_day" in df_tod.columns
    assert "rate" in df_tod.columns


def test_csv_export_generation():
    """Verify generation of valid comprehensive clinical CSV dossier with adherence and vitals."""
    csv_str = generate_clinical_csv_export(patient_id=1, days=7)
    assert isinstance(csv_str, str)
    assert "medication_name" in csv_str
    assert "scheduled_date" in csv_str
    assert "drift_minutes" in csv_str
    assert "systolic_bp" in csv_str
    assert "SECTION 1: MEDICATION ADHERENCE" in csv_str
    assert "SECTION 2: LONGITUDINAL BIOMETRIC & VITAL SIGNS" in csv_str
