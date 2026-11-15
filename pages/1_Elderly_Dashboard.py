"""
Senior / Elderly Accessible Touch Portal for GoldenCare.
Engineered for seniors with large fonts, high-contrast visual cues,
audio readouts, and effortless one-tap dose logging.
"""

from __future__ import annotations

import streamlit as st
from datetime import datetime, date

from utils.auth import require_auth, get_current_user
from db.database import get_patient, get_todays_doses, get_appointments
from components.header import render_app_header, render_alert_banner
from components.elderly_ui import render_elderly_dose_card, render_elderly_sos_widget
from utils.tts import render_speech_button
from utils.timezone_util import get_now

# Security gate
require_auth(allowed_roles=["elderly", "caretaker"])

render_app_header()
render_alert_banner()

curr_user = get_current_user()
patient_id = curr_user.get("patient_id", 1)
patient = get_patient(patient_id)
patient_name = patient["name"] if patient else "Eleanor"

# Time-based greeting using platform timezone
now_dt = get_now()
current_hour = now_dt.hour
if current_hour < 12:
    greeting_prefix = "Good Morning"
    time_icon = "🌅"
elif current_hour < 17:
    greeting_prefix = "Good Afternoon"
    time_icon = "☀️"
elif current_hour < 21:
    greeting_prefix = "Good Evening"
    time_icon = "🌆"
else:
    greeting_prefix = "Good Night"
    time_icon = "🌙"

today_display = now_dt.strftime("%A, %B %d, %Y")

# High-accessibility Header
col_greet, col_acc = st.columns([3, 1])

with col_greet:
    st.markdown(f"""
        <div style="margin-bottom: 14px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                <span style="font-size: 16px; font-weight: 800; color: #059669; text-transform: uppercase; letter-spacing: 0.05em;">
                    {time_icon} {today_display}
                </span>
                <span style="
                    background: #FEF3C7;
                    color: #92400E;
                    padding: 3px 10px;
                    border-radius: 9999px;
                    font-size: 13px;
                    font-weight: 700;
                    border: 1px solid #FCD34D;
                ">
                    🔥 3-Day Adherence Streak!
                </span>
            </div>
            <h1 style="font-size: 40px; font-weight: 800; color: #0F172A; margin: 0; font-family: 'Outfit', sans-serif;">
                {greeting_prefix}, {patient_name.split()[0]}!
            </h1>
        </div>
    """, unsafe_allow_html=True)

with col_acc:
    high_contrast = st.toggle("🔍 High Contrast Mode", key="toggle_high_contrast", value=st.session_state.get("high_contrast", False))
    st.session_state["high_contrast"] = high_contrast

if high_contrast:
    st.markdown("""
        <style>
            html, body, [class*="css"] {
                font-size: 20px !important;
                color: #000000 !important;
            }
            .stButton > button {
                font-size: 22px !important;
                font-weight: 800 !important;
                min-height: 56px !important;
                border: 3px solid #000000 !important;
            }
            div[data-testid="stMetricValue"] {
                font-size: 32px !important;
                font-weight: 900 !important;
            }
            .stTabs [data-baseweb="tab"] {
                font-size: 20px !important;
                font-weight: 700 !important;
                padding: 12px 24px !important;
            }
        </style>
    """, unsafe_allow_html=True)

# Retrieve today's medication doses
doses = get_todays_doses(patient_id)
total_doses = len(doses)
taken_doses = sum(1 for d in doses if d["status"] == "TAKEN")
pending_doses = total_doses - taken_doses

# Accessibility Progress Bar & Audio Schedule Summary
col_prog, col_audio = st.columns([2.6, 1.4])

