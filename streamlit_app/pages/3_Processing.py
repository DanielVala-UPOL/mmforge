"""
Sample Processing Page - Process samples using calibration.

This page handles:
- Sample file discovery
- Batch processing with progress
- Mueller matrix visualization
- Export functionality

Author: Daniel Vala
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.sidebar import render_sidebar
from components.file_browser import directory_selector_compact
from utils.session_state import initialize_session_state, is_calibrated, get_calibration_info


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="ECM - Processing",
    page_icon="📈",
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
    st.title("📈 Sample Processing")

    # -------------------------------------------------
    # Calibration Status Check
    # -------------------------------------------------
    if is_calibrated():
        st.success("✅ **Calibrated** - Ready to process samples")

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
                    st.metric("Calibration Quality", f"{mean_ratio:.2e}")

        # Link to load different calibration
        with st.expander("🔄 Change Calibration", expanded=False):
            if st.button("Load Different Calibration"):
                st.switch_page("pages/2_Calibration.py")

    else:
        st.warning("⚠️ **Not calibrated** - Please run calibration or load a saved calibration first.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔧 Go to Calibration", use_container_width=True):
                st.switch_page("pages/2_Calibration.py")
        with col2:
            if st.button("⚙️ Go to Configuration", use_container_width=True):
                st.switch_page("pages/1_Configuration.py")

        st.stop()  # Don't show rest of page if not calibrated

    st.markdown("---")

    # -------------------------------------------------
    # Sample Selection Section
    # -------------------------------------------------
    with st.expander("📁 Sample Selection", expanded=True):
        st.markdown("Select the directory containing your sample measurements.")

        sample_dir = directory_selector_compact(
            label="Sample Directory",
            key="sample_dir",
            default_path=""
        )

        if sample_dir:
            st.session_state['sample_dir_path'] = str(sample_dir)

        col1, col2 = st.columns([1, 3])

        with col1:
            discover_disabled = not st.session_state.get('sample_dir_path', '')
            if st.button("🔍 Discover Samples", use_container_width=True, disabled=discover_disabled):
                st.info("Sample discovery will be implemented in Phase 4")

        # Placeholder sample list
        st.markdown("---")
        st.markdown("**Available Samples:** (placeholder)")

        # Checkbox list placeholder
        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("QWP_0deg", value=False, disabled=True)
            st.checkbox("QWP_45deg", value=False, disabled=True)
        with col2:
            st.checkbox("HWP_0deg", value=False, disabled=True)
            st.checkbox("Unknown_sample", value=False, disabled=True)

        col1, col2 = st.columns(2)
        with col1:
            st.button("Select All", disabled=True)
        with col2:
            st.button("Deselect All", disabled=True)

    # -------------------------------------------------
    # Process Samples Section
    # -------------------------------------------------
    st.markdown("---")

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("▶️ Process Selected", use_container_width=True, disabled=True):
            st.info("Sample processing will be implemented in Phase 4")

    with col2:
        st.caption("Select samples above to enable processing")

    # -------------------------------------------------
    # Results Section (placeholder)
    # -------------------------------------------------
    with st.expander("📊 Results", expanded=False):
        st.info("Mueller matrix results will be displayed here after processing (Phase 4)")

        # View toggle placeholder
        col1, col2 = st.columns(2)
        with col1:
            st.button("🔲 4×4 Matrix View", disabled=True)
        with col2:
            st.button("📈 Select Elements", disabled=True)

        st.markdown("*Mueller matrix plot will appear here*")

        # m00 transmission placeholder
        st.markdown("---")
        st.markdown("**Transmission (m₀₀):** *Plot will appear here*")

    # -------------------------------------------------
    # Export Section (placeholder)
    # -------------------------------------------------
    st.markdown("---")
    st.subheader("Export")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.button("💾 Save Results (.npz)", disabled=True)
    with col2:
        st.button("📊 Export Plot (.png)", disabled=True)
    with col3:
        st.button("📄 Export Data (.csv)", disabled=True)

    st.caption("Export options will be enabled after processing samples (Phase 4)")


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
