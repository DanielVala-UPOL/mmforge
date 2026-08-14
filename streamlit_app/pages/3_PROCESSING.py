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
    create_ellipsometry_plot,
    create_ellipsometry_comparison_plot,
)
from components.mueller_selector import mueller_element_selector
from utils.session_state import (
    initialize_session_state,
    is_calibrated,
    is_reflection_calibrated,
    get_calibration_result,
    get_calibration_diagnostics,
    get_reflection_calibration_result,
    get_reflection_calibration_diagnostics,
    get_processed_samples,
    add_processed_sample,
    add_reflection_processed_sample,
    get_current_sample,
    set_current_sample,
    get_selected_elements,
    set_selected_elements,
    get_config,
    get_output_dir,
)
from utils.theme import sync_theme
from utils.styling import inject_custom_css, soft_divider

# ECM imports
from ecm.io import discover_sample_files
from ecm.core.sample_processing import process_sample
from ecm.core.ellipsometry import extract_ellipsometric_parameters
from ecm.utils.io import load_spectral_data


# ============================================================================
# MODE-AWARE STATE HELPERS
# ============================================================================

def _active_state():
    """Return mode-aware lookups used throughout this page.

    Returns
    -------
    dict with keys: mode, is_reflection, calibrated, cal_result, cal_diag,
        data_dir, processed_samples, ellips_results, processed_key,
        ellips_key, current_key, selected_key, discovered_key, aoi_deg
    """
    mode = st.session_state.get('calibration_mode', 'Transmission')
    is_reflection = (mode == 'Reflection')

    if is_reflection:
        return {
            'mode': mode,
            'is_reflection': True,
            'calibrated': is_reflection_calibrated(),
            'cal_result': get_reflection_calibration_result(),
            'cal_diag': get_reflection_calibration_diagnostics(),
            'data_dir': st.session_state.get('refl_data_dir_path', ''),
            'processed_samples': st.session_state.get('refl_processed_samples', {}),
            'ellips_results': st.session_state.get('refl_ellipsometry_results', {}),
            'processed_key': 'refl_processed_samples',
            'ellips_key': 'refl_ellipsometry_results',
            'current_key': 'refl_current_sample',
            'selected_key': 'refl_selected_samples',
            'discovered_key': 'refl_discovered_samples',
            'aoi_deg': float(st.session_state.get('refl_aoi_deg', 70.0)),
        }
    return {
        'mode': mode,
        'is_reflection': False,
        'calibrated': is_calibrated(),
        'cal_result': get_calibration_result(),
        'cal_diag': get_calibration_diagnostics(),
        'data_dir': st.session_state.get('data_dir_path', ''),
        'processed_samples': get_processed_samples(),
        'ellips_results': {},
        'processed_key': 'processed_samples',
        'ellips_key': None,
        'current_key': 'current_sample',
        'selected_key': 'selected_samples',
        'discovered_key': 'discovered_samples',
        'aoi_deg': None,
    }


def _active_processed():
    """Mode-aware accessor for the processed-samples dict (mirrors get_processed_samples)."""
    s = _active_state()
    return s['processed_samples']


def _active_set_current(name):
    """Mode-aware setter for the currently selected sample."""
    s = _active_state()
    st.session_state[s['current_key']] = name


def _active_get_current():
    """Mode-aware getter for the currently selected sample."""
    s = _active_state()
    return st.session_state.get(s['current_key'])


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

# Notice a theme switch and rerun once, so the Plotly figures are
# rebuilt with the new palette instead of lagging a frame behind
# the chrome. Must run after initialize_session_state(), which
# creates the key this compares against.
sync_theme()

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
        data_dir = st.session_state.get('refl_data_dir_path', '')
        refl_assets_dir = st.session_state.get('refl_assets_dir_path', '')
        cfg.mode = 'reflection'
        if refl_assets_dir:
            cfg.paths.assets_dir = Path(refl_assets_dir)
        cfg.reflection_cal.angle_of_incidence_deg = float(
            st.session_state.get('refl_aoi_deg', 70.0)
        )
    else:
        data_dir = st.session_state.get('data_dir_path', '')
    if data_dir:
        cfg.paths.data_dir = Path(data_dir)
        if mode == 'Reflection':
            cfg.paths.calibration_reflection_dir = Path(data_dir)

    wl_min = st.session_state.get('wl_min', 400)
    wl_max = st.session_state.get('wl_max', 1000)
    cfg.wavelength.range_nm = (float(wl_min), float(wl_max))
    cfg.wavelength.reference_nm = 633.0

    # Leave cfg.acquisition.n_angular_positions = None — backend auto-detects.
    return cfg


