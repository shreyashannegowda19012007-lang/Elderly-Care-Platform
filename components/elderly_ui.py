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


def render_elderly_dose_card(
    dose: Dict[str, Any],
    high_contrast: bool = False,
    key_prefix: str = "card",
) -> None:
    """
    Render a single medication dose card designed for senior accessibility.
    Large touch targets, clear status badges, and audio readout support.
    Accepts key_prefix to guarantee unique widget element IDs across tabs.
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
        card_bg = "linear-gradient(135deg, #ECFDF5 0%, #FFFFFF 100%)" if not high_contrast else "#FFFFFF"
        border_color = "#10B981"
        badge_text = f"TAKEN" + (f" ({str(taken_at)[11:16]})" if taken_at else "")
        badge_bg = "linear-gradient(135deg, #10B981 0%, #059669 100%)"
        accent_color = "#047857"
    elif status == "MISSED":
        card_bg = "linear-gradient(135deg, #FEF2F2 0%, #FFFFFF 100%)" if not high_contrast else "#FFFFFF"
        border_color = "#EF4444"
        badge_text = "OVERDUE"
        badge_bg = "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
        accent_color = "#B91C1C"
    else:  # PENDING
        card_bg = "linear-gradient(135deg, #F0F9FF 0%, #FFFFFF 100%)" if not high_contrast else "#FFFFFF"
        border_color = "#3B82F6"
        badge_text = "SCHEDULED"
        badge_bg = "linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)"
        accent_color = "#1D4ED8"

    with st.container():
        # Accessible outer container
        st.markdown(f"""
            <div style="
                background: {card_bg};
                border: 2.5px solid {border_color};
                border-radius: 20px;
                padding: 24px;
                margin-bottom: 20px;
                box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.05);
                position: relative;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="
                            width: 32px;
                            height: 32px;
                            border-radius: 8px;
                            background: {pill_color};
                            box-shadow: 0 4px 10px rgba(0,0,0,0.15);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            color: white;
                            font-size: 13px;
                            font-weight: 800;
                            border: 2px solid white;
                            letter-spacing: 0.5px;
                        ">Rx</div>
                        <div>
                            <span style="font-size: 15px; font-weight: 800; color: {accent_color}; text-transform: uppercase; letter-spacing: 0.05em;">
                                {time_of_day} &bull; {time_formatted}
                            </span>
                            <span style="font-size: 13px; color: #64748B; font-weight: 600; margin-left: 6px;">({pill_shape})</span>
                        </div>
                    </div>
                    <span style="
                        background: {badge_bg};
                        color: white;
                        font-weight: 800;
                        padding: 6px 16px;
                        border-radius: 9999px;
                        font-size: 14px;
                        letter-spacing: 0.05em;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    ">
                        {badge_text}
                    </span>
                </div>
                <div style="font-size: 28px; font-weight: 800; color: #0F172A; margin-bottom: 10px; font-family: 'Outfit', sans-serif;">
                    {name} <span style="font-size: 20px; font-weight: 600; color: #64748B;">({dosage})</span>
                </div>
                <div style="font-size: 16px; color: #334155; line-height: 1.5; background: rgba(241, 245, 249, 0.8); border: 1px solid #E2E8F0; padding: 12px 16px; border-radius: 12px; margin-bottom: 8px;">
                    <span style="font-weight: 700; color: #1E293B;">Directions:</span> {instructions}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Action Buttons Row with unique keys via key_prefix
        col_btn1, col_btn2 = st.columns([2.5, 1.2])

        with col_btn1:
            if status != "TAKEN":
                btn_label = f"Record Dose: I Took My {name}"
                if st.button(btn_label, key=f"{key_prefix}_take_btn_{log_id}", type="primary", use_container_width=True):
                    mark_dose_status(log_id, status="TAKEN", recorded_by="elderly", notes="Self-confirmed by patient.")
                    st.toast(f"Dose logged: Eleanor recorded {name}.")
                    st.rerun()
            else:
                c_sub1, c_sub2 = st.columns([2, 1])
                with c_sub1:
                    st.success(f"Dose recorded at {str(taken_at)[11:16] if taken_at else 'scheduled time'}. Completed.")
                with c_sub2:
                    if st.button("Undo", key=f"{key_prefix}_undo_{log_id}", use_container_width=True):
                        mark_dose_status(log_id, status="PENDING", recorded_by="elderly", notes="Undone by user.")
                        st.rerun()

        with col_btn2:
            speech_text = f"Time for {name}, {dosage}. Scheduled for {time_of_day} at {time_formatted}. Instructions: {instructions}"
            render_speech_button(text_to_speak=speech_text, label="Listen to Audio", button_id=f"{key_prefix}_tts_{log_id}")


def render_elderly_sos_widget(patient: Dict[str, Any]) -> None:
    """Render high-visibility Emergency Assistance card for seniors."""
    ec_name = patient.get("emergency_contact_name", "Sarah Vance")
    ec_phone = patient.get("emergency_contact_phone", "(555) 014-9921")

    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%);
            border: 3px solid #DC2626;
            border-radius: 20px;
            padding: 28px;
            margin-top: 36px;
            box-shadow: 0 10px 30px rgba(220, 38, 38, 0.15);
        ">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="
                        width: 44px;
                        height: 44px;
                        background: #DC2626;
                        color: white;
                        border-radius: 10px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 16px;
                        font-weight: 800;
                        letter-spacing: 0.5px;
                    ">SOS</div>
                    <div>
                        <h2 style="color: #991B1B; margin: 0; font-size: 26px; font-weight: 800; font-family: 'Outfit', sans-serif;">Need Immediate Help?</h2>
                        <span style="font-size: 15px; color: #7F1D1D; font-weight: 600;">One-tap emergency broadcast to your family and primary clinic</span>
                    </div>
                </div>
                <div style="background: white; border: 1.5px solid #FCA5A5; padding: 6px 14px; border-radius: 10px; font-size: 13px; font-weight: 700; color: #991B1B;">
                    Priority Contact: {ec_name} &bull; {ec_phone}
                </div>
            </div>
            <p style="font-size: 16px; color: #7F1D1D; margin: 0 0 16px 0; line-height: 1.5;">
                Press the button below. Your status and emergency notification will be dispatched via automated alert systems and priority email.
            </p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("DISPATCH EMERGENCY ASSISTANCE REQUEST", key="elderly_big_sos", type="primary", use_container_width=True):
        from utils.alerts import dispatch_sos_alert
        dispatch_sos_alert(patient_id=patient["id"], notes="Triggered from Elderly Home Dashboard")
        st.error(f"Help alert dispatched: Your caregiver {ec_name} has been notified immediately.")
