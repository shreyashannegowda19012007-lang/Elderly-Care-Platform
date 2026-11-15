"""
GoldenCare — Autonomous Elderly Care & Medication Management Platform.
Main application entry point, passcode-based authentication routing,
and platform overview.
"""

from __future__ import annotations

import streamlit as st

from components.header import render_alert_banner, render_app_header
from db.database import (
    get_patient,
    get_todays_doses,
    get_users,
    init_db,
    seed_initial_data,
)
from utils.alerts import get_alert_summary
from utils.auth import get_current_user, init_session_state, login_user
from utils.google_services import get_google_services_health

# Configure Streamlit page settings
st.set_page_config(
    page_title="GoldenCare | Compassionate Healthcare Platform",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Run schema initialization and initial seed data population
init_db()
seed_initial_data()
init_session_state()

# Global Header & Navigation
render_app_header()
render_alert_banner()

# Streamlined Hero Banner (Simplified text, no overcrowding)
st.markdown("""
    <div style="
        background: linear-gradient(135deg, #064E3B 0%, #065F46 45%, #0F766E 100%);
        color: white;
        padding: 28px 32px;
        border-radius: 20px;
        margin-bottom: 24px;
        box-shadow: 0 12px 30px -8px rgba(6, 78, 59, 0.3);
    ">
        <h1 style="color: white; margin: 0 0 8px 0; font-size: 32px; font-weight: 800; letter-spacing: -0.02em;">
            GoldenCare Healthcare Sanctuary
        </h1>
        <p style="color: #D1FAE5; font-size: 16px; margin: 0; font-weight: 400; line-height: 1.5;">
            Connected daily care for seniors and families. Large tactile controls, voice guidance, and real-time caregiver alerts.
        </p>
    </div>
""", unsafe_allow_html=True)

# Authentication & Fast Role Switcher Section
st.subheader("Select Profile & Enter Portal")

curr_user = get_current_user()
active_role = curr_user.get("role")

all_users = get_users()
eld_user = next((u for u in all_users if u["role"] == "elderly"), None)
car_user = next((u for u in all_users if u["role"] == "caretaker"), None)
eld_pin_active = eld_user["passcode"] if eld_user and eld_user.get("passcode") else "1234"
car_pin_active = car_user["passcode"] if car_user and car_user.get("passcode") else "8888"

if active_role:
    st.markdown(f"""
        <div style="background: #ECFDF5; border: 1.5px solid #10B981; border-radius: 12px; padding: 12px 18px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
                <strong style="color: #065F46; font-size: 15px;">Active Profile:</strong>
                <span style="color: #047857; font-size: 15px; font-weight: 700;">{curr_user.get('name')} ({active_role.capitalize()})</span>
            </div>
            <span style="font-size: 12.5px; color: #065F46;">Switch below or use the top navigation.</span>
        </div>
    """, unsafe_allow_html=True)

col_eld, col_car = st.columns(2)

with col_eld:
    st.markdown(f"""
        <div class="gc-card" style="
            border: 2px solid #10B981;
            background: linear-gradient(180deg, #F0FDF4 0%, #FFFFFF 100%);
            border-radius: 18px;
            padding: 22px;
            margin-bottom: 12px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="
                        width: 44px;
                        height: 44px;
                        background: #DCFCE7;
                        border-radius: 12px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border: 1.5px solid #86EFAC;
                    ">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#047857" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>
                        </svg>
                    </div>
                    <div>
                        <h3 style="color: #065F46; margin: 0; font-size: 20px; font-weight: 800;">Eleanor Vance</h3>
                        <span style="font-size: 13px; color: #047857; font-weight: 600;">Senior Patient Portal</span>
                    </div>
                </div>
                <span style="background: #059669; color: white; padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 800;">PIN: {eld_pin_active}</span>
            </div>
            <p style="color: #475569; font-size: 14px; line-height: 1.5; margin: 0;">
                Large tactile buttons, spoken voice assistance, and single-tap dose confirmation.
            </p>
        </div>
    """, unsafe_allow_html=True)

    if active_role == "elderly":
        if st.button("Enter Senior Portal (Active Session)", width="stretch", type="primary"):
            st.switch_page("pages/1_Elderly_Dashboard.py")
    else:
        if st.button(f"Quick Enter as Eleanor (PIN: {eld_pin_active})", key="quick_eld_enter", width="stretch", type="primary") and login_user("elderly", eld_pin_active):
            st.success("Welcome back, Eleanor!")
            st.switch_page("pages/1_Elderly_Dashboard.py")

        with st.expander("Or enter custom Senior PIN"):
            eld_pin = st.text_input("Senior Passcode (PIN)", type="password", placeholder=f"Default: {eld_pin_active}", key="home_eld_pin")
            if st.button("Unlock Senior Portal", width="stretch", key="btn_unlock_eld_custom"):
                if eld_pin and login_user("elderly", eld_pin):
                    st.success("Authenticated as Eleanor Vance (Senior)!")
                    st.switch_page("pages/1_Elderly_Dashboard.py")
                else:
                    st.error(f"Invalid PIN. The configured PIN is {eld_pin_active}.")

with col_car:
    st.markdown(f"""
        <div class="gc-card" style="
            border: 2px solid #0284C7;
            background: linear-gradient(180deg, #F0F9FF 0%, #FFFFFF 100%);
            border-radius: 18px;
            padding: 22px;
            margin-bottom: 12px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="
                        width: 44px;
                        height: 44px;
                        background: #E0F2FE;
                        border-radius: 12px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border: 1.5px solid #7DD3FC;
                    ">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0284C7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
                            <line x1="16" x2="16" y1="2" y2="6"/>
                            <line x1="8" x2="8" y1="2" y2="6"/>
                            <line x1="3" x2="21" y1="10" y2="10"/>
                            <path d="m9 16 2 2 4-4"/>
                        </svg>
                    </div>
                    <div>
                        <h3 style="color: #0369A1; margin: 0; font-size: 20px; font-weight: 800;">Sarah Vance</h3>
                        <span style="font-size: 13px; color: #0284C7; font-weight: 600;">Caregiver Cockpit</span>
                    </div>
                </div>
                <span style="background: #0284C7; color: white; padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 800;">PIN: {car_pin_active}</span>
            </div>
            <p style="color: #475569; font-size: 14px; line-height: 1.5; margin: 0;">
                Live schedule monitoring, drug interaction checks, and email escalation alerts.
            </p>
        </div>
    """, unsafe_allow_html=True)

    if active_role == "caretaker":
        if st.button("Enter Caregiver Cockpit (Active Session)", width="stretch", type="primary"):
            st.switch_page("pages/2_Caretaker_Dashboard.py")
    else:
        if st.button(f"Quick Enter as Sarah (PIN: {car_pin_active})", key="quick_car_enter", width="stretch", type="primary") and login_user("caretaker", car_pin_active):
            st.success("Welcome back, Sarah!")
            st.switch_page("pages/2_Caretaker_Dashboard.py")

        with st.expander("Or enter custom Caregiver PIN"):
            car_pin = st.text_input("Caregiver Passcode (PIN)", type="password", placeholder=f"Default: {car_pin_active}", key="home_car_pin")
            if st.button("Unlock Caregiver Cockpit", width="stretch", key="btn_unlock_car_custom"):
                if car_pin and login_user("caretaker", car_pin):
                    st.success("Authenticated as Sarah Vance (Caregiver)!")
                    st.switch_page("pages/2_Caretaker_Dashboard.py")
                else:
                    st.error(f"Invalid PIN. The configured PIN is {car_pin_active}.")

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# Quick Stats
st.subheader("Daily Status")

p_patient = get_patient(1)
p_doses = get_todays_doses(1)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        label="Patient",
        value=p_patient["name"] if p_patient else "Eleanor Vance",
    )

