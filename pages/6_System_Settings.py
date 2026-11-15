"""
System Settings, Security & SMTP Alert Configuration for GoldenCare.
Enables caregivers to manage security PINs, configure live SMTP credentials,
dispatch verification test emails, and inspect complete audit logs.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from components.header import render_alert_banner, render_app_header
from db.database import (
    DB_PATH,
    get_alerts,
    get_users,
    init_db,
    seed_initial_data,
    update_user_passcode,
)
from utils.alerts import get_smtp_config, send_email_alert
from utils.auth import get_current_user, require_auth

init_db()
seed_initial_data()
render_app_header()
render_alert_banner()

# Security Gate: Caregivers only
require_auth(allowed_roles=["caretaker"])

curr_user = get_current_user()

st.markdown("""
    <div style="margin-bottom: 20px;">
        <h1 style="color: #0F172A; margin: 0 0 6px 0;">System Settings & Alert Dispatcher</h1>
        <p style="color: #64748B; font-size: 16px; margin: 0;">
            Configure platform security, active SMTP credentials, notification routing, and audit logs.
        </p>
    </div>
""", unsafe_allow_html=True)

tab_sec, tab_smtp, tab_logs, tab_maint = st.tabs([
    "Security & Passcodes",
    "SMTP Notification Engine",
    "Complete Alert Audit Logs",
    "System Maintenance",
])

# 1. Passcode Management
with tab_sec:
    st.subheader("Manage Portal Security PINs")
    st.caption("Change default passcodes for patient or caregiver authentication.")

    users = get_users()
    elderly_user = next((u for u in users if u["role"] == "elderly"), None)
    caretaker_user = next((u for u in users if u["role"] == "caretaker"), None)

    c_pin1, c_pin2 = st.columns(2)

    with c_pin1:
        st.markdown("#### Senior / Elderly PIN")
        if elderly_user:
            st.write(f"**Current User:** {elderly_user['name']}")
            st.write(f"**Active PIN:** `{elderly_user['passcode']}`")
            new_eld_pin = st.text_input("Enter New 4-Digit Senior PIN", max_chars=8, key="input_new_eld_pin", placeholder="e.g., 1234")
            if st.button("Update Senior PIN", key="btn_update_eld_pin", type="primary"):
                clean_pin = new_eld_pin.strip()
                if not clean_pin:
                    st.error("PIN cannot be empty.")
                elif not clean_pin.isdigit() or len(clean_pin) < 4:
                    st.error("PIN must consist of at least 4 numeric digits.")
                else:
                    update_user_passcode(elderly_user["id"], clean_pin)
                    st.success(f"Senior PIN updated to '{clean_pin}'.")
                    st.rerun()

    with c_pin2:
        st.markdown("#### Caregiver PIN")
        if caretaker_user:
            st.write(f"**Current User:** {caretaker_user['name']}")
            st.write(f"**Active PIN:** `{caretaker_user['passcode']}`")
            new_car_pin = st.text_input("Enter New 4-Digit Caregiver PIN", max_chars=8, key="input_new_car_pin", placeholder="e.g., 8888")
            if st.button("Update Caregiver PIN", key="btn_update_car_pin", type="primary"):
                clean_pin = new_car_pin.strip()
                if not clean_pin:
                    st.error("PIN cannot be empty.")
                elif not clean_pin.isdigit() or len(clean_pin) < 4:
                    st.error("PIN must consist of at least 4 numeric digits.")
                else:
                    update_user_passcode(caretaker_user["id"], clean_pin)
                    st.success(f"Caregiver PIN updated to '{clean_pin}'.")
                    st.rerun()

# 2. SMTP Alert Configuration
with tab_smtp:
    st.subheader("Google Services & Proactive Email Alert Gateway")
    st.caption("GoldenCare connects directly to Google Mail (Gmail SMTP over TLS) or Google Cloud services for autonomous caregiver escalation.")

    from utils.google_services import get_google_services_health
    g_health = get_google_services_health()
    smtp_cfg = get_smtp_config()

    if smtp_cfg["is_configured"]:
        st.success(f"**Live Google Mail / SMTP Active**: Connected to `{smtp_cfg['server']}:{smtp_cfg['port']}` as `{smtp_cfg['username']}`.")
    else:
        st.warning("**Sandbox Audit Mode Active**: Google Mail / SMTP credentials not found in secrets or environment. Alerts are safely written to SQLite audit logs without crashing.")

    st.markdown(f"**Integration Channel:** `{g_health['service']}` ({g_health['server']}) &bull; **Status:** {g_health['status_label']}")

    st.markdown("#### Test Live Alert Dispatch")
    col_tmail, col_tbtn = st.columns([2, 1])
    with col_tmail:
        test_target_email = st.text_input("Recipient Email for Verification Test", value=smtp_cfg["alert_recipient"] or "caretaker@example.com")
    with col_tbtn:
        st.write("")
        st.write("")
        if st.button("Send Test Verification Email", width="stretch", type="primary"):
            test_html = f"""
                <div style="font-family: sans-serif; padding: 24px; border: 2px solid #2563EB; border-radius: 12px; background: #F8FAFC;">
                    <h2 style="color: #1E40AF; margin-top: 0;">GoldenCare SMTP Gateway Test</h2>
                    <p>This verification confirms that proactive alert delivery is operational.</p>
                    <p><strong>Configured Sender:</strong> {smtp_cfg['sender_name']}</p>
                    <p><strong>Target Recipient:</strong> {test_target_email}</p>
                    <p><strong>Security Protocol:</strong> TLS Encrypted</p>
                    <hr style="border: 1px solid #E2E8F0;"/>
                    <p style="font-size: 12px; color: #64748B;">GoldenCare Autonomous Elderly Care Platform</p>
                </div>
            """
            res = send_email_alert(
                recipient_email=test_target_email,
                subject="[GoldenCare] Proactive Email Alert Dispatch Verification",
                body_html=test_html,
                alert_type="SYSTEM_TEST",
                severity="INFO",
                patient_id=1,
            )
            if res["status"] == "SENT":
                st.toast(f"{res['message']}")
            else:
                st.toast(f"{res['message']}")
            st.rerun()

    st.markdown("---")
    st.markdown("#### How to Set Live SMTP in Production")
    st.markdown("""
        To enable direct Gmail/SMTP sending in Streamlit Community Cloud:
        1. Open your Streamlit App settings -> **Secrets**.
        2. Paste the following configuration:
        ```toml
        [smtp]
        server = "smtp.gmail.com"
        port = 587
        use_tls = true
        username = "your-email@gmail.com"
        password = "your-app-password" # Generate in Google Account -> Security -> App Passwords
        sender_name = "GoldenCare Alerts"
        alert_recipient = "caretaker@example.com"
        ```
    """)

# 3. Complete Audit Logs
with tab_logs:
    st.subheader("System Alert Audit Trail")
    st.caption("Immutable chronological record of missed dose escalations, refill warnings, and emergency SOS signals.")

    all_alerts = get_alerts(limit=100)
    if all_alerts:
        df_alerts = pd.DataFrame(all_alerts)
        disp_alerts = df_alerts[["sent_at", "severity", "alert_type", "delivery_status", "recipient_email", "message"]].copy()
        disp_alerts.columns = ["Timestamp", "Severity", "Type", "Status", "Recipient", "Event Description"]
        st.dataframe(disp_alerts, width="stretch", hide_index=True)
    else:
        st.info("No alert logs registered.")

# 4. Storage & Diagnostics
with tab_maint:
    st.subheader("Storage & Diagnostic Information")
    st.write(f"**Database Location:** `{DB_PATH}`")
    if os.path.exists(DB_PATH):
        db_size_kb = os.path.getsize(DB_PATH) / 1024
        st.write(f"**Database Size:** `{db_size_kb:.1f} KB`")
    st.info("Database Write-Ahead Logging (WAL) is active for concurrent multi-user synchronization.")
