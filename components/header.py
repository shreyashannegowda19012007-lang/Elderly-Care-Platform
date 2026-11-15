"""
Global Header and Navigation Component for GoldenCare Platform.
Provides persistent role context, high-contrast toggle, emergency SOS button,
proactive background alert synchronization, and a smooth flowy top navigation bar.
"""

from __future__ import annotations

import streamlit as st
import inspect
from datetime import datetime
from utils.auth import get_current_user, login_user, logout_user
from utils.alerts import check_and_trigger_alerts, dispatch_sos_alert, get_alert_summary
from db.database import get_patient
from components.styles import apply_custom_styles


def _detect_current_page() -> str:
    """Identify the caller page filename to highlight the active navigation pill."""
    for frame in inspect.stack():
        fname = frame.filename.replace("\\", "/")
        if "pages/" in fname:
            return fname.split("/")[-1]
        elif "Home.py" in fname:
            return "Home.py"
    return "Home.py"


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

    col_title, col_actions = st.columns([2.3, 1.7])

    with col_title:
        st.markdown("""
            <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 6px;">
                <div style="
                    width: 48px;
                    height: 48px;
                    border-radius: 14px;
                    background: linear-gradient(135deg, #059669 0%, #047857 100%);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 4px 14px rgba(5, 150, 105, 0.3);
                ">
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 2v20M2 12h20"/>
                    </svg>
                </div>
                <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <h2 style="margin: 0; color: #0F172A; font-weight: 800; font-size: 26px; line-height: 1.1; letter-spacing: -0.03em;">GoldenCare</h2>
                        <span style="
                            background: #ECFDF5;
                            color: #065F46;
                            border: 1px solid #A7F3D0;
                            padding: 3px 10px;
                            border-radius: 9999px;
                            font-size: 11px;
                            font-weight: 700;
                            text-transform: uppercase;
                            letter-spacing: 0.04em;
                        ">Family Healthcare</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-top: 3px;">
                        <span class="pulse-green"></span>
                        <span style="font-size: 13.5px; color: #64748B; font-weight: 500;">Connected Daily Care for Seniors & Caregivers</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_actions:
        if authenticated and role:
            role_badge_bg = "linear-gradient(135deg, #059669 0%, #047857 100%)" if role == "elderly" else "linear-gradient(135deg, #0284C7 0%, #0369A1 100%)"
            role_title = "Senior Patient" if role == "elderly" else "Caregiver & Family"

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
                        background: #F1F5F9;
                        color: #475569;
                        border: 1px solid #CBD5E1;
                        padding: 5px 14px;
                        border-radius: 9999px;
                        font-size: 12.5px;
                        font-weight: 700;
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                    ">
                        Select Profile to Begin (PIN Protected)
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

    # Flowy Horizontal Quick Navigation Bar
    curr_page = _detect_current_page()
    nav_links = [
        ("Home", "Home.py"),
        ("Senior Portal", "pages/1_Elderly_Dashboard.py"),
        ("Caregiver", "pages/2_Caretaker_Dashboard.py"),
        ("Calendar", "pages/3_Appointments_and_Calendar.py"),
        ("Analytics", "pages/4_Adherence_Analytics.py"),
        ("Prescriptions", "pages/5_Medication_Manager.py"),
        ("Settings", "pages/6_System_Settings.py"),
    ]

    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
    cols = st.columns(len(nav_links))
    for idx, (label, target_page) in enumerate(nav_links):
        target_name = target_page.split("/")[-1]
        is_active = (target_name == curr_page)
        with cols[idx]:
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"flow_nav_{idx}_{target_name}", type=btn_type, width="stretch"):
                if not is_active:
                    st.switch_page(target_page)

    st.markdown("<div style='height: 1px; background: linear-gradient(90deg, #E2E8F0 0%, #CBD5E1 50%, #E2E8F0 100%); margin: 12px 0 20px 0;'></div>", unsafe_allow_html=True)


def render_alert_banner(patient_id: int = 1) -> None:
    """Render notification bar if there are unhandled critical alerts."""
    summary = get_alert_summary(patient_id)
    if summary["critical"] > 0:
        latest = summary["recent"][0] if summary["recent"] else None
        msg = latest["message"] if latest else "Critical alerts require attention."
        st.markdown(f"""
            <div style="background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 14px 18px; border-radius: 12px; margin-bottom: 18px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.08);">
                <div>
                    <span style="color: #991B1B; font-weight: 800; font-size: 14px; text-transform: uppercase; letter-spacing: 0.03em;">Urgent Notice: </span>
                    <span style="color: #7F1D1D; font-size: 14.5px; font-weight: 500;">{msg}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
