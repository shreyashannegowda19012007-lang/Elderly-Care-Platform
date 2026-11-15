"""Utility modules for GoldenCare Platform."""
from .auth import (
    init_session_state,
    is_authenticated,
    get_current_role,
    get_current_user,
    login_user,
    logout_user,
    require_auth,
)
from .alerts import (
    check_and_trigger_alerts,
    send_email_alert,
    dispatch_sos_alert,
    get_alert_summary,
)
from .interactions import (
    evaluate_interactions,
    get_interaction_details,
)
from .tts import (
    render_speech_button,
    speak_text_script,
)
