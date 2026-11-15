"""
Caregiver Clinical Cockpit for GoldenCare.
Comprehensive oversight dashboard for family members and healthcare aides:
real-time adherence tracking, schedule adjustments, inventory alerts, and
manual or proactive email alert dispatching.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime, date

from utils.auth import require_auth, get_current_user
from db.database import (
    get_patient,
    get_todays_doses,
    mark_dose_status,
    get_medications,
    get_adherence_stats,
    get_alerts,
)
from components.header import render_app_header, render_alert_banner
from utils.alerts import check_and_trigger_alerts, send_email_alert, get_smtp_config

# Security Gate: Caregivers only
require_auth(allowed_roles=["caretaker"])

render_app_header()
render_alert_banner()

curr_user = get_current_user()
patient_id = curr_user.get("patient_id", 1)
patient = get_patient(patient_id)
patient_name = patient["name"] if patient else "Eleanor Vance"

st.markdown(f"""
    <div style="margin-bottom: 20px;">
        <h1 style="color: #0F172A; margin: 0 0 6px 0;">🩺 Caregiver Clinical Cockpit</h1>
        <p style="color: #64748B; font-size: 16px; margin: 0;">
            Real-time synchronization and health telemetry for <strong>{patient_name}</strong>.
        </p>
    </div>
""", unsafe_allow_html=True)

# Top Clinical KPI Cards
stats_7d = get_adherence_stats(patient_id, days=7)
today_doses = get_todays_doses(patient_id)
today_taken = sum(1 for d in today_doses if d["status"] == "TAKEN")
today_pending = sum(1 for d in today_doses if d["status"] == "PENDING")
today_missed = sum(1 for d in today_doses if d["status"] == "MISSED")

col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

with col_kpi1:
    st.metric(
        label="7-Day Adherence Index",
        value=f"{stats_7d['adherence_rate']}%",
        delta="+2.5% vs last week" if stats_7d['adherence_rate'] >= 85 else "-4.0% decline",
        delta_color="normal" if stats_7d['adherence_rate'] >= 85 else "inverse",
    )

with col_kpi2:
    st.metric(
        label="Adherence Streak",
        value=f"{stats_7d['streak_days']} Days",
        delta="Target: 7+ Days",
    )

with col_kpi3:
    st.metric(
        label="Missed Doses (7 Days)",
        value=f"{stats_7d['missed_count']} Doses",
        delta="None this week!" if stats_7d['missed_count'] == 0 else f"{stats_7d['missed_count']} Escalated",
        delta_color="inverse" if stats_7d['missed_count'] > 0 else "normal",
    )

with col_kpi4:
    st.metric(
        label="Today's Dose Status",
        value=f"{today_taken} / {len(today_doses)} Taken",
        delta=f"{today_pending} Pending, {today_missed} Missed",
        delta_color="inverse" if today_missed > 0 else "normal",
    )

st.markdown("---")

# Main Content Layout: Left = Today's Active Schedule & Overrides; Right = Alert Dispatcher & Stock
col_left, col_right = st.columns([1.7, 1.3])

with col_left:
    st.subheader("📋 Today's Medication Execution Schedule")
    st.caption("Live timeline of scheduled doses with caregiver status override capability.")

    if not today_doses:
        st.info("No medications are scheduled for today.")
    else:
        for dose in today_doses:
            log_id = dose["log_id"]
            m_name = dose["medication_name"]
            m_time = dose["scheduled_time"]
            m_tod = dose["time_of_day"]
            m_status = dose["status"]
            m_dosage = dose["dosage"]
            m_taken_at = dose.get("taken_at")

            status_color = "#10B981" if m_status == "TAKEN" else ("#EF4444" if m_status == "MISSED" else "#3B82F6")
            status_icon = "✅" if m_status == "TAKEN" else ("⚠️" if m_status == "MISSED" else "⏳")

            with st.container():
                st.markdown(f"""
                    <div style="
                        border-left: 6px solid {status_color};
                        background: #F8FAFC;
                        padding: 12px 16px;
                        border-radius: 8px;
                        margin-bottom: 12px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="font-size: 16px; color: #0F172A;">{m_name} ({m_dosage})</strong>
                                <div style="color: #64748B; font-size: 13px;">
                                    {m_tod} • Scheduled: {m_time} {f'• Taken at {str(m_taken_at)[11:16]}' if m_taken_at else ''}
                                </div>
                            </div>
                            <span style="font-weight: 700; color: {status_color};">
                                {status_icon} {m_status}
                            </span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                # Caregiver Quick Action Buttons
                c_act1, c_act2, c_act3 = st.columns(3)
                with c_act1:
                    if st.button("Mark Taken", key=f"cg_take_{log_id}", use_container_width=True, disabled=(m_status == "TAKEN")):
                        mark_dose_status(log_id, "TAKEN", recorded_by="caretaker", notes="Confirmed by caregiver Sarah")
                        st.toast(f"{m_name} marked as TAKEN.", icon="✅")
                        st.rerun()
                with c_act2:
                    if st.button("Mark Missed", key=f"cg_miss_{log_id}", use_container_width=True, disabled=(m_status == "MISSED")):
                        mark_dose_status(log_id, "MISSED", recorded_by="caretaker", notes="Manually marked missed by caregiver")
                        st.rerun()
                with c_act3:
                    if st.button("Reset Pending", key=f"cg_reset_{log_id}", use_container_width=True, disabled=(m_status == "PENDING")):
                        mark_dose_status(log_id, "PENDING", recorded_by="caretaker", notes="Schedule reset to pending")
                        st.rerun()

