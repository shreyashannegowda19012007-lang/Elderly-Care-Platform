"""
Authentication and Role-Based Access Control module for GoldenCare.
Manages secure passcode-based session authentication, role switching (Elderly vs Caretaker),
and UI access gates across multi-page workflows.
"""

from __future__ import annotations

import hmac
from typing import Any

import streamlit as st

from db.database import get_patient, get_users, verify_user_passcode


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


def get_current_role() -> str | None:
    """Return active role: 'elderly', 'caretaker', or None if unauthenticated."""
    init_session_state()
    return st.session_state.get("user_role")


def get_current_user() -> dict[str, Any]:
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
    except (UnicodeEncodeError, TypeError, AttributeError):
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


def render_login_form(allowed_roles: list[str] | None = None) -> None:
    """Render a clean, warm, secure PIN login widget when access is restricted."""
    from components.styles import apply_custom_styles
    apply_custom_styles()

    users = get_users()
    eld_u = next((u for u in users if u["role"] == "elderly"), None)
    car_u = next((u for u in users if u["role"] == "caretaker"), None)
    eld_pin_cfg = eld_u["passcode"] if eld_u and eld_u.get("passcode") else "1234"
    car_pin_cfg = car_u["passcode"] if car_u and car_u.get("passcode") else "8888"

    st.markdown("""
        <div style="
            text-align: center;
            max-width: 600px;
            margin: 16px auto 26px auto;
            padding: 26px 20px;
            background: #FFFFFF;
            border-radius: 24px;
            border: 1.5px solid #E2E8F0;
            box-shadow: 0 10px 30px -5px rgba(15, 23, 42, 0.05);
        ">
            <div style="
                width: 54px;
                height: 54px;
                margin: 0 auto 12px auto;
                border-radius: 16px;
                background: #ECFDF5;
                border: 2px solid #A7F3D0;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 14px rgba(5, 150, 105, 0.15);
            ">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
            </div>
            <h2 style="color: #0F172A; margin: 0 0 4px 0; font-size: 24px; font-weight: 800;">Confidential Healthcare Portal</h2>
            <p style="color: #64748B; font-size: 15px; margin: 0; line-height: 1.5;">
                Please select your profile to view protected medication schedules and medical records.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Show only the relevant role login if allowed_roles has a single role
    if allowed_roles and len(allowed_roles) == 1 and allowed_roles[0] == "caretaker":
        st.markdown("""
            <div class="gc-card" style="max-width: 500px; margin: 0 auto 18px auto; border: 2px solid #0284C7; background: linear-gradient(180deg, #F0F9FF 0%, #FFFFFF 100%);">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                    <div style="width: 44px; height: 44px; border-radius: 12px; background: #E0F2FE; display: flex; align-items: center; justify-content: center; border: 1.5px solid #7DD3FC;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0284C7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
                            <line x1="16" x2="16" y1="2" y2="6"/>
                            <line x1="8" x2="8" y1="2" y2="6"/>
                            <line x1="3" x2="21" y1="10" y2="10"/>
                            <path d="m9 16 2 2 4-4"/>
                        </svg>
                    </div>
                    <div>
                        <h3 style="color: #0369A1; margin: 0; font-size: 20px; font-weight: 800;">Sarah Vance</h3>
                        <span style="font-size: 13px; color: #0284C7; font-weight: 600;">Caregiver Clinical Cockpit</span>
                    </div>
                </div>
                <p style="color: #475569; font-size: 14px; margin-bottom: 16px;">This clinical section is restricted to authorized family caregivers.</p>
            </div>
        """, unsafe_allow_html=True)

        if st.button(f"Unlock as Sarah (PIN: {car_pin_cfg})", key="btn_quick_car_single", width="stretch", type="primary"):
            login_user("caretaker", car_pin_cfg)
            st.success("Welcome back, Sarah!")
            st.rerun()

        with st.expander("Or enter PIN manually"):
            car_pin = st.text_input("Enter Caretaker PIN", type="password", key="login_single_car_pin", placeholder=f"PIN ({car_pin_cfg})")
            if st.button("Unlock Caretaker Portal", key="btn_unlock_car", width="stretch"):
                if car_pin and login_user("caretaker", car_pin):
                    st.success("Welcome back, Sarah!")
                    st.rerun()
                else:
                    st.error("Invalid PIN.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
            <div class="gc-card" style="border: 2px solid #10B981; background: linear-gradient(180deg, #F0FDF4 0%, #FFFFFF 100%);">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                    <div style="width: 44px; height: 44px; border-radius: 12px; background: #DCFCE7; display: flex; align-items: center; justify-content: center; border: 1.5px solid #86EFAC;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#047857" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>
                        </svg>
                    </div>
                    <div>
                        <h3 style="color: #065F46; margin: 0; font-size: 20px; font-weight: 800;">Eleanor Vance</h3>
                        <span style="font-size: 13px; color: #047857; font-weight: 600;">Senior Patient Portal</span>
                    </div>
                </div>
                <p style="color: #475569; font-size: 14px; margin-bottom: 14px;">Large text touch portal with spoken audio assistance.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button(f"Unlock as Eleanor (PIN: {eld_pin_cfg})", key="btn_quick_eld_dual", width="stretch", type="primary"):
            login_user("elderly", eld_pin_cfg)
            st.success("Welcome back, Eleanor!")
            st.rerun()

        with st.expander("Or type Senior PIN"):
            elderly_pin = st.text_input("Senior PIN", type="password", key="login_elderly_pin", placeholder=f"Default: {eld_pin_cfg}")
            if st.button("Unlock Senior Portal", key="btn_unlock_eld", width="stretch"):
                if login_user("elderly", elderly_pin):
                    st.success("Welcome back, Eleanor!")
                    st.rerun()
                else:
                    st.error("Invalid PIN.")

    with col2:
        st.markdown("""
            <div class="gc-card" style="border: 2px solid #0284C7; background: linear-gradient(180deg, #F0F9FF 0%, #FFFFFF 100%);">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                    <div style="width: 44px; height: 44px; border-radius: 12px; background: #E0F2FE; display: flex; align-items: center; justify-content: center; border: 1.5px solid #7DD3FC;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0284C7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
                            <line x1="16" x2="16" y1="2" y2="6"/>
                            <line x1="8" x2="8" y1="2" y2="6"/>
                            <line x1="3" x2="21" y1="10" y2="10"/>
                            <path d="m9 16 2 2 4-4"/>
                        </svg>
                    </div>
                    <div>
                        <h3 style="color: #0369A1; margin: 0; font-size: 20px; font-weight: 800;">Sarah Vance</h3>
                        <span style="font-size: 13px; color: #0284C7; font-weight: 600;">Caregiver Cockpit</span>
                    </div>
                </div>
                <p style="color: #475569; font-size: 14px; margin-bottom: 14px;">Clinical telemetry, adherence analytics & scheduling.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button(f"Unlock as Sarah (PIN: {car_pin_cfg})", key="btn_quick_car_dual", width="stretch", type="primary"):
            login_user("caretaker", car_pin_cfg)
            st.success("Welcome back, Sarah!")
            st.rerun()

        with st.expander("Or type Caregiver PIN"):
            caretaker_pin = st.text_input("Caregiver PIN", type="password", key="login_caretaker_pin", placeholder=f"Default: {car_pin_cfg}")
            if st.button("Unlock Caretaker Portal", key="btn_unlock_car_dual", width="stretch"):
                if login_user("caretaker", caretaker_pin):
                    st.success("Welcome back, Sarah!")
                    st.rerun()
                else:
                    st.error("Invalid PIN.")


def require_auth(allowed_roles: list[str] | None = None) -> bool:
    """
    Guard helper for Streamlit pages.
    Verifies authentication and role eligibility.
    If unauthorized, displays login form and calls st.stop().
    """
    init_session_state()

    # If unauthenticated, show login
    if not st.session_state.get("authenticated", False):
        render_login_form(allowed_roles)
        st.stop()
        return False

    # Check role permissions if specified
    current_role = st.session_state.get("user_role")
    if allowed_roles and current_role not in allowed_roles:
        st.error(f"Access Restricted: This section requires {' or '.join(allowed_roles).capitalize()} authorization.")
        st.write(f"You are currently logged in as **{st.session_state.get('user_name', 'Unknown')}** ({str(current_role).capitalize()}).")
        
        target_role = allowed_roles[0]
        users = get_users()
        target_u = next((u for u in users if u["role"] == target_role), None)
        target_u["passcode"] if target_u and target_u.get("passcode") else ("1234" if target_role == "elderly" else "8888")

        col_elev1, col_elev2 = st.columns(2)
        with col_elev1:
            elev_pin = st.text_input(f"Enter {target_role.capitalize()} PIN to elevate", type="password", key=f"pin_elev_{target_role}")
            if st.button(f"Unlock as {target_role.capitalize()}", key=f"btn_elev_{target_role}", type="primary", width="stretch"):
                if login_user(target_role, elev_pin):
                    st.success(f"Access granted as {target_role.capitalize()}!")
                    st.rerun()
                else:
                    st.error(f"Invalid {target_role.capitalize()} PIN.")

        with col_elev2:
            if st.button("Log Out / Change Profile", key="btn_elev_logout", width="stretch"):
                logout_user()
                st.rerun()

        st.stop()
        return False

    return True
