"""
Proactive Alert Engine and Notification Dispatcher for GoldenCare.
Monitors medication schedules, detects overdue/missed doses, triggers
escalation alerts, dispatches proactive emails via SMTP, and records audit logs.
"""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import streamlit as st

from db.database import (
    get_todays_doses,
    mark_dose_status,
    add_alert,
    get_alerts,
    get_patient,
    get_users,
    get_medications,
    get_vitals,
    reconcile_past_doses,
)


def get_smtp_config() -> Dict[str, Any]:
    """
    Retrieve SMTP configuration from Streamlit secrets or OS environment.
    Falls back gracefully if unconfigured.
    """
    server = ""
    port = 587
    use_tls = True
    username = ""
    password = ""
    sender_name = "GoldenCare Alerts"
    alert_recipient = "caretaker@example.com"

    # Try Streamlit Secrets first
    try:
        if hasattr(st, "secrets") and "smtp" in st.secrets:
            s = st.secrets["smtp"]
            server = s.get("server", "")
            port = int(s.get("port", 587))
            use_tls = bool(s.get("use_tls", True))
            username = s.get("username", "")
            password = s.get("password", "")
            sender_name = s.get("sender_name", "GoldenCare Alerts")
            alert_recipient = s.get("alert_recipient", "caretaker@example.com")
    except Exception:
        pass

    # Fallback to Environment variables
    if not server:
        server = os.environ.get("SMTP_SERVER", "")
        port = int(os.environ.get("SMTP_PORT", 587))
        use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
        username = os.environ.get("SMTP_USERNAME", "")
        password = os.environ.get("SMTP_PASSWORD", "")
        sender_name = os.environ.get("ALERT_SENDER_NAME", "GoldenCare Alerts")
        alert_recipient = os.environ.get("ALERT_EMAIL_RECIPIENT", "caretaker@example.com")

    is_configured = bool(server and username and password)
    return {
        "server": server,
        "port": port,
        "use_tls": use_tls,
        "username": username,
        "password": password,
        "sender_name": sender_name,
        "alert_recipient": alert_recipient,
        "is_configured": is_configured,
    }


