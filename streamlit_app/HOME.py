"""
ECM Polarimetry GUI - Home Page

Main entry point for the Streamlit GUI application.
Provides workflow overview and quick navigation.

Author: Daniel Vala
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent directory to path for ECM imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

# Local imports
from components.sidebar import render_sidebar
from utils.session_state import initialize_session_state


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="MMForge - HOME",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom page width (~1.3x default centered = 61rem)
st.html("""
    <style>
        .stMainBlockContainer {
            max-width: 61rem;
        }
    </style>
""")

# MMForge primary color theming
st.html("""
    <style>
        /* Primary color for interactive elements */
        .stSlider > div > div > div > div {
            background-color: #FF1F5B !important;
        }
        .stProgress > div > div > div > div {
            background-color: #FF1F5B !important;
        }
        .stCheckbox > label > div[data-checked="true"] {
            background-color: #FF1F5B !important;
            border-color: #FF1F5B !important;
        }

        /* Primary buttons */
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

        /* Message colors */
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

        /* Sidebar active page indicator */
        [data-testid="stSidebarNav"] li[aria-selected="true"] {
            background-color: rgba(255, 31, 91, 0.1) !important;
            border-left: 3px solid #FF1F5B !important;
        }

        /* Expander headers with brand color */
        [data-testid="stExpander"] > details > summary {
            background-color: #FF1F5B !important;
            color: white !important;
            border-radius: 4px;
            padding: 0.5rem 1rem;
        }
        [data-testid="stExpander"] > details > summary:hover {
            background-color: #d91a4e !important;
        }
        [data-testid="stExpander"] > details > summary svg {
            fill: white !important;
        }
    </style>
""")


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

initialize_session_state()


# ============================================================================
# SIDEBAR
# ============================================================================

render_sidebar()


# ============================================================================
# MAIN CONTENT
# ============================================================================

def main():
    """Render home page content."""

    # -------------------------------------------------
    # Header with Logo and Title
    # -------------------------------------------------
    logo_path = Path(__file__).parent / "assets" / "MMForge_v1.png"

    col1, col2 = st.columns([1, 3])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
    with col2:
        st.title("MMForge")

    st.markdown("""
    Welcome to **MMForge** — the Mueller Matrix Forge for spectroscopic polarimetry.
    This application provides an intuitive workflow for:

    - **Calibrating** your polarimeter using the ECM algorithm
    - **Processing** sample measurements to extract Mueller matrices
    - **Analyzing** results with Lu-Chipman polar decomposition
    """)

    # -------------------------------------------------
    # Workflow Overview
    # -------------------------------------------------
    st.markdown("---")
    st.subheader("Workflow")

    # CSS for uniform box heights with muted brand color
    st.markdown("""
    <style>
    .workflow-box {
        text-align: center;
        padding: 20px;
        background-color: rgba(255, 31, 91, 0.15);
        border-radius: 10px;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .workflow-box h4 { margin: 0 0 8px 0; }
    .workflow-box p { margin: 0; font-size: 0.9em; color: #666; }
    </style>
    """, unsafe_allow_html=True)

    # Visual workflow diagram using columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            '<div class="workflow-box"><h4>1. Configure</h4><p>Set paths and parameters</p></div>',
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            '<div class="workflow-box"><h4>2. Calibrate</h4><p>Run ECM calibration</p></div>',
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            '<div class="workflow-box"><h4>3. Process</h4><p>Extract Mueller matrices</p></div>',
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
            '<div class="workflow-box"><h4>4. Parameters</h4><p>Lu-Chipman analysis</p></div>',
            unsafe_allow_html=True
        )

    # -------------------------------------------------
    # Information
    # -------------------------------------------------
    st.markdown("---")

    with st.expander("About ECM", expanded=False):
        st.markdown("""
        The **Eigenvalue Calibration Method (ECM)** is a self-consistent approach for
        calibrating Mueller matrix polarimeters with dual rotating compensators.

        **Key features:**
        - Self-consistent calibration using eigenvalue analysis
        - Automatic extraction of instrument matrices (W, A)
        - Quality metrics via eigenvalue ratio analysis
        - Support for transmission and reflection modes

        **References:**
        - Compain et al., "General and self-consistent method for the calibration
          of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
          *Appl. Opt.* **38**, 3490-3502 (1999)
        """)


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
