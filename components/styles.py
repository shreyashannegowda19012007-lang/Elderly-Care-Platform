"""
Design System and Modern Theme Styling for GoldenCare Platform.
Injects healthcare-grade CSS, warm typography, responsive tactile cards,
micro-interactions, and accessibility enhancements across all Streamlit pages.
Completely removes default Streamlit chrome (Deploy button, toolbar, menu).
"""

from __future__ import annotations
import streamlit as st


def apply_custom_styles() -> None:
    """Inject universal modern healthcare CSS theme and micro-interactions."""
    st.markdown("""
        <style>
            /* Google Fonts */
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@500;600;700;800;900&display=swap');

            /* Global Typography */
            html, body, [class*="css"] {
                font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
                color: #0F172A;
            }

            h1, h2, h3, h4, h5 {
                font-family: 'Outfit', sans-serif !important;
                letter-spacing: -0.02em;
            }

            /* HIDE STREAMLIT DEPLOY BUTTON, HEADER CHROME, TOOLBAR, & FOOTER */
            header[data-testid="stHeader"] {
                display: none !important;
                visibility: hidden !important;
                height: 0 !important;
            }

            [data-testid="stToolbar"] {
                display: none !important;
                visibility: hidden !important;
                height: 0 !important;
            }

            .stDeployButton {
                display: none !important;
                visibility: hidden !important;
            }

            #MainMenu {
                display: none !important;
                visibility: hidden !important;
            }

            footer {
                display: none !important;
                visibility: hidden !important;
            }

            /* Smooth Scrolling Across Whole Window */
            html {
                scroll-behavior: smooth !important;
            }

            /* Thin, Modern Healthcare Scrollbar */
            ::-webkit-scrollbar {
                width: 7px;
                height: 7px;
            }
            ::-webkit-scrollbar-track {
                background: #F8FAFC;
            }
            ::-webkit-scrollbar-thumb {
                background: #CBD5E1;
                border-radius: 9999px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #94A3B8;
            }

            /* Main Layout Background - Warm, Reassuring Healthcare Palette */
            .stApp {
                background: linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 50%, #E2E8F0 100%);
            }

            /* Flowy Page Transitions: Subtle Entrance Animation */
            @keyframes smoothFlowIn {
                0% {
                    opacity: 0;
                    transform: translateY(8px);
                }
                100% {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .main .block-container {
                padding-top: 1.5rem !important;
                padding-bottom: 3rem !important;
                max-width: 1200px !important;
                animation: smoothFlowIn 0.32s cubic-bezier(0.16, 1, 0.3, 1) !important;
            }

            /* Streamlit Sidebar Custom Polish */
            [data-testid="stSidebar"] {
                background-color: #FFFFFF !important;
                border-right: 1.5px solid #E2E8F0 !important;
                box-shadow: 4px 0 25px rgba(0, 0, 0, 0.03) !important;
            }

            [data-testid="stSidebar"] .block-container {
                padding-top: 1.2rem !important;
                padding-left: 1.2rem !important;
                padding-right: 1.2rem !important;
            }

            /* Style the Sidebar Multi-Page Navigation List */
            [data-testid="stSidebarNav"] {
                padding-top: 0.5rem !important;
                margin-bottom: 1rem !important;
            }

            [data-testid="stSidebarNav"]::before {
                content: "CARE NAVIGATION";
                display: block;
                font-size: 11px;
                font-weight: 800;
                color: #94A3B8;
                letter-spacing: 0.06em;
                padding: 6px 14px 10px 14px;
                text-transform: uppercase;
            }

            [data-testid="stSidebarNav"] ul {
                gap: 5px !important;
            }

            [data-testid="stSidebarNav"] li {
                margin-bottom: 4px !important;
            }

            [data-testid="stSidebarNav"] a {
                border-radius: 12px !important;
                padding: 10px 16px !important;
                font-size: 14.5px !important;
                font-weight: 600 !important;
                color: #334155 !important;
                background: #F8FAFC !important;
                border: 1px solid #E2E8F0 !important;
                display: flex !important;
                align-items: center !important;
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
                text-decoration: none !important;
            }

            [data-testid="stSidebarNav"] a:hover {
                background: #ECFDF5 !important;
                border-color: #10B981 !important;
                color: #065F46 !important;
                transform: translateX(4px) !important;
                box-shadow: 0 4px 14px rgba(16, 185, 129, 0.12) !important;
            }

            [data-testid="stSidebarNav"] a[aria-current="page"] {
                background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%) !important;
                border-color: #059669 !important;
                color: #065F46 !important;
                font-weight: 800 !important;
                border-left: 5px solid #059669 !important;
                box-shadow: 0 4px 14px rgba(6, 95, 70, 0.1) !important;
            }

            /* Sleek Card Styling */
            .gc-card {
                background: #FFFFFF;
                border-radius: 20px;
                padding: 24px;
                border: 1px solid rgba(226, 232, 240, 0.9);
                box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.04), 0 8px 10px -6px rgba(15, 23, 42, 0.02);
                transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s ease;
                margin-bottom: 20px;
            }

            .gc-card:hover {
                transform: translateY(-3px);
                box-shadow: 0 20px 32px -10px rgba(15, 23, 42, 0.08);
                border-color: rgba(148, 163, 184, 0.6);
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
                border-radius: 18px;
                padding: 20px 22px;
                border: 1px solid #E2E8F0;
                box-shadow: 0 4px 14px rgba(15, 23, 42, 0.03);
                transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            }

            [data-testid="stMetric"]:hover {
                border-color: #CBD5E1;
                transform: translateY(-2px);
                box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
            }

            [data-testid="stMetricLabel"] {
                font-size: 13px !important;
                font-weight: 700 !important;
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

            /* Modern Streamlit Tabs */
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
                background-color: #F1F5F9;
                padding: 6px;
                border-radius: 14px;
                border: 1px solid #E2E8F0;
            }

            .stTabs [data-baseweb="tab"] {
                height: 44px;
                white-space: pre-wrap;
                background-color: transparent;
                border-radius: 10px;
                color: #475569;
                font-size: 15px;
                font-weight: 600;
                border: none !important;
                padding: 0 20px;
                transition: all 0.2s ease;
            }

            .stTabs [aria-selected="true"] {
                background-color: #FFFFFF !important;
                color: #0284C7 !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06) !important;
                font-weight: 700 !important;
            }

            /* Primary Action Buttons - Tactile & High Contrast */
            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
                color: #FFFFFF !important;
                border: none !important;
                border-radius: 14px !important;
                padding: 12px 24px !important;
                font-weight: 700 !important;
                font-size: 16px !important;
                letter-spacing: 0.01em !important;
                box-shadow: 0 4px 14px rgba(5, 150, 105, 0.35) !important;
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
                min-height: 48px !important;
            }

            .stButton > button[kind="primary"]:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 8px 22px rgba(5, 150, 105, 0.45) !important;
                background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
            }

            /* Secondary Buttons */
            .stButton > button:not([kind="primary"]) {
                background: #FFFFFF !important;
                color: #1E293B !important;
                border: 1.5px solid #CBD5E1 !important;
                border-radius: 14px !important;
                padding: 12px 20px !important;
                font-weight: 600 !important;
                font-size: 15px !important;
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
                min-height: 48px !important;
            }

            .stButton > button:not([kind="primary"]):hover {
                border-color: #0284C7 !important;
                color: #0284C7 !important;
                background: #F0F9FF !important;
                transform: translateY(-1px) !important;
            }

            /* Form Inputs - Large and Clear */
            .stTextInput input, .stSelectbox select, .stNumberInput input {
                border-radius: 12px !important;
                border: 1.5px solid #CBD5E1 !important;
                padding: 12px 16px !important;
                font-size: 16px !important;
                background: #FFFFFF !important;
            }

            .stTextInput input:focus, .stSelectbox select:focus, .stNumberInput input:focus {
                border-color: #0284C7 !important;
                box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.15) !important;
            }

            /* Custom Progress Bar */
            .stProgress > div > div > div > div {
                background: linear-gradient(90deg, #10B981 0%, #059669 100%) !important;
                border-radius: 9999px !important;
            }

            /* Toast Notification Styling */
            [data-testid="stToast"] {
                border-radius: 16px !important;
                box-shadow: 0 12px 30px rgba(0,0,0,0.15) !important;
                font-weight: 600 !important;
            }

            /* Realistic 3D CSS Pill Graphic */
            .pill-capsule {
                display: inline-block;
                width: 38px;
                height: 18px;
                border-radius: 9999px;
                border: 2px solid rgba(255,255,255,0.8);
                box-shadow: 0 3px 6px rgba(0,0,0,0.18), inset 0 2px 4px rgba(255,255,255,0.4);
                vertical-align: middle;
            }

            .pill-tablet {
                display: inline-block;
                width: 22px;
                height: 22px;
                border-radius: 50%;
                border: 2px solid rgba(255,255,255,0.8);
                box-shadow: 0 3px 6px rgba(0,0,0,0.18), inset 0 2px 4px rgba(255,255,255,0.4);
                vertical-align: middle;
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