with c2:
    taken_cnt = sum(1 for d in p_doses if d["status"] == "TAKEN")
    st.metric(
        label="Today's Doses",
        value=f"{taken_cnt} / {len(p_doses)} Taken",
        delta=f"{(taken_cnt / len(p_doses) * 100):.0f}% Done" if p_doses else "0%",
    )

with c3:
    google_health = get_google_services_health()
    st.metric(
        label="Alert Gateway",
        value=google_health["status_label"],
    )

with c4:
    alert_sum = get_alert_summary(1)
    st.metric(
        label="Safety Alerts",
        value=f"{alert_sum['total']} Logged",
        delta=f"{alert_sum['critical']} Urgent" if alert_sum['critical'] > 0 else "Normal",
        delta_color="inverse" if alert_sum['critical'] > 0 else "normal",
    )

# Clean, Simplified 4 Feature Cards (Short text, zero clutter)
st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
f1, f2, f3, f4 = st.columns(4)

with f1:
    st.markdown("""
        <div class="gc-card" style="border-top: 3px solid #10B981; padding: 18px; height: 100%;">
            <strong style="color: #065F46; font-size: 15px;">Voice Guidance</strong>
            <p style="color: #64748B; font-size: 13px; line-height: 1.4; margin: 6px 0 0 0;">
                Spoken dose instructions with a single tap.
            </p>
        </div>
    """, unsafe_allow_html=True)

with f2:
    st.markdown("""
        <div class="gc-card" style="border-top: 3px solid #0284C7; padding: 18px; height: 100%;">
            <strong style="color: #0369A1; font-size: 15px;">Proactive Alerts</strong>
            <p style="color: #64748B; font-size: 13px; line-height: 1.4; margin: 6px 0 0 0;">
                Automated email alerts if a dose is overdue.
            </p>
        </div>
    """, unsafe_allow_html=True)

with f3:
    st.markdown("""
        <div class="gc-card" style="border-top: 3px solid #8B5CF6; padding: 18px; height: 100%;">
            <strong style="color: #5B21B6; font-size: 15px;">Prescription Safety</strong>
            <p style="color: #64748B; font-size: 13px; line-height: 1.4; margin: 6px 0 0 0;">
                Real-time drug interaction safety checks.
            </p>
        </div>
    """, unsafe_allow_html=True)

with f4:
    st.markdown("""
        <div class="gc-card" style="border-top: 3px solid #F59E0B; padding: 18px; height: 100%;">
            <strong style="color: #B45309; font-size: 15px;">Doctor Dossier</strong>
            <p style="color: #64748B; font-size: 13px; line-height: 1.4; margin: 6px 0 0 0;">
                One-click export of clinical adherence trends.
            </p>
        </div>
    """, unsafe_allow_html=True)
