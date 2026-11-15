"""
Clinical Drug-Drug Interaction Safety Engine for GoldenCare.
Evaluates scheduled and proposed medications against clinical interaction
rules to prevent adverse drug events (ADEs).
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional
from db.database import get_drug_interactions


# Core clinical interaction rules dictionary for rapid memory lookups
CLINICAL_RULES: List[Dict[str, str]] = [
    {
        "drug_a": "Aspirin",
        "drug_b": "Warfarin",
        "severity": "High",
        "description": "Concurrent use elevates major gastrointestinal and systemic hemorrhage risk.",
        "recommendation": "Avoid combination unless strictly directed and monitored by a hematologist with INR monitoring.",
    },
    {
        "drug_a": "Lisinopril",
        "drug_b": "Spironolactone",
        "severity": "High",
        "description": "Potassium-sparing diuretic with ACE inhibitor triggers dangerous hyperkalemia.",
        "recommendation": "Check baseline serum potassium and renal panel within 14 days of initiation.",
    },
    {
        "drug_a": "Metformin",
        "drug_b": "Furosemide",
        "severity": "Moderate",
        "description": "Loop diuretics may alter renal clearance and elevate plasma metformin concentration.",
        "recommendation": "Monitor blood glucose stability; ensure patient stays well hydrated to prevent lactic acidosis.",
    },
    {
        "drug_a": "Atorvastatin",
        "drug_b": "Clarithromycin",
        "severity": "High",
        "description": "Potent CYP3A4 inhibition drastically raises statin bioavailability, risking rhabdomyolysis.",
        "recommendation": "Temporarily withhold Atorvastatin during macrolide therapy or use an alternative antibiotic.",
    },
    {
        "drug_a": "Lisinopril",
        "drug_b": "Ibuprofen",
        "severity": "Moderate",
        "description": "NSAIDs impair prostaglandin-mediated vasodilation, diminishing ACE inhibitor efficacy and reducing GFR.",
        "recommendation": "Use Acetaminophen for acute analgesia instead of NSAIDs for elderly hypertensive patients.",
    },
    {
        "drug_a": "Calcium",
        "drug_b": "Levothyroxine",
        "severity": "Moderate",
        "description": "Calcium carbonate chelates thyroid hormone in the gastrointestinal tract.",
        "recommendation": "Administer Levothyroxine in morning fasting state; take Calcium at least 4 hours later.",
    },
    {
        "drug_a": "Baby Aspirin",
        "drug_b": "Ibuprofen",
        "severity": "Moderate",
        "description": "Ibuprofen competitively inhibits platelet COX-1 binding site, blunting aspirin's cardioprotection.",
        "recommendation": "Take aspirin 30 minutes before or at least 8 hours after ibuprofen.",
    },
    {
        "drug_a": "Amlodipine",
        "drug_b": "Simvastatin",
        "severity": "Moderate",
        "description": "Amlodipine increases Simvastatin exposure, increasing myopathy risk.",
        "recommendation": "Limit Simvastatin dose to 20 mg daily when co-administered with Amlodipine.",
    },
    {
        "drug_a": "Metoprolol",
        "drug_b": "Fluoxetine",
        "severity": "Moderate",
        "description": "CYP2D6 inhibition by fluoxetine can double metoprolol blood levels, risking severe bradycardia.",
        "recommendation": "Monitor heart rate and blood pressure; consider titration or non-interacting SSRI.",
    },
]


def _is_drug_match(med_name: str, rule_drug: str) -> bool:
    """
    Check if a medication name matches a clinical rule drug name.
    Uses exact equality or word-boundary token matching to prevent
    substring false positives (e.g., 'Sin' matching 'Lisinopril').
    """
    m = med_name.strip().lower()
    r = rule_drug.strip().lower()
    if not m or not r:
        return False
    if m == r:
        return True

    # Check if rule drug is present as a whole word/phrase in medication name
    # e.g., 'Lisinopril' in 'Lisinopril 10mg' or 'Baby Aspirin' in 'Baby Aspirin 81mg'
    pattern_r = r'(?:\b|^)' + re.escape(r) + r'(?:\b|$)'
    if re.search(pattern_r, m):
        return True

    # Check if medication name is present as a whole word/phrase in rule drug
    # e.g., 'Aspirin' in 'Baby Aspirin', but NOT 'Sin' in 'Lisinopril'
    pattern_m = r'(?:\b|^)' + re.escape(m) + r'(?:\b|$)'
    if len(m) >= 3 and re.search(pattern_m, r):
        return True

    return False


def evaluate_interactions(
    medication_list: Optional[List[Any]] = None,
    proposed_drug: Optional[str] = None,
    current_medications: Optional[List[Any]] = None,
) -> List[Dict[str, str]]:
    """
    Evaluate whether a list of current drugs (plus an optional newly proposed drug)
    triggers any known safety conflicts.
    """
    raw_meds = current_medications if current_medications is not None else (medication_list if medication_list is not None else [])

    # Filter current_medications to remove any None or non-string/empty elements
    meds = [str(m).strip() for m in raw_meds if m is not None and str(m).strip()]

    # Handle proposed_drug: if None or empty, set to None; otherwise str(proposed_drug).strip()
    clean_proposed = str(proposed_drug).strip() if (proposed_drug is not None and str(proposed_drug).strip()) else None
    if clean_proposed:
        meds.append(clean_proposed)

    if len(meds) < 2:
        return []

    # Combine static clinical rules with any database-stored rules
    db_rules = []
    try:
        db_rules = get_drug_interactions()
    except Exception:
        pass

    combined_rules = CLINICAL_RULES + [
        {
            "drug_a": r["drug_a"],
            "drug_b": r["drug_b"],
            "severity": r["severity"],
            "description": r["description"],
            "recommendation": r["recommendation"],
        }
        for r in db_rules
    ]

    warnings = []
    seen = set()

    for rule in combined_rules:
        ra = rule["drug_a"]
        rb = rule["drug_b"]

        # Check if ra matches any drug and rb matches any OTHER drug in meds
        match_a_idx = [i for i, name in enumerate(meds) if _is_drug_match(name, ra)]
        match_b_idx = [i for i, name in enumerate(meds) if _is_drug_match(name, rb)]

        for ia in match_a_idx:
            for ib in match_b_idx:
                if ia != ib:
                    pair_key = tuple(sorted([meds[ia].lower(), meds[ib].lower()]))
                    if pair_key not in seen:
                        seen.add(pair_key)
                        warnings.append({
                            "drug_1": meds[ia],
                            "drug_2": meds[ib],
                            "severity": rule["severity"],
                            "description": rule["description"],
                            "recommendation": rule["recommendation"],
                        })

    return warnings


def get_interaction_details(rule: Dict[str, str]) -> str:
    """Format markdown callout for an interaction."""
    color = "🔴" if rule.get("severity") == "High" else "🟡"
    return f"{color} **{rule.get('severity', 'Warning')} Risk**: {rule.get('description', '')}\n\n*Action:* {rule.get('recommendation', '')}"
