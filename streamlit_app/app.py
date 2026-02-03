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
from utils.session_state import initialize_session_state, is_calibrated


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="ECM Polarimetry",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)


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
    # Title and Welcome
    # -------------------------------------------------
    st.title("🔬 ECM Polarimetry GUI")

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

    # Visual workflow diagram using columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
            <h3>⚙️</h3>
            <h4>1. Configure</h4>
            <p style="font-size: 0.9em; color: #666;">Set paths and parameters</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
            <h3>🔧</h3>
            <h4>2. Calibrate</h4>
            <p style="font-size: 0.9em; color: #666;">Run ECM calibration</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
            <h3>📈</h3>
            <h4>3. Process</h4>
            <p style="font-size: 0.9em; color: #666;">Extract Mueller matrices</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
            <h3>🎯</h3>
            <h4>4. Decompose</h4>
            <p style="font-size: 0.9em; color: #666;">Lu-Chipman analysis</p>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------
    # Current Status
    # -------------------------------------------------
    st.markdown("---")
    st.subheader("Current Status")

    if is_calibrated():
        st.success("✅ **Calibrated** - Ready to process samples")

        # Show calibration summary
        from utils.session_state import get_calibration_info
        cal_info = get_calibration_info()
        if cal_info:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Wavelengths", cal_info.get('n_wavelengths', 'N/A'))
            with col2:
                wl_min = cal_info.get('wl_min')
                wl_max = cal_info.get('wl_max')
                if wl_min and wl_max:
                    st.metric("Range", f"{wl_min:.0f} - {wl_max:.0f} nm")
            with col3:
                mean_ratio = cal_info.get('mean_ratio')
                if mean_ratio:
                    st.metric("Mean Ratio", f"{mean_ratio:.2e}")
    else:
        st.warning("⚠️ **Not calibrated** - Please configure and run calibration, or load a saved calibration.")

    # -------------------------------------------------
    # Quick Actions
    # -------------------------------------------------
    st.markdown("---")
    st.subheader("Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📂 Load Calibration", use_container_width=True):
            st.switch_page("pages/2_Calibration.py")

    with col2:
        if st.button("⚙️ Configure New", use_container_width=True):
            st.switch_page("pages/1_Configuration.py")

    with col3:
        if is_calibrated():
            if st.button("📈 Process Samples", use_container_width=True):
                st.switch_page("pages/3_Processing.py")
        else:
            st.button("📈 Process Samples", use_container_width=True, disabled=True)
            st.caption("Requires calibration")

    # -------------------------------------------------
    # Information
    # -------------------------------------------------
    st.markdown("---")

    with st.expander("ℹ️ About ECM", expanded=False):
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
