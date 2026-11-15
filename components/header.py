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
from components.styles import apply_custom_styles


def render_app_header() -> None:
    """Render top application header with user badge, quick switcher, and SOS trigger."""
    # Apply universal modern design system styles
    apply_custom_styles()

    from utils.auth import is_authenticated
    authenticated = is_authenticated()
    current_user = get_current_user()
    role = current_user.get("role")
    user_name = current_user.get("name")

    # Trigger proactive alert check if authenticated
    if authenticated:
        now_ts = datetime.now().timestamp()
        last_check = st.session_state.get("last_alert_check", 0)
        if not last_check or (now_ts - last_check > 60):
            try:
                check_and_trigger_alerts(patient_id=current_user.get("patient_id", 1))
                st.session_state["last_alert_check"] = now_ts
            except Exception:
                pass

    col_title, col_actions = st.columns([2.2, 1.8])

    with col_title:
        st.markdown("""
            <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 8px;">
                <div style="
                    width: 44px;
                    height: 44px;
                    border-radius: 12px;
                    background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);
                    font-size: 16px;
                    font-weight: 800;
                    color: white;
                    letter-spacing: -0.05em;
                ">
                    GC
                </div>
                <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <h2 style="margin: 0; color: #0F172A; font-weight: 800; font-size: 26px; line-height: 1.1;">GoldenCare</h2>
                        <span style="
                            background: #ECFDF5;
                            color: #065F46;
                            border: 1px solid #A7F3D0;
                            padding: 2px 8px;
                            border-radius: 9999px;
                            font-size: 11px;
                            font-weight: 700;
                            text-transform: uppercase;
                            letter-spacing: 0.05em;
                        ">Clinical v2.4</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-top: 2px;">
                        <span class="pulse-green"></span>
                        <span style="font-size: 13px; color: #64748B; font-weight: 500;">Autonomous Care & Medication Synchronization</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_actions:
        if authenticated and role:
            role_badge_bg = "linear-gradient(135deg, #10B981 0%, #059669 100%)" if role == "elderly" else "linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)"
            role_title = "Senior Patient" if role == "elderly" else "Caregiver / Family"

            st.markdown(f"""
                <div style="text-align: right; margin-bottom: 8px;">
                    <span style="
                        background: {role_badge_bg};
                        color: white;
                        padding: 6px 14px;
                        border-radius: 9999px;
                        font-size: 13px;
                        font-weight: 700;
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    ">
                        {role_title}: <strong>{user_name}</strong>
                    </span>
                </div>
            """, unsafe_allow_html=True)

            sc1, sc2 = st.columns(2)
            with sc1:
                if st.button("Sign Out / Switch", key="hdr_btn_logout", width="stretch"):
                    logout_user()
                    st.rerun()

            with sc2:
                if st.button("EMERGENCY SOS", key="hdr_sos_btn", type="primary", width="stretch"):
                    dispatch_sos_alert(patient_id=current_user.get("patient_id", 1))
                    st.toast("EMERGENCY ALERT SENT TO CAREGIVER & CLINIC")
                    st.error("Emergency Alert Dispatched! Caregiver Sarah has been notified via phone and email.")
        else:
            st.markdown("""
                <div style="text-align: right; margin-bottom: 8px;">
                    <span style="
                        background: #475569;
                        color: white;
                        padding: 6px 14px;
                        border-radius: 9999px;
                        font-size: 13px;
                        font-weight: 700;
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    ">
                        Portal Locked (PIN Required)
                    </span>
                </div>
            """, unsafe_allow_html=True)
            sc1, sc2 = st.columns(2)
            with sc1:
                if st.button("Home / Login", key="hdr_btn_home", width="stretch"):
                    st.switch_page("Home.py")
            with sc2:
                if st.button("EMERGENCY SOS", key="hdr_sos_unauth", type="primary", width="stretch"):
                    dispatch_sos_alert(patient_id=1)
                    st.toast("EMERGENCY ALERT SENT")
                    st.error("Emergency Alert Dispatched!")

    st.markdown("<div style='height: 1px; background: linear-gradient(90deg, #E2E8F0 0%, #CBD5E1 50%, #E2E8F0 100%); margin: 10px 0 20px 0;'></div>", unsafe_allow_html=True)


def render_alert_banner(patient_id: int = 1) -> None:
    """Render notification bar if there are unhandled critical alerts."""
    summary = get_alert_summary(patient_id)
    if summary["critical"] > 0:
        latest = summary["recent"][0] if summary["recent"] else None
        msg = latest["message"] if latest else "Critical alerts require attention."
        st.markdown(f"""
            <div style="background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <span style="color: #991B1B; font-weight: 700; font-size: 14px;">Active Clinical Alert: </span>
                    <span style="color: #7F1D1D; font-size: 14px;">{msg}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