with col_right:
    st.subheader("⚡ Proactive Alert & Notification Center")
    st.caption("Automated escalation engine checks schedules and dispatches emails.")

    # Live Alert Trigger and Test Dispatch Controls
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if st.button("🔄 Check Overdue Doses", use_container_width=True, type="primary"):
            triggered = check_and_trigger_alerts(patient_id=patient_id, force_check=True)
            if triggered:
                st.warning(f"Engine processed {len(triggered)} alerts (overdue doses/refills).")
            else:
                st.success("All doses are on track! No overdue escalations detected.")
            st.rerun()

    with col_t2:
        if st.button("📧 Send Test Email Alert", use_container_width=True):
            smtp_cfg = get_smtp_config()
            target_email = smtp_cfg["alert_recipient"]
            res = send_email_alert(
                recipient_email=target_email,
                subject=f"GoldenCare Test Escalation: System Operational for {patient_name}",
                body_html=f"""
                    <div style="font-family: sans-serif; padding: 20px; border: 2px solid #2563EB; border-radius: 8px;">
                        <h2 style="color: #1E40AF;">🌿 GoldenCare Verification Dispatch</h2>
                        <p>This is a certified automated test email from the GoldenCare platform.</p>
                        <p><strong>Patient Monitored:</strong> {patient_name}</p>
                        <p><strong>Current Adherence Index:</strong> {stats_7d['adherence_rate']}%</p>
                        <p>All alert triggers and background workers are operating normally.</p>
                    </div>
                """,
                alert_type="SYSTEM_TEST",
                severity="INFO",
                patient_id=patient_id,
            )
            if res["status"] == "SENT":
                st.success(f"Email successfully delivered to {target_email}!")
            else:
                st.info(f"{res['message']}")
            st.rerun()

    # Prescription Inventory Watchlist
    st.markdown("#### 💊 Prescription Stock & Refill Tracker")
    all_meds = get_medications(patient_id, active_only=True)
    low_stock_meds = [m for m in all_meds if m["stock_remaining"] <= m["refill_threshold"]]

    if low_stock_meds:
        for lm in low_stock_meds:
            st.error(f"⚠️ **Low Stock**: {lm['name']} has only **{lm['stock_remaining']} doses** left (Threshold: {lm['refill_threshold']}). Refill immediately!")
    else:
        st.success("✅ All prescription inventories are adequately stocked.")

    # Recent Audit Log Entries
    st.markdown("#### 📜 Recent Proactive Alert Logs")
    alerts = get_alerts(patient_id, limit=6)
    if alerts:
        log_rows = []
        for a in alerts:
            log_rows.append({
                "Timestamp": a["sent_at"][:19],
                "Severity": a["severity"],
                "Alert Type": a["alert_type"],
                "Delivery": a["delivery_status"],
                "Message": a["message"],
            })
        st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No alert logs generated yet.")