def send_email_alert(
    recipient_email: str,
    subject: str,
    body_html: str,
    alert_type: str = "NOTIFICATION",
    severity: str = "WARNING",
    patient_id: int = 1,
    medication_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Dispatch an email notification.
    If SMTP credentials are provided, transmits via live SMTP over TLS.
    If unconfigured or in demo mode, records an audit log in SQLite and simulates delivery.
    """
    config = get_smtp_config()
    target_email = recipient_email or config["alert_recipient"]

    if config["is_configured"]:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{severity}] {subject}"
            msg["From"] = f"{config['sender_name']} <{config['username']}>"
            msg["To"] = target_email

            part = MIMEText(body_html, "html")
            msg.attach(part)

            with smtplib.SMTP(config["server"], config["port"], timeout=10) as s:
                if config["use_tls"]:
                    s.starttls()
                s.login(config["username"], config["password"])
                s.sendmail(config["username"], [target_email], msg.as_string())

            add_alert(
                patient_id=patient_id,
                medication_id=medication_id,
                alert_type=alert_type,
                severity=severity,
                message=subject,
                recipient_email=target_email,
                delivery_status="SENT",
            )
            return {"success": True, "status": "SENT", "message": f"Email delivered to {target_email}."}
        except Exception as e:
            add_alert(
                patient_id=patient_id,
                medication_id=medication_id,
                alert_type=alert_type,
                severity=severity,
                message=f"{subject} (Error: {str(e)})",
                recipient_email=target_email,
                delivery_status="FAILED",
            )
            return {"success": False, "status": "FAILED", "message": f"SMTP Dispatch Error: {str(e)}"}
    else:
        # Graceful sandbox / demo fallback
        add_alert(
            patient_id=patient_id,
            medication_id=medication_id,
            alert_type=alert_type,
            severity=severity,
            message=subject,
            recipient_email=target_email,
            delivery_status="LOGGED",
        )
        return {
            "success": True,
            "status": "LOGGED",
            "message": f"Alert registered in database for {target_email} (Demo Mode / SMTP Unset).",
        }


def check_and_trigger_alerts(patient_id: int = 1, force_check: bool = False) -> List[Dict[str, Any]]:
    """
    Core proactive alert engine:
    1. Reconciles past days' pending doses to 'MISSED'.
    2. Scans today's medication schedule for the patient.
    3. Identifies doses pending beyond the grace period (30 mins past scheduled time).
    4. Escalates overdue doses to 'MISSED' status.
    5. Automatically generates proactive email alert to caretaker.
    6. Checks medication stock levels and triggers refill warnings.
    """
    # 0. Historical reconciliation of prior unconfirmed doses
    reconcile_past_doses(patient_id)

    now = datetime.now()
    today_str = date.today().isoformat()
    triggered_alerts = []

    patient = get_patient(patient_id)
    patient_name = patient["name"] if patient else "Eleanor Vance"

    # Get caretaker email
    users = get_users()
    caretaker = next((u for u in users if u["role"] == "caretaker"), None)
    caretaker_email = caretaker["email"] if caretaker else "caretaker@example.org"

    # 1. Check Doses
    doses = get_todays_doses(patient_id, today_str)
    existing_alerts = get_alerts(patient_id, limit=100)
    todays_sent_missed_meds = {
        a["medication_id"] for a in existing_alerts 
        if a["alert_type"] == "MISSED_DOSE" and str(a.get("sent_at", "")).startswith(today_str)
    }
    todays_sent_refill_meds = {
        a["medication_id"] for a in existing_alerts 
        if a["alert_type"] == "REFILL_ALERT" and str(a.get("sent_at", "")).startswith(today_str)
    }

    for dose in doses:
        sched_time_str = dose["scheduled_time"]
        try:
            sh, sm = map(int, sched_time_str.split(":"))
            scheduled_dt = datetime(now.year, now.month, now.day, sh, sm)
        except Exception:
            continue

        # Check for OVERDUE / MISSED (> 30 mins overdue)
        grace_period = timedelta(minutes=30)
        if dose["status"] == "PENDING" and now > (scheduled_dt + grace_period):
            # Mark status in DB as MISSED
            mark_dose_status(dose["log_id"], status="MISSED", recorded_by="system", notes="Automated miss detection (>30 min grace)")

            alert_title = f"Missed Dose Alert: {dose['medication_name']} {dose['dosage']} ({sched_time_str})"
            already_alerted = dose["medication_id"] in todays_sent_missed_meds
            if not already_alerted or force_check:
                html_body = f"""
                <div style="font-family: sans-serif; padding: 20px; border: 2px solid #EF4444; border-radius: 8px; background: #FEF2F2;">
                    <h2 style="color: #991B1B;">⚠️ Overdue Medication Alert</h2>
                    <p>Dear Caretaker,</p>
                    <p><strong>{patient_name}</strong> was scheduled to take <strong>{dose['medication_name']} ({dose['dosage']})</strong> at <strong>{sched_time_str}</strong>.</p>
                    <p style="color: #B91C1C; font-weight: bold;">Status: MISSED (>30 minutes past scheduled time without confirmation).</p>
                    <p><strong>Special Instructions:</strong> {dose.get('instructions', 'None')}</p>
                    <hr style="border: 1px solid #FECACA;"/>
                    <p style="font-size: 12px; color: #7F1D1D;">Automated notification generated by GoldenCare AI Patient Monitoring Engine.</p>
                </div>
                """
                res = send_email_alert(
                    recipient_email=caretaker_email,
                    subject=alert_title,
                    body_html=html_body,
                    alert_type="MISSED_DOSE",
                    severity="CRITICAL",
                    patient_id=patient_id,
                    medication_id=dose["medication_id"],
                )
                todays_sent_missed_meds.add(dose["medication_id"])
                triggered_alerts.append({"type": "MISSED_DOSE", "medication": dose["medication_name"], "result": res})

    # 2. Check Inventory & Refill Needs
    meds = get_medications(patient_id, active_only=True)
    for m in meds:
        if m["stock_remaining"] <= m["refill_threshold"]:
            refill_title = f"Low Prescription Inventory: {m['name']} ({m['stock_remaining']} doses remaining)"
            already_alerted = m["id"] in todays_sent_refill_meds
            if not already_alerted or force_check:
                html_body = f"""
                <div style="font-family: sans-serif; padding: 20px; border: 2px solid #F59E0B; border-radius: 8px; background: #FFFBEB;">
                    <h2 style="color: #B45309;">💊 Prescription Refill Advisory</h2>
                    <p><strong>{patient_name}'s</strong> prescription for <strong>{m['name']}</strong> is running low.</p>
                    <p>Remaining count: <strong>{m['stock_remaining']}</strong> units (Threshold: {m['refill_threshold']}).</p>
                    <p>Please contact the prescribing pharmacy or schedule a refill order.</p>
                </div>
                """
                res = send_email_alert(
                    recipient_email=caretaker_email,
                    subject=refill_title,
                    body_html=html_body,
                    alert_type="REFILL_ALERT",
                    severity="WARNING",
                    patient_id=patient_id,
                    medication_id=m["id"],
                )
                todays_sent_refill_meds.add(m["id"])
                triggered_alerts.append({"type": "REFILL_ALERT", "medication": m["name"], "result": res})

    return triggered_alerts


def dispatch_sos_alert(patient_id: int = 1, notes: str = "Patient pressed Emergency SOS button") -> Dict[str, Any]:
    """Trigger immediate emergency SOS dispatch to caretaker."""
    patient = get_patient(patient_id)
    patient_name = patient["name"] if patient else "Eleanor Vance"
    phone = patient["emergency_contact_phone"] if patient else "+1 (555) 987-6543"

    users = get_users()
    caretaker = next((u for u in users if u["role"] == "caretaker"), None)
    caretaker_email = caretaker["email"] if caretaker else "caretaker@example.org"

    subject = f"🚨 URGENT: EMERGENCY ASSISTANCE REQUESTED BY {patient_name.upper()}!"
    html_body = f"""
    <div style="font-family: sans-serif; padding: 24px; border: 3px solid #DC2626; border-radius: 12px; background: #FEF2F2;">
        <h1 style="color: #991B1B; margin-top: 0;">🚨 EMERGENCY SOS ALERT</h1>
        <p style="font-size: 18px; color: #7F1D1D;"><strong>{patient_name}</strong> pressed the Emergency Assistance button on the Elderly Touch Portal.</p>
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Emergency Contact Phone:</strong> {phone}</p>
        <p><strong>Notes:</strong> {notes}</p>
        <p style="background: #FEE2E2; padding: 12px; border-radius: 6px; font-weight: bold; color: #991B1B;">
            Action Required: Please phone the patient immediately or coordinate with local emergency responders.
        </p>
    </div>
    """
    return send_email_alert(
        recipient_email=caretaker_email,
        subject=subject,
        body_html=html_body,
        alert_type="EMERGENCY_SOS",
        severity="CRITICAL",
        patient_id=patient_id,
    )


def get_alert_summary(patient_id: int = 1) -> Dict[str, Any]:
    """Return summary statistics of active alerts for UI badges."""
    alerts = get_alerts(patient_id, limit=100)
    critical_count = sum(1 for a in alerts if a["severity"] == "CRITICAL")
    warning_count = sum(1 for a in alerts if a["severity"] == "WARNING")
    recent = alerts[:5]
    return {
        "total": len(alerts),
        "critical": critical_count,
        "warning": warning_count,
        "recent": recent,
    }
