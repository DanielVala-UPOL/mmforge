"""
Calibration Page - Run ECM calibration and view diagnostics.

This page handles:
- File discovery with FP2 auto-detection
- Calibration execution with progress bar
- Quality breakdown display with eigenvalue ratio plot
- Save/load calibration

Author: Daniel Vala
"""

import streamlit as st
from pathlib import Path
import sys
import numpy as np

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.sidebar import render_sidebar
from components.file_browser import file_selector
from components.plots_plotly import (
    create_eigenvalue_plot,
    create_quality_breakdown_chart,
)
from utils.session_state import (
    initialize_session_state,
    is_calibrated,
    get_calibration_info,
    set_calibration,
    clear_calibration,
    get_calibration_result,
    get_calibration_diagnostics,
    set_config,
    get_config
)

# ECM imports
from ecm.config import ECMConfig
from ecm.core import calibrate_transmission
from ecm.core.file_discovery import discover_calibration_files
from ecm.io import save_calibration, load_calibration


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="ECM - Calibration",
    page_icon=None,
    layout="wide"
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
# HELPER FUNCTIONS
# ============================================================================

def build_config_from_session() -> ECMConfig:
    """
    Build ECMConfig from current session state values.

    Maps UI configuration values to the ECMConfig dataclass structure.
    """
    # Get values from session state with defaults
    data_dir = st.session_state.get('data_dir_path', '')
    output_dir = st.session_state.get('output_dir_path', str(Path.cwd() / 'calibration_output'))
    wl_min = st.session_state.get('wl_min', 400)
    wl_max = st.session_state.get('wl_max', 1000)
    n_positions = st.session_state.get('n_positions', 96)

    # Create config with overridden values
    cfg = ECMConfig()

    # Override paths
    if data_dir:
        cfg.paths.data_dir = Path(data_dir)
    cfg.paths.calibration_output_dir = Path(output_dir)

    # Override wavelength settings
    cfg.wavelength.range_nm = (float(wl_min), float(wl_max))
    cfg.wavelength.reference_nm = 633.0  # Hardcoded

    # Override acquisition settings
    cfg.acquisition.n_angular_positions = n_positions

    return cfg


def calculate_quality_breakdown(eigenvalue_ratio: np.ndarray) -> dict:
    """Calculate quality category counts from eigenvalue ratios."""
    return {
        'excellent': int(np.sum(eigenvalue_ratio < 1e-4)),
        'good': int(np.sum((eigenvalue_ratio >= 1e-4) & (eigenvalue_ratio < 1e-3))),
        'acceptable': int(np.sum((eigenvalue_ratio >= 1e-3) & (eigenvalue_ratio < 1e-2))),
        'marginal': int(np.sum((eigenvalue_ratio >= 1e-2) & (eigenvalue_ratio < 0.1))),
        'poor': int(np.sum(eigenvalue_ratio >= 0.1)),
    }


def discover_and_display_files():
    """Discover calibration files and display results."""
    cfg = build_config_from_session()

    if cfg.paths.data_dir is None:
        st.error("Data directory not set. Go to **Configuration** page and enter the path to your calibration data folder.")
        return None

    try:
        with st.spinner("Discovering calibration files..."):
            cal_files = discover_calibration_files(cfg)

        # Store in session state
        st.session_state['discovered_files'] = cal_files

        # Display results
        display_discovered_files(cal_files)

        return cal_files

    except FileNotFoundError as e:
        st.error(f"File discovery failed: {e}. Check that the data directory contains the required calibration files (DARK, ST, P0, P45, FP1).")
        return None
    except ValueError as e:
        st.error(f"Multiple matching files found: {e}. Ensure each calibration type has only one .bin file in the directory.")
        return None
    except Exception as e:
        st.error(f"Unexpected error during file discovery: {e}")
        return None


def display_discovered_files(cal_files):
    """Display discovered files status as a simple message."""
    file_info = [
        ("DARK", cal_files.dark, True),
        ("ST", cal_files.air, True),
        ("P0", cal_files.pol_0, True),
        ("P45", cal_files.pol_45, True),
        ("FP1", cal_files.ret_90, True),
        ("FP2", cal_files.ret_45, False),
    ]

    # Count found and missing required files
    required_found = sum(1 for _, path, req in file_info if req and path is not None)
    required_total = sum(1 for _, _, req in file_info if req)
    missing_required = [name for name, path, req in file_info if req and path is None]
    fp2_found = cal_files.ret_45 is not None

    # Display simple status message
    if required_found == required_total:
        if fp2_found:
            st.success("Found all calibration files.")
        else:
            st.success("Found all calibration files. FP2 not included (optional).")
    else:
        missing_str = ", ".join(missing_required)
        st.error(f"Missing calibration files: **{missing_str}**. Found {required_found}/{required_total} required files. Check that all calibration .bin files are in the data directory.")


