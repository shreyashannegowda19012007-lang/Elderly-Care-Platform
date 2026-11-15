"""
Clinical Drug-Drug Interaction Safety Engine for GoldenCare.
Evaluates scheduled and proposed medications against clinical interaction
rules to prevent adverse drug events (ADEs).
"""

from __future__ import annotations

from typing import List, Dict, Any
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


def evaluate_interactions(medication_list: List[str], proposed_drug: str = "") -> List[Dict[str, str]]:
    """
    Evaluate whether a list of current drugs (plus an optional newly proposed drug)
    triggers any known safety conflicts.
    """
    all_drugs = [d.strip() for d in medication_list if d.strip()]
    if proposed_drug.strip():
        all_drugs.append(proposed_drug.strip())

    if len(all_drugs) < 2:
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

    clean_names = [d.lower() for d in all_drugs]

    for rule in combined_rules:
        ra = rule["drug_a"].lower()
        rb = rule["drug_b"].lower()

        # Check if ra matches any drug and rb matches any OTHER drug in clean_names
        match_a_idx = [i for i, name in enumerate(clean_names) if ra in name or name in ra]
        match_b_idx = [i for i, name in enumerate(clean_names) if rb in name or name in rb]

        for ia in match_a_idx:
            for ib in match_b_idx:
                if ia != ib:
                    pair_key = tuple(sorted([all_drugs[ia], all_drugs[ib]]))
                    if pair_key not in seen:
                        seen.add(pair_key)
                        warnings.append({
                            "drug_1": all_drugs[ia],
                            "drug_2": all_drugs[ib],
                            "severity": rule["severity"],
                            "description": rule["description"],
                            "recommendation": rule["recommendation"],
                        })

    return warnings


def get_interaction_details(rule: Dict[str, str]) -> str:
    """Format markdown callout for an interaction."""
    color = "🔴" if rule.get("severity") == "High" else "🟡"
    return f"{color} **{rule.get('severity', 'Warning')} Risk**: {rule.get('description', '')}\n\n*Action:* {rule.get('recommendation', '')}"
