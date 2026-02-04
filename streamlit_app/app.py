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
    page_title="ECM Polarimetry",
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
    # Welcome
    # -------------------------------------------------
    st.markdown("""
    Welcome to the **Eigenvalue Calibration Method** interface for Mueller matrix
    polarimetry. This application provides an intuitive workflow for:

    - **Calibrating** your polarimeter using the ECM algorithm
    - **Processing** sample measurements to extract Mueller matrices
    - **Analyzing** results with Lu-Chipman polar decomposition
    """)

    # -------------------------------------------------
    # Workflow Overview
    # -------------------------------------------------
    st.markdown("---")
    st.subheader("Workflow")

    # CSS for uniform box heights
    st.markdown("""
    <style>
    .workflow-box {
        text-align: center;
        padding: 20px;
        background-color: #f0f2f6;
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
