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
import numpy as np

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.sidebar import render_sidebar
from components.plots_plotly import (
    create_mueller_matrix_plot,
    create_selected_elements_plot,
    create_mueller_comparison_plot,
)
from components.mueller_selector import mueller_element_selector
from utils.session_state import (
    initialize_session_state,
    is_calibrated,
    get_calibration_result,
    get_calibration_diagnostics,
    get_processed_samples,
    add_processed_sample,
    get_current_sample,
    set_current_sample,
    get_selected_elements,
    set_selected_elements,
    get_config,
)
from utils.styling import inject_custom_css, soft_divider

# ECM imports
from ecm.io import discover_sample_files
from ecm.core.sample_processing import process_sample
from ecm.utils.io import load_spectral_data


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="MMForge - PROCESSING",
    page_icon=None,
    layout="wide"
)

# Inject consolidated MMForge styling
inject_custom_css()


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

initialize_session_state()

# Initialize processing-specific session state
if 'discovered_samples' not in st.session_state:
    st.session_state['discovered_samples'] = None
if 'selected_samples' not in st.session_state:
    st.session_state['selected_samples'] = []
if 'view_mode' not in st.session_state:
    st.session_state['view_mode'] = '4x4 Grid'


# ============================================================================
# SIDEBAR
# ============================================================================

render_sidebar()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_config_from_session():
    """Build ECMConfig from session state for sample processing."""
    from ecm.config import ECMConfig

    cfg = get_config()
    if cfg is not None:
        return cfg

    # Build from session state if no config stored
    cfg = ECMConfig()
    mode = st.session_state.get('calibration_mode', 'Transmission')
    if mode == 'Reflection':
        data_dir = st.session_state.get('reflection_dir_path', '')
    else:
        data_dir = st.session_state.get('data_dir_path', '')
    if data_dir:
        cfg.paths.data_dir = Path(data_dir)

    wl_min = st.session_state.get('wl_min', 400)
    wl_max = st.session_state.get('wl_max', 1000)
    cfg.wavelength.range_nm = (float(wl_min), float(wl_max))
    cfg.wavelength.reference_nm = 633.0

    n_positions = st.session_state.get('n_positions', 96)
    cfg.acquisition.n_angular_positions = n_positions

    return cfg


def discover_samples():
    """Discover sample files in the data directory for the current mode."""
    mode = st.session_state.get('calibration_mode', 'Transmission')
    if mode == 'Reflection':
        data_dir = st.session_state.get('reflection_dir_path', '')
    else:
        data_dir = st.session_state.get('data_dir_path', '')
    if not data_dir:
        st.error("Data directory not set. Go to **Configuration** page and set the data directory first.")
        return

    cfg = build_config_from_session()

    try:
        with st.spinner("Discovering sample files..."):
            samples = discover_sample_files(Path(data_dir), cfg)

        st.session_state['discovered_samples'] = samples
        st.session_state['selected_samples'] = []  # Reset selection

        if samples.n_samples > 0:
            st.success(f"Found {samples.n_samples} sample(s)")
        else:
            st.warning("No sample .bin files found in directory. Check that your sample measurements are in .bin format.")

    except FileNotFoundError as e:
        st.error("Directory not found. Check that the sample directory path exists and is accessible.")
    except Exception as e:
        st.error(f"Error discovering samples: {e}")


