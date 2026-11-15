"""
Prescription & Medication Schedule Manager for GoldenCare.
Allows caregivers to add, modify, and monitor medications with
an automated real-time drug-drug interaction safety checker.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import time

from utils.auth import require_auth, get_current_user
from db.database import (
    get_patient,
    get_medications,
    add_medication,
    update_medication,
    delete_medication,
)
from components.header import render_app_header, render_alert_banner
from utils.interactions import evaluate_interactions, get_interaction_details

render_app_header()
render_alert_banner()

# Gate: Caregivers only
require_auth(allowed_roles=["caretaker"])

curr_user = get_current_user()
patient_id = curr_user.get("patient_id", 1)
patient = get_patient(patient_id)
patient_name = patient["name"] if patient else "Eleanor Vance"

st.markdown(f"""
    <div style="margin-bottom: 20px;">
        <h1 style="color: #0F172A; margin: 0 0 6px 0;">Medication & Prescription Manager</h1>
        <p style="color: #64748B; font-size: 16px; margin: 0;">
            Configure prescriptions, schedules, pill visuals, and verify pharmacological interactions for <strong>{patient_name}</strong>.
        </p>
    </div>
""", unsafe_allow_html=True)

# Tabs: Active Medications, Add New Medication, Drug Interaction Safety Checker
tab_list, tab_add, tab_interactions = st.tabs([
    "Active Prescription Regimen",
    "Prescribe New Medication",
    "Drug-Drug Interaction Safety Engine",
])

# 1. Active Regimen Tab
with tab_list:
    meds = get_medications(patient_id, active_only=True)
    st.subheader(f"Current Prescriptions ({len(meds)} Active)")

    if not meds:
        st.info("No active medications found. Add one in the 'Prescribe New Medication' tab.")
    else:
        for m in meds:
            m_id = m["id"]
            with st.expander(f"{m['name']} — {m['dosage']} ({m['time_of_day']} at {m['scheduled_time']})", expanded=False):
                c1, c2, c3 = st.columns([1.5, 1.5, 1])

                with c1:
                    st.write(f"**Frequency:** {m['frequency']}")
                    st.write(f"**Time of Day:** {m['time_of_day']} ({m['scheduled_time']})")
                    st.write(f"**Instructions:** {m['instructions'] or 'Take as directed.'}")

                with c2:
                    st.write(f"**Pill Visual:** {m['pill_shape']} (Color: `{m['pill_color']}`)")
                    st.write(f"**Remaining Inventory:** {m['stock_remaining']} doses")
                    st.write(f"**Refill Threshold:** {m['refill_threshold']} doses")
                    if m["stock_remaining"] <= m["refill_threshold"]:
                        st.error("Warning: Stock is below refill warning threshold.")

                with c3:
                    st.markdown("#### Quick Actions")
                    safe_stock = max(0, min(500, int(m["stock_remaining"] or 0)))
                    new_stock = st.number_input("Update Stock", min_value=0, max_value=500, value=safe_stock, key=f"stock_edit_{m_id}")
                    if st.button("Save Stock Count", key=f"btn_save_stock_{m_id}", width="stretch"):
                        try:
                            update_medication(
                                med_id=m_id,
                                name=m["name"],
                                dosage=m["dosage"],
                                frequency=m["frequency"],
                                time_of_day=m["time_of_day"],
                                scheduled_time=m["scheduled_time"],
                                pill_color=m["pill_color"],
                                pill_shape=m["pill_shape"],
                                instructions=m["instructions"],
                                stock_remaining=new_stock,
                                refill_threshold=m["refill_threshold"],
                            )
                            st.success("Stock updated.")
                            st.rerun()
                        except ValueError as ve:
                            st.error(str(ve))

                    if st.button("Remove Prescription", key=f"btn_del_{m_id}", width="stretch", type="secondary"):
                        delete_medication(m_id)
                        st.warning(f"Prescription {m['name']} removed.")
                        st.rerun()

# 2. Add New Medication Tab (With Real-Time Interaction Safety Check)
with tab_add:
    st.subheader("Add New Medication to Regimen")
    st.caption("All additions are automatically evaluated against the patient's existing medications for safety.")

    with st.form("form_add_medication", clear_on_submit=False):
        c_a1, c_a2 = st.columns(2)
        with c_a1:
            med_name = st.text_input("Medication Name *", placeholder="e.g., Warfarin, Lisinopril, Metformin")
            med_dosage = st.text_input("Dosage Strength *", placeholder="e.g., 10mg, 500mg, 1 tablet")
            med_frequency = st.selectbox("Frequency", ["Daily", "Twice Daily", "Three Times Daily", "Weekly", "As Needed"])
            med_tod = st.selectbox("Time of Day Slot", ["Morning", "Afternoon", "Evening", "Bedtime"])

        with c_a2:
            med_time = st.time_input("Scheduled Administration Time", value=time(8, 0))
            med_shape = st.selectbox("Pill Physical Shape", ["Tablet", "Capsule", "Round", "Oval", "Liquid", "Inhaler"])
            med_color = st.color_picker("Pill Color Representation", value="#2563EB")
            med_stock = st.number_input("Starting Supply (Doses)", min_value=1, max_value=365, value=30)
            med_refill = st.number_input("Refill Warning Threshold", min_value=1, max_value=60, value=7)

        med_instructions = st.text_area(
            "Patient Clinical Instructions",
            placeholder="e.g., Take with food and a full glass of water. Do not crush or chew."
        )

        med_override_ack = st.checkbox(
            "Override Clinical Contraindication Warning (Physician-Approved)",
            value=False,
            help="Check this box ONLY if the prescribing physician has explicitly confirmed this drug combination is clinically indicated despite known drug interactions."
        )

        submit_btn = st.form_submit_button("Verify Safety & Schedule Medication", type="primary", width="stretch")

    # Real-Time Safety Analysis when form submitted or medication name entered
    if submit_btn:
        clean_d_str = med_dosage.strip() if med_dosage else ""
        if not med_name or not clean_d_str:
            st.error("Please provide both Medication Name and Dosage Strength.")
        elif clean_d_str.startswith("-") or any(part.startswith("-") for part in clean_d_str.split()):
            st.error("Medication dosage cannot be negative.")
        else:
            # Check for Drug Interactions against current active medications
            existing_meds = get_medications(patient_id, active_only=True)
            existing_names = [m["name"] for m in existing_meds]
            interactions = evaluate_interactions(existing_names, proposed_drug=med_name)

            high_risk_interactions = [i for i in interactions if i.get("severity") == "High"]

            if high_risk_interactions and not med_override_ack:
                st.error("PRESCRIPTION BLOCKED: HIGH-RISK CONTRAINDICATION DETECTED")
                for inter in high_risk_interactions:
                    st.markdown(f"""
                        <div style="background: #FEF2F2; border-left: 6px solid #DC2626; padding: 14px; border-radius: 8px; margin-bottom: 10px;">
                            <strong style="color: #991B1B; font-size: 16px;">
                                CONTRAINDICATION WARNING: {inter['drug_1']} + {inter['drug_2']}
                            </strong>
                            <p style="color: #7F1D1D; margin: 4px 0;">{inter['description']}</p>
                            <p style="color: #991B1B; font-weight: bold; margin: 0;">Recommendation: {inter['recommendation']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                st.warning("Medication was NOT scheduled to protect patient safety. If physician explicitly approves, check the override box and re-submit.")
                from db.database import add_alert
                add_alert(
                    patient_id=patient_id,
                    alert_type="CONTRAINDICATION_BLOCKED",
                    message=f"Prescription of {med_name} blocked due to high-risk interaction with existing regimen ({', '.join(i['drug_2'] for i in high_risk_interactions)}).",
                    severity="CRITICAL",
                )
            else:
                if interactions:
                    if med_override_ack:
                        st.info("Physician override acknowledged for known interactions.")
                        from db.database import add_alert
                        add_alert(
                            patient_id=patient_id,
                            alert_type="CONTRAINDICATION_OVERRIDDEN",
                            message=f"Prescription of {med_name} added under physician override despite interaction warnings.",
                            severity="WARNING",
                        )

                # Add to database
                time_str = med_time.strftime("%H:%M")
                try:
                    new_id = add_medication(
                        patient_id=patient_id,
                        name=med_name,
                        dosage=med_dosage,
                        frequency=med_frequency,
                        time_of_day=med_tod,
                        scheduled_time=time_str,
                        pill_color=med_color,
                        pill_shape=med_shape,
                        instructions=med_instructions,
                        stock_remaining=med_stock,
                        refill_threshold=med_refill,
                    )
                    st.toast(f"Successfully scheduled {med_name} ({med_dosage}) at {time_str}.")
                    st.success(f"Successfully scheduled {med_name} ({med_dosage}) at {time_str}.")
                    st.rerun()
                except ValueError as ve:
                    st.error(f"Cannot schedule medication: {str(ve)}")

# 3. Drug Interaction Safety Matrix Tab
with tab_interactions:
    st.subheader("Active Drug-Drug Interaction Safety Catalog")
    st.caption("Automated surveillance matrix analyzing all medications currently prescribed to Eleanor Vance.")

    existing_meds = get_medications(patient_id, active_only=True)
    existing_names = [m["name"] for m in existing_meds]

    active_warnings = evaluate_interactions(existing_names)

    if active_warnings:
        st.error(f"Found {len(active_warnings)} active interactions requiring clinical monitoring in the current regimen:")
        for w in active_warnings:
            st.markdown(f"""
                <div style="background: #FFFBEB; border: 2px solid #F59E0B; border-radius: 10px; padding: 16px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #B45309;">{w['drug_1']} &bull; {w['drug_2']}</h4>
                        <span style="background: #F59E0B; color: white; padding: 2px 10px; border-radius: 9999px; font-size: 12px; font-weight: bold;">
                            {w['severity']} Risk
                        </span>
                    </div>
                    <p style="color: #78350F; margin: 8px 0 4px 0;"><strong>Mechanism:</strong> {w['description']}</p>
                    <p style="color: #92400E; margin: 0;"><strong>Guidance:</strong> {w['recommendation']}</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No adverse drug-drug interactions detected among Eleanor's current medications.")

    st.markdown("---")
    st.markdown("#### Reference Drug Interaction Safety Rules in Clinical Knowledge Base")
    from db.database import get_drug_interactions
    kb_rules = get_drug_interactions()
    if kb_rules:
        kb_df = pd.DataFrame(kb_rules)[["drug_a", "drug_b", "severity", "description", "recommendation"]]
        kb_df.columns = ["Primary Drug", "Secondary Drug", "Severity Level", "Clinical Adverse Effect", "Actionable Guidance"]
        st.dataframe(kb_df, width="stretch", hide_index=True)