with col_prog:
    progress_val = (taken_doses / total_doses) if total_doses > 0 else 1.0
    st.markdown(f"""
        <div class="gc-card" style="padding: 18px 24px; margin-bottom: 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 17px; font-weight: 800; color: #1E293B;">
                    Today's Medication Progress
                </span>
                <div style="display: flex; gap: 8px;">
                    <span style="background: #ECFDF5; color: #065F46; padding: 2px 10px; border-radius: 9999px; font-size: 13px; font-weight: 700;">
                        🟢 {taken_doses} Taken
                    </span>
                    <span style="background: #EFF6FF; color: #1E40AF; padding: 2px 10px; border-radius: 9999px; font-size: 13px; font-weight: 700;">
                        ⏳ {pending_doses} Remaining
                    </span>
                </div>
            </div>
            <div style="font-size: 14px; color: #64748B; margin-bottom: 10px;">
                {taken_doses} of {total_doses} doses completed ({int(progress_val * 100)}%)
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.progress(progress_val)

with col_audio:
    # Build complete schedule speech summary
    pending_names = [f"{d['medication_name']} ({d['time_of_day']})" for d in doses if d['status'] != 'TAKEN']
    if pending_names:
        speech_overview = f"Hello {patient_name.split()[0]}. Today is {today_display}. You have {len(pending_names)} doses remaining: {', '.join(pending_names)}. Please take your medicines on time."
    else:
        speech_overview = f"Congratulations {patient_name.split()[0]}! You have completed all of your scheduled medications for today. Have a wonderful day!"
    
    st.markdown("""
        <div style="padding-top: 10px;">
            <span style="font-size: 13px; font-weight: 600; color: #64748B; display: block; margin-bottom: 6px;">Voice Companion:</span>
        </div>
    """, unsafe_allow_html=True)
    render_speech_button(text_to_speak=speech_overview, label="🔊 Read Today's Plan", button_id="tts_overall_schedule")

st.markdown("<hr style='border: 0; border-top: 1px solid #CBD5E1; margin: 20px 0;'/>", unsafe_allow_html=True)

# Time-of-day tabs for clutter-free focus
tab_all, tab_morn, tab_aft, tab_eve, tab_bed = st.tabs([
    f"📋 All Doses ({total_doses})",
    "🌅 Morning",
    "☀️ Afternoon",
    "🌆 Evening",
    "🌙 Bedtime",
])

with tab_all:
    if not doses:
        st.info("No medications are scheduled for today.")
    else:
        for dose in doses:
            render_elderly_dose_card(dose, high_contrast=high_contrast, key_prefix="all")

with tab_morn:
    morning_doses = [d for d in doses if d["time_of_day"] == "Morning"]
    if not morning_doses:
        st.info("No morning medications scheduled.")
    else:
        for dose in morning_doses:
            render_elderly_dose_card(dose, high_contrast=high_contrast, key_prefix="morn")

with tab_aft:
    afternoon_doses = [d for d in doses if d["time_of_day"] == "Afternoon"]
    if not afternoon_doses:
        st.info("No afternoon medications scheduled.")
    else:
        for dose in afternoon_doses:
            render_elderly_dose_card(dose, high_contrast=high_contrast, key_prefix="aft")

with tab_eve:
    evening_doses = [d for d in doses if d["time_of_day"] == "Evening"]
    if not evening_doses:
        st.info("No evening medications scheduled.")
    else:
        for dose in evening_doses:
            render_elderly_dose_card(dose, high_contrast=high_contrast, key_prefix="eve")

with tab_bed:
    bedtime_doses = [d for d in doses if d["time_of_day"] == "Bedtime"]
    if not bedtime_doses:
        st.info("No bedtime medications scheduled.")
    else:
        for dose in bedtime_doses:
            render_elderly_dose_card(dose, high_contrast=high_contrast, key_prefix="bed")

# Doctor Appointment Reminder Section
st.markdown("<hr style='border: 0; border-top: 1px solid #CBD5E1; margin: 36px 0 24px 0;'/>", unsafe_allow_html=True)
st.markdown("""
    <div style="margin-bottom: 16px;">
        <h2 style="color: #0F172A; margin: 0; font-size: 26px; font-weight: 800; font-family: 'Outfit', sans-serif;">
            📅 Upcoming Doctor Visits
        </h2>
        <span style="color: #64748B; font-size: 15px;">Your scheduled clinic visits and physician consultations</span>
    </div>
""", unsafe_allow_html=True)

appointments = get_appointments(patient_id, status="SCHEDULED")
if appointments:
    next_apt = appointments[0]
    apt_date = datetime.strptime(next_apt["appointment_date"], "%Y-%m-%d").strftime("%A, %B %d")
    
    st.markdown(f"""
        <div class="gc-card" style="
            background: linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 100%);
            border: 2px solid #3B82F6;
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 16px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="
                        width: 44px;
                        height: 44px;
                        background: #DBEAFE;
                        border-radius: 12px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 24px;
                    ">🩺</div>
                    <div>
                        <h3 style="color: #1E40AF; margin: 0; font-size: 22px; font-weight: 800;">{next_apt['title']}</h3>
                        <span style="font-size: 15px; color: #1D4ED8; font-weight: 600;">Physician: {next_apt['doctor_name']}</span>
                    </div>
                </div>
                <span style="
                    background: #2563EB;
                    color: white;
                    padding: 6px 14px;
                    border-radius: 9999px;
                    font-weight: 700;
                    font-size: 14px;
                    box-shadow: 0 4px 10px rgba(37, 99, 235, 0.25);
                ">
                    🗓️ {apt_date} • {next_apt['appointment_time']}
                </span>
            </div>
            <div style="font-size: 15px; color: #334155; margin-bottom: 8px;">
                📍 <strong>Facility / Address:</strong> {next_apt['clinic_address']}
            </div>
            <div style="display: flex; gap: 12px; flex-wrap: wrap; font-size: 13.5px;">
                <span style="background: #F1F5F9; color: #1E293B; padding: 4px 10px; border-radius: 8px; font-weight: 600;">
                    🚗 Transport: {'Arranged by Caregiver' if next_apt['transport_required'] else 'Self-Transport'}
                </span>
                <span style="background: #F1F5F9; color: #1E293B; padding: 4px 10px; border-radius: 8px; font-weight: 600;">
                    📝 Notes: {next_apt['prep_notes']}
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    apt_speech = f"Reminder: You have an appointment for {next_apt['title']} with {next_apt['doctor_name']} on {apt_date} at {next_apt['appointment_time']}. Location is {next_apt['clinic_address']}."
    render_speech_button(text_to_speak=apt_speech, label="🔊 Read Appointment Details", button_id="tts_next_appointment")
else:
    st.info("No upcoming doctor appointments scheduled this week.")

# Emergency Assistance SOS Trigger
if patient:
    render_elderly_sos_widget(patient)
