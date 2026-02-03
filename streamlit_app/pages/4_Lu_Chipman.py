"""
Lu-Chipman Decomposition Page - Polar decomposition of Mueller matrices.

This page handles:
- Loading processed Mueller matrices
- Running Lu-Chipman decomposition
- Parameter visualization (DI, R, D, psi, chi)
- Decomposed matrix display
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
from utils.session_state import (
    initialize_session_state,
    is_calibrated,
    get_processed_samples,
    get_lu_chipman_results
)


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="ECM - Lu-Chipman",
    page_icon="🎯",
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
    st.title("🎯 Lu-Chipman Decomposition")

    st.markdown("""
    Perform **polar decomposition** of Mueller matrices to extract physical parameters:
    - **Depolarization Index (DI)**: Measure of polarization preservation [0, 1]
    - **Diattenuation (D)**: Differential attenuation of polarization states
    - **Retardance (R)**: Phase shift between polarization components
    - **Fast-axis angles (ψ, χ)**: Orientation of optical axes
    """)

    st.markdown("---")

    # -------------------------------------------------
    # Prerequisites Check
    # -------------------------------------------------
    if not is_calibrated():
        st.warning("⚠️ **Not calibrated** - Please run calibration first.")
        if st.button("🔧 Go to Calibration"):
            st.switch_page("pages/2_Calibration.py")
        st.stop()

    processed_samples = get_processed_samples()

    if not processed_samples:
        st.info("ℹ️ No processed samples available. Process samples first, or load from file.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📈 Go to Processing", use_container_width=True):
                st.switch_page("pages/3_Processing.py")
        with col2:
            if st.button("📂 Load from File", use_container_width=True):
                st.info("File loading will be implemented in Phase 5")

    # -------------------------------------------------
    # Sample Selection
    # -------------------------------------------------
    with st.expander("📁 Sample Selection", expanded=True):
        sample_names = list(processed_samples.keys()) if processed_samples else ["(No samples)"]

        col1, col2 = st.columns([2, 1])

        with col1:
            selected_sample = st.selectbox(
                "Select Sample",
                options=sample_names,
                key="lu_chipman_sample",
                disabled=not processed_samples
            )

        with col2:
            st.markdown("")  # Spacer
            if st.button("📂 Load from File"):
                st.info("File loading will be implemented in Phase 5")

    # -------------------------------------------------
    # Run Decomposition
    # -------------------------------------------------
    st.markdown("---")

    col1, col2 = st.columns([1, 3])

    with col1:
        run_disabled = not processed_samples
        if st.button("▶️ Run Decomposition", use_container_width=True, disabled=run_disabled):
            st.info("Lu-Chipman decomposition will be implemented in Phase 5")

    with col2:
        if run_disabled:
            st.caption("Process samples first to enable decomposition")

    # -------------------------------------------------
    # Summary Statistics (placeholder)
    # -------------------------------------------------
    with st.expander("📊 Summary Statistics", expanded=False):
        st.info("Summary statistics will be displayed after decomposition (Phase 5)")

        # Placeholder table
        st.markdown("""
        | Parameter | Mean ± Std | Range |
        |-----------|------------|-------|
        | Diattenuation (D) | -- | -- |
        | Retardance (R) | -- | -- |
        | Depol. Index (DI) | -- | -- |
        | Fast-axis (ψ) | -- | -- |
        | Ellipticity (χ) | -- | -- |
        """)

    # -------------------------------------------------
    # Parameter Plots (placeholder)
    # -------------------------------------------------
    with st.expander("📈 Parameter Plots", expanded=False):
        st.info("Interactive parameter plots will be displayed after decomposition (Phase 5)")

        # Tab placeholders
        tab1, tab2, tab3, tab4 = st.tabs(["Depolarization", "Retardance", "Diattenuation", "Axis Angles"])

        with tab1:
            st.markdown("*Depolarization Index (DI) plot will appear here*")

        with tab2:
            st.markdown("*Retardance plot with QWP/HWP reference lines will appear here*")

        with tab3:
            st.markdown("*Diattenuation plot will appear here*")

        with tab4:
            st.markdown("*Fast-axis angles (ψ, χ) plot will appear here*")

    # -------------------------------------------------
    # Decomposed Matrices (placeholder)
    # -------------------------------------------------
    with st.expander("🔲 Decomposed Matrices", expanded=False):
        st.info("Decomposed matrices will be displayed after decomposition (Phase 5)")

        tab1, tab2, tab3 = st.tabs(["Mᴅ (Diattenuator)", "Mᴿ (Retarder)", "MΔ (Depolarizer)"])

        with tab1:
            st.markdown("*Diattenuator matrix elements will appear here*")

        with tab2:
            st.markdown("*Retarder matrix elements will appear here*")

        with tab3:
            st.markdown("*Depolarizer matrix elements will appear here*")

    # -------------------------------------------------
    # Export Section
    # -------------------------------------------------
    st.markdown("---")
    st.subheader("Export")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.button("💾 Save Decomposition (.npz)", disabled=True)
    with col2:
        st.button("📊 Export Plots (.png)", disabled=True)
    with col3:
        st.button("📄 Export Data (.csv)", disabled=True)

    st.caption("Export options will be enabled after running decomposition (Phase 5)")


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
