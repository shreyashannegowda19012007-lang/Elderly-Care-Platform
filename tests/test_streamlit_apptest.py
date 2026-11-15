"""
Automated Streamlit AppTest verification suite.
Executes Home.py and every multi-page application script in bare runtime mode,
verifying that no unhandled exceptions, syntax errors, or element key collisions occur.
"""

from __future__ import annotations

import os

import pytest
from streamlit.testing.v1 import AppTest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_home_page_apptest():
    """Verify Home.py executes and renders with zero exceptions."""
    home_path = os.path.join(WORKSPACE_ROOT, "Home.py")
    at = AppTest.from_file(home_path).run()
    assert len(at.exception) == 0, f"Exceptions in Home.py: {[e.value for e in at.exception]}"


def test_home_page_authenticated_apptest():
    """Verify Home.py renders active session state for authenticated users."""
    home_path = os.path.join(WORKSPACE_ROOT, "Home.py")
    at = AppTest.from_file(home_path)
    at.session_state["authenticated"] = True
    at.session_state["user_role"] = "elderly"
    at.session_state["user_id"] = 1
    at.session_state["user_name"] = "Eleanor Vance"
    at.session_state["elderly_patient_id"] = 1
    at.run()
    assert len(at.exception) == 0, f"Exceptions in Home.py (Elderly Auth): {[e.value for e in at.exception]}"


@pytest.mark.parametrize("page_name", [
    "1_Elderly_Dashboard.py",
    "2_Caretaker_Dashboard.py",
    "3_Appointments_and_Calendar.py",
    "4_Adherence_Analytics.py",
    "5_Medication_Manager.py",
    "6_System_Settings.py",
])
def test_all_pages_apptest(page_name):
    """Verify each page in pages/ executes without uncaught exceptions when unauthenticated."""
    page_path = os.path.join(WORKSPACE_ROOT, "pages", page_name)
    assert os.path.exists(page_path), f"Page file {page_name} does not exist at {page_path}"
    at = AppTest.from_file(page_path).run()
    assert len(at.exception) == 0, f"Exceptions in unauthenticated {page_name}: {[e.value for e in at.exception]}"


@pytest.mark.parametrize("page_name, role, user_id, user_name", [
    ("1_Elderly_Dashboard.py", "elderly", 1, "Eleanor Vance"),
    ("2_Caretaker_Dashboard.py", "caretaker", 2, "Sarah Vance"),
    ("3_Appointments_and_Calendar.py", "elderly", 1, "Eleanor Vance"),
    ("3_Appointments_and_Calendar.py", "caretaker", 2, "Sarah Vance"),
    ("4_Adherence_Analytics.py", "elderly", 1, "Eleanor Vance"),
    ("4_Adherence_Analytics.py", "caretaker", 2, "Sarah Vance"),
    ("5_Medication_Manager.py", "caretaker", 2, "Sarah Vance"),
    ("6_System_Settings.py", "caretaker", 2, "Sarah Vance"),
])
def test_all_pages_authenticated_apptest(page_name, role, user_id, user_name):
    """Verify each page in pages/ executes and renders all components when fully authenticated."""
    page_path = os.path.join(WORKSPACE_ROOT, "pages", page_name)
    assert os.path.exists(page_path), f"Page file {page_name} does not exist at {page_path}"
    at = AppTest.from_file(page_path)
    at.session_state["authenticated"] = True
    at.session_state["user_role"] = role
    at.session_state["user_id"] = user_id
    at.session_state["user_name"] = user_name
    at.session_state["elderly_patient_id"] = 1
    at.run()
    assert len(at.exception) == 0, f"Exceptions in authenticated {page_name} ({role}): {[e.value for e in at.exception]}"


def test_elderly_high_contrast_mode_apptest():
    """Verify Elderly Dashboard renders cleanly with high contrast mode activated."""
    page_path = os.path.join(WORKSPACE_ROOT, "pages", "1_Elderly_Dashboard.py")
    at = AppTest.from_file(page_path)
    at.session_state["authenticated"] = True
    at.session_state["user_role"] = "elderly"
    at.session_state["user_id"] = 1
    at.session_state["user_name"] = "Eleanor Vance"
    at.session_state["elderly_patient_id"] = 1
    at.session_state["high_contrast"] = True
    at.run()
    assert len(at.exception) == 0, f"Exceptions in Elderly High Contrast mode: {[e.value for e in at.exception]}"
