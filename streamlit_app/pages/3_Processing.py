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
from components.file_browser import directory_selector_compact
from components.plots_plotly import (
    create_mueller_matrix_plot,
    create_selected_elements_plot,
    create_m00_plot,
    create_mueller_comparison_plot,
)
from components.mueller_selector import mueller_element_selector
from utils.session_state import (
    initialize_session_state,
    is_calibrated,
    get_calibration_info,
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

# ECM imports
from ecm.io import discover_sample_files
from ecm.core.sample_processing import process_sample
from ecm.utils.io import load_spectral_data


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="ECM - Processing",
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
    """Discover sample files in the sample directory."""
    sample_dir = st.session_state.get('sample_dir_path', '')
    if not sample_dir:
        st.error("Please enter a sample directory path")
        return

    cfg = build_config_from_session()

    try:
        with st.spinner("Discovering sample files..."):
            samples = discover_sample_files(Path(sample_dir), cfg)

        st.session_state['discovered_samples'] = samples
        st.session_state['selected_samples'] = []  # Reset selection

        if samples.n_samples > 0:
            st.success(f"Found {samples.n_samples} sample(s)")
        else:
            st.warning("No sample files found in directory")

    except FileNotFoundError as e:
        st.error(f"Directory not found: {e}")
    except Exception as e:
        st.error(f"Error discovering samples: {e}")


def process_selected_samples():
    """Process all selected samples."""
    selected = st.session_state.get('selected_samples', [])
    if not selected:
        st.error("No samples selected")
        return

    samples = st.session_state.get('discovered_samples')
    if samples is None:
        st.error("No samples discovered")
        return

    cal_result = get_calibration_result()
    if cal_result is None:
        st.error("Calibration not available")
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

    # Sample selector dropdown
    sample_names = list(processed.keys())
    current = get_current_sample()

    if current not in sample_names:
        current = sample_names[0]
        set_current_sample(current)

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

    cal_result = get_calibration_result()

    if view_mode == "Compare Samples":
        # Multi-sample comparison mode
        st.markdown("**Select samples to compare:**")

        # Initialize comparison selection if needed
        if 'comparison_samples' not in st.session_state:
            st.session_state['comparison_samples'] = []

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
        # Single sample view modes
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
        st.error("No processed samples to save")
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
    """Export current sample data to CSV."""
    current = get_current_sample()
    processed = get_processed_samples()

    if not current or current not in processed:
        st.error("No sample selected")
        return

    result = processed[current]
    cal_result = get_calibration_result()
    # M_normalized shape is (4, 4, n_wavelengths) - third dimension is wavelengths
    wavelengths = cal_result.wavelengths if cal_result else np.arange(result.M_normalized.shape[2])

    output_dir = st.session_state.get('output_dir_path', str(Path.cwd() / 'processing_output'))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Build CSV data - wavelength + all 16 Mueller elements
    import pandas as pd

    data = {'wavelength_nm': wavelengths}
    M = result.M_normalized

    for i in range(4):
        for j in range(4):
            col_name = f'm{i+1}{j+1}'
            data[col_name] = M[i, j, :]

    # Add unnormalized M00 (transmission)
    data['M00_transmission'] = result.m00

    df = pd.DataFrame(data)
    filepath = output_path / f'{current}_mueller_matrix.csv'
    df.to_csv(filepath, index=False)

    st.success(f"Exported to: `{filepath}`")


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
    # Sample Selection Section
    # -------------------------------------------------
    has_processed = len(get_processed_samples()) > 0

    with st.expander("Sample Selection", expanded=not has_processed):
        st.markdown("Select the directory containing your sample measurements.")

        # Sample directory input
        sample_dir = directory_selector_compact(
            label="Sample Directory",
            key="sample_dir",
            default_path=""
        )

        # Discover button
        discover_disabled = not st.session_state.get('sample_dir_path', '')

        if st.button(
            "Discover Samples",
            use_container_width=False,
            disabled=discover_disabled,
            help="Enter sample directory path first" if discover_disabled else None
        ):
            discover_samples()

        # Display sample checkboxes
        st.markdown("---")
        display_sample_checkboxes()

    # -------------------------------------------------
    # Process Samples Section
    # -------------------------------------------------
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        selected = st.session_state.get('selected_samples', [])
        process_disabled = len(selected) == 0

        if st.button(
            "Process Selected",
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
    st.markdown("---")
    st.subheader("Export")

    col1, col2, col3 = st.columns(3)

    export_disabled = not has_processed

    with col1:
        if st.button(
            "Save Results (.npz)",
            use_container_width=True,
            disabled=export_disabled
        ):
            save_results()

    with col2:
        st.button(
            "Export Plot (.png)",
            use_container_width=True,
            disabled=True,  # TODO: Implement with kaleido
            help="Coming soon"
        )

    with col3:
        if st.button(
            "Export Data (.csv)",
            use_container_width=True,
            disabled=export_disabled
        ):
            export_csv()

    if export_disabled:
        st.caption("Process samples to enable export options")


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
