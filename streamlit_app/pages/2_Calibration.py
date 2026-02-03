"""
Calibration Page - Run ECM calibration and view diagnostics.

This page handles:
- File discovery
- Calibration execution with progress
- Quality breakdown display
- Diagnostic plot visualization
- Save/load calibration

Author: Daniel Vala
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.sidebar import render_sidebar
from components.file_browser import file_selector
from utils.session_state import initialize_session_state, is_calibrated, get_calibration_info


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="ECM - Calibration",
    page_icon="🔧",
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
    st.title("🔧 Calibration")

    # -------------------------------------------------
    # Current Status
    # -------------------------------------------------
    if is_calibrated():
        st.success("✅ Calibration loaded")
        cal_info = get_calibration_info()
        if cal_info:
            col1, col2, col3, col4 = st.columns(4)
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
            with col4:
                if cal_info.get('use_ret45'):
                    st.metric("FP2", "Detected")
                else:
                    st.metric("FP2", "Not used")

        st.markdown("---")

    # -------------------------------------------------
    # Calibration Files Section
    # -------------------------------------------------
    with st.expander("📁 Calibration Files", expanded=True):
        st.markdown("Discover calibration files in your data directory.")

        col1, col2 = st.columns([1, 3])

        with col1:
            if st.button("🔍 Discover Files", use_container_width=True):
                st.info("File discovery will be implemented in Phase 3")

        with col2:
            data_dir = st.session_state.get('data_dir_path', '')
            if data_dir:
                st.write(f"📂 Looking in: `{data_dir}`")
            else:
                st.warning("⚠️ Please set data directory in Configuration page first")

        # Placeholder for discovered files
        st.markdown("---")
        st.markdown("**Discovered Files:** (placeholder)")
        st.markdown("""
        - ⏳ Dark: *not discovered*
        - ⏳ Air: *not discovered*
        - ⏳ Polarizer 0°: *not discovered*
        - ⏳ Polarizer 45°: *not discovered*
        - ⏳ Retarder 90° (FP1): *not discovered*
        - ⏳ Retarder 45° (FP2): *auto-detect*
        """)

    # -------------------------------------------------
    # Run Calibration Section
    # -------------------------------------------------
    st.markdown("---")

    col1, col2 = st.columns([1, 3])

    with col1:
        run_disabled = not st.session_state.get('data_dir_path', '')
        if st.button("▶️ Run Calibration", use_container_width=True, disabled=run_disabled):
            st.info("Calibration execution will be implemented in Phase 3")

            # Placeholder progress bar
            import time
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress_bar.progress(i + 1)
            st.success("Calibration complete (placeholder)")

    with col2:
        if run_disabled:
            st.caption("⚠️ Set data directory in Configuration page to enable calibration")

    # -------------------------------------------------
    # Quality Summary Section (placeholder)
    # -------------------------------------------------
    with st.expander("📊 Quality Summary", expanded=False):
        st.info("Quality breakdown will be displayed after calibration (Phase 3)")

        # Placeholder quality breakdown
        st.markdown("""
        **Quality Breakdown:** (placeholder)
        - Excellent (< 1e-4): --
        - Good (< 1e-3): --
        - Acceptable (< 1e-2): --
        - Marginal (< 0.1): --
        - Poor (≥ 0.1): --
        """)

    # -------------------------------------------------
    # Save/Load Calibration Section
    # -------------------------------------------------
    st.markdown("---")
    st.subheader("Save / Load Calibration")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Save Current Calibration**")
        save_disabled = not is_calibrated()
        if st.button("💾 Save Calibration", use_container_width=True, disabled=save_disabled):
            st.info("Save functionality will be implemented in Phase 3")
        if save_disabled:
            st.caption("Run calibration first to enable saving")

    with col2:
        st.markdown("**Load Saved Calibration**")
        cal_file = file_selector(
            label="Calibration File",
            key="load_calibration",
            file_types=['.npz'],
            default_path=""
        )

        if cal_file:
            if st.button("📂 Load Selected", use_container_width=True):
                st.info("Load functionality will be implemented in Phase 3")

    # -------------------------------------------------
    # Diagnostic Plots Section (placeholder)
    # -------------------------------------------------
    with st.expander("📈 Diagnostic Plots", expanded=False):
        st.info("Interactive diagnostic plots will be displayed after calibration (Phase 3)")

        # Tab placeholders
        tab1, tab2, tab3, tab4 = st.tabs(["Eigenvalue Ratio", "W Matrix", "A Matrix", "Air Validation"])

        with tab1:
            st.markdown("Eigenvalue ratio plot will appear here")

        with tab2:
            st.markdown("W matrix elements plot will appear here")

        with tab3:
            st.markdown("A matrix elements plot will appear here")

        with tab4:
            st.markdown("Air Mueller matrix validation plot will appear here")


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
