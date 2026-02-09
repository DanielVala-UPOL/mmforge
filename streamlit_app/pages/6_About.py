"""
About the application and code.

Author: Daniel Vala
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.sidebar import render_sidebar
from utils.session_state import initialize_session_state
from utils.styling import inject_custom_css


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="MMForge - About",
    page_icon=None,
    layout="wide"
)

# Inject consolidated MMForge styling
inject_custom_css()


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

initialize_session_state()


# ============================================================================
# SIDEBAR
# ============================================================================

render_sidebar()


# ============================================================================
# MAIN PAGE CONTENT
# ============================================================================

def main():
    st.title("About MMForge 1.2")

    st.space(size="small")

    st.markdown("""
    This cross-platform, browser-based application was built with Streamlit and is powered by the ECM calibration Python package developed by the author. Currently, the application supports Mueller matrix spectroscopic
    ellipsometry in transmission mode, with plans to extend support to reflection mode and additional features in the future.

    This is MMForge 1.2, released in February 2026. Due to specific requirements of the ECM algorithm, correct operation of the application requires a particular instrument design. This version is intended for exclusive use
    with the custom-built Mueller matrix spectroscopic ellipsometer at the Department of Optics, Palacký University Olomouc, and may not be compatible with other instruments without modification.
    Future versions will aim to support a wider range of instrument configurations.
    """)

    st.space(size="small")

    with st.expander("About ECM", expanded=False):
        st.markdown("""
        The **Eigenvalue Calibration Method (ECM)** is a self-consistent approach for
        calibrating Mueller matrix spectroscopic ellipsometers with an arbitrary design of the Polarization State Generator (PSG) and Polarization State Analyzer (PSA).

        **Key features:**
        - Self-consistent calibration using eigenvalue analysis
        - Automatic extraction of instrument matrices (W, A)
        - Quality metrics via eigenvalue ratio analysis
        - Currently supports transmission mode only

        **Main references:**
        - Compain et al., "General and self-consistent method for the calibration
          of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
          *Appl. Opt.* **38**, 3490–3502 (1999)
        """)

    with st.expander("Changelog", expanded=False):
        st.markdown("""
        ## v1.2 (February 2026)

        **New Features:**
        - Tutorial Data mode with bundled example calibration and sample data
        - Learn the workflow without needing your own measurement data

        **Changes:**
        - Saving/loading disabled in Tutorial mode
        - Auto-configured data paths in Tutorial mode

        ---

        ## v1.1 (February 2026)

        **New Features:**
        - Auto-detect rotator steps from calibration file dimensions
        - Calibration Mode selector (Transmission/Reflection/Combined)

        **Changes:**
        - Removed manual "Angular Positions" input
        - File discovery validates dimension consistency
        - HOME page visual updates and cleanup

        ---

        ## v1.0 (February 2026)

        **Initial Release:**
        - ECM calibration for Mueller matrix spectroscopic polarimetry
        - Transmission mode support
        - Lu-Chipman polar decomposition
        - Interactive Plotly visualizations
        """)


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