def process_selected_samples():
    """Process all selected samples."""
    selected = st.session_state.get('selected_samples', [])
    if not selected:
        st.error("No samples selected. Select at least one sample from the list above.")
        return

    samples = st.session_state.get('discovered_samples')
    if samples is None:
        st.error("No samples discovered. Click 'Discover Samples' first to find sample files.")
        return

    cal_result = get_calibration_result()
    if cal_result is None:
        st.error("Calibration not available. Run calibration or load a saved calibration on the Calibration page first.")
        return

    # Get calibration diagnostics for dark subtraction
    cal_diag = get_calibration_diagnostics()

    cfg = build_config_from_session()

    # Get calibration matrices
    A = cal_result.A
    W = cal_result.W
    inv_W_mod = cal_result.inv_W_mod

    # Progress bar
    progress_bar = st.progress(0, text="Processing...")

    processed_count = 0
    errors = []

    for i, sample_name in enumerate(selected):
        # Find sample path
        try:
            sample_idx = samples.names.index(sample_name)
            sample_path = samples.paths[sample_idx]
        except (ValueError, IndexError):
            errors.append(f"{sample_name}: not found in discovered samples")
            continue

        try:
            # Load sample data (returns tuple: data, info)
            sample_data, _ = load_spectral_data(sample_path, cfg)

            # Crop sample data to match calibration wavelength range
            # Raw data has 2048 wavelengths, calibration has subset (e.g., 1414)
            if hasattr(cal_result, 'wl_indices') and cal_result.wl_indices is not None:
                sample_data = sample_data[:, cal_result.wl_indices]

            # Subtract dark signal (CRITICAL for correct Mueller matrix)
            if cal_diag is not None and hasattr(cal_diag, 'I_dark') and cal_diag.I_dark is not None:
                sample_data = sample_data - cal_diag.I_dark
                sample_data = np.maximum(sample_data, 0.0)  # Clamp negative values

            # Process sample
            result = process_sample(
                sample_data,
                A=A,
                W=W,
                inv_W_mod=inv_W_mod,
                dark=None,
                cfg=cfg
            )

            # Store result
            add_processed_sample(sample_name, result)
            processed_count += 1

        except Exception as e:
            errors.append(f"{sample_name}: {e}")

        # Update progress
        progress = (i + 1) / len(selected)
        progress_bar.progress(progress, text=f"Processing {i+1}/{len(selected)}...")

    # Store results in session state for display after rerun
    st.session_state['_processing_done'] = True
    st.session_state['_processing_count'] = processed_count
    st.session_state['_processing_total'] = len(selected)
    st.session_state['_processing_errors'] = errors

    # Set current sample
    if processed_count > 0:
        if get_current_sample() is None or get_current_sample() not in get_processed_samples():
            set_current_sample(selected[0])

    st.rerun()


def display_sample_checkboxes():
    """Display checkboxes for sample selection."""
    samples = st.session_state.get('discovered_samples')
    if samples is None or samples.n_samples == 0:
        return

    st.markdown("**Available Samples:**")

    # Select All / Deselect All buttons FIRST (before checkboxes are instantiated)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", use_container_width=True):
            # Update selection list AND checkbox widget keys BEFORE widgets exist
            st.session_state['selected_samples'] = list(samples.names)
            for name in samples.names:
                st.session_state[f"sample_cb_{name}"] = True
            st.rerun()
    with col2:
        if st.button("Deselect All", use_container_width=True):
            st.session_state['selected_samples'] = []
            for name in samples.names:
                st.session_state[f"sample_cb_{name}"] = False
            st.rerun()

    # Display checkboxes in 2 columns
    n_samples = samples.n_samples
    mid = (n_samples + 1) // 2

    col1, col2 = st.columns(2)

    new_selection = []

    for i, name in enumerate(samples.names):
        col = col1 if i < mid else col2
        with col:
            checked = st.checkbox(
                name,
                key=f"sample_cb_{name}"
            )
            if checked:
                new_selection.append(name)

    st.session_state['selected_samples'] = new_selection


