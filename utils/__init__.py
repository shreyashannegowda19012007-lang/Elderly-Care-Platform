"""Utility modules for GoldenCare Platform."""

from .alerts import (
    check_and_trigger_alerts,
    dispatch_sos_alert,
    get_alert_summary,
    send_email_alert,
)
from .auth import (
    get_current_role,
    get_current_user,
    init_session_state,
    is_authenticated,
    login_user,
    logout_user,
    require_auth,
    validate_pin,
)
from .interactions import (
    evaluate_interactions,
    get_interaction_details,
)
from .tts import (
    render_speech_button,
    speak_text_script,
)

__all__ = [
    "check_and_trigger_alerts",
    "dispatch_sos_alert",
    "evaluate_interactions",
    "get_alert_summary",
    "get_current_role",
    "get_current_user",
    "get_interaction_details",
    "init_session_state",
    "is_authenticated",
    "login_user",
    "logout_user",
    "render_speech_button",
    "require_auth",
    "send_email_alert",
    "speak_text_script",
    "validate_pin",
]
