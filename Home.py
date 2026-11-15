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
    page_title="GoldenCare | Elderly Care Platform",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database and tables
from db.database import init_db, seed_initial_data, get_patient, get_users, get_medications, get_todays_doses
from utils.auth import init_session_state, get_current_user, login_user, logout_user
from utils.alerts import get_smtp_config, check_and_trigger_alerts, get_alert_summary
from components.header import render_app_header, render_alert_banner

# Run schema initialization and initial seed data population
init_db()
seed_initial_data()
init_session_state()

# Global Header & Navigation
render_app_header()
render_alert_banner()

# App Hero Banner
st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 50%, #3B82F6 100%);
        color: white;
        padding: 32px;
        border-radius: 16px;
        margin-bottom: 24px;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.2);
    ">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
            <div>
                <span style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 9999px; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                    Catalyst Hackathon Submission • Autonomous Healthcare
                </span>
                <h1 style="color: white; margin: 12px 0 8px 0; font-size: 34px; font-weight: 800;">
                    🌿 GoldenCare Synchronized Ecosystem
                </h1>
                <p style="color: #E0E7FF; font-size: 17px; max-width: 720px; line-height: 1.5; margin: 0;">
                    A unified care bridge connecting seniors and family caregivers through accessible touch controls,
                    proactive email escalation alerts, automated adherence intelligence, and clinical safety checks.
                </p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Authentication & Fast Role Switcher Section
st.subheader("🔐 Secure Passcode Authentication & Role Switcher")
st.caption("Select your profile and enter your 4-digit security PIN to access specialized interfaces.")

curr_user = get_current_user()
active_role = curr_user.get("role")

if active_role:
    st.markdown(f"""
        <div style="background: #F0FDF4; border: 2px solid #10B981; border-radius: 10px; padding: 14px 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
                <strong style="color: #065F46; font-size: 16px;">🟢 Currently Authenticated:</strong> 
                <span style="color: #047857; font-size: 16px;">{curr_user.get('name')} ({active_role.capitalize()})</span>
            </div>
            <span style="font-size: 13px; color: #065F46;">Switch roles below or click Log Out in the top navigation.</span>
        </div>
    """, unsafe_allow_html=True)

col_eld, col_car = st.columns(2)

with col_eld:
    st.markdown("""
        <div style="
            border: 2px solid #10B981;
            background: #F0FDF4;
            border-radius: 12px;
            padding: 20px;
            min-height: 220px;
        ">
            <h3 style="color: #065F46; margin-top: 0; display: flex; align-items: center; gap: 8px;">
                <span>👴</span> Senior / Elderly Portal
            </h3>
            <p style="color: #047857; font-size: 14px; line-height: 1.4;">
                High-contrast, large-print tactile interface. Audio readout of doses, one-tap "Took It" confirmation,
                and emergency SOS alert trigger.
            </p>
            <p style="font-size: 12px; color: #065F46;"><strong>Assigned Profile:</strong> Eleanor Vance (Age 78)</p>
            <p style="font-size: 12px; color: #065F46;"><strong>Default Passcode:</strong> <code>1234</code></p>
        </div>
    """, unsafe_allow_html=True)
    
    eld_pin = st.text_input("Senior Passcode (PIN)", type="password", value="1234", key="home_eld_pin")
    if st.button("🚀 Enter Senior Portal (PIN: 1234)", use_container_width=True, type="primary" if active_role == "elderly" else "secondary"):
        if login_user("elderly", eld_pin):
            st.success("Authenticated as Eleanor Vance (Senior)!")
            st.switch_page("pages/1_Elderly_Dashboard.py")
        else:
            st.error("Invalid Senior PIN. Default is 1234.")