def run_calibration_workflow():
    """Execute ECM calibration with progress display."""
    cfg = build_config_from_session()

    # Initialize progress elements - centered and wider
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        progress_container = st.empty()
        progress_bar = progress_container.progress(0, text="0%")

    def progress_callback(current_wl, total_wl, eigenvalue_ratio):
        """Update Streamlit progress bar - only show percentage."""
        progress = current_wl / total_wl
        progress_bar.progress(progress, text=f"{int(progress * 100)}%")

    try:
        result, diagnostics = calibrate_transmission(cfg, progress_callback)

        # Update session state
        set_calibration(result, diagnostics)
        set_config(cfg)

        # Clear progress elements
        progress_container.empty()

        st.success(
            f"Calibration complete! "
            f"{len(result.wavelengths)} wavelengths calibrated. "
            f"Mean eigenvalue ratio: {np.mean(diagnostics.eigenvalue_ratio):.2e}"
        )

        # Trigger rerun to update display
        st.rerun()

    except Exception as e:
        progress_container.empty()
        st.error(f"Calibration failed: {e}. Check that calibration files are valid and not corrupted.")


def display_quality_summary(diagnostics, result):
    """Display quality breakdown with metrics, chart, and eigenvalue plot."""
    ratio = diagnostics.eigenvalue_ratio
    n_total = len(ratio)
    quality = calculate_quality_breakdown(ratio)

    # Calculate ≥Good (excellent + good)
    good_or_better = quality['excellent'] + quality['good']

    # Summary statistics row - changed to 4 columns, removed FP2, renamed Mean Ratio → Mean Quality
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Wavelengths", n_total)
    col2.metric("Mean Quality", f"{np.mean(ratio):.2e}")
    col3.metric("Median Quality", f"{np.median(ratio):.2e}")
    col4.metric("≥Good (%)", f"{100 * good_or_better / n_total:.1f}%")

    # Detailed breakdown table
    st.markdown("**Quality Distribution:**")

    breakdown_data = [
        ("Excellent", "< 1e-4", quality['excellent'], quality['excellent'] / n_total * 100),
        ("Good", "< 1e-3", quality['good'], quality['good'] / n_total * 100),
        ("Acceptable", "< 1e-2", quality['acceptable'], quality['acceptable'] / n_total * 100),
        ("Marginal", "< 0.1", quality['marginal'], quality['marginal'] / n_total * 100),
        ("Poor", "≥ 0.1", quality['poor'], quality['poor'] / n_total * 100),
    ]

    cols = st.columns([2, 2, 2, 2])
    cols[0].markdown("**Category**")
    cols[1].markdown("**Threshold**")
    cols[2].markdown("**Count**")
    cols[3].markdown("**Percentage**")

    for category, threshold, count, pct in breakdown_data:
        cols = st.columns([2, 2, 2, 2])
        cols[0].write(category)
        cols[1].write(threshold)
        cols[2].write(count)
        cols[3].write(f"{pct:.1f}%")

    # Bar chart visualization
    fig = create_quality_breakdown_chart(quality, n_total)
    st.plotly_chart(fig, use_container_width=True)

    # Eigenvalue Ratio plot - now inside Quality Summary
    fig = create_eigenvalue_plot(
        ratio,
        result.wavelengths,
        title="Eigenvalue Ratio (Calibration Quality)"
    )
    st.plotly_chart(fig, use_container_width=True)


def save_current_calibration():
    """Save current calibration to file."""
    result = get_calibration_result()
    diagnostics = get_calibration_diagnostics()
    cfg = get_config()

    if result is None or diagnostics is None:
        st.error("No calibration data available. Run calibration first before saving.")
        return

    if cfg is None:
        cfg = build_config_from_session()

    output_dir = st.session_state.get('output_dir_path', str(Path.cwd() / 'calibration_output'))

    try:
        filepath = save_calibration(
            result=result,
            diagnostics=diagnostics,
            cfg=cfg,
            output_path=Path(output_dir),
            verbose=False
        )
        st.success(f"Calibration saved to: `{filepath}`")

    except Exception as e:
        st.error(f"Failed to save calibration: {e}. Check that the output directory is writable.")


