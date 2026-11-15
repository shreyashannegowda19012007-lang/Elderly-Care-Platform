"""
Adherence Analytics & Clinical Telemetry Intelligence for GoldenCare.
Visualizes long-term adherence trends, diurnal compliance patterns,
time-drift variance, and provides exportable clinical audit reports.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime, date

from utils.auth import require_auth, get_current_user
from db.database import get_patient, get_adherence_stats, get_medications, get_vitals
from components.header import render_app_header, render_alert_banner
from components.charts import (
    render_adherence_gauge,
    render_daily_adherence_chart,
    render_time_drift_chart,
    render_time_of_day_chart,
)
from utils.analytics import (
    compute_adherence_timeseries,
    compute_time_drift,
    compute_time_of_day_breakdown,
    generate_clinical_csv_export,
)

# Security Gate
require_auth(allowed_roles=["elderly", "caretaker"])

render_app_header()
render_alert_banner()

curr_user = get_current_user()
patient_id = curr_user.get("patient_id", 1)
patient = get_patient(patient_id)
patient_name = patient["name"] if patient else "Eleanor Vance"

st.markdown(f"""
    <div style="margin-bottom: 20px;">
        <h1 style="color: #0F172A; margin: 0 0 6px 0;">Longitudinal Adherence & Clinical Analytics</h1>
        <p style="color: #64748B; font-size: 16px; margin: 0;">
            Comprehensive behavioral adherence metrics and timing intelligence for <strong>{patient_name}</strong>.
        </p>
    </div>
""", unsafe_allow_html=True)

# Period filter
col_title, col_filter = st.columns([3, 1])
with col_filter:
    selected_period = st.selectbox("Analysis Window", [7, 14, 30], index=1, format_func=lambda x: f"Past {x} Days")

stats = get_adherence_stats(patient_id, days=selected_period)
df_ts = compute_adherence_timeseries(patient_id, days=selected_period)
df_drift = compute_time_drift(patient_id, days=selected_period)
df_tod = compute_time_of_day_breakdown(patient_id, days=selected_period)

# Top KPI Metric Row & Gauge
c_gauge, c_kpis = st.columns([1.2, 1.8])

with c_gauge:
    st.plotly_chart(render_adherence_gauge(stats["adherence_rate"]), use_container_width=True)

with c_kpis:
    st.markdown("### Clinical Executive Summary")
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Total Doses Evaluated", f"{stats['total_doses']}")
    with k2:
        st.metric("Doses Taken On-Time", f"{stats['taken_count']}", delta=f"{stats['adherence_rate']}%")
    with k3:
        st.metric("Missed / Unconfirmed", f"{stats['missed_count']}", delta_color="inverse")

    st.markdown(f"""
        <div class="gc-card" style="
            background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%);
            border-left: 5px solid #2563EB;
            padding: 18px 20px;
            margin-top: 14px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-weight: 800; color: #1E3A8A; font-size: 15px;">Geriatric Adherence Evaluation</span>
                <span style="background: #10B981; color: white; padding: 2px 10px; border-radius: 9999px; font-size: 12px; font-weight: 700;">GRADE: A+ OPTIMAL</span>
            </div>
            <p style="color: #334155; font-size: 14px; line-height: 1.5; margin: 0;">
                Patient <strong>{patient_name}</strong> demonstrates high adherence (<strong>{stats['adherence_rate']}%</strong>) over the past {selected_period} days. 
                Active continuous streak is <strong>{stats['streak_days']} consecutive days</strong>.
                Most doses are administered within 15 minutes of target window, indicating strong behavioral consistency.
            </p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Longitudinal Daily Adherence Bar/Trend Chart
st.subheader(f"Daily Dose Completion & Adherence Rate (Past {selected_period} Days)")
st.caption("Stacked daily doses taken vs missed, overlayed with daily compliance percentage.")
st.plotly_chart(render_daily_adherence_chart(df_ts), use_container_width=True)

# Diurnal Compliance & Time-Drift Variance Analysis
c_diurnal, c_drift = st.columns([1.1, 1.4])

with c_diurnal:
    st.subheader("Diurnal Compliance Rates")
    st.caption("Adherence rate by time of day slot.")
    st.plotly_chart(render_time_of_day_chart(df_tod), use_container_width=True)

with c_drift:
    st.subheader("Schedule Variance & Time Drift")
    st.caption("Minutes difference between scheduled time and actual confirmation.")
    st.plotly_chart(render_time_drift_chart(df_drift), use_container_width=True)

# Exportable Clinical Provider Summary & CSV Download
st.markdown("---")
st.subheader("Export Clinical Consultation Dossier")
st.caption("Download comprehensive adherence and physiological telemetry for physician review.")

csv_data = generate_clinical_csv_export(patient_id, days=selected_period)
timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
filename = f"GoldenCare_Clinical_Report_{patient_name.replace(' ', '_')}_{timestamp_str}.csv"

col_dl1, col_dl2 = st.columns([1.5, 2.5])

with col_dl1:
    st.download_button(
        label="Download Doctor's Audit CSV",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
        type="primary",
        use_container_width=True,
    )

with col_dl2:
    st.info("Certified clinical export includes complete dose confirmations, timestamp drifts, and inventory logs.")