def display_results():
    """Display processed sample results with Mueller matrix plots."""
    processed = get_processed_samples()
    if not processed:
        st.info("No processed samples yet. Process samples to see results.")
        return

    sample_names = list(processed.keys())
    current = get_current_sample()

    if current not in sample_names:
        current = sample_names[0]
        set_current_sample(current)

    cal_result = get_calibration_result()

    # View mode toggle - add Compare Samples option if multiple samples
    view_options = ["4x4 Grid", "Selected Elements"]
    if len(processed) > 1:
        view_options.append("Compare Samples")

    view_mode = st.radio(
        "View Mode",
        view_options,
        horizontal=True,
        key="view_mode_radio"
    )

    if view_mode == "Compare Samples":
        # Multi-sample comparison mode
        st.markdown("**Select samples to compare:**")

        # Sample selection checkboxes for comparison
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Select All", key="compare_select_all", use_container_width=True):
                for name in sample_names:
                    st.session_state[f"compare_cb_{name}"] = True
                st.rerun()
        with col2:
            if st.button("Clear All", key="compare_clear_all", use_container_width=True):
                for name in sample_names:
                    st.session_state[f"compare_cb_{name}"] = False
                st.rerun()

        selected_for_compare = []
        cols = st.columns(min(3, len(sample_names)))
        for idx, name in enumerate(sample_names):
            with cols[idx % len(cols)]:
                if st.checkbox(name, key=f"compare_cb_{name}"):
                    selected_for_compare.append(name)

        if len(selected_for_compare) >= 2:
            # Build samples dictionary for comparison plot
            wavelengths = cal_result.wavelengths if cal_result else np.arange(processed[sample_names[0]].M_normalized.shape[2])
            samples_dict = {}
            for name in selected_for_compare:
                result = processed[name]
                samples_dict[name] = (result.M_normalized, result.m00)

            fig = create_mueller_comparison_plot(
                samples_dict,
                wavelengths,
                title="Mueller Matrix Comparison"
            )
            st.plotly_chart(fig, use_container_width=True)

        elif len(selected_for_compare) == 1:
            st.info("Select at least 2 samples to compare")
        else:
            st.info("Select samples above to compare")

    else:
        # Single sample view modes - Select Sample FIRST
        selected_sample = st.selectbox(
            "Select Sample",
            sample_names,
            index=sample_names.index(current) if current in sample_names else 0,
            key="result_sample_selector"
        )

        if selected_sample != current:
            set_current_sample(selected_sample)

        result = processed[selected_sample]
        wavelengths = cal_result.wavelengths if cal_result else np.arange(result.M_normalized.shape[2])

        if view_mode == "4x4 Grid":
            # Full 4x4 Mueller matrix plot with M00 (transmission) in top-left
            fig = create_mueller_matrix_plot(
                result.M_normalized,
                wavelengths,
                title=f"Mueller Matrix - {selected_sample}",
                m00=result.m00
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            # Selected elements view
            st.markdown("**Select Mueller Matrix Elements:**")

            # Mueller element selector
            selected_elements = mueller_element_selector(
                key="processing_element_selector",
                default_selection=get_selected_elements()
            )

            if selected_elements != get_selected_elements():
                set_selected_elements(selected_elements)

            if selected_elements:
                fig = create_selected_elements_plot(
                    result.M_normalized,
                    wavelengths,
                    selected_elements,
                    title=f"Selected Elements - {selected_sample}"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Select elements from the grid above to display")


def save_results():
    """Save processed samples to .npz file."""
    processed = get_processed_samples()
    if not processed:
        st.error("No processed samples to save. Process samples first before exporting.")
        return

    output_dir = st.session_state.get('output_dir_path', str(Path.cwd() / 'processing_output'))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    cal_result = get_calibration_result()
    wavelengths = cal_result.wavelengths if cal_result else None

    # Build save data
    save_data = {
        'wavelengths': wavelengths,
        'sample_names': list(processed.keys()),
    }

    for name, result in processed.items():
        save_data[f'{name}_M'] = result.M
        save_data[f'{name}_M_normalized'] = result.M_normalized
        save_data[f'{name}_m00'] = result.m00

    # Save file
    filepath = output_path / 'processed_samples.npz'
    np.savez(filepath, **save_data)

    st.success(f"Saved to: `{filepath}`")


def export_csv():
    """Export Mueller matrix data to CSV with selection dialog."""
    processed = get_processed_samples()
    if not processed:
        st.error("No processed samples available for export. Process samples first.")
        return

    cal_result = get_calibration_result()
    sample_names = list(processed.keys())

    # Show dialog in expander
    with st.expander("CSV Export Options", expanded=True):
        st.markdown("**Select samples to export:**")

        # Sample selection
        selected_samples = []
        cols = st.columns(min(3, len(sample_names)))
        for idx, name in enumerate(sample_names):
            with cols[idx % len(cols)]:
                if st.checkbox(name, value=True, key=f"csv_export_{name}"):
                    selected_samples.append(name)

        st.markdown("**Select data to include:**")
        col1, col2 = st.columns(2)
        with col1:
            include_normalized = st.checkbox("Normalized Mueller Matrix (m11-m44)", value=True, key="csv_inc_norm")
        with col2:
            include_m00 = st.checkbox("M00 Transmission", value=True, key="csv_inc_m00")

        if st.button("Export Selected", type="primary", disabled=len(selected_samples) == 0, key="csv_export_btn"):
            _do_csv_export(selected_samples, include_normalized, include_m00)


def _do_csv_export(selected_samples, include_normalized, include_m00):
    """Actually perform the CSV export."""
    processed = get_processed_samples()
    cal_result = get_calibration_result()

    output_dir = st.session_state.get('output_dir_path', str(Path.cwd() / 'processing_output'))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    import pandas as pd

    for name in selected_samples:
        result = processed[name]
        wavelengths = cal_result.wavelengths if cal_result else np.arange(result.M_normalized.shape[2])

        data = {'wavelength_nm': wavelengths}

        if include_normalized:
            M = result.M_normalized
            for i in range(4):
                for j in range(4):
                    data[f'm{i+1}{j+1}'] = M[i, j, :]

        if include_m00:
            data['M00_transmission'] = result.m00

        df = pd.DataFrame(data)
        filepath = output_path / f'{name}_mueller_matrix.csv'
        df.to_csv(filepath, index=False)

    st.success(f"Exported {len(selected_samples)} sample(s) to: `{output_path}`")


# ============================================================================
# MAIN PAGE CONTENT
# ============================================================================

def main():
    st.title("Sample Processing")

    # -------------------------------------------------
    # Calibration Status Check
    # -------------------------------------------------
    if not is_calibrated():
        st.warning("Not calibrated. Please run calibration or load a saved calibration first.")
        st.stop()

    st.success("Calibrated - Ready to process samples")

    soft_divider()

    # -------------------------------------------------
    # Sample Selection Section
    # -------------------------------------------------
    has_processed = len(get_processed_samples()) > 0

    with st.expander("Sample Selection", expanded=not has_processed):
        st.markdown("Discover and select samples from your data directory.")

        # Discover button (uses data_dir from Configuration)
        discover_disabled = not st.session_state.get('data_dir_path', '')

        if st.button(
            "Discover Samples",
            use_container_width=False,
            disabled=discover_disabled,
            help="Set data directory in Configuration first" if discover_disabled else None
        ):
            discover_samples()

        if discover_disabled:
            st.caption("Set the data directory in Configuration page first.")

        # Display sample checkboxes
        soft_divider()
        display_sample_checkboxes()

    # -------------------------------------------------
    # Process Samples Section
    # -------------------------------------------------
    soft_divider()

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        selected = st.session_state.get('selected_samples', [])
        process_disabled = len(selected) == 0

        if st.button(
            "Process Selected",
            type="primary",
            use_container_width=True,
            disabled=process_disabled,
            help="Select samples first" if process_disabled else f"Process {len(selected)} sample(s)"
        ):
            process_selected_samples()

    if process_disabled:
        st.caption("Select samples above to enable processing")
    else:
        st.caption(f"{len(selected)} sample(s) selected")

    # Show processing results (persisted in session state across rerun)
    if st.session_state.get('_processing_done'):
        count = st.session_state.get('_processing_count', 0)
        total = st.session_state.get('_processing_total', 0)
        errors = st.session_state.get('_processing_errors', [])

        if count > 0:
            st.success(f"Processed {count}/{total} samples")
        elif total > 0:
            st.error(f"Failed to process all {total} samples")

        if errors:
            with st.expander("Processing Errors", expanded=True):
                for err in errors:
                    st.error(err)

        # Clear the flags after displaying
        del st.session_state['_processing_done']
        del st.session_state['_processing_count']
        del st.session_state['_processing_total']
        del st.session_state['_processing_errors']

        # Update has_processed for Results section
        has_processed = len(get_processed_samples()) > 0

    # -------------------------------------------------
    # Results Section
    # -------------------------------------------------
    if has_processed:
        with st.expander("Results", expanded=True):
            display_results()

    # -------------------------------------------------
    # Export Section
    # -------------------------------------------------
    soft_divider()
    st.subheader("Export")

    col1, col2 = st.columns(2)

    tutorial_mode = st.session_state.get('tutorial_mode', False)
    export_disabled = not has_processed or tutorial_mode

    with col1:
        if st.button(
            "Save Results (.npz)",
            use_container_width=True,
            disabled=export_disabled,
            help="Saving is disabled in Tutorial mode" if tutorial_mode else None
        ):
            save_results()

    with col2:
        if st.button(
            "Export Data (.csv)",
            use_container_width=True,
            disabled=export_disabled,
            help="Exporting is disabled in Tutorial mode" if tutorial_mode else None
        ):
            st.session_state['_show_csv_export'] = True

    if tutorial_mode:
        st.caption("Export is disabled in Tutorial mode")
    elif export_disabled:
        st.caption("Process samples to enable export options")

    # Show CSV export dialog if requested
    if st.session_state.get('_show_csv_export', False) and has_processed:
        export_csv()


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
