"""
Configuration Page - Set up paths, wavelength range, and acquisition parameters.

This page handles:
- Data directory selection (drag-drop + browse)
- Output directory selection
- Wavelength range configuration
- Angular positions setting

Author: Daniel Vala
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.sidebar import render_sidebar
from components.file_browser import directory_selector, directory_selector_compact
from utils.session_state import initialize_session_state
from utils.styling import inject_custom_css


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="MMForge - CONFIGURATION",
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
    st.title("Configuration")

    # -------------------------------------------------
    # Data Paths Section
    # -------------------------------------------------
    with st.expander("Data Paths", expanded=True):
        st.markdown("Select the directories containing both your calibration and sampledata and where to save outputs.")

        col1, col2 = st.columns(2)

        with col1:
            data_dir = directory_selector(
                label="Data Directory",
                key="data_dir",
                default_path="",
                help_text="Directory containing calibration .bin files"
            )

        with col2:
            output_dir = directory_selector_compact(
                label="Output Directory",
                key="output_dir",
                default_path=str(Path.cwd() / "calibration_output")
            )

    # -------------------------------------------------
    # Wavelength and Acquisition Settings (side by side)
    # -------------------------------------------------
    # CSS to equalize expander content heights
    st.markdown("""
    <style>
    /* Make side-by-side expanders equal height */
    [data-testid="stExpander"] {
        min-height: 180px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        with st.expander("Wavelength Settings", expanded=True):
            st.markdown("Configure the wavelength range for calibration.")

            # Use range slider instead of two number inputs
            wl_range = st.slider(
                "Wavelength Range (nm)",
                min_value=400,
                max_value=1000,
                value=(400, 1000),
                step=5,
                key="wavelength_range"
            )
            wl_min, wl_max = wl_range

            # Store in session state for other components
            st.session_state['wl_min'] = wl_min
            st.session_state['wl_max'] = wl_max

            # Validation warnings (non-blocking)
            if wl_min < 350:
                st.warning("Wavelength minimum is below 350 nm. Most polarimeters operate in the visible range (400-800 nm).")
            if wl_max > 1200:
                st.warning("Wavelength maximum exceeds 1200 nm. Verify your detector supports this range.")

            # Hardcode reference wavelength internally (633nm)
            st.session_state['wl_ref'] = 633.0

    with col2:
        with st.expander("Acquisition Settings", expanded=True):
            st.markdown("Configure data acquisition parameters.")

            n_positions = st.number_input(
                "Angular Positions",
                min_value=16,
                max_value=256,
                value=96,
                step=1,
                key="n_positions",
                help="96 positions provides good accuracy while maintaining reasonable measurement time."
            )

            # Validation info for extreme values
            if n_positions < 64:
                st.info("Consider using more steps to avoid calibration instability.")
            elif n_positions > 304:
                st.info("Adding more than 304 steps will not increase precision considerably.")


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