def discover_samples():
    """Discover sample files in the data directory for the current mode."""
    state = _active_state()
    data_dir = state['data_dir']
    if not data_dir:
        st.error("Data directory not set. Go to **Configuration** page and set the data directory first.")
        return

    cfg = build_config_from_session()

    try:
        with st.spinner("Discovering sample files..."):
            samples = discover_sample_files(Path(data_dir), cfg)

        st.session_state[state['discovered_key']] = samples
        st.session_state[state['selected_key']] = []  # Reset selection

        if samples.n_samples > 0:
            st.success(f"Found {samples.n_samples} sample(s)")
        else:
            st.warning("No sample .bin files found in directory. Check that your sample measurements are in .bin format.")

    except FileNotFoundError as e:
        st.error("Directory not found. Check that the sample directory path exists and is accessible.")
    except Exception as e:
        st.error(f"Error discovering samples: {e}")


def process_selected_samples():
    """Process all selected samples. Computes ellipsometric params for Reflection mode."""
    state = _active_state()
    selected = st.session_state.get(state['selected_key'], [])
    if not selected:
        st.error("No samples selected. Select at least one sample from the list above.")
        return

    samples = st.session_state.get(state['discovered_key'])
    if samples is None:
        st.error("No samples discovered. Click 'Discover Samples' first to find sample files.")
        return

    cal_result = state['cal_result']
    if cal_result is None:
        st.error("Calibration not available. Run calibration or load a saved calibration on the Calibration page first.")
        return

    cal_diag = state['cal_diag']
    cfg = build_config_from_session()

    A = cal_result.A
    W = cal_result.W
    inv_W_mod = cal_result.inv_W_mod

    progress_bar = st.progress(0, text="Processing...")

    processed_count = 0
    errors = []

    for i, sample_name in enumerate(selected):
        try:
            sample_idx = samples.names.index(sample_name)
            sample_path = samples.paths[sample_idx]
        except (ValueError, IndexError):
            errors.append(f"{sample_name}: not found in discovered samples")
            continue

        try:
            sample_data, _ = load_spectral_data(sample_path, cfg)

            if hasattr(cal_result, 'wl_indices') and cal_result.wl_indices is not None:
                sample_data = sample_data[:, cal_result.wl_indices]

            if cal_diag is not None and hasattr(cal_diag, 'I_dark') and cal_diag.I_dark is not None:
                sample_data = sample_data - cal_diag.I_dark
                sample_data = np.maximum(sample_data, 0.0)

            result = process_sample(
                sample_data,
                A=A,
                W=W,
                inv_W_mod=inv_W_mod,
                dark=None,
                cfg=cfg
            )

            if state['is_reflection']:
                ellips = extract_ellipsometric_parameters(
                    result.M_normalized,
                    aoi_deg=state['aoi_deg'],
                )
                add_reflection_processed_sample(sample_name, result, ellips)
            else:
                add_processed_sample(sample_name, result)
            processed_count += 1

        except Exception as e:
            errors.append(f"{sample_name}: {e}")

        progress = (i + 1) / len(selected)
        progress_bar.progress(progress, text=f"Processing {i+1}/{len(selected)}...")

    st.session_state['_processing_done'] = True
    st.session_state['_processing_count'] = processed_count
    st.session_state['_processing_total'] = len(selected)
    st.session_state['_processing_errors'] = errors

    # Set current sample
    if processed_count > 0:
        current = _active_get_current()
        active_samples = _active_processed()
        if current is None or current not in active_samples:
            _active_set_current(selected[0])

    st.rerun()


def display_sample_checkboxes():
    """Display checkboxes for sample selection."""
    state = _active_state()
    samples = st.session_state.get(state['discovered_key'])
    if samples is None or samples.n_samples == 0:
        return

    st.markdown("**Available Samples:**")

    # Select All / Deselect All buttons FIRST (before checkboxes are instantiated)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", use_container_width=True):
            st.session_state[state['selected_key']] = list(samples.names)
            for name in samples.names:
                st.session_state[f"sample_cb_{name}"] = True
            st.rerun()
    with col2:
        if st.button("Deselect All", use_container_width=True):
            st.session_state[state['selected_key']] = []
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

    st.session_state[state['selected_key']] = new_selection


