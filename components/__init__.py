"""UI Components module for GoldenCare Platform."""

from .charts import (
    render_adherence_gauge,
    render_daily_adherence_chart,
    render_time_drift_chart,
    render_time_of_day_chart,
    render_vitals_trend_chart,
)
from .elderly_ui import render_elderly_dose_card, render_elderly_sos_widget
from .header import render_alert_banner, render_app_header
from .styles import apply_custom_styles

__all__ = [
    "apply_custom_styles",
    "render_adherence_gauge",
    "render_alert_banner",
    "render_app_header",
    "render_daily_adherence_chart",
    "render_elderly_dose_card",
    "render_elderly_sos_widget",
    "render_time_drift_chart",
    "render_time_of_day_chart",
    "render_vitals_trend_chart",
]