with col_car:
    st.markdown("""
        <div style="
            border: 2px solid #2563EB;
            background: #EFF6FF;
            border-radius: 12px;
            padding: 20px;
            min-height: 220px;
        ">
            <h3 style="color: #1E40AF; margin-top: 0; display: flex; align-items: center; gap: 8px;">
                <span>🩺</span> Caregiver Clinical Cockpit
            </h3>
            <p style="color: #1D4ED8; font-size: 14px; line-height: 1.4;">
                Full adherence analytics, longitudinal vitals tracking, prescription refill monitors,
                drug-drug interaction safety checker, and automated SMTP escalation controls.
            </p>
            <p style="font-size: 12px; color: #1E40AF;"><strong>Assigned Profile:</strong> Sarah Vance (Caregiver)</p>
            <p style="font-size: 12px; color: #1E40AF;"><strong>Default Passcode:</strong> <code>8888</code></p>
        </div>
    """, unsafe_allow_html=True)
    
    car_pin = st.text_input("Caregiver Passcode (PIN)", type="password", value="8888", key="home_car_pin")
    if st.button("🚀 Enter Caregiver Cockpit (PIN: 8888)", use_container_width=True, type="primary" if active_role == "caretaker" else "secondary"):
        if login_user("caretaker", car_pin):
            st.success("Authenticated as Sarah Vance (Caregiver)!")
            st.switch_page("pages/2_Caretaker_Dashboard.py")
        else:
            st.error("Invalid Caregiver PIN. Default is 8888.")

st.markdown("---")

# Quick Stats and System Health Dashboard
st.subheader("📊 Platform Health & Operational Status")

p_patient = get_patient(1)
p_doses = get_todays_doses(1)
smtp_cfg = get_smtp_config()

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        label="Active Patient",
        value=p_patient["name"] if p_patient else "Eleanor Vance",
        help="Monitored senior patient profile"
    )

with c2:
    taken_cnt = sum(1 for d in p_doses if d["status"] == "TAKEN")
    st.metric(
        label="Today's Dose Progress",
        value=f"{taken_cnt} / {len(p_doses)} Doses",
        delta=f"{(taken_cnt / len(p_doses) * 100):.0f}% Complete" if p_doses else "0%",
    )

with c3:
    smtp_status = "🟢 Live SMTP TLS" if smtp_cfg["is_configured"] else "🟡 Sandbox / Audit Log"
    st.metric(
        label="Email Alert Engine",
        value=smtp_status,
        help="Proactive SMTP notification delivery status",
    )

with c4:
    alert_sum = get_alert_summary(1)
    st.metric(
        label="Active Audit Alerts",
        value=f"{alert_sum['total']} Logged",
        delta=f"{alert_sum['critical']} Critical" if alert_sum['critical'] > 0 else "All Clear",
        delta_color="inverse" if alert_sum['critical'] > 0 else "normal",
    )

# Killer Features Architecture Highlight
st.markdown("---")
st.subheader("💡 Three Beyond-Basic Killer Architectural Features")

f1, f2, f3 = st.columns(3)

with f1:
    st.markdown("""
        #### 1. ⚡ Autonomous Escalation Engine
        - **Automatic Overdue Detection:** If a dose is unconfirmed >30 minutes past its scheduled slot, it automatically escalates to `MISSED`.
        - **Proactive SMTP Alerts:** Immediate dispatch of emergency/missed dose emails to family caregivers.
        - **Refill Anticipation:** Automatically notifies caregivers when pills hit restock thresholds.
    """)

with f2:
    st.markdown("""
        #### 2. 🔊 Accessible Voice & Tactile UX
        - **Web Speech API Audio:** Offline natural voice guidance reads prescription details aloud for visually impaired seniors.
        - **Color & Shape Indicators:** High-contrast color pills (Blue, Pink, Gold) with tablet/capsule badges.
        - **Giant Touch Targets:** One-tap dose confirmation designed specifically for seniors with tremors or arthritis.
    """)

with f3:
    st.markdown("""
        #### 3. 🔬 Clinical Safety & Analytics
        - **Drug-Drug Interaction Engine:** Scans medication combinations for dangerous contraindications (e.g., Warfarin + Aspirin, ACE inhibitors + NSAIDs).
        - **Time-Drift Analysis:** Quantifies schedule variance to spot early signs of cognitive decline or routine disruption.
        - **Longitudinal Vitals Overlay:** Cross-correlates blood pressure and glucose with medication adherence.
    """)

# Evaluator Guidance Note
st.info("""
    🎯 **Hackathon Jury & Evaluator Guide:** 
    Use the top sidebar navigation to seamlessly explore all 6 dedicated modules:
    **1. Elderly Dashboard** • **2. Caretaker Dashboard** • **3. Appointments and Calendar** • **4. Adherence Analytics** • **5. Medication Manager** • **6. System Settings**.
""")
