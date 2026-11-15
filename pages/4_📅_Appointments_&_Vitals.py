"""
Clinical Appointments & Health Vitals Telemetry for GoldenCare.
Enables appointment scheduling with transport coordination and
longitudinal biometric tracking (blood pressure, glucose, pulse, weight).
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime, date, time

from utils.auth import require_auth, get_current_user
from db.database import (
    get_patient,
    get_appointments,
    add_appointment,
    update_appointment_status,
    get_vitals,
    add_vitals,
)
from components.header import render_app_header, render_alert_banner
from components.charts import render_vitals_trend_chart

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
        <h1 style="color: #0F172A; margin: 0 0 6px 0;">📅 Appointments & Health Vitals Telemetry</h1>
        <p style="color: #64748B; font-size: 16px; margin: 0;">
            Manage clinical consultations, specialized geriatric exams, and daily physiological biomarkers for <strong>{patient_name}</strong>.
        </p>
    </div>
""", unsafe_allow_html=True)

tab_apts, tab_vitals = st.tabs([
    "🩺 Clinical Appointments Calendar",
    "📈 Daily Vitals & Biometric Tracking",
])

# 1. Appointments Calendar Tab
with tab_apts:
    c_ap1, c_ap2 = st.columns([1.6, 1.4])

    with c_ap1:
        st.subheader("Upcoming Clinical Consultations")
        appointments = get_appointments(patient_id)
        active_apts = [a for a in appointments if a["status"] == "SCHEDULED"]

        if not active_apts:
            st.info("No upcoming appointments scheduled. Schedule one using the form on the right.")
        else:
            for apt in active_apts:
                apt_id = apt["id"]
                apt_dt = datetime.strptime(apt["appointment_date"], "%Y-%m-%d").date()
                days_away = (apt_dt - date.today()).days
                countdown_label = "Today!" if days_away == 0 else (f"Tomorrow" if days_away == 1 else f"In {days_away} days")

                with st.container():
                    st.markdown(f"""
                        <div style="
                            background: white;
                            border: 2px solid #E2E8F0;
                            border-left: 6px solid #2563EB;
                            border-radius: 12px;
                            padding: 16px;
                            margin-bottom: 14px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
                        ">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <strong style="font-size: 18px; color: #1E293B;">{apt['title']}</strong>
                                <span style="background: #EFF6FF; color: #1D4ED8; font-weight: 700; padding: 4px 10px; border-radius: 9999px; font-size: 13px;">
                                    ⏳ {countdown_label} ({apt['appointment_date']} at {apt['appointment_time']})
                                </span>
                            </div>
                            <div style="margin: 8px 0; color: #475569; font-size: 14px;">
                                👨‍⚕️ <strong>Physician:</strong> {apt['doctor_name']} • 🏥 <strong>Clinic:</strong> {apt['clinic_address']}
                            </div>
                            <div style="background: #F8FAFC; padding: 8px 12px; border-radius: 6px; font-size: 13px; color: #334155;">
                                🚗 <strong>Transport Assistance:</strong> {'Required & Scheduled' if apt['transport_required'] else 'Self-Arranged'}<br/>
                                📝 <strong>Prep Instructions:</strong> {apt['prep_notes'] or 'Standard follow-up.'}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    btn_c1, btn_c2 = st.columns([1, 1])
                    with btn_c1:
                        if st.button("Mark Completed", key=f"apt_done_{apt_id}", use_container_width=True):
                            update_appointment_status(apt_id, "COMPLETED")
                            st.success("Appointment completed!")
                            st.rerun()
                    with btn_c2:
                        if st.button("Cancel Appointment", key=f"apt_cancel_{apt_id}", use_container_width=True):
                            update_appointment_status(apt_id, "CANCELLED")
                            st.warning("Appointment cancelled.")
                            st.rerun()

        # Completed Appointments History Expander
        completed_apts = [a for a in appointments if a["status"] != "SCHEDULED"]
        if completed_apts:
            with st.expander(f"📁 Past & Cancelled Consultations ({len(completed_apts)})"):
                for ca in completed_apts:
                    st.write(f"• **{ca['appointment_date']}**: {ca['title']} with {ca['doctor_name']} — Status: *{ca['status']}*")

    with c_ap2:
        st.subheader("Schedule New Appointment")
        with st.form("form_schedule_apt", clear_on_submit=True):
            apt_title = st.text_input("Visit Title *", placeholder="e.g., Geriatric Cardiology Consultation")
            apt_doc = st.text_input("Physician / Specialist *", placeholder="e.g., Dr. Robert Chen, MD")
            apt_address = st.text_input("Clinic / Hospital Address *", placeholder="e.g., St. Luke Medical Center, Suite 300")
            
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                apt_date_val = st.date_input("Date", min_value=date.today())
            with c_d2:
                apt_time_val = st.time_input("Time", value=time(10, 0))

            apt_transport = st.checkbox("Requires Caregiver Transport Coordination", value=True)
            apt_notes = st.text_area("Pre-visit Preparation & Notes", placeholder="e.g., Fasting 8 hours prior; bring blood pressure log.")

            apt_submit = st.form_submit_button("Book & Synchronize Appointment", type="primary", use_container_width=True)

        if apt_submit:
            if not apt_title or not apt_doc or not apt_address:
                st.error("Please fill in the appointment title, physician, and location.")
            else:
                add_appointment(
                    patient_id=patient_id,
                    title=apt_title,
                    doctor_name=apt_doc,
                    clinic_address=apt_address,
                    appointment_date=apt_date_val.isoformat(),
                    appointment_time=apt_time_val.strftime("%H:%M"),
                    transport_required=apt_transport,
                    prep_notes=apt_notes,
                )
                st.success(f"Appointment '{apt_title}' scheduled for {apt_date_val}!")
                st.rerun()

# 2. Daily Health Vitals Telemetry Tab
with tab_vitals:
    vitals_data = get_vitals(patient_id, limit=30)

    # Top Vitals Trend Chart
    st.subheader("📈 Longitudinal Vital Signs Trend")
    st.caption("Cross-referenced with medication adherence to evaluate therapeutic efficacy.")
    st.plotly_chart(render_vitals_trend_chart(vitals_data), use_container_width=True)

    col_v_form, col_v_hist = st.columns([1.3, 1.7])

    with col_v_form:
        st.subheader("Log Today's Vitals")
        with st.form("form_log_vitals", clear_on_submit=True):
            col_bp1, col_bp2 = st.columns(2)
            with col_bp1:
                v_sys = st.number_input("Systolic BP (mmHg)", min_value=70, max_value=240, value=126)
            with col_bp2:
                v_dia = st.number_input("Diastolic BP (mmHg)", min_value=40, max_value=140, value=78)

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                v_glu = st.number_input("Blood Glucose (mg/dL)", min_value=40.0, max_value=400.0, value=112.0, step=1.0)
            with col_g2:
                v_hr = st.number_input("Heart Rate (BPM)", min_value=40, max_value=180, value=72)

            col_w1, col_m1 = st.columns(2)
            with col_w1:
                v_wt = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0, value=64.0, step=0.1)
            with col_m1:
                v_mood = st.selectbox("Patient Mood / Sensation", ["Great", "Good", "Normal", "Tired", "Pain", "Dizzy"])

            v_notes = st.text_input("Notes", placeholder="e.g., Taken before breakfast; resting state.")

            v_submit = st.form_submit_button("Record Vitals", type="primary", use_container_width=True)

        if v_submit:
            now_dt = datetime.now()
            v_id = add_vitals(
                patient_id=patient_id,
                recorded_date=now_dt.strftime("%Y-%m-%d"),
                recorded_time=now_dt.strftime("%H:%M"),
                systolic_bp=v_sys,
                diastolic_bp=v_dia,
                blood_glucose=v_glu,
                heart_rate=v_hr,
                weight_kg=v_wt,
                mood=v_mood,
                notes=v_notes,
            )

            # Abnormality Callout
            if v_sys > 140 or v_glu > 140 or v_hr > 100:
                st.warning("⚠️ Reading registered as ABNORMAL: Elevated metric recorded. Notification logged.")
            else:
                st.success("✅ Vitals safely recorded within standard clinical reference ranges.")
            st.rerun()

    with col_v_hist:
        st.subheader("Recent Biometric Records")
        if vitals_data:
            df_v = pd.DataFrame(vitals_data)
            display_cols = ["recorded_date", "recorded_time", "systolic_bp", "diastolic_bp", "blood_glucose", "heart_rate", "mood", "is_abnormal"]
            df_disp = df_v[display_cols].copy()
            df_disp.columns = ["Date", "Time", "Sys BP", "Dia BP", "Glucose", "HR (BPM)", "Mood", "Abnormal Flag"]
            df_disp["Abnormal Flag"] = df_disp["Abnormal Flag"].map({1: "⚠️ Yes", 0: "✅ Normal"})
            st.dataframe(df_disp, use_container_width=True, hide_index=True)
        else:
            st.info("No vitals records logged yet.")
