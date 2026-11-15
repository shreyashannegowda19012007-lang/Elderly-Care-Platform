"""
Design System and Modern Theme Styling for GoldenCare Platform.
Injects healthcare-grade CSS, typography, responsive cards, micro-interactions,
and glowing status indicators across all Streamlit pages.
"""

import streamlit as st


def apply_custom_styles() -> None:
    """Inject universal modern healthcare CSS theme and micro-interactions."""
    st.markdown("""
        <style>
            /* Google Fonts */
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@500;600;700;800&display=swap');

            /* Global Typography */
            html, body, [class*="css"] {
                font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            h1, h2, h3, h4 {
                font-family: 'Outfit', sans-serif !important;
                letter-spacing: -0.02em;
            }

            /* Main Layout Background */
            .stApp {
                background: linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%);
            }

            /* Top Header Decoration */
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 3.5rem;
                max-width: 1280px;
            }

            /* Sleek Card Styling */
            .gc-card {
                background: #FFFFFF;
                border-radius: 20px;
                padding: 24px;
                border: 1px solid rgba(226, 232, 240, 0.8);
                box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.04), 0 8px 10px -6px rgba(15, 23, 42, 0.02);
                transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
                margin-bottom: 20px;
            }

            .gc-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 20px 30px -10px rgba(15, 23, 42, 0.08);
                border-color: rgba(148, 163, 184, 0.5);
            }

            /* Glowing Status Dot Animation */
            @keyframes pulse-dot {
                0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
                70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
                100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
            }

            .pulse-green {
                width: 10px;
                height: 10px;
                background-color: #10B981;
                border-radius: 50%;
                display: inline-block;
                animation: pulse-dot 2s infinite;
            }

            /* Modern Streamlit Metric Cards */
            [data-testid="stMetric"] {
                background: #FFFFFF;
                border-radius: 16px;
                padding: 18px 20px;
                border: 1px solid #E2E8F0;
                box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
                transition: all 0.2s ease;
            }

            [data-testid="stMetric"]:hover {
                border-color: #CBD5E1;
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(15, 23, 42, 0.06);
            }

            [data-testid="stMetricLabel"] {
                font-size: 13px !important;
                font-weight: 600 !important;
                color: #64748B !important;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }

            [data-testid="stMetricValue"] {
                font-size: 30px !important;
                font-weight: 800 !important;
                color: #0F172A !important;
                font-family: 'Outfit', sans-serif !important;
            }

            /* Modern Tabs */
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
                background-color: #E2E8F0;
                padding: 6px;
                border-radius: 14px;
            }

            .stTabs [data-baseweb="tab"] {
                height: 42px;
                white-space: pre-wrap;
                background-color: transparent;
                border-radius: 10px;
                color: #475569;
                font-size: 14px;
                font-weight: 600;
                border: none !important;
                padding: 0 18px;
                transition: all 0.2s ease;
            }

            .stTabs [aria-selected="true"] {
                background-color: #FFFFFF !important;
                color: #2563EB !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06) !important;
            }

            /* Primary Action Buttons */
            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
                color: white !important;
                border: none !important;
                border-radius: 12px !important;
                padding: 10px 24px !important;
                font-weight: 700 !important;
                font-size: 15px !important;
                box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
                transition: all 0.2s ease !important;
            }

            .stButton > button[kind="primary"]:hover {
                transform: translateY(-1px) !important;
                box-shadow: 0 6px 20px rgba(37, 99, 235, 0.45) !important;
            }

            /* Secondary Buttons */
            .stButton > button:not([kind="primary"]) {
                background: #FFFFFF !important;
                color: #1E293B !important;
                border: 1.5px solid #CBD5E1 !important;
                border-radius: 12px !important;
                padding: 10px 20px !important;
                font-weight: 600 !important;
                font-size: 14px !important;
                transition: all 0.2s ease !important;
            }

            .stButton > button:not([kind="primary"]):hover {
                border-color: #2563EB !important;
                color: #2563EB !important;
                background: #EFF6FF !important;
                transform: translateY(-1px) !important;
            }

            /* Form Inputs */
            .stTextInput input, .stSelectbox select, .stNumberInput input {
                border-radius: 12px !important;
                border: 1.5px solid #CBD5E1 !important;
                padding: 10px 14px !important;
                font-size: 15px !important;
            }

            .stTextInput input:focus, .stSelectbox select:focus, .stNumberInput input:focus {
                border-color: #2563EB !important;
                box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
            }

            /* Custom Progress Bar */
            .stProgress > div > div > div > div {
                background: linear-gradient(90deg, #10B981 0%, #059669 100%) !important;
                border-radius: 9999px !important;
            }

            /* Toast Notification Styling */
            [data-testid="stToast"] {
                border-radius: 14px !important;
                box-shadow: 0 10px 25px rgba(0,0,0,0.12) !important;
            }

            /* Responsive Container Tweaks */
            @media (max-width: 768px) {
                .main .block-container {
                    padding-left: 1rem;
                    padding-right: 1rem;
                }
            }
        </style>
    """, unsafe_allow_html=True)