def display_results():
    """Display processed sample results with Mueller matrix plots."""
    state = _active_state()
    processed = state['processed_samples']
    if not processed:
        st.info("No processed samples yet. Process samples to see results.")
        return

    sample_names = list(processed.keys())
    current = _active_get_current()

    if current not in sample_names:
        current = sample_names[0]
        _active_set_current(current)

    cal_result = state['cal_result']

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

            # Ellipsometric comparison plots for reflection mode
            if state['is_reflection']:
                ellips_dict = {
                    name: state['ellips_results'][name]
                    for name in selected_for_compare
                    if name in state['ellips_results']
                }
                if len(ellips_dict) >= 2:
                    _render_ellipsometry_comparison(wavelengths, ellips_dict)

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
            _active_set_current(selected_sample)

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

        # Ellipsometric parameter block for reflection samples
        if state['is_reflection']:
            ellips = state['ellips_results'].get(selected_sample)
            if ellips is not None:
                _render_ellipsometry_single(wavelengths, ellips, selected_sample)


def _render_ellipsometry_single(wavelengths, ellips, sample_name):
    """Render the 4-tab ellipsometric parameter block for one sample."""
    with st.expander(f"Ellipsometric Parameters — {sample_name}", expanded=True):
        tab_pd, tab_ncs, tab_eps, tab_nk = st.tabs([
            "Psi & Delta", "N, C, S", "Pseudo-ε", "Pseudo n & k"
        ])
        with tab_pd:
            fig = create_ellipsometry_plot(wavelengths, ellips, parameter='psi_delta')
            st.plotly_chart(fig, use_container_width=True)
        with tab_ncs:
            fig = create_ellipsometry_plot(wavelengths, ellips, parameter='ncs')
            st.plotly_chart(fig, use_container_width=True)
        with tab_eps:
            fig = create_ellipsometry_plot(wavelengths, ellips, parameter='pseudo_epsilon')
            st.plotly_chart(fig, use_container_width=True)
        with tab_nk:
            fig = create_ellipsometry_plot(wavelengths, ellips, parameter='pseudo_nk')
            st.plotly_chart(fig, use_container_width=True)


def _render_ellipsometry_comparison(wavelengths, ellips_dict):
    """Render the 4-tab multi-sample ellipsometry comparison block."""
    with st.expander("Compare Ellipsometric Parameters", expanded=False):
        tab_pd, tab_ncs, tab_eps, tab_nk = st.tabs([
            "Psi & Delta", "N, C, S", "Pseudo-ε", "Pseudo n & k"
        ])
        with tab_pd:
            fig = create_ellipsometry_comparison_plot(wavelengths, ellips_dict, parameter='psi_delta')
            st.plotly_chart(fig, use_container_width=True)
        with tab_ncs:
            fig = create_ellipsometry_comparison_plot(wavelengths, ellips_dict, parameter='ncs')
            st.plotly_chart(fig, use_container_width=True)
        with tab_eps:
            fig = create_ellipsometry_comparison_plot(wavelengths, ellips_dict, parameter='pseudo_epsilon')
            st.plotly_chart(fig, use_container_width=True)
        with tab_nk:
            fig = create_ellipsometry_comparison_plot(wavelengths, ellips_dict, parameter='pseudo_nk')
            st.plotly_chart(fig, use_container_width=True)


def save_results():
    """Save processed samples (and ellipsometry for reflection mode) to .npz file."""
    state = _active_state()
    processed = state['processed_samples']
    if not processed:
        st.error("No processed samples to save. Process samples first before exporting.")
        return

    output_dir = get_output_dir()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    cal_result = state['cal_result']
    wavelengths = cal_result.wavelengths if cal_result else None

    save_data = {
        'wavelengths': wavelengths,
        'sample_names': list(processed.keys()),
        'mode': state['mode'],
    }

    for name, result in processed.items():
        save_data[f'{name}_M'] = result.M
        save_data[f'{name}_M_normalized'] = result.M_normalized
        save_data[f'{name}_m00'] = result.m00

    if state['is_reflection']:
        for name, ellips in state['ellips_results'].items():
            save_data[f'{name}_psi_deg'] = ellips.psi_deg
            save_data[f'{name}_delta_deg'] = ellips.delta_deg
            save_data[f'{name}_N'] = ellips.N
            save_data[f'{name}_C'] = ellips.C
            save_data[f'{name}_S'] = ellips.S
            save_data[f'{name}_pseudo_n'] = ellips.pseudo_n
            save_data[f'{name}_pseudo_k'] = ellips.pseudo_k
            save_data[f'{name}_pseudo_eps_real'] = ellips.pseudo_epsilon.real
            save_data[f'{name}_pseudo_eps_imag'] = ellips.pseudo_epsilon.imag

    suffix = 'reflection' if state['is_reflection'] else 'transmission'
    filepath = output_path / f'processed_samples_{suffix}.npz'
    np.savez(filepath, **save_data)

    st.success(f"Saved to: `{filepath}`")


