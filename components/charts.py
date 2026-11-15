"""
Plotly Charting and Data Visualization Components for GoldenCare.
Renders clinical adherence gauges, longitudinal adherence trendlines,
time-drift variance analysis, diurnal distribution, and vital sign trends.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, Any, List


def render_adherence_gauge(rate: float) -> go.Figure:
    """Generate an accessible speedometer gauge chart of current adherence rate."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rate,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Adherence Index", 'font': {'size': 20, 'color': '#1E293B', 'family': 'sans-serif'}},
        number={'suffix': "%", 'font': {'size': 38, 'color': '#0F172A', 'weight': 'bold'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#94A3B8"},
            'bar': {'color': "#2563EB", 'thickness': 0.3},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#E2E8F0",
            'steps': [
                {'range': [0, 70], 'color': '#FEE2E2'},
                {'range': [70, 85], 'color': '#FEF3C7'},
                {'range': [85, 100], 'color': '#DCFCE7'},
            ],
            'threshold': {
                'line': {'color': "#10B981", 'width': 4},
                'thickness': 0.75,
                'value': 90.0,
            }
        }
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def render_daily_adherence_chart(df: pd.DataFrame) -> go.Figure:
    """Generate 14-day stacked bar and adherence rate trend chart."""
    fig = go.Figure()

    if df.empty:
        fig.add_annotation(text="No adherence records available", showarrow=False, font=dict(size=14))
        return fig

    # Doses Taken Bar
    fig.add_trace(go.Bar(
        x=df["date"],
        y=df["taken"],
        name="Taken Doses",
        marker_color="#10B981",
    ))

    # Doses Missed Bar
    fig.add_trace(go.Bar(
        x=df["date"],
        y=df["missed"],
        name="Missed Doses",
        marker_color="#EF4444",
    ))

    # Daily Adherence Rate Line
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["rate"],
        name="Adherence Rate (%)",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color="#2563EB", width=3),
        marker=dict(size=7, color="#1D4ED8"),
    ))

    fig.update_layout(
        barmode='stack',
        height=340,
        margin=dict(l=30, r=40, t=30, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title="Date", showgrid=False),
        yaxis=dict(title="Dose Count", showgrid=True, gridcolor="#E2E8F0"),
        yaxis2=dict(
            title="Adherence %",
            overlaying="y",
            side="right",
            range=[0, 105],
            showgrid=False,
        ),
    )
    return fig


def render_time_drift_chart(df: pd.DataFrame) -> go.Figure:
    """Render scatter analysis of dose timing adherence drift (minutes from schedule)."""
    fig = go.Figure()

    if df.empty:
        fig.add_annotation(text="No time drift data available", showarrow=False, font=dict(size=14))
        return fig

    # Add zero baseline
    fig.add_hline(y=0, line_dash="dash", line_color="#10B981", annotation_text="Exact On-Time", annotation_position="bottom right")

    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["drift_minutes"],
        mode="markers",
        marker=dict(
            size=10,
            color=df["drift_minutes"],
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Min Delay"),
        ),
        text=df.apply(lambda r: f"{r['medication']} ({r['time_of_day']}): {r['drift_minutes']} min delay", axis=1),
        hoverinfo="text",
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=30, r=30, t=30, b=30),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title="Date", showgrid=False),
        yaxis=dict(title="Time Drift (Minutes Late)", showgrid=True, gridcolor="#E2E8F0"),
    )
    return fig


def render_time_of_day_chart(df: pd.DataFrame) -> go.Figure:
    """Render adherence distribution by diurnal time slot (Morning, Afternoon, Evening, Bedtime)."""
    fig = go.Figure()

    if df.empty:
        fig.add_annotation(text="No time slot data available", showarrow=False, font=dict(size=14))
        return fig

    order_map = {"Morning": 1, "Afternoon": 2, "Evening": 3, "Bedtime": 4}
    df["order"] = df["time_of_day"].map(order_map).fillna(5)
    df = df.sort_values("order")

    fig.add_trace(go.Bar(
        x=df["time_of_day"],
        y=df["rate"],
        text=[f"{r:.1f}%" for r in df["rate"]],
        textposition="auto",
        marker_color=["#3B82F6", "#F59E0B", "#10B981", "#8B5CF6"][:len(df)],
    ))

    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=20, b=30),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title="Time of Day", showgrid=False),
        yaxis=dict(title="Adherence %", range=[0, 110], showgrid=True, gridcolor="#E2E8F0"),
    )
    return fig


def render_vitals_trend_chart(vitals_list: List[Dict[str, Any]]) -> go.Figure:
    """Generate longitudinal vital sign trends with blood pressure and glucose lines."""
    fig = go.Figure()

    if not vitals_list:
        fig.add_annotation(text="No vitals logged yet", showarrow=False, font=dict(size=14))
        return fig

    df = pd.DataFrame(vitals_list).sort_values("recorded_date")

    # Systolic BP
    fig.add_trace(go.Scatter(
        x=df["recorded_date"],
        y=df["systolic_bp"],
        name="Systolic BP (mmHg)",
        mode="lines+markers",
        line=dict(color="#DC2626", width=2),
    ))

    # Diastolic BP
    fig.add_trace(go.Scatter(
        x=df["recorded_date"],
        y=df["diastolic_bp"],
        name="Diastolic BP (mmHg)",
        mode="lines+markers",
        line=dict(color="#EA580C", width=2),
    ))

    # Blood Glucose
    fig.add_trace(go.Scatter(
        x=df["recorded_date"],
        y=df["blood_glucose"],
        name="Blood Glucose (mg/dL)",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color="#2563EB", width=2, dash="dot"),
    ))

    # Add Normal Range Band for Systolic BP (90-140)
    fig.add_hrect(
        y0=90, y1=140,
        line_width=0, fillcolor="#10B981", opacity=0.1,
        annotation_text="Normal BP Target", annotation_position="top left"
    )

    fig.update_layout(
        height=320,
        margin=dict(l=30, r=40, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title="Date", showgrid=False),
        yaxis=dict(title="Blood Pressure (mmHg)", showgrid=True, gridcolor="#E2E8F0"),
        yaxis2=dict(
            title="Blood Glucose (mg/dL)",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
    )
    return fig
