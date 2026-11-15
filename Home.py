"""
GoldenCare — Autonomous Elderly Care & Medication Management Platform.
Main application entry point, passcode-based authentication routing,
and platform overview.
"""

from __future__ import annotations

import streamlit as st
from datetime import datetime, date

# Configure Streamlit page settings
st.set_page_config(
    page_title="GoldenCare | Compassionate Healthcare Platform",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize database and tables
from db.database import init_db, seed_initial_data, get_patient, get_users, get_medications, get_todays_doses
from utils.auth import init_session_state, get_current_user, login_user, logout_user
from utils.alerts import get_smtp_config, check_and_trigger_alerts, get_alert_summary
from utils.google_services import get_google_services_health
from components.header import render_app_header, render_alert_banner

# Run schema initialization and initial seed data population
init_db()
seed_initial_data()
init_session_state()

# Global Header & Navigation
render_app_header()
render_alert_banner()

# Warm, Welcoming Hero Banner
st.markdown("""
    <div style="
        background: linear-gradient(135deg, #064E3B 0%, #065F46 45%, #0F766E 100%);
        color: white;
        padding: 38px 40px;
        border-radius: 24px;
        margin-bottom: 28px;
        box-shadow: 0 16px 36px -10px rgba(6, 78, 59, 0.35);
        position: relative;
        overflow: hidden;
    ">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px;">
            <div style="flex: 1; min-width: 320px;">
                <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px;">
                    <span style="background: rgba(255,255,255,0.18); backdrop-filter: blur(8px); padding: 4px 12px; border-radius: 9999px; font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; border: 1px solid rgba(255,255,255,0.25);">
                        Certified Health Platform
                    </span>
                    <span style="background: rgba(16, 185, 129, 0.25); color: #A7F3D0; padding: 4px 12px; border-radius: 9999px; font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; border: 1px solid rgba(16, 185, 129, 0.4);">
                        Live Family Sync Active
                    </span>
                </div>
                <h1 style="color: white; margin: 0 0 10px 0; font-size: 38px; font-weight: 800; line-height: 1.15; letter-spacing: -0.02em;">
                    Gentle Care & Peace of Mind for Your Loved Ones
                </h1>
                <p style="color: #D1FAE5; font-size: 17px; max-width: 760px; line-height: 1.6; margin: 0 0 18px 0; font-weight: 400;">
                    A warm, interconnected healthcare companion connecting seniors with their families.
                    Seniors enjoy large tactile buttons and spoken reminders, while caregivers stay informed in real time.
                </p>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <span style="background: rgba(255,255,255,0.12); padding: 5px 12px; border-radius: 8px; font-size: 12.5px; font-weight: 600; color: #ECFDF5;">
                        Spoken Voice Guidance
                    </span>
                    <span style="background: rgba(255,255,255,0.12); padding: 5px 12px; border-radius: 8px; font-size: 12.5px; font-weight: 600; color: #ECFDF5;">
                        Automatic Family Reminders
                    </span>
                    <span style="background: rgba(255,255,255,0.12); padding: 5px 12px; border-radius: 8px; font-size: 12.5px; font-weight: 600; color: #ECFDF5;">
                        Prescription Safety Guard
                    </span>
                    <span style="background: rgba(255,255,255,0.12); padding: 5px 12px; border-radius: 8px; font-size: 12.5px; font-weight: 600; color: #ECFDF5;">
                        Doctor Consultation Dossier
                    </span>
                </div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Authentication & Fast Role Switcher Section
st.subheader("Select Profile & Enter Portal")
st.caption("Choose your profile below. Click the direct button to enter with the pre-configured PIN, or type a custom PIN.")

curr_user = get_current_user()
active_role = curr_user.get("role")

all_users = get_users()
eld_user = next((u for u in all_users if u["role"] == "elderly"), None)
car_user = next((u for u in all_users if u["role"] == "caretaker"), None)
eld_pin_active = eld_user["passcode"] if eld_user and eld_user.get("passcode") else "1234"
car_pin_active = car_user["passcode"] if car_user and car_user.get("passcode") else "8888"

if active_role:
    st.markdown(f"""
        <div style="background: #ECFDF5; border: 2px solid #10B981; border-radius: 14px; padding: 14px 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
                <strong style="color: #065F46; font-size: 16px;">Currently Logged In:</strong> 
                <span style="color: #047857; font-size: 16px; font-weight: 700;">{curr_user.get('name')} ({active_role.capitalize()})</span>
            </div>
            <span style="font-size: 13px; color: #065F46;">Switch profiles below or use the top navigation menu.</span>
        </div>
    """, unsafe_allow_html=True)

col_eld, col_car = st.columns(2)

with col_eld:
    st.markdown(f"""
        <div class="gc-card" style="
            border: 2px solid #10B981;
            background: linear-gradient(180deg, #F0FDF4 0%, #FFFFFF 100%);
            border-radius: 22px;
            padding: 26px;
            min-height: 250px;
            box-shadow: 0 8px 24px -4px rgba(16, 185, 129, 0.12);
        ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 14px;">
                    <div style="
                        width: 52px;
                        height: 52px;
                        background: #DCFCE7;
                        border-radius: 16px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border: 2px solid #86EFAC;
                    ">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#047857" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>
                        </svg>
                    </div>
                    <div>
                        <h3 style="color: #065F46; margin: 0; font-size: 22px; font-weight: 800;">Eleanor Vance</h3>
                        <span style="font-size: 13.5px; color: #047857; font-weight: 600;">Senior Patient Portal (Age 78)</span>
                    </div>
                </div>
                <span style="
                    background: #059669;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 9999px;
                    font-size: 12px;
                    font-weight: 800;
                    letter-spacing: 0.04em;
                ">PIN: {eld_pin_active}</span>
            </div>
            <p style="color: #334155; font-size: 15px; line-height: 1.55; margin: 0 0 16px 0;">
                Designed for comfort: <strong>Extra-large text (28px+)</strong>, clear visual pill colors, 
                <strong>spoken voice instructions</strong> with one tap, and an emergency help button.
            </p>
            <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px;">
                <span style="background: #E2E8F0; color: #334155; font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 8px;">Large Text</span>
                <span style="background: #E2E8F0; color: #334155; font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 8px;">Spoken Audio</span>
                <span style="background: #E2E8F0; color: #334155; font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 8px;">1-Tap Logging</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if active_role == "elderly":
        if st.button("Enter Senior Portal (Active Session)", width="stretch", type="primary"):
            st.switch_page("pages/1_Elderly_Dashboard.py")
    else:
        # Direct one-click entrance with pre-configured PIN
        if st.button(f"Quick Enter as Eleanor (PIN: {eld_pin_active})", key="quick_eld_enter", width="stretch", type="primary"):
            if login_user("elderly", eld_pin_active):
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
            border-radius: 22px;
            padding: 26px;
            min-height: 250px;
            box-shadow: 0 8px 24px -4px rgba(2, 132, 199, 0.12);
        ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 14px;">
                    <div style="
                        width: 52px;
                        height: 52px;
                        background: #E0F2FE;
                        border-radius: 16px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border: 2px solid #7DD3FC;
                    ">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0284C7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
                            <line x1="16" x2="16" y1="2" y2="6"/>
                            <line x1="8" x2="8" y1="2" y2="6"/>
                            <line x1="3" x2="21" y1="10" y2="10"/>
                            <path d="m9 16 2 2 4-4"/>
                        </svg>
                    </div>
                    <div>
                        <h3 style="color: #0369A1; margin: 0; font-size: 22px; font-weight: 800;">Sarah Vance</h3>
                        <span style="font-size: 13.5px; color: #0284C7; font-weight: 600;">Caregiver & Family Cockpit</span>
                    </div>
                </div>
                <span style="
                    background: #0284C7;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 9999px;
                    font-size: 12px;
                    font-weight: 800;
                    letter-spacing: 0.04em;
                ">PIN: {car_pin_active}</span>
            </div>
            <p style="color: #334155; font-size: 15px; line-height: 1.55; margin: 0 0 16px 0;">
                Clinical peace of mind: Track adherence, review <strong>drug-drug interaction safety</strong>,
                manage prescriptions, and receive <strong>proactive email alerts</strong> if a dose is missed.
            </p>
            <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px;">
                <span style="background: #E2E8F0; color: #334155; font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 8px;">Adherence Charts</span>
                <span style="background: #E2E8F0; color: #334155; font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 8px;">Drug Safety</span>
                <span style="background: #E2E8F0; color: #334155; font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 8px;">Email Alerts</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if active_role == "caretaker":
        if st.button("Enter Caregiver Cockpit (Active Session)", width="stretch", type="primary"):
            st.switch_page("pages/2_Caretaker_Dashboard.py")
    else:
        # Direct one-click entrance with pre-configured PIN
        if st.button(f"Quick Enter as Sarah (PIN: {car_pin_active})", key="quick_car_enter", width="stretch", type="primary"):
            if login_user("caretaker", car_pin_active):
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

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# Quick Stats and System Health Dashboard
st.subheader("Daily Care Snapshot & System Status")

p_patient = get_patient(1)
p_doses = get_todays_doses(1)
smtp_cfg = get_smtp_config()

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        label="Monitored Patient",
        value=p_patient["name"] if p_patient else "Eleanor Vance",
        help="Monitored senior patient profile"
    )

with c2:
    taken_cnt = sum(1 for d in p_doses if d["status"] == "TAKEN")
    st.metric(
        label="Today's Doses",
        value=f"{taken_cnt} / {len(p_doses)} Taken",
        delta=f"{(taken_cnt / len(p_doses) * 100):.0f}% Completed" if p_doses else "0%",
    )

with c3:
    google_health = get_google_services_health()
    st.metric(
        label="Alert & Email System",
        value=google_health["status_label"],
        help=f"Alert Gateway ({google_health['server']})",
    )

with c4:
    alert_sum = get_alert_summary(1)
    st.metric(
        label="Safety Alerts",
        value=f"{alert_sum['total']} Logged",
        delta=f"{alert_sum['critical']} Urgent" if alert_sum['critical'] > 0 else "All Clear",
        delta_color="inverse" if alert_sum['critical'] > 0 else "normal",
    )

# How GoldenCare Protects Your Family (4 Pillars)
st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
st.markdown("""
    <div style="margin-bottom: 20px;">
        <h2 style="color: #0F172A; margin: 0; font-size: 26px; font-weight: 800;">Four Pillars of Connected Care</h2>
        <span style="color: #64748B; font-size: 15px;">Thoughtfully engineered to make elderly healthcare simpler, safer, and collaborative.</span>
    </div>
""", unsafe_allow_html=True)

f1, f2, f3, f4 = st.columns(4)

with f1:
    st.markdown("""
        <div class="gc-card" style="border-top: 4px solid #10B981; height: 100%;">
            <div style="font-size: 12px; font-weight: 800; color: #059669; text-transform: uppercase; margin-bottom: 6px;">Pillar 1</div>
            <h4 style="color: #065F46; margin: 0 0 8px 0; font-size: 17px; font-weight: 800;">Voice Guidance</h4>
            <p style="color: #475569; font-size: 13.5px; line-height: 1.5; margin: 0;">
                Browser speaks instructions aloud in a gentle, calibrated voice with zero delay, ideal for seniors with visual fatigue.
            </p>
        </div>
    """, unsafe_allow_html=True)

with f2:
    st.markdown("""
        <div class="gc-card" style="border-top: 4px solid #0284C7; height: 100%;">
            <div style="font-size: 12px; font-weight: 800; color: #0284C7; text-transform: uppercase; margin-bottom: 6px;">Pillar 2</div>
            <h4 style="color: #0369A1; margin: 0 0 8px 0; font-size: 17px; font-weight: 800;">Proactive Alerts</h4>
            <p style="color: #475569; font-size: 13.5px; line-height: 1.5; margin: 0;">
                If a vital medication is overdue by 30 minutes, GoldenCare automatically notifies family caregivers via secure email.
            </p>
        </div>
    """, unsafe_allow_html=True)

with f3:
    st.markdown("""
        <div class="gc-card" style="border-top: 4px solid #8B5CF6; height: 100%;">
            <div style="font-size: 12px; font-weight: 800; color: #8B5CF6; text-transform: uppercase; margin-bottom: 6px;">Pillar 3</div>
            <h4 style="color: #5B21B6; margin: 0 0 8px 0; font-size: 17px; font-weight: 800;">Prescription Safety</h4>
            <p style="color: #475569; font-size: 13.5px; line-height: 1.5; margin: 0;">
                Evaluates every new prescription against clinical contraindication rules, stopping dangerous drug interactions.
            </p>
        </div>
    """, unsafe_allow_html=True)

with f4:
    st.markdown("""
        <div class="gc-card" style="border-top: 4px solid #F59E0B; height: 100%;">
            <div style="font-size: 12px; font-weight: 800; color: #D97706; text-transform: uppercase; margin-bottom: 6px;">Pillar 4</div>
            <h4 style="color: #B45309; margin: 0 0 8px 0; font-size: 17px; font-weight: 800;">Doctor Dossier</h4>
            <p style="color: #475569; font-size: 13.5px; line-height: 1.5; margin: 0;">
                One-click export of 14-day adherence trends and vital signs, ready to print or email to the primary physician.
            </p>
        </div>
    """, unsafe_allow_html=True)

# Family Care Assurance Note
st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
st.markdown("""
    <div style="
        background: #F8FAFC;
        border: 1.5px solid #E2E8F0;
        border-radius: 18px;
        padding: 20px 24px;
        margin-top: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
    ">
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 38px; height: 38px; border-radius: 10px; background: #ECFDF5; border: 1.5px solid #A7F3D0; display: flex; align-items: center; justify-content: center;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/>
                </svg>
            </div>
            <div>
                <strong style="color: #0F172A; font-size: 15px;">Private, Protected Healthcare Environment</strong>
                <div style="color: #64748B; font-size: 13.5px;">All patient medical telemetry and medication records are encrypted and stored securely.</div>
            </div>
        </div>
        <span style="background: #ECFDF5; color: #065F46; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700;">
            Secure Family Network Active
        </span>
    </div>
""", unsafe_allow_html=True)
