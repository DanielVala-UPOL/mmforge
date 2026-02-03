"""
Configuration Page - Set up paths, wavelength range, and acquisition parameters.

This page handles:
- Data directory selection (drag-drop + browse)
- Output directory selection
- Wavelength range configuration
- Angular positions setting
- Config save/load functionality

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
from utils.session_state import initialize_session_state, get_config, set_config


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="ECM - Configuration",
    page_icon="⚙️",
    layout="wide"
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
# MAIN PAGE CONTENT
# ============================================================================

def main():
    st.title("⚙️ Configuration")

    # -------------------------------------------------
    # Save/Load buttons in header
    # -------------------------------------------------
    col1, col2, _, _ = st.columns([1, 1, 4, 4])

    with col1:
        if st.button("💾 Save Config", use_container_width=True):
            st.info("Config save will be implemented in Phase 2")

    with col2:
        if st.button("📂 Load Config", use_container_width=True):
            st.info("Config load will be implemented in Phase 2")

    st.markdown("---")

    # -------------------------------------------------
    # Data Paths Section
    # -------------------------------------------------
    with st.expander("📁 Data Paths", expanded=True):
        st.markdown("Select the directories containing your calibration data and where to save outputs.")

        col1, col2 = st.columns(2)

        with col1:
            data_dir = directory_selector(
                label="Data Directory",
                key="data_dir",
                default_path="",
                help_text="Directory containing calibration .bin files"
            )

            if data_dir:
                st.session_state['data_dir_path'] = str(data_dir)

        with col2:
            output_dir = directory_selector_compact(
                label="Output Directory",
                key="output_dir",
                default_path=str(Path.cwd() / "calibration_output")
            )

            if output_dir:
                st.session_state['output_dir_path'] = str(output_dir)

    # -------------------------------------------------
    # Wavelength Settings Section
    # -------------------------------------------------
    with st.expander("🌈 Wavelength Settings", expanded=True):
        st.markdown("Configure the wavelength range for calibration.")

        col1, col2, col3 = st.columns(3)

        with col1:
            wl_min = st.number_input(
                "Min Wavelength (nm)",
                min_value=200.0,
                max_value=2000.0,
                value=400.0,
                step=10.0,
                key="wl_min"
            )

        with col2:
            wl_max = st.number_input(
                "Max Wavelength (nm)",
                min_value=200.0,
                max_value=2000.0,
                value=1000.0,
                step=10.0,
                key="wl_max"
            )

        with col3:
            wl_ref = st.number_input(
                "Reference Wavelength (nm)",
                min_value=200.0,
                max_value=2000.0,
                value=633.0,
                step=1.0,
                key="wl_ref",
                help="Reference wavelength for retarder characterization"
            )

        # Validation
        if wl_min >= wl_max:
            st.error("Min wavelength must be less than max wavelength")

    # -------------------------------------------------
    # Acquisition Section
    # -------------------------------------------------
    with st.expander("📊 Acquisition Settings", expanded=True):
        st.markdown("Configure data acquisition parameters.")

        col1, col2 = st.columns(2)

        with col1:
            n_positions = st.number_input(
                "Angular Positions",
                min_value=16,
                max_value=256,
                value=96,
                step=1,
                key="n_positions",
                help="Number of angular positions per rotation cycle"
            )

        with col2:
            st.markdown("")  # Spacer
            st.markdown("")
            st.info("💡 96 positions provides good accuracy while maintaining reasonable measurement time.")

    # -------------------------------------------------
    # Auto-detection Note
    # -------------------------------------------------
    st.markdown("---")
    st.info("📝 **Note:** Second retarder (FP2) is automatically detected from calibration files. No manual configuration needed.")

    # -------------------------------------------------
    # Configuration Summary
    # -------------------------------------------------
    with st.expander("📋 Configuration Summary", expanded=False):
        st.markdown("**Current Settings:**")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Paths:**")
            st.write(f"- Data: `{st.session_state.get('data_dir_path', 'Not set')}`")
            st.write(f"- Output: `{st.session_state.get('output_dir_path', 'Not set')}`")

        with col2:
            st.markdown("**Parameters:**")
            st.write(f"- Wavelength range: {st.session_state.get('wl_min', 400)} - {st.session_state.get('wl_max', 1000)} nm")
            st.write(f"- Reference: {st.session_state.get('wl_ref', 633)} nm")
            st.write(f"- Angular positions: {st.session_state.get('n_positions', 96)}")


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
