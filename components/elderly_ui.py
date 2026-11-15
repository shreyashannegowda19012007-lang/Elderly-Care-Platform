"""
Accessible UI components tailored specifically for elderly users.
Features high contrast, 24px+ typography, visual pill indicators,
audio readouts, and zero-confusion single-tap dose confirmation.
"""

from __future__ import annotations

import streamlit as st
from typing import Dict, Any
from db.database import mark_dose_status
from utils.tts import render_speech_button


def render_elderly_dose_card(dose: Dict[str, Any], high_contrast: bool = False) -> None:
    """
    Render a single medication dose card designed for senior accessibility.
    Large touch targets, clear status badges, and audio readout support.
    """
    log_id = dose["log_id"]
    status = dose["status"]
    name = dose["medication_name"]
    dosage = dose["dosage"]
    scheduled_time = dose["scheduled_time"]
    time_of_day = dose["time_of_day"]
    instructions = dose.get("instructions") or "Take with water."
    pill_color = dose.get("pill_color") or "#2563EB"
    pill_shape = dose.get("pill_shape") or "Tablet"
    taken_at = dose.get("taken_at")

    # Format 24-hr time to friendly 12-hr format
    try:
        hh, mm = map(int, scheduled_time.split(":"))
        period = "AM" if hh < 12 else "PM"
        display_hh = hh if hh <= 12 else hh - 12
        if display_hh == 0:
            display_hh = 12
        time_formatted = f"{display_hh}:{mm:02d} {period}"
    except Exception:
        time_formatted = scheduled_time

    # Card background and border based on status
    if status == "TAKEN":
        card_bg = "#ECFDF5" if not high_contrast else "#FFFFFF"
        border_color = "#10B981"
        badge_text = f"✅ TAKEN" + (f" ({str(taken_at)[11:16]})" if taken_at else "")
        badge_bg = "#059669"
    elif status == "MISSED":
        card_bg = "#FEF2F2" if not high_contrast else "#FFFFFF"
        border_color = "#EF4444"
        badge_text = "⚠️ OVERDUE"
        badge_bg = "#DC2626"
    else:  # PENDING
        card_bg = "#FFFFFF"
        border_color = "#3B82F6"
        badge_text = "⏳ SCHEDULED"
        badge_bg = "#2563EB"

    with st.container():
        # Accessible outer container
        st.markdown(f"""
            <div style="
                background: {card_bg};
                border: 3px solid {border_color};
                border-radius: 16px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.06);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="
                            display: inline-block;
                            width: 22px;
                            height: 22px;
                            border-radius: 50%;
                            background-color: {pill_color};
                            border: 2px solid #0F172A;
                        "></span>
                        <span style="font-size: 16px; font-weight: 700; color: #334155; text-transform: uppercase;">
                            {time_of_day} • {time_formatted} • {pill_shape}
                        </span>
                    </div>
                    <span style="
                        background-color: {badge_bg};
                        color: white;
                        font-weight: 800;
                        padding: 6px 14px;
                        border-radius: 9999px;
                        font-size: 15px;
                        letter-spacing: 0.5px;
                    ">
                        {badge_text}
                    </span>
                </div>
                <div style="font-size: 26px; font-weight: 800; color: #0F172A; margin-bottom: 6px;">
                    {name} <span style="font-size: 20px; font-weight: 600; color: #475569;">({dosage})</span>
                </div>
                <div style="font-size: 18px; color: #334155; line-height: 1.4; margin-bottom: 12px; background: #F1F5F9; padding: 10px 14px; border-radius: 8px;">
                    📋 <strong>Instructions:</strong> {instructions}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Action Buttons Row
        col_btn1, col_btn2 = st.columns([2.5, 1.2])

        with col_btn1:
            if status != "TAKEN":
                btn_label = f"👍 I Took My {name}"
                if st.button(btn_label, key=f"take_btn_{log_id}", type="primary", use_container_width=True):
                    mark_dose_status(log_id, status="TAKEN", recorded_by="elderly", notes="Self-confirmed by patient.")
                    st.toast(f"Great job Eleanor! You took your {name}.", icon="🌟")
                    st.rerun()
            else:
                c_sub1, c_sub2 = st.columns([2, 1])
                with c_sub1:
                    st.success(f"Dose recorded at {str(taken_at)[11:16] if taken_at else 'scheduled time'}. Well done!")
                with c_sub2:
                    if st.button("Undo", key=f"undo_{log_id}", use_container_width=True):
                        mark_dose_status(log_id, status="PENDING", recorded_by="elderly", notes="Undone by user.")
                        st.rerun()

        with col_btn2:
            speech_text = f"Time for {name}, {dosage}. Scheduled for {time_of_day} at {time_formatted}. Instructions: {instructions}"
            render_speech_button(text_to_speak=speech_text, label="🔊 Read to Me", button_id=f"tts_{log_id}")


def render_elderly_sos_widget(patient: Dict[str, Any]) -> None:
    """Render high-visibility Emergency Assistance card for seniors."""
    st.markdown("""
        <div style="
            background: #FEF2F2;
            border: 3px solid #DC2626;
            border-radius: 16px;
            padding: 24px;
            margin-top: 30px;
            text-align: center;
        ">
            <h2 style="color: #991B1B; margin-top: 0; font-size: 28px;">🚨 Need Immediate Help?</h2>
            <p style="font-size: 18px; color: #7F1D1D; margin-bottom: 16px;">
                Press the button below to instantly alert your family caregiver and clinic.
            </p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🚨 PRESS FOR EMERGENCY ASSISTANCE", key="elderly_big_sos", type="primary", use_container_width=True):
        from utils.alerts import dispatch_sos_alert
        dispatch_sos_alert(patient_id=patient["id"], notes="Triggered from Elderly Home Dashboard")
        st.error(f"🚨 Help alert dispatched! Your caregiver {patient.get('emergency_contact_name', 'Sarah')} has been alerted.")
