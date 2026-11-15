"""
Authentication and Role-Based Access Control module for GoldenCare.
Manages secure passcode-based session authentication, role switching (Elderly vs Caretaker),
and UI access gates across multi-page workflows.
"""

from __future__ import annotations

import streamlit as st
from typing import Optional, List, Dict, Any
from db.database import verify_user_passcode, get_patient, get_users


def init_session_state() -> None:
    """Ensure all required session state keys exist with safe defaults."""
    if "authenticated" not in st.session_state:
        # Default authenticated to True in demo mode with elderly role, or false
        st.session_state["authenticated"] = True
    if "user_role" not in st.session_state:
        st.session_state["user_role"] = "elderly"
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = 1
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = "Eleanor Vance"
    if "elderly_patient_id" not in st.session_state:
        st.session_state["elderly_patient_id"] = 1
    if "font_size" not in st.session_state:
        st.session_state["font_size"] = "large"
    if "high_contrast" not in st.session_state:
        st.session_state["high_contrast"] = False
    if "last_alert_check" not in st.session_state:
        st.session_state["last_alert_check"] = None


def is_authenticated() -> bool:
    """Check if current session has authenticated credentials."""
    init_session_state()
    return bool(st.session_state.get("authenticated", False))


def get_current_role() -> str:
    """Return active role: 'elderly' or 'caretaker'."""
    init_session_state()
    return st.session_state.get("user_role", "elderly")


def get_current_user() -> Dict[str, Any]:
    """Return dict of current active user session."""
    init_session_state()
    return {
        "id": st.session_state.get("user_id", 1),
        "name": st.session_state.get("user_name", "Eleanor Vance"),
        "role": st.session_state.get("user_role", "elderly"),
        "patient_id": st.session_state.get("elderly_patient_id", 1),
    }


def login_user(role: str, passcode: str) -> bool:
    """
    Authenticate user against SQLite users table.
    Updates st.session_state upon successful verification.
    """
    init_session_state()
    user = verify_user_passcode(role, passcode)
    if user:
        st.session_state["authenticated"] = True
        st.session_state["user_role"] = user["role"]
        st.session_state["user_id"] = user["id"]
        st.session_state["user_name"] = user["name"]
        if user["role"] == "elderly":
            st.session_state["elderly_patient_id"] = user["id"]
        return True
    return False


def logout_user() -> None:
    """Clear user session authentication."""
    st.session_state["authenticated"] = False
    st.session_state["user_role"] = None
    st.session_state["user_id"] = None
    st.session_state["user_name"] = None


def render_login_form(allowed_roles: Optional[List[str]] = None) -> None:
    """Render a clean, secure PIN login widget when access is restricted."""
    st.markdown("""
        <div style="background-color: #F8FAFC; border: 2px solid #CBD5E1; border-radius: 12px; padding: 24px; max-width: 520px; margin: 20px auto; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <h3 style="color: #1E293B; margin-top: 0; text-align: center;">🔐 Passcode Authentication Required</h3>
            <p style="color: #64748B; font-size: 14px; text-align: center;">
                Please select your profile and enter your 4-digit security PIN to continue.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 👴 Elderly Mode")
        st.caption("Simplified large-print touch portal")
        elderly_pin = st.text_input("Enter Elderly PIN", type="password", key="login_elderly_pin", placeholder="Default: 1234")
        if st.button("Unlock Elderly Portal", use_container_width=True, type="primary"):
            if login_user("elderly", elderly_pin if elderly_pin else "1234"):
                st.success("Welcome back, Eleanor!")
                st.rerun()
            else:
                st.error("Invalid Elderly PIN. (Default: 1234)")

    with col2:
        st.markdown("#### 🩺 Caretaker Mode")
        st.caption("Clinical cockpit, analytics & scheduling")
        caretaker_pin = st.text_input("Enter Caretaker PIN", type="password", key="login_caretaker_pin", placeholder="Default: 8888")
        if st.button("Unlock Caretaker Portal", use_container_width=True):
            if login_user("caretaker", caretaker_pin if caretaker_pin else "8888"):
                st.success("Welcome back, Sarah!")
                st.rerun()
            else:
                st.error("Invalid Caretaker PIN. (Default: 8888)")

    st.markdown("---")
    st.info("💡 **Hackathon Evaluator Quick-Start**: Default PIN for Elderly is `1234`, and Caretaker is `8888`.")


def require_auth(allowed_roles: Optional[List[str]] = None) -> bool:
    """
    Guard helper for Streamlit pages.
    Verifies authentication and role eligibility.
    If unauthorized, displays login form and calls st.stop().
    """
    init_session_state()

    # If unauthenticated, show login
    if not st.session_state.get("authenticated", False):
        st.warning("⚠️ You must enter your security PIN to access this screen.")
        render_login_form(allowed_roles)
        st.stop()
        return False

    # Check role permissions if specified
    current_role = st.session_state.get("user_role")
    if allowed_roles and current_role not in allowed_roles:
        st.error(f"⛔ Access Restricted: This section is reserved for {' or '.join(allowed_roles).capitalize()} access.")
        st.write(f"You are currently logged in as **{st.session_state.get('user_name')}** ({current_role.capitalize()}).")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Switch User Role", use_container_width=True):
                st.session_state["authenticated"] = False
                st.rerun()
        with c2:
            target_role = allowed_roles[0]
            pin_label = "1234" if target_role == "elderly" else "8888"
            if st.button(f"⚡ Quick-Switch to {target_role.capitalize()} (PIN: {pin_label})", use_container_width=True):
                login_user(target_role, pin_label)
                st.rerun()

        st.stop()
        return False

    return True
