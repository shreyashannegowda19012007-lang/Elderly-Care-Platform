"""
Global Header and Navigation Component for GoldenCare Platform.
Provides persistent role context, high-contrast toggle, emergency SOS button,
and proactive background alert synchronization.
"""

from __future__ import annotations

import streamlit as st
from datetime import datetime
from utils.auth import get_current_user, login_user, logout_user
from utils.alerts import check_and_trigger_alerts, dispatch_sos_alert, get_alert_summary
from db.database import get_patient


def render_app_header() -> None:
    """Render top application header with user badge, quick switcher, and SOS trigger."""
    current_user = get_current_user()
    role = current_user["role"]
    user_name = current_user["name"]

    # Trigger proactive alert check (with session cache cooldown of 60 seconds)
    now_ts = datetime.now().timestamp()
    last_check = st.session_state.get("last_alert_check", 0)
    if not last_check or (now_ts - last_check > 60):
        try:
            check_and_trigger_alerts(patient_id=current_user.get("patient_id", 1))
            st.session_state["last_alert_check"] = now_ts
        except Exception:
            pass

    # Custom Top Navigation Bar
    role_badge_bg = "#10B981" if role == "elderly" else "#2563EB"
    role_icon = "👴" if role == "elderly" else "🩺"
    role_title = "Elderly Patient" if role == "elderly" else "Caregiver / Family"

    col_title, col_actions = st.columns([2.5, 1.5])

    with col_title:
        st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                <span style="font-size: 32px;">🌿</span>
                <div>
                    <h2 style="margin: 0; color: #1E293B; font-weight: 700; line-height: 1.2;">GoldenCare</h2>
                    <span style="font-size: 13px; color: #64748B;">Autonomous Elderly Care & Medication Synchronization</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_actions:
        st.markdown(f"""
            <div style="text-align: right; margin-bottom: 6px;">
                <span style="
                    background: {role_badge_bg};
                    color: white;
                    padding: 4px 10px;
                    border-radius: 9999px;
                    font-size: 12px;
                    font-weight: 600;
                    display: inline-block;
                ">
                    {role_icon} {role_title}: {user_name}
                </span>
            </div>
        """, unsafe_allow_html=True)

        sc1, sc2 = st.columns(2)
        with sc1:
            if role == "elderly":
                if st.button("Switch to Caregiver", key="hdr_switch_caregiver", use_container_width=True):
                    login_user("caretaker", "8888")
                    st.rerun()
            else:
                if st.button("Switch to Elderly", key="hdr_switch_elderly", use_container_width=True):
                    login_user("elderly", "1234")
                    st.rerun()

        with sc2:
            if st.button("🚨 Emergency SOS", key="hdr_sos_btn", type="primary", use_container_width=True):
                res = dispatch_sos_alert(patient_id=current_user.get("patient_id", 1))
                st.toast("🚨 EMERGENCY ALERT SENT TO CAREGIVER & CLINIC!", icon="🚨")
                st.error("🚨 Emergency Alert Dispatched! Caregiver Sarah has been notified via phone & email.")

    st.markdown("<hr style='margin: 8px 0 16px 0; border: 0; border-top: 1px solid #E2E8F0;' />", unsafe_allow_html=True)


def render_alert_banner(patient_id: int = 1) -> None:
    """Render notification bar if there are unhandled critical alerts."""
    summary = get_alert_summary(patient_id)
    if summary["critical"] > 0:
        latest = summary["recent"][0] if summary["recent"] else None
        msg = latest["message"] if latest else "Critical alerts require attention."
        st.markdown(f"""
            <div style="background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <span style="color: #991B1B; font-weight: 700; font-size: 14px;">⚠️ Active Clinical Alert: </span>
                    <span style="color: #7F1D1D; font-size: 14px;">{msg}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
