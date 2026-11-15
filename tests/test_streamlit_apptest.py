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


@pytest.mark.parametrize("page_name", [
    "1_Elderly_Dashboard.py",
    "2_Caretaker_Dashboard.py",
    "3_Appointments_and_Calendar.py",
    "4_Adherence_Analytics.py",
    "5_Medication_Manager.py",
    "6_System_Settings.py",
])
def test_all_pages_apptest(page_name):
    """Verify each page in pages/ executes without uncaught exceptions."""
    page_path = os.path.join(WORKSPACE_ROOT, "pages", page_name)
    assert os.path.exists(page_path), f"Page file {page_name} does not exist at {page_path}"
    at = AppTest.from_file(page_path).run()
    assert len(at.exception) == 0, f"Exceptions in {page_name}: {[e.value for e in at.exception]}"
