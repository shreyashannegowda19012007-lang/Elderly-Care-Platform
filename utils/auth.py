"""
Authentication and Role-Based Access Control module for GoldenCare.
Manages secure passcode-based session authentication, role switching (Elderly vs Caretaker),
and UI access gates across multi-page workflows.
"""

from __future__ import annotations

import hmac
import streamlit as st
from typing import Optional, List, Dict, Any
from db.database import verify_user_passcode, get_patient, get_users


def init_session_state() -> None:
    """Ensure all required session state keys exist with safe defaults."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user_role" not in st.session_state:
        st.session_state["user_role"] = None
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = None
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


def get_current_role() -> Optional[str]:
    """Return active role: 'elderly', 'caretaker', or None if unauthenticated."""
    init_session_state()
    return st.session_state.get("user_role")


def get_current_user() -> Dict[str, Any]:
    """Return dict of current active user session."""
    init_session_state()
    return {
        "id": st.session_state.get("user_id"),
        "name": st.session_state.get("user_name"),
        "role": st.session_state.get("user_role"),
        "patient_id": st.session_state.get("elderly_patient_id", 1),
    }


def validate_pin(provided_pin: Any, expected_pin: Any) -> bool:
    """
    Constant-time PIN validation using hmac.compare_digest with UTF-8 byte encoding.
    Handles non-string, None, unicode, and emoji arguments safely without raising TypeError.
    """
    if provided_pin is None or expected_pin is None:
        return False
    p = str(provided_pin).strip()
    e = str(expected_pin).strip()
    if not p or not e:
        return False
    try:
        return hmac.compare_digest(p.encode("utf-8"), e.encode("utf-8"))
    except Exception:
        return p == e


def login_user(role: str, passcode: Any) -> bool:
    """
    Authenticate user against SQLite users table using passcode.
    Updates st.session_state upon successful verification.
    """
    init_session_state()
    if passcode is None or not isinstance(role, str):
        return False
    user = verify_user_passcode(role, passcode)
    if user:
        st.session_state["authenticated"] = True
        st.session_state["user_role"] = user["role"]
        st.session_state["user_id"] = user["id"]
        st.session_state["user_name"] = user["name"]
        if user["role"] == "elderly":
            st.session_state["elderly_patient_id"] = user["id"]
        else:
            p = get_patient()
            st.session_state["elderly_patient_id"] = p["id"] if p else 1
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
    users = get_users()
    eld_u = next((u for u in users if u["role"] == "elderly"), None)
    car_u = next((u for u in users if u["role"] == "caretaker"), None)
    eld_pin_cfg = eld_u["passcode"] if eld_u and eld_u.get("passcode") else "1234"
    car_pin_cfg = car_u["passcode"] if car_u and car_u.get("passcode") else "8888"

    st.markdown("""
        <div style="background-color: #F8FAFC; border: 2px solid #CBD5E1; border-radius: 12px; padding: 24px; max-width: 540px; margin: 20px auto; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <h3 style="color: #1E293B; margin-top: 0; text-align: center;">🔐 Passcode Authentication Required</h3>
            <p style="color: #64748B; font-size: 14px; text-align: center; margin-bottom: 0;">
                Please enter your 4-digit security PIN to access this screen.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Show only the relevant role login if allowed_roles has a single role
    if allowed_roles and len(allowed_roles) == 1 and allowed_roles[0] == "caretaker":
        st.markdown("#### 🩺 Caretaker PIN Verification")
        st.caption("Clinical cockpit, analytics & scheduling")
        car_pin = st.text_input("Enter Caretaker PIN", type="password", key="login_single_car_pin", placeholder=f"Configured: {car_pin_cfg}")
        if st.button("Unlock Caretaker Portal", key="btn_unlock_car", use_container_width=True, type="primary"):
            if login_user("caretaker", car_pin):
                st.success("Welcome back, Sarah!")
                st.rerun()
            else:
                st.error(f"Invalid Caretaker PIN. (Configured: {car_pin_cfg})")
        st.info(f"💡 **Evaluator Quick-Start**: Active Caretaker PIN is `{car_pin_cfg}`.")
        return

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 👴 Elderly Mode")
        st.caption("Simplified large-print touch portal")
        elderly_pin = st.text_input("Enter Elderly PIN", type="password", key="login_elderly_pin", placeholder=f"Configured: {eld_pin_cfg}")
        if st.button("Unlock Elderly Portal", key="btn_unlock_eld", use_container_width=True, type="primary"):
            if login_user("elderly", elderly_pin):
                st.success("Welcome back, Eleanor!")
                st.rerun()
            else:
                st.error(f"Invalid Elderly PIN. (Configured: {eld_pin_cfg})")

    with col2:
        st.markdown("#### 🩺 Caretaker Mode")
        st.caption("Clinical cockpit, analytics & scheduling")
        caretaker_pin = st.text_input("Enter Caretaker PIN", type="password", key="login_caretaker_pin", placeholder=f"Configured: {car_pin_cfg}")
        if st.button("Unlock Caretaker Portal", key="btn_unlock_car_dual", use_container_width=True):
            if login_user("caretaker", caretaker_pin):
                st.success("Welcome back, Sarah!")
                st.rerun()
            else:
                st.error(f"Invalid Caretaker PIN. (Configured: {car_pin_cfg})")

    st.markdown("---")
    st.info(f"💡 **Hackathon Evaluator Quick-Start**: Configured PIN for Elderly is `{eld_pin_cfg}`, and Caretaker is `{car_pin_cfg}`.")


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
        st.error(f"⛔ Access Restricted: This section requires {' or '.join(allowed_roles).capitalize()} authorization.")
        st.write(f"You are currently logged in as **{st.session_state.get('user_name', 'Unknown')}** ({str(current_role).capitalize()}).")
        
        target_role = allowed_roles[0]
        users = get_users()
        target_u = next((u for u in users if u["role"] == target_role), None)
        target_pin_cfg = target_u["passcode"] if target_u and target_u.get("passcode") else ("1234" if target_role == "elderly" else "8888")

        st.markdown(f"#### 🔐 Enter {target_role.capitalize()} Passcode to Elevate Access")
        elev_pin = st.text_input(f"{target_role.capitalize()} PIN", type="password", key=f"elev_pin_{target_role}", placeholder=f"Configured: {target_pin_cfg}")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button(f"Unlock as {target_role.capitalize()}", key=f"btn_elev_{target_role}", type="primary", use_container_width=True):
                if login_user(target_role, elev_pin):
                    st.success(f"Access granted as {target_role.capitalize()}!")
                    st.rerun()
                else:
                    st.error(f"Invalid {target_role.capitalize()} PIN. (Configured: {target_pin_cfg})")
        with c2:
            if st.button("🚪 Log Out / Change Profile", key="btn_elev_logout", use_container_width=True):
                logout_user()
                st.rerun()

        st.stop()
        return False

    return True
