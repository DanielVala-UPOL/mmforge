"""
Shared styling utilities for MMForge.

This module consolidates all CSS styling into a single source of truth,
reducing duplication across page files and making style changes easier.

Color Strategy:
- PRIMARY (#FF1F5B): Brand magenta - buttons, sliders, checkboxes, links
- SECONDARY (#2D3E50): Slate blue - expanders, sidebar highlight, structural elements
- Quality colors: Unchanged from previous implementation

Author: Daniel Vala
"""

import streamlit as st

# ============================================================================
# COLOR CONSTANTS
# ============================================================================

PRIMARY_COLOR = "#FF1F5B"       # Brand magenta - interactive elements
SECONDARY_COLOR = "#2D3E50"     # Slate blue - structural elements
PRIMARY_HOVER = "#d91a4e"       # Darker magenta for hover
SECONDARY_HOVER = "#3d5166"     # Lighter slate for hover

# Message colors
SUCCESS_COLOR = "#56D39A"
WARNING_COLOR = "#E8C34A"
INFO_COLOR = "#0C8AB3"
ERROR_COLOR = "#C22026"


# ============================================================================
# CONSOLIDATED CSS
# ============================================================================

MMFORGE_CSS = """
<style>
    /* ===== Page Container ===== */
    .stMainBlockContainer {
        max-width: 70rem;
    }

    /* ===== Primary Interactive Elements (keep magenta) ===== */
    /* Slider: Only color the selected range, not the full track */
    .stSlider [data-baseweb="slider"] [data-testid="stTickBar"] > div {
        background-color: #ddd !important;
    }
    .stSlider [data-baseweb="slider"] > div > div[role="slider"] {
        background-color: #FF1F5B !important;
    }
    .stSlider [data-baseweb="slider"] > div > div:not([role="slider"]) {
        background-color: #ddd !important;
    }
    .stProgress > div > div > div > div {
        background-color: #FF1F5B !important;
    }
    .stCheckbox > label > div[data-checked="true"] {
        background-color: #FF1F5B !important;
        border-color: #FF1F5B !important;
    }

    /* ===== Primary Buttons (keep magenta for brand) ===== */
    .stButton > button[kind="primary"] {
        background-color: #FF1F5B !important;
        border-color: #FF1F5B !important;
        color: white !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #d91a4e !important;
        border-color: #d91a4e !important;
        color: white !important;
    }

    /* ===== Secondary Buttons ===== */
    .stButton > button:not([kind="primary"]) {
        background-color: #f8f9fa !important;
        border: 1px solid #E0E0E0 !important;
        color: #333333 !important;
    }
    .stButton > button:not([kind="primary"]):hover {
        background-color: #e9ecef !important;
        border-color: #2D3E50 !important;
    }

    /* ===== Message Colors ===== */
    .stSuccess {
        background-color: rgba(86, 211, 154, 0.1) !important;
        border-left-color: #56D39A !important;
    }
    .stWarning {
        background-color: rgba(232, 195, 74, 0.1) !important;
        border-left-color: #E8C34A !important;
    }
    .stInfo {
        background-color: rgba(12, 138, 179, 0.1) !important;
        border-left-color: #0C8AB3 !important;
    }

    /* ===== Sidebar Active Page (use slate blue) ===== */
    [data-testid="stSidebarNav"] li[aria-selected="true"] {
        background-color: rgba(45, 62, 80, 0.1) !important;
        border-left: 3px solid #2D3E50 !important;
    }

    /* ===== Expander Headers (use slate blue) ===== */
    [data-testid="stExpander"] > details > summary {
        background-color: #2D3E50 !important;
        color: white !important;
        border-radius: 4px;
        padding: 0.5rem 1rem;
    }
    [data-testid="stExpander"] > details > summary:hover {
        background-color: #3d5166 !important;
    }
    [data-testid="stExpander"] > details > summary svg {
        fill: white !important;
    }

    /* ===== Form Input Focus States ===== */
    .stTextInput > div > div > input:focus {
        border-color: #2D3E50 !important;
        box-shadow: 0 0 0 2px rgba(45, 62, 80, 0.2) !important;
    }
    .stNumberInput > div > div > input:focus {
        border-color: #2D3E50 !important;
        box-shadow: 0 0 0 2px rgba(45, 62, 80, 0.2) !important;
    }
    .stSelectbox > div > div:focus-within {
        border-color: #2D3E50 !important;
    }

    /* ===== Dataframe Styling ===== */
    [data-testid="stDataFrame"] th {
        background-color: #2D3E50 !important;
        color: white !important;
        font-weight: 600;
    }
    [data-testid="stDataFrame"] tr:hover {
        background-color: rgba(45, 62, 80, 0.05) !important;
    }

    /* ===== Larger Tab Fonts (for decomposed matrix selectors) ===== */
    [data-testid="stTabs"] button {
        font-size: 1.1rem !important;
        font-weight: 500 !important;
    }
</style>
"""


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def inject_custom_css():
    """
    Inject MMForge custom CSS into the current page.

    Call this function once at the top of each page, after st.set_page_config().
    This replaces the need for inline <style> blocks in each page file.

    Example:
        st.set_page_config(page_title="MMForge - PAGE", layout="wide")
        inject_custom_css()
    """
    st.html(MMFORGE_CSS)


def soft_divider():
    """
    Insert a subtle divider between sections.

    Use instead of st.markdown("---") for a softer visual separation.
    """
    st.markdown("""
    <div style="height: 1px; background: linear-gradient(to right, transparent, #E0E0E0, transparent); margin: 1.5rem 0;"></div>
    """, unsafe_allow_html=True)
