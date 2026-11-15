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

# Security gate
require_auth(allowed_roles=["elderly", "caretaker"])

render_app_header()
render_alert_banner()

curr_user = get_current_user()
patient_id = curr_user.get("patient_id", 1)
patient = get_patient(patient_id)
patient_name = patient["name"] if patient else "Eleanor"

# Time-based greeting
current_hour = datetime.now().hour
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

today_display = datetime.now().strftime("%A, %B %d, %Y")

# High-accessibility Header
col_greet, col_acc = st.columns([3, 1])

with col_greet:
    st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <span style="font-size: 20px; font-weight: 700; color: #059669; text-transform: uppercase;">
                {time_icon} {today_display}
            </span>
            <h1 style="font-size: 38px; font-weight: 800; color: #0F172A; margin: 4px 0 0 0;">
                {greeting_prefix}, {patient_name.split()[0]}!
            </h1>
        </div>
    """, unsafe_allow_html=True)

with col_acc:
    high_contrast = st.toggle("🔍 High Contrast Mode", key="toggle_high_contrast", value=st.session_state.get("high_contrast", False))
    st.session_state["high_contrast"] = high_contrast

# Retrieve today's medication doses
doses = get_todays_doses(patient_id)
total_doses = len(doses)
taken_doses = sum(1 for d in doses if d["status"] == "TAKEN")
pending_doses = total_doses - taken_doses

# Accessibility Progress Bar & Audio Schedule Summary
col_prog, col_audio = st.columns([2.5, 1.5])

with col_prog:
    progress_val = (taken_doses / total_doses) if total_doses > 0 else 1.0
    st.markdown(f"""
        <div style="font-size: 18px; font-weight: 700; color: #1E293B; margin-bottom: 6px;">
            Today's Progress: {taken_doses} of {total_doses} doses taken ({int(progress_val * 100)}%)
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
    
    render_speech_button(text_to_speak=speech_overview, label="🔊 Read Today's Plan", button_id="tts_overall_schedule")

st.markdown("<hr style='border: 0; border-top: 2px solid #CBD5E1; margin: 20px 0;'/>", unsafe_allow_html=True)

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
            render_elderly_dose_card(dose, high_contrast=high_contrast)

with tab_morn:
    morning_doses = [d for d in doses if d["time_of_day"] == "Morning"]
    if not morning_doses:
        st.info("No morning medications scheduled.")
    else:
        for dose in morning_doses:
            render_elderly_dose_card(dose, high_contrast=high_contrast)

with tab_aft:
    afternoon_doses = [d for d in doses if d["time_of_day"] == "Afternoon"]
    if not afternoon_doses:
        st.info("No afternoon medications scheduled.")
    else:
        for dose in afternoon_doses:
            render_elderly_dose_card(dose, high_contrast=high_contrast)

with tab_eve:
    evening_doses = [d for d in doses if d["time_of_day"] == "Evening"]
    if not evening_doses:
        st.info("No evening medications scheduled.")
    else:
        for dose in evening_doses:
            render_elderly_dose_card(dose, high_contrast=high_contrast)

with tab_bed:
    bedtime_doses = [d for d in doses if d["time_of_day"] == "Bedtime"]
    if not bedtime_doses:
        st.info("No bedtime medications scheduled.")
    else:
        for dose in bedtime_doses:
            render_elderly_dose_card(dose, high_contrast=high_contrast)

# Doctor Appointment Reminder Section
st.markdown("<hr style='border: 0; border-top: 2px solid #CBD5E1; margin: 30px 0 20px 0;'/>", unsafe_allow_html=True)
st.subheader("📅 Your Upcoming Doctor Visits")

appointments = get_appointments(patient_id, status="SCHEDULED")
if appointments:
    next_apt = appointments[0]
    apt_date = datetime.strptime(next_apt["appointment_date"], "%Y-%m-%d").strftime("%A, %B %d")
    
    st.markdown(f"""
        <div style="
            background: #EFF6FF;
            border: 3px solid #3B82F6;
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 20px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="color: #1E40AF; margin: 0; font-size: 22px;">🩺 {next_apt['title']}</h3>
                <span style="background: #2563EB; color: white; padding: 4px 12px; border-radius: 9999px; font-weight: 700; font-size: 14px;">
                    {apt_date} at {next_apt['appointment_time']}
                </span>
            </div>
            <p style="font-size: 17px; color: #1E3A8A; margin: 8px 0 4px 0;">
                <strong>Physician:</strong> {next_apt['doctor_name']} • <strong>Location:</strong> {next_apt['clinic_address']}
            </p>
            <p style="font-size: 15px; color: #3B82F6; margin: 0;">
                🚗 <strong>Transport:</strong> {'Arranged by Caregiver' if next_apt['transport_required'] else 'Self-Transport'} | 📝 <strong>Notes:</strong> {next_apt['prep_notes']}
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    apt_speech = f"Reminder: You have an appointment for {next_apt['title']} with {next_apt['doctor_name']} on {apt_date} at {next_apt['appointment_time']}. Location is {next_apt['clinic_address']}."
    render_speech_button(text_to_speak=apt_speech, label="🔊 Read Appointment Details", button_id="tts_next_appointment")
else:
    st.info("No upcoming doctor appointments scheduled this week.")

# Emergency Assistance SOS Trigger
if patient:
    render_elderly_sos_widget(patient)
