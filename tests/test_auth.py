"""
Unit tests for authentication, role switching, and session logic.
"""

import pytest
import streamlit as st
from utils.auth import init_session_state, is_authenticated, get_current_role, get_current_user, login_user, logout_user
import db.database as db


@pytest.fixture(autouse=True)
def setup_test_auth(tmp_path, monkeypatch):
    """Set up database and fresh session state for testing."""
    test_db_path = str(tmp_path / "test_auth.db")
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()
    db.seed_initial_data()
    # Reset streamlit session state
    st.session_state.clear()
    init_session_state()


def test_session_initialization():
    """Verify session state defaults to unauthenticated before PIN entry."""
    assert is_authenticated() is False
    assert get_current_role() is None
    user = get_current_user()
    assert user["role"] is None
    assert user["name"] is None


def test_login_and_logout():
    """Verify login with correct and incorrect credentials, and logout."""
    # Test valid Caretaker PIN
    success = login_user("caretaker", "8888")
    assert success is True
    assert get_current_role() == "caretaker"
    assert get_current_user()["name"] == "Sarah Vance"

    # Test Logout
    logout_user()
    assert is_authenticated() is False
    assert get_current_role() is None

    # Test invalid PIN
    fail = login_user("elderly", "0000")
    assert fail is False
    assert is_authenticated() is False

    # Test valid Senior PIN
    success_eld = login_user("elderly", "1234")
    assert success_eld is True
    assert get_current_role() == "elderly"
