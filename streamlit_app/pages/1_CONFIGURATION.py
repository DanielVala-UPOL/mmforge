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
from utils.session_state import initialize_session_state, default_output_dir
from utils.theme import sync_theme
from utils.styling import inject_custom_css


def get_tutorial_data_path() -> Path:
    """Get absolute path to bundled tutorial data."""
    # Path relative to this file: pages/1_CONFIGURATION.py
    # Tutorial data at: project_root/data/tutorial/
    return Path(__file__).parent.parent.parent / "data" / "tutorial"


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

# Notice a theme switch and rerun once, so the Plotly figures are
# rebuilt with the new palette instead of lagging a frame behind
# the chrome. Must run after initialize_session_state(), which
# creates the key this compares against.
sync_theme()


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
    # Determine tutorial mode from current selectbox value
    # (must be done before Data Paths renders to avoid stale state)
    # -------------------------------------------------
    current_mode = st.session_state.get('calibration_mode', 'Transmission')
    tutorial_mode = (current_mode == "Tutorial Data")

    # Update session state flags based on current mode
    st.session_state['tutorial_mode'] = tutorial_mode
    st.session_state['saving_disabled'] = tutorial_mode
    if tutorial_mode:
        st.session_state['data_dir_path'] = str(get_tutorial_data_path())
    else:
        # Reset data_dir_path if it was set to tutorial path (user switched away from Tutorial mode)
        tutorial_path_str = str(get_tutorial_data_path())
        if st.session_state.get('data_dir_path', '') == tutorial_path_str:
            st.session_state['data_dir_path'] = ''

    # -------------------------------------------------
    # Data Paths Section
    # -------------------------------------------------
    with st.expander("Data Paths", expanded=True):
        st.markdown("Select the directories containing your calibration and sample data and where to save outputs.")

        if tutorial_mode:
            # Tutorial mode: show read-only paths
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Data Directory**")
                tutorial_path = get_tutorial_data_path()
                st.text_input(
                    "Path",
                    value=str(tutorial_path),
                    key="data_dir_tutorial_display",
                    disabled=True,
                    label_visibility="collapsed"
                )
                st.info("Using bundled tutorial data.")
            with col2:
                st.markdown("**Output Directory**")
                st.text_input(
                    "Path",
                    value="(Saving disabled)",
                    key="output_dir_tutorial_display",
                    disabled=True,
                    label_visibility="collapsed"
                )
                st.warning("Saving is disabled in Tutorial mode.")

        elif current_mode == "Transmission":
            col1, col2 = st.columns(2)
            with col1:
                directory_selector(
                    label="Transmission Data Directory",
                    key="data_dir",
                    default_path="",
                    help_text="Directory containing transmission calibration and sample .bin files"
                )
            with col2:
                directory_selector_compact(
                    label="Output Directory",
                    key="output_dir",
                    default_path=default_output_dir()
                )

        elif current_mode == "Reflection":
            col1, col2 = st.columns(2)
            with col1:
                directory_selector(
                    label="Reflection Data Directory",
                    key="refl_data_dir",
                    default_path="",
                    help_text="Directory containing reflection calibration (DARK, WAFER25NM/10NM, POL_BEFORE, POL_AFTER) and sample .bin files"
                )
            with col2:
                directory_selector_compact(
                    label="Output Directory",
                    key="output_dir",
                    default_path=default_output_dir()
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
            # NOTE: no `value=` — default is pre-loaded into session_state by
            # initialize_session_state(); passing `value=` together with `key=`
            # and a pre-populated session_state entry triggers a Streamlit
            # "default value but also had its value set via Session State"
            # warning when the user switches modes.
            wl_range = st.slider(
                "Wavelength Range (nm)",
                min_value=400,
                max_value=1000,
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
        with st.expander("Calibration Mode", expanded=True):
            st.markdown("Select the measurement configuration.")

            # No `index=` — default comes from session_state (pre-initialized).
            mode = st.selectbox(
                "Mode",
                options=["Transmission", "Reflection", "Tutorial Data"],
                key="calibration_mode",
                help="Transmission calibrates the straight-through configuration. "
                     "Reflection calibrates oblique-incidence measurements using two wafer references. "
                     "Tutorial Data uses bundled example files."
            )

            # Display mode-specific messages (state already updated at top of main())
            if mode == "Tutorial Data":
                st.info("Using bundled tutorial data for learning and demonstration. Saving is disabled in this mode.")
            elif mode == "Reflection":
                # AOI input — passes through to cfg.reflection_cal.angle_of_incidence_deg
                unlock_aoi = st.checkbox(
                    "I understand the risks of changing the AOI",
                    key="unlock_aoi",
                    help="The AOI is fixed at 70° by default as it provides the best calibration results."
                )
                # No `value=` — default comes from session_state (pre-initialized to 70.0).
                st.number_input(
                    "Angle of Incidence (degrees)",
                    min_value=55.0,
                    max_value=75.0,
                    step=1.0,
                    key="refl_aoi_deg",
                    disabled=not unlock_aoi,
                    help="AOI of the reflection measurement. Default is 70°."
                )
                if unlock_aoi:
                    st.warning(
                        "**Changing the AOI may lead to incorrect calibration results if it does not match the actual measurement geometry.**",
                        icon="⚠️"
                    )


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
