"""
Timezone management utility for GoldenCare Platform.
Ensures accurate scheduling, overdue dose detection, and diurnal period calculations
across diverse cloud environments and local timezones.
"""

from __future__ import annotations

import os
import zoneinfo
from datetime import date, datetime

import streamlit as st


def get_app_timezone() -> zoneinfo.ZoneInfo | datetime.tzinfo:
    """
    Retrieve configured application timezone.
    Checks Streamlit secrets, environment variables, and falls back to local machine timezone.
    """
    tz_name = None
    try:
        from streamlit.errors import StreamlitSecretNotFoundError

        if hasattr(st, "secrets") and "timezone" in st.secrets:
            tz_name = str(st.secrets["timezone"]).strip()
        elif hasattr(st, "secrets") and "app" in st.secrets and "timezone" in st.secrets["app"]:
            tz_name = str(st.secrets["app"]["timezone"]).strip()
    except (StreamlitSecretNotFoundError, FileNotFoundError, KeyError, AttributeError, TypeError):
        pass

    if not tz_name:
        tz_name = os.environ.get("APP_TIMEZONE")

    if tz_name:
        try:
            return zoneinfo.ZoneInfo(tz_name)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError, OSError):
            pass

    # Default to system local timezone
    return datetime.now().astimezone().tzinfo


def get_now() -> datetime:
    """Return timezone-aware current datetime for the platform."""
    tz = get_app_timezone()
    return datetime.now(tz)


def get_today_date() -> date:
    """Return timezone-aware current calendar date."""
    return get_now().date()


def get_today_str() -> str:
    """Return YYYY-MM-DD string for current platform date."""
    return get_today_date().isoformat()


def get_now_time_str() -> str:
    """Return HH:MM string for current platform time."""
    return get_now().strftime("%H:%M")


def get_now_timestamp_str() -> str:
    """Return YYYY-MM-DD HH:MM:SS string for current platform timestamp."""
    return get_now().strftime("%Y-%m-%d %H:%M:%S")