def load_calibration_from_file(filepath: str):
    """Load calibration from file and update session state."""
    try:
        with st.spinner("Loading calibration..."):
            result, diagnostics, cfg, metadata = load_calibration(
                Path(filepath),
                verbose=False
            )

        # Update session state
        set_calibration(result, diagnostics)
        set_config(cfg)

        st.success(
            f"Loaded calibration from {metadata.timestamp}\n\n"
            f"Wavelengths: {metadata.n_wavelengths}, "
            f"Range: {metadata.wavelength_range[0]:.0f}-{metadata.wavelength_range[1]:.0f} nm"
        )

        st.rerun()

    except FileNotFoundError:
        st.error(f"Calibration file not found: `{filepath}`. Check that the file path is correct.")
    except Exception as e:
        st.error(f"Failed to load calibration: {e}. The file may be corrupted or incompatible.")


# ============================================================================
# MAIN PAGE CONTENT
# ============================================================================

def main():
    st.title("Calibration")

    # -------------------------------------------------
    # Current Status (if calibrated) - removed FP2
    # -------------------------------------------------
    if is_calibrated():
        st.success("Calibrated")
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
                    st.metric("Mean Quality", f"{mean_ratio:.2e}")

        st.markdown("---")

    # -------------------------------------------------
    # Calibration Files Section - full width file list
    # -------------------------------------------------
    with st.expander("Calibration Files", expanded=not is_calibrated()):
        st.markdown("Discover calibration files in your data directory.")

        data_dir = st.session_state.get('data_dir_path', '')
        discover_disabled = not data_dir

        if st.button(
            "Discover Files",
            use_container_width=False,
            disabled=discover_disabled,
            help="Set data directory in Configuration page first" if discover_disabled else None
        ):
            discover_and_display_files()

        if not data_dir:
            st.caption("Please set data directory in Configuration page first")

    # -------------------------------------------------
    # Run Calibration Section - centered wider button
    # -------------------------------------------------
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        has_files = 'discovered_files' in st.session_state and st.session_state['discovered_files']
        run_disabled = not has_files

        if st.button(
            "Run Calibration",
            use_container_width=True,
            disabled=run_disabled,
            help="Discover calibration files first" if run_disabled else None
        ):
            # Check if already calibrated - show confirmation dialog
            if is_calibrated():
                st.session_state['_show_recal_dialog'] = True
                st.rerun()
            else:
                run_calibration_workflow()

    if run_disabled:
        st.caption("Click 'Discover Files' first to find calibration files")

    # Re-calibration confirmation dialog
    @st.dialog("Start New Calibration?")
    def confirm_recalibration():
        st.write("This will clear the current calibration and all processed samples.")
        st.write("Are you sure you want to proceed?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("New Calibration", use_container_width=True):
                clear_calibration()
                st.session_state['_show_recal_dialog'] = False
                st.session_state['_run_calibration'] = True
                st.rerun()
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state['_show_recal_dialog'] = False
                st.rerun()

    # Show dialog if triggered
    if st.session_state.get('_show_recal_dialog', False):
        confirm_recalibration()

    # Run calibration if triggered from dialog
    if st.session_state.get('_run_calibration', False):
        st.session_state['_run_calibration'] = False
        run_calibration_workflow()

    # -------------------------------------------------
    # Quality Summary Section (now includes eigenvalue plot)
    # -------------------------------------------------
    if is_calibrated():
        result = get_calibration_result()
        diagnostics = get_calibration_diagnostics()
        if result and diagnostics:
            with st.expander("Quality Summary", expanded=True):
                display_quality_summary(diagnostics, result)

    # -------------------------------------------------
    # Save/Load Calibration Section (moved to bottom)
    # -------------------------------------------------
    st.markdown("---")
    st.subheader("Save / Load Calibration")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Save Current Calibration**")
        save_disabled = not is_calibrated()
        if st.button(
            "Save Calibration",
            use_container_width=True,
            disabled=save_disabled,
            help="Run calibration first to enable saving" if save_disabled else None
        ):
            save_current_calibration()

    with col2:
        st.markdown("**Load Saved Calibration**")

        # File path input
        cal_file_path = st.text_input(
            "Calibration file path (.npz)",
            key="load_cal_path",
            placeholder="/path/to/calibration.npz"
        )

        if cal_file_path:
            if st.button("Load Selected", use_container_width=True):
                load_calibration_from_file(cal_file_path)


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