def export_csv():
    """Export Mueller matrix (and ellipsometry for reflection) data to CSV."""
    state = _active_state()
    processed = state['processed_samples']
    if not processed:
        st.error("No processed samples available for export. Process samples first.")
        return

    sample_names = list(processed.keys())
    m00_label = "M00 Reflection" if state['is_reflection'] else "M00 Transmission"

    with st.expander("CSV Export Options", expanded=True):
        st.markdown("**Select samples to export:**")

        selected_samples = []
        cols = st.columns(min(3, len(sample_names)))
        for idx, name in enumerate(sample_names):
            with cols[idx % len(cols)]:
                if st.checkbox(name, value=True, key=f"csv_export_{name}"):
                    selected_samples.append(name)

        st.markdown("**Select data to include:**")
        if state['is_reflection']:
            col1, col2, col3 = st.columns(3)
        else:
            col1, col2 = st.columns(2)
        with col1:
            include_normalized = st.checkbox("Normalized Mueller Matrix (m11-m44)", value=True, key="csv_inc_norm")
        with col2:
            include_m00 = st.checkbox(m00_label, value=True, key="csv_inc_m00")
        if state['is_reflection']:
            with col3:
                include_ellips = st.checkbox("Ellipsometric Parameters", value=True, key="csv_inc_ellips")
        else:
            include_ellips = False

        if st.button("Export Selected", type="primary", disabled=len(selected_samples) == 0, key="csv_export_btn"):
            _do_csv_export(selected_samples, include_normalized, include_m00, include_ellips)


def _do_csv_export(selected_samples, include_normalized, include_m00, include_ellips=False):
    """Actually perform the CSV export."""
    state = _active_state()
    processed = state['processed_samples']
    cal_result = state['cal_result']
    ellips_results = state['ellips_results']

    output_dir = get_output_dir()
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
            data['m00'] = result.m00

        if include_ellips and name in ellips_results:
            e = ellips_results[name]
            data['psi_deg'] = e.psi_deg
            data['delta_deg'] = e.delta_deg
            data['N'] = e.N
            data['C'] = e.C
            data['S'] = e.S
            data['pseudo_n'] = e.pseudo_n
            data['pseudo_k'] = e.pseudo_k
            data['pseudo_eps_real'] = e.pseudo_epsilon.real
            data['pseudo_eps_imag'] = e.pseudo_epsilon.imag

        df = pd.DataFrame(data)
        filepath = output_path / f'{name}_mueller_matrix.csv'
        df.to_csv(filepath, index=False)

    st.success(f"Exported {len(selected_samples)} sample(s) to: `{output_path}`")


# ============================================================================
# MAIN PAGE CONTENT
# ============================================================================

def main():
    st.title("Sample Processing")

    state = _active_state()

    # -------------------------------------------------
    # Calibration Status Check
    # -------------------------------------------------
    if not state['calibrated']:
        mode_label = "reflection" if state['is_reflection'] else "transmission"
        st.warning(
            f"Not calibrated in {mode_label} mode. "
            "Please run calibration or load a saved calibration first."
        )
        st.stop()

    st.success(f"Calibrated ({state['mode']}) — Ready to process samples")

    soft_divider()

    # -------------------------------------------------
    # Sample Selection Section
    # -------------------------------------------------
    has_processed = len(state['processed_samples']) > 0

    with st.expander("Sample Selection", expanded=not has_processed):
        st.markdown("Discover and select samples from your data directory.")

        discover_disabled = not state['data_dir']

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
        selected = st.session_state.get(state['selected_key'], [])
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

        # Re-read state (it picked up new processed samples)
        state = _active_state()
        has_processed = len(state['processed_samples']) > 0

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
