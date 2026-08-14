"""
Parameters Extraction Page - Decompositions and other methods.

This page handles:
- Sample selection for decomposition
- Running Lu-Chipman, Cloude, and Differential decomposition; Purity Space analysis
- Parameter visualization
- Export functionality

Note: ECM code uses 'psi' internally, but GUI displays it as 'ν' (nu).

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
from components.mueller_selector import mueller_element_selector
from components.plots_plotly import (
    create_mueller_matrix_plot,
    create_mueller_comparison_plot,
    create_selected_elements_plot,
    create_diattenuation_plot,
    create_diattenuation_comparison_plot,
    create_di_plot,
    create_di_comparison_plot,
    create_retardance_plot,
    create_retardance_comparison_plot,
    create_fast_axis_plot,
    create_fast_axis_comparison_plot,
    create_eigenvalue_spectrum_plot,
    create_eigenvalue_spectrum_comparison_plot,
    create_coherency_matrix_plot,
    create_purity_indices_plot,
    create_purity_indices_comparison_plot,
    create_purity_space_scatter,
    create_purity_space_comparison_scatter,
)
from utils.session_state import (
    initialize_session_state,
    is_calibrated,
    is_reflection_calibrated,
    has_any_calibration,
    get_active_processed_samples,
    get_lu_chipman_results,
    add_lu_chipman_result,
    get_calibration_result,
    get_reflection_calibration_result,
    get_output_dir,
)
from utils.theme import sync_theme
from utils.styling import inject_custom_css, soft_divider

# ECM imports
from ecm.postprocessing import (
    lu_chipman_decomposition,
    differential_decomposition,
    cloude_decomposition,
    purity_analysis,
)


# ----------------------------------------------------------------------------
# Mode-aware helpers used throughout this page
# ----------------------------------------------------------------------------

def _active_cal_result():
    """Return the calibration result matching the active mode."""
    mode = st.session_state.get('calibration_mode', 'Transmission')
    if mode == 'Reflection':
        return get_reflection_calibration_result()
    return get_calibration_result()


def _active_wavelengths(fallback_len: int = 0):
    """Return the wavelength array from the active calibration, or arange(n)."""
    cal = _active_cal_result()
    if cal is not None and getattr(cal, 'wavelengths', None) is not None:
        return cal.wavelengths
    return np.arange(fallback_len) if fallback_len else None


# ----------------------------------------------------------------------------
# Reusable matrix-roller helper — unifies the Lu-Chipman "Decomposed Matrices"
# layout (View mode radio + sample selector + matrix tabs) for all four
# decompositions on this page.
# ----------------------------------------------------------------------------

def _render_matrix_roller(
    results: dict,
    wavelengths,
    tabs_spec: list,
    state_prefix: str,
) -> None:
    """Render a "View mode + sample selector + matrix tabs" block.

    Parameters
    ----------
    results : dict[str, Any]
        Mapping ``sample_name -> decomposition result object``.
    wavelengths : ndarray
    tabs_spec : list of tuples ``(tab_label, getter_fn)``
        ``getter_fn(result_obj)`` returns the 4×4×n_wl Mueller matrix for
        that tab. ``tab_label`` is the human-readable label (markdown
        allowed inside ``st.tabs`` strings, but Streamlit doesn't render
        markdown there, so use plain text).
    state_prefix : str
        Unique prefix for all widget/session-state keys so this roller's
        view-mode + checkboxes don't collide with other decompositions'.

    Notes
    -----
    The pattern is identical to the original Lu-Chipman
    ``display_decomposed_matrices``: a horizontal radio for "View mode"
    at the top (4x4 Grid / Selected Elements / Compare Samples, with
    Compare only offered when there are ≥2 samples), then a single
    sample-selector or compare-checkbox row (shared across tabs), and
    finally one tab per matrix.
    """
    if not results:
        st.info("Run decomposition to see results.")
        return

    sample_names = list(results.keys())

    # View mode toggle
    view_options = ["4x4 Grid", "Selected Elements"]
    if len(results) > 1:
        view_options.append("Compare Samples")

    view_mode = st.radio(
        "View Mode",
        view_options,
        horizontal=True,
        key=f"{state_prefix}_view_mode",
    )

    # Sample selection (shared across all tabs)
    selected_for_compare: list = []
    selected_sample: str = sample_names[0]

    if view_mode == "Compare Samples":
        st.markdown("**Select samples to compare:**")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Select All", key=f"{state_prefix}_cmp_all", use_container_width=True):
                for name in sample_names:
                    st.session_state[f"{state_prefix}_cmp_cb_{name}"] = True
                st.rerun()
        with c2:
            if st.button("Clear All", key=f"{state_prefix}_cmp_clear", use_container_width=True):
                for name in sample_names:
                    st.session_state[f"{state_prefix}_cmp_cb_{name}"] = False
                st.rerun()

        cols = st.columns(min(3, len(sample_names)))
        for idx, name in enumerate(sample_names):
            with cols[idx % len(cols)]:
                if st.checkbox(name, key=f"{state_prefix}_cmp_cb_{name}"):
                    selected_for_compare.append(name)
    else:
        # Single-sample modes use a dropdown that survives across tabs.
        current = st.session_state.get(f"{state_prefix}_current_sample")
        if current not in sample_names:
            current = sample_names[0]
            st.session_state[f"{state_prefix}_current_sample"] = current

        selected_sample = st.selectbox(
            "Select Sample",
            sample_names,
            index=sample_names.index(current) if current in sample_names else 0,
            key=f"{state_prefix}_sample_selector",
        )
        if selected_sample != current:
            st.session_state[f"{state_prefix}_current_sample"] = selected_sample

    # Matrix tabs
    tab_labels = [label for label, _ in tabs_spec]
    matrix_tabs = st.tabs(tab_labels)

    for tab_idx, (tab, (label, getter)) in enumerate(zip(matrix_tabs, tabs_spec)):
        with tab:
            if view_mode == "Compare Samples":
                if len(selected_for_compare) >= 2:
                    samples_dict = {
                        name: (getter(results[name]), None)
                        for name in selected_for_compare
                    }
                    fig = create_mueller_comparison_plot(
                        samples_dict,
                        wavelengths,
                        title=f"{label} Comparison",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                elif len(selected_for_compare) == 1:
                    st.info("Select at least 2 samples to compare")
                else:
                    st.info("Select samples above to compare")
            else:
                M = getter(results[selected_sample])

                if view_mode == "4x4 Grid":
                    fig = create_mueller_matrix_plot(
                        M,
                        wavelengths,
                        title=f"{label} — {selected_sample}",
                        m00=None,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    # Selected Elements view — local selector per tab so
                    # users can compare different elements per matrix.
                    st.markdown("**Select Mueller Matrix Elements:**")
                    selected_elements = mueller_element_selector(
                        key=f"{state_prefix}_sel_{tab_idx}",
                        default_selection=[],
                    )
                    if selected_elements:
                        fig = create_selected_elements_plot(
                            M,
                            wavelengths,
                            selected_elements,
                            title=f"{label} elements — {selected_sample}",
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Select elements from the grid above to display")


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="MMForge - PARAMETERS",
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

# Initialize page-specific session state
if 'decomp_selected_samples' not in st.session_state:
    st.session_state['decomp_selected_samples'] = []
if 'decomp_current_sample' not in st.session_state:
    st.session_state['decomp_current_sample'] = None
if 'decomp_view_mode' not in st.session_state:
    st.session_state['decomp_view_mode'] = '4x4 Grid'
if 'decomp_selected_elements' not in st.session_state:
    st.session_state['decomp_selected_elements'] = []


# ============================================================================
# SIDEBAR
# ============================================================================

render_sidebar()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def run_decomposition(selected_samples: list):
    """Run Lu-Chipman decomposition on selected samples."""
    processed = get_active_processed_samples()

    # Progress bar - centered
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        progress_container = st.empty()
        progress_bar = progress_container.progress(0, text="0%")

    errors = []
    decomposed_count = 0

    for i, name in enumerate(selected_samples):
        try:
            result = processed[name]
            M_norm = result.M_normalized  # shape (4, 4, n_wl)

            # Run decomposition
            lc_result = lu_chipman_decomposition(M_norm)

            # Store in session state
            add_lu_chipman_result(name, lc_result)
            decomposed_count += 1

        except Exception as e:
            errors.append(f"{name}: {e}")

        # Update progress
        progress = (i + 1) / len(selected_samples)
        progress_bar.progress(progress, text=f"{int(progress * 100)}%")

    # Clear progress
    progress_container.empty()

    # Store results for display after rerun
    st.session_state['_decomp_done'] = True
    st.session_state['_decomp_count'] = decomposed_count
    st.session_state['_decomp_total'] = len(selected_samples)
    st.session_state['_decomp_errors'] = errors

    st.rerun()


def display_sample_checkboxes():
    """Display checkboxes for sample selection."""
    processed = get_active_processed_samples()
    sample_names = list(processed.keys())

    if not sample_names:
        return

    st.markdown("**Select samples for decomposition:**")

    # Select All / Clear All buttons FIRST
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All", key="decomp_select_all", use_container_width=True):
            st.session_state['decomp_selected_samples'] = list(sample_names)
            for name in sample_names:
                st.session_state[f"decomp_cb_{name}"] = True
            st.rerun()
    with col2:
        if st.button("Clear All", key="decomp_clear_all", use_container_width=True):
            st.session_state['decomp_selected_samples'] = []
            for name in sample_names:
                st.session_state[f"decomp_cb_{name}"] = False
            st.rerun()

    # Display checkboxes in 2 columns
    n_samples = len(sample_names)
    mid = (n_samples + 1) // 2

    col1, col2 = st.columns(2)

    new_selection = []

    for i, name in enumerate(sample_names):
        col = col1 if i < mid else col2
        with col:
            checked = st.checkbox(
                name,
                key=f"decomp_cb_{name}"
            )
            if checked:
                new_selection.append(name)

    st.session_state['decomp_selected_samples'] = new_selection


def display_decomposed_matrices():
    """Display decomposed Mueller matrices (M_D, M_R, M_Delta)."""
    lc_results = get_lu_chipman_results()
    if not lc_results:
        st.info("Run decomposition to see results.")
        return

    sample_names = list(lc_results.keys())
    cal_result = _active_cal_result()

    # Get wavelengths
    if cal_result:
        wavelengths = cal_result.wavelengths
    else:
        # Fallback
        first_result = lc_results[sample_names[0]]
        wavelengths = np.arange(first_result.M_D.shape[2])

    # View mode toggle - add Compare option if multiple samples
    view_options = ["4x4 Grid", "Selected Elements"]
    if len(lc_results) > 1:
        view_options.append("Compare Samples")

    view_mode = st.radio(
        "View Mode",
        view_options,
        horizontal=True,
        key="decomp_matrix_view_mode"
    )

    # --- SAMPLE SELECTION (OUTSIDE tabs, shared across all) ---
    if view_mode == "Compare Samples":
        # Multi-sample comparison mode - checkboxes
        st.markdown("**Select samples to compare:**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Select All", key="decomp_matrix_compare_select_all", use_container_width=True):
                for name in sample_names:
                    st.session_state[f"decomp_matrix_compare_cb_{name}"] = True
                st.rerun()
        with col2:
            if st.button("Clear All", key="decomp_matrix_compare_clear_all", use_container_width=True):
                for name in sample_names:
                    st.session_state[f"decomp_matrix_compare_cb_{name}"] = False
                st.rerun()

        selected_for_compare = []
        cols = st.columns(min(3, len(sample_names)))
        for idx, name in enumerate(sample_names):
            with cols[idx % len(cols)]:
                if st.checkbox(name, key=f"decomp_matrix_compare_cb_{name}"):
                    selected_for_compare.append(name)

    else:
        # Single sample view modes - dropdown (shared key for all tabs)
        current = st.session_state.get('decomp_current_sample')
        if current not in sample_names:
            current = sample_names[0]
            st.session_state['decomp_current_sample'] = current

        selected_sample = st.selectbox(
            "Select Sample",
            sample_names,
            index=sample_names.index(current) if current in sample_names else 0,
            key="decomp_matrix_sample_selector"
        )

        if selected_sample != current:
            st.session_state['decomp_current_sample'] = selected_sample

    # --- MATRIX TABS (only plots, no sample selection inside) ---
    matrix_tabs = st.tabs(["MM of Diattenuator", "MM of Depolarizer", "MM of Retarder"])

    matrix_keys = ['M_D', 'M_Delta', 'M_R']
    matrix_names = ['M<sub>D</sub>', 'M<sub>Δ</sub>', 'M<sub>R</sub>']

    for tab_idx, tab in enumerate(matrix_tabs):
        with tab:
            matrix_key = matrix_keys[tab_idx]
            matrix_name = matrix_names[tab_idx]

            if view_mode == "Compare Samples":
                if len(selected_for_compare) >= 2:
                    # Build samples dictionary for comparison plot
                    samples_dict = {}
                    for name in selected_for_compare:
                        result = lc_results[name]
                        M = getattr(result, matrix_key)
                        samples_dict[name] = (M, None)

                    fig = create_mueller_comparison_plot(
                        samples_dict,
                        wavelengths,
                        title=f"{matrix_name} Comparison"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                elif len(selected_for_compare) == 1:
                    st.info("Select at least 2 samples to compare")
                else:
                    st.info("Select samples above to compare")

            else:
                # Single sample view modes - use the shared selected_sample
                result = lc_results[selected_sample]
                M = getattr(result, matrix_key)

                if view_mode == "4x4 Grid":
                    fig = create_mueller_matrix_plot(
                        M,
                        wavelengths,
                        title=f"{matrix_name} - {selected_sample}",
                        m00=None
                    )
                    st.plotly_chart(fig, use_container_width=True)

                else:
                    # Selected elements view
                    st.markdown("**Select Mueller Matrix Elements:**")

                    selected_elements = mueller_element_selector(
                        key=f"decomp_element_selector_{matrix_key}",
                        default_selection=st.session_state.get('decomp_selected_elements', [])
                    )

                    if selected_elements != st.session_state.get('decomp_selected_elements', []):
                        st.session_state['decomp_selected_elements'] = selected_elements

                    if selected_elements:
                        fig = create_selected_elements_plot(
                            M,
                            wavelengths,
                            selected_elements,
                            title=f"{matrix_name} Selected Elements - {selected_sample}"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Select elements from the grid above to display")


def display_parameter_plots():
    """Display decomposition parameter plots (D, DI, R, ν/χ)."""
    lc_results = get_lu_chipman_results()
    if not lc_results:
        return

    sample_names = list(lc_results.keys())
    cal_result = _active_cal_result()

    # Get wavelengths
    if cal_result:
        wavelengths = cal_result.wavelengths
    else:
        first_result = lc_results[sample_names[0]]
        wavelengths = np.arange(len(first_result.D))

    # --- UNIFIED SAMPLE SELECTION (above tabs) ---
    show_comparison = len(lc_results) > 1
    selected = sample_names  # Default: all selected

    if show_comparison:
        st.markdown("**Select samples to display:**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Select All", key="param_select_all", use_container_width=True):
                for name in sample_names:
                    st.session_state[f"param_cb_{name}"] = True
                st.rerun()
        with col2:
            if st.button("Clear All", key="param_clear_all", use_container_width=True):
                for name in sample_names:
                    st.session_state[f"param_cb_{name}"] = False
                st.rerun()

        selected = []
        cols = st.columns(min(3, len(sample_names)))
        for idx, name in enumerate(sample_names):
            with cols[idx % len(cols)]:
                if st.checkbox(name, key=f"param_cb_{name}", value=True):
                    selected.append(name)

        soft_divider()

    # Parameter tabs (now use unified `selected` list)
    param_tabs = st.tabs(["Diattenuation (D)", "Depolarization Index (DI)", "Retardance (R)", "Eigenmodes"])

    with param_tabs[0]:  # Diattenuation
        if show_comparison and selected:
            samples_dict = {name: lc_results[name].D for name in selected}
            fig = create_diattenuation_comparison_plot(samples_dict, wavelengths)
            st.plotly_chart(fig, use_container_width=True)

        elif not show_comparison:
            name = sample_names[0]
            fig = create_diattenuation_plot(lc_results[name].D, wavelengths, sample_name=name)
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Select at least one sample above to display")

    with param_tabs[1]:  # DI
        if show_comparison and selected:
            samples_dict = {name: lc_results[name].DI for name in selected}
            fig = create_di_comparison_plot(samples_dict, wavelengths)
            st.plotly_chart(fig, use_container_width=True)

        elif not show_comparison:
            name = sample_names[0]
            fig = create_di_plot(lc_results[name].DI, wavelengths, sample_name=name)
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Select at least one sample above to display")

    with param_tabs[2]:  # Retardance
        # Unit selector
        unit = st.radio(
            "Y-axis unit",
            ["degrees", "radians", "waves"],
            horizontal=True,
            key="retardance_unit"
        )

        if show_comparison and selected:
            samples_dict = {name: lc_results[name] for name in selected}
            fig = create_retardance_comparison_plot(samples_dict, wavelengths, unit=unit)
            st.plotly_chart(fig, use_container_width=True)

        elif not show_comparison:
            name = sample_names[0]
            result = lc_results[name]
            fig = create_retardance_plot(
                result.R_deg, wavelengths,
                R_rad=result.R_rad,
                R_waves=result.R_waves,
                unit=unit,
                sample_name=name
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Select at least one sample above to display")

    with param_tabs[3]:  # Eigenmodes
        # Unit selector (degrees or radians only - no waves for angles)
        axis_unit = st.radio(
            "Y-axis unit",
            ["degrees", "radians"],
            horizontal=True,
            key="fast_axis_unit"
        )

        if show_comparison and selected:
            samples_dict = {name: lc_results[name] for name in selected}
            fig = create_fast_axis_comparison_plot(samples_dict, wavelengths, unit=axis_unit)
            st.plotly_chart(fig, use_container_width=True)

        elif not show_comparison:
            name = sample_names[0]
            result = lc_results[name]
            fig = create_fast_axis_plot(
                result.psi_deg, result.chi_deg, wavelengths,
                unit=axis_unit, sample_name=name
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Select at least one sample above to display")


def save_decomposition():
    """Save decomposition results to .npz file."""
    lc_results = get_lu_chipman_results()
    if not lc_results:
        st.error("No decomposition results to save")
        return

    cal_result = _active_cal_result()
    wavelengths = cal_result.wavelengths if cal_result else None

    output_dir = get_output_dir()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Build save data
    save_data = {
        'wavelengths': wavelengths,
        'sample_names': list(lc_results.keys()),
    }

    for name, result in lc_results.items():
        save_data[f'{name}_M_D'] = result.M_D
        save_data[f'{name}_M_R'] = result.M_R
        save_data[f'{name}_M_Delta'] = result.M_Delta
        save_data[f'{name}_D'] = result.D
        save_data[f'{name}_R_deg'] = result.R_deg
        save_data[f'{name}_R_rad'] = result.R_rad
        save_data[f'{name}_R_waves'] = result.R_waves
        save_data[f'{name}_DI'] = result.DI
        save_data[f'{name}_psi_deg'] = result.psi_deg  # ECM uses psi
        save_data[f'{name}_chi_deg'] = result.chi_deg

    filepath = output_path / 'lu_chipman_decomposition.npz'
    np.savez(filepath, **save_data)

    st.success(f"Saved to: `{filepath}`")


def export_decomposition_csv():
    """Export decomposition results to CSV with selection dialog."""
    lc_results = get_lu_chipman_results()
    if not lc_results:
        st.error("No decomposition results")
        return

    sample_names = list(lc_results.keys())

    with st.expander("CSV Export Options", expanded=True):
        st.markdown("**Select samples to export:**")

        selected_samples = []
        cols = st.columns(min(3, len(sample_names)))
        for idx, name in enumerate(sample_names):
            with cols[idx % len(cols)]:
                if st.checkbox(name, value=True, key=f"decomp_csv_{name}"):
                    selected_samples.append(name)

        st.markdown("**Select parameters to include:**")
        col1, col2 = st.columns(2)
        with col1:
            inc_D = st.checkbox("Diattenuation (D)", value=True, key="csv_D")
            inc_DI = st.checkbox("Depolarization Index (DI)", value=True, key="csv_DI")
            inc_R = st.checkbox("Retardance (R)", value=True, key="csv_R")
        with col2:
            inc_nu = st.checkbox("Fast Axis (ν)", value=True, key="csv_nu")
            inc_chi = st.checkbox("Ellipticity (χ)", value=True, key="csv_chi")

        st.markdown("**Select matrices to include:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            inc_MD = st.checkbox("M_D (Diattenuator)", value=False, key="csv_MD")
        with col2:
            inc_MDelta = st.checkbox("M_Δ (Depolarizer)", value=False, key="csv_MDelta")
        with col3:
            inc_MR = st.checkbox("M_R (Retarder)", value=False, key="csv_MR")

        if st.button("Export Selected", type="primary", disabled=len(selected_samples) == 0, key="decomp_export_btn"):
            _do_decomp_csv_export(selected_samples, inc_D, inc_DI, inc_R, inc_nu, inc_chi, inc_MD, inc_MDelta, inc_MR)


def _do_decomp_csv_export(selected_samples, inc_D, inc_DI, inc_R, inc_nu, inc_chi, inc_MD, inc_MDelta, inc_MR):
    """Actually perform the decomposition CSV export."""
    lc_results = get_lu_chipman_results()
    cal_result = _active_cal_result()

    output_dir = get_output_dir()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    import pandas as pd

    for name in selected_samples:
        result = lc_results[name]
        wavelengths = cal_result.wavelengths if cal_result else np.arange(len(result.D))

        # Parameters CSV
        param_data = {'wavelength_nm': wavelengths}
        if inc_D:
            param_data['diattenuation_D'] = result.D
        if inc_DI:
            param_data['depolarization_index_DI'] = result.DI
        if inc_R:
            param_data['retardance_deg'] = result.R_deg
            param_data['retardance_rad'] = result.R_rad
            param_data['retardance_waves'] = result.R_waves
        if inc_nu:
            param_data['fast_axis_nu_deg'] = result.psi_deg
        if inc_chi:
            param_data['ellipticity_chi_deg'] = result.chi_deg

        if len(param_data) > 1:  # More than just wavelength
            df = pd.DataFrame(param_data)
            filepath = output_path / f'{name}_parameters.csv'
            df.to_csv(filepath, index=False)

        # Matrix CSVs (one file per matrix if selected)
        for matrix_name, inc_flag, matrix_attr in [
            ('M_D', inc_MD, 'M_D'),
            ('M_Delta', inc_MDelta, 'M_Delta'),
            ('M_R', inc_MR, 'M_R'),
        ]:
            if inc_flag:
                M = getattr(result, matrix_attr)
                mat_data = {'wavelength_nm': wavelengths}
                for i in range(4):
                    for j in range(4):
                        mat_data[f'm{i+1}{j+1}'] = M[i, j, :]
                df = pd.DataFrame(mat_data)
                filepath = output_path / f'{name}_{matrix_name}.csv'
                df.to_csv(filepath, index=False)

    st.success(f"Exported {len(selected_samples)} sample(s) to: `{output_path}`")


def display_summary_table():
    """Display parameter summary table with mean ± std or single wavelength values."""
    import pandas as pd

    lc_results = get_lu_chipman_results()
    if not lc_results:
        return

    sample_names = list(lc_results.keys())
    cal_result = _active_cal_result()
    wavelengths = cal_result.wavelengths if cal_result else np.arange(len(lc_results[sample_names[0]].D))

    # Controls row
    col1, col2 = st.columns([1, 2])
    with col1:
        angle_unit = st.selectbox("Angle unit", ["degrees", "radians"], key="summary_angle_unit")
    with col2:
        view_mode = st.radio("View", ["Mean ± Std", "Single wavelength"], horizontal=True, key="summary_view_mode")

    # Wavelength slider (only shown for single wavelength mode)
    wl_idx = len(wavelengths) // 2
    if view_mode == "Single wavelength":
        wl_options = [f"{w:.1f}" for w in wavelengths]
        wl_val = st.select_slider(
            "Wavelength (nm)",
            options=wl_options,
            value=wl_options[len(wavelengths) // 2],
            key="summary_wl_slider"
        )
        wl_idx = wl_options.index(wl_val)

    # Build table
    unit_symbol = "°" if angle_unit == "degrees" else "rad"
    parameters = [
        ('D', 'Diattenuation (D)', lambda r: r.D),
        ('DI', 'Depol. Index (DI)', lambda r: r.DI),
        ('R', f'Retardance ({unit_symbol})',
         lambda r: r.R_deg if angle_unit == "degrees" else r.R_rad),
        ('ν', f'Fast Axis ν ({unit_symbol})',
         lambda r: r.psi_deg if angle_unit == "degrees" else np.deg2rad(r.psi_deg)),
        ('χ', f'Ellipticity χ ({unit_symbol})',
         lambda r: r.chi_deg if angle_unit == "degrees" else np.deg2rad(r.chi_deg)),
    ]

    rows = []
    for key, label, getter in parameters:
        row = {'Parameter': label}
        for name in sample_names:
            data = getter(lc_results[name])
            if view_mode == "Single wavelength":
                row[name] = f"{data[wl_idx]:.4f}"
            else:
                row[name] = f"{np.mean(data):.4f} ± {np.std(data):.4f}"
        rows.append(row)

    df = pd.DataFrame(rows).set_index('Parameter')
    st.dataframe(df, use_container_width=True)


# ============================================================================
# SHARED SAMPLE SELECTION (for new decomposition tabs)
# ============================================================================

def _generic_sample_selection(tab_key: str) -> list:
    """Generic sample-selection block with Select-All / Clear-All buttons.

    Each tab uses a unique `tab_key` so checkbox widget keys don't collide.
    Returns the selected list of sample names. Stores selection under
    session_state[f'{tab_key}_selected'].
    """
    processed = get_active_processed_samples()
    sample_names = list(processed.keys())

    if not sample_names:
        st.info("No processed samples available.")
        return []

    sel_key = f'{tab_key}_selected'
    if sel_key not in st.session_state:
        st.session_state[sel_key] = []

    st.markdown("**Select samples for decomposition:**")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Select All", key=f"{tab_key}_select_all", use_container_width=True):
            st.session_state[sel_key] = list(sample_names)
            for name in sample_names:
                st.session_state[f"{tab_key}_cb_{name}"] = True
            st.rerun()
    with c2:
        if st.button("Clear All", key=f"{tab_key}_clear_all", use_container_width=True):
            st.session_state[sel_key] = []
            for name in sample_names:
                st.session_state[f"{tab_key}_cb_{name}"] = False
            st.rerun()

    n_samples = len(sample_names)
    mid = (n_samples + 1) // 2
    col1, col2 = st.columns(2)

    new_selection = []
    for i, name in enumerate(sample_names):
        col = col1 if i < mid else col2
        with col:
            if st.checkbox(name, key=f"{tab_key}_cb_{name}"):
                new_selection.append(name)

    st.session_state[sel_key] = new_selection
    return new_selection


def _run_button_block(tab_key: str, selected: list) -> bool:
    """Render the centered Run button. Returns True if clicked."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        disabled = len(selected) == 0
        clicked = st.button(
            "Run Decomposition",
            type="primary",
            use_container_width=True,
            disabled=disabled,
            help="Select samples first" if disabled else f"Decompose {len(selected)} sample(s)",
            key=f"{tab_key}_run_btn",
        )
    if not selected:
        st.caption("Select samples above to enable decomposition")
    else:
        st.caption(f"{len(selected)} sample(s) selected")
    return clicked


def _show_run_feedback(tab_key: str) -> None:
    """Read and display transient run-result counters for a given tab."""
    done_flag = f'_{tab_key}_done'
    count_flag = f'_{tab_key}_count'
    total_flag = f'_{tab_key}_total'
    errors_flag = f'_{tab_key}_errors'
    if not st.session_state.get(done_flag):
        return
    count = st.session_state.get(count_flag, 0)
    total = st.session_state.get(total_flag, 0)
    errors = st.session_state.get(errors_flag, [])
    if count > 0:
        st.success(f"Decomposed {count}/{total} samples")
    elif total > 0:
        st.error(f"Failed to decompose all {total} samples")
    if errors:
        with st.expander("Decomposition Errors", expanded=True):
            for err in errors:
                st.error(err)
    del st.session_state[done_flag]
    del st.session_state[count_flag]
    del st.session_state[total_flag]
    del st.session_state[errors_flag]


def _run_generic_decomp(tab_key: str, selected: list, decomp_fn, results_key: str) -> None:
    """Run `decomp_fn` on each selected sample's M_normalized and store under results_key."""
    processed = get_active_processed_samples()
    if results_key not in st.session_state:
        st.session_state[results_key] = {}

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        progress_container = st.empty()
        progress_bar = progress_container.progress(0, text="0%")

    errors = []
    count = 0
    for i, name in enumerate(selected):
        try:
            res = decomp_fn(processed[name].M_normalized)
            st.session_state[results_key][name] = res
            count += 1
        except Exception as e:
            errors.append(f"{name}: {e}")
        progress = (i + 1) / len(selected)
        progress_bar.progress(progress, text=f"{int(progress * 100)}%")

    progress_container.empty()

    st.session_state[f'_{tab_key}_done'] = True
    st.session_state[f'_{tab_key}_count'] = count
    st.session_state[f'_{tab_key}_total'] = len(selected)
    st.session_state[f'_{tab_key}_errors'] = errors
    st.rerun()


# ============================================================================
# DIFFERENTIAL DECOMPOSITION TAB
# ============================================================================

def _render_differential_tab(processed_samples: dict):
    """Differential (Minkowski) decomposition tab.

    Result fields per sample (DifferentialDecompositionResult):
      - L_m, L_u, M_m, M_u — all shape (4, 4, n_wl).
    """
    results = st.session_state.get('differential_results', {})
    has_results = len(results) > 0

    st.markdown(
        "Differential decomposition splits the logarithm of the Mueller matrix into "
        "**L<sub>m</sub>** (mean nondepolarizing properties) and "
        "**L<sub>u</sub>** (depolarization). Their exponentials produce the "
        "**M<sub>m</sub>** and **M<sub>u</sub>** component matrices.",
        unsafe_allow_html=True,
    )

    with st.expander("Sample Selection", expanded=not has_results):
        selected = _generic_sample_selection('diff')

    soft_divider()
    if _run_button_block('diff', selected):
        _run_generic_decomp('diff', selected, differential_decomposition, 'differential_results')
    _show_run_feedback('diff')

    results = st.session_state.get('differential_results', {})
    if not results:
        return

    wavelengths = _active_wavelengths(
        fallback_len=next(iter(results.values())).L_m.shape[2]
    )

    # Unified Decomposed Matrices roller — View mode (4x4 Grid / Selected
    # Elements / Compare Samples) shared across all four matrix tabs.
    with st.expander("Decomposed Matrices", expanded=True):
        _render_matrix_roller(
            results=results,
            wavelengths=wavelengths,
            tabs_spec=[
                ("L_m (polarization)", lambda r: r.L_m),
                ("L_u (depolarization)", lambda r: r.L_u),
                ("M_m (nondepolarizing)", lambda r: r.M_m),
                ("M_u (depolarizing)", lambda r: r.M_u),
            ],
            state_prefix='diff_matrix',
        )

    # Export
    soft_divider()
    st.subheader("Export")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save Differential (.npz)", use_container_width=True, key='diff_save'):
            _save_differential(results, wavelengths)
    with c2:
        if st.button("Export Differential (.csv)", use_container_width=True, key='diff_csv'):
            _export_differential_csv(results, wavelengths)


# ============================================================================
# CLOUDE SPECTRAL DECOMPOSITION TAB
# ============================================================================

def _render_cloude_tab(processed_samples: dict):
    """Cloude spectral decomposition tab.

    Result fields (CloudeDecompositionResult):
      - eigenvalues:  (4, n_wl)
      - M_components: (4, 4, 4, n_wl)  — first axis indexes the 4 components.
      - H:            (4, 4, n_wl), complex coherency matrix.
    """
    results = st.session_state.get('cloude_results', {})
    has_results = len(results) > 0

    st.markdown(
        "Cloude spectral decomposition diagonalizes the coherency matrix **H** "
        "into four Mueller matrices weighted by eigenvalues λ₀ ≥ λ₁ ≥ λ₂ ≥ λ₃."
    )

    with st.expander("Sample Selection", expanded=not has_results):
        selected = _generic_sample_selection('cloude')

    soft_divider()
    if _run_button_block('cloude', selected):
        _run_generic_decomp('cloude', selected, cloude_decomposition, 'cloude_results')
    _show_run_feedback('cloude')

    results = st.session_state.get('cloude_results', {})
    if not results:
        return

    wavelengths = _active_wavelengths(
        fallback_len=next(iter(results.values())).eigenvalues.shape[1]
    )
    sample_names = list(results.keys())

    # ---- Decomposed Matrices roller (mirrors Lu-Chipman) ----
    # View mode + sample selector + 4 component-matrix tabs.
    with st.expander("Decomposed Matrices", expanded=True):
        _render_matrix_roller(
            results=results,
            wavelengths=wavelengths,
            tabs_spec=[
                ("M₀ (dominant)", lambda r: r.M_components[0]),
                ("M₁", lambda r: r.M_components[1]),
                ("M₂", lambda r: r.M_components[2]),
                ("M₃", lambda r: r.M_components[3]),
            ],
            state_prefix='cloude_matrix',
        )

    # ---- Decomposition Parameters roller (mirrors Lu-Chipman) ----
    # Two tabs: eigenvalue spectrum and |H_ij| coherency. Each tab gets
    # its own per-sample / comparison toggle when multiple samples are
    # available.
    with st.expander("Decomposition Parameters", expanded=True):
        show_comparison = len(sample_names) > 1
        view_mode = "Per-sample"
        if show_comparison:
            view_mode = st.radio(
                "View",
                ["Per-sample", "Comparison"],
                horizontal=True,
                key='cloude_param_view_mode',
            )

        param_tabs = st.tabs(["Eigenvalue Spectrum", "Coherency Matrix |H_ij|"])

        with param_tabs[0]:
            if view_mode == "Comparison":
                fig = create_eigenvalue_spectrum_comparison_plot(wavelengths, results)
            else:
                sel = st.selectbox(
                    "Select Sample", sample_names, key='cloude_eig_sample'
                )
                fig = create_eigenvalue_spectrum_plot(
                    wavelengths, results[sel].eigenvalues,
                    title=f"Eigenvalues — {sel}",
                )
            st.plotly_chart(fig, use_container_width=True)

        with param_tabs[1]:
            # |H_ij| is intrinsically per-sample (it's a complex 4×4
            # spectrum with no straightforward overlay). Even in
            # Comparison view mode we offer a sample picker so the user
            # can browse them.
            sel = st.selectbox(
                "Select Sample", sample_names, key='cloude_H_sample'
            )
            fig = create_coherency_matrix_plot(
                wavelengths, results[sel].H,
                title=f"Coherency Matrix |H_ij| — {sel}",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Export
    soft_divider()
    st.subheader("Export")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save Cloude (.npz)", use_container_width=True, key='cloude_save'):
            _save_cloude(results, wavelengths)
    with c2:
        if st.button("Export Cloude (.csv)", use_container_width=True, key='cloude_csv'):
            _export_cloude_csv(results, wavelengths)


# ============================================================================
# PURITY SPACE TAB
# ============================================================================

def _render_purity_tab(processed_samples: dict):
    """Purity space analysis tab.

    Result fields (PurityResult):
      - P_P, P_S, P_Delta: (n_wl,) purity indices.
      - D_vec, P_vec: (3, n_wl) diattenuation and polarizance 3-vectors.
    """
    results = st.session_state.get('purity_results', {})
    has_results = len(results) > 0

    st.markdown(
        "Purity space helps visualize the relationship of the three fundamental polarization properties of a sample and the sources of the depolarization in them.",
        unsafe_allow_html=True,
    )

    with st.expander("Sample Selection", expanded=not has_results):
        selected = _generic_sample_selection('purity')

    soft_divider()
    if _run_button_block('purity', selected):
        _run_generic_decomp('purity', selected, purity_analysis, 'purity_results')
    _show_run_feedback('purity')

    results = st.session_state.get('purity_results', {})
    if not results:
        return

    wavelengths = _active_wavelengths(
        fallback_len=next(iter(results.values())).P_P.shape[0]
    )
    sample_names = list(results.keys())

    # Purity indices vs wavelength
    with st.expander("Purity Indices", expanded=True):
        if len(sample_names) > 1:
            mode = st.radio(
                "View",
                ["Per-sample", "Comparison"],
                horizontal=True,
                key='purity_indices_mode',
            )
        else:
            mode = "Per-sample"

        if mode == "Per-sample":
            sel = st.selectbox("Select Sample", sample_names, key='purity_idx_sample')
            res = results[sel]
            fig = create_purity_indices_plot(
                wavelengths, res.P_P, res.P_S, res.P_Delta,
                sample_name=sel,
            )
        else:
            fig = create_purity_indices_comparison_plot(wavelengths, results)
        st.plotly_chart(fig, use_container_width=True)

    # Purity space scatter (P_S vs P_P) with boundary curves
    with st.expander("Purity Space (P_S vs P_P)", expanded=True):
        if len(sample_names) > 1:
            mode = st.radio(
                "View",
                ["Per-sample", "Comparison"],
                horizontal=True,
                key='purity_space_mode',
            )
        else:
            mode = "Per-sample"

        if mode == "Per-sample":
            sel = st.selectbox("Select Sample", sample_names, key='purity_scatter_sample')
            res = results[sel]
            fig = create_purity_space_scatter(
                res.P_S, res.P_P,
                wavelengths=wavelengths,
                sample_name=sel,
            )
        else:
            fig = create_purity_space_comparison_scatter(results, wavelengths=wavelengths)
        st.plotly_chart(fig, use_container_width=True)

    # Export
    soft_divider()
    st.subheader("Export")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save Purity (.npz)", use_container_width=True, key='purity_save'):
            _save_purity(results, wavelengths)
    with c2:
        if st.button("Export Purity (.csv)", use_container_width=True, key='purity_csv'):
            _export_purity_csv(results, wavelengths)


# ============================================================================
# EXPORTS FOR NEW DECOMPOSITIONS
# ============================================================================

def _output_path() -> Path:
    out = get_output_dir()
    p = Path(out)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _save_differential(results: dict, wavelengths: np.ndarray) -> None:
    out = _output_path()
    save_data = {'wavelengths': wavelengths, 'sample_names': list(results.keys())}
    for name, res in results.items():
        save_data[f'{name}_L_m'] = res.L_m
        save_data[f'{name}_L_u'] = res.L_u
        save_data[f'{name}_M_m'] = res.M_m
        save_data[f'{name}_M_u'] = res.M_u
    filepath = out / 'differential_decomposition.npz'
    np.savez(filepath, **save_data)
    st.success(f"Saved to: `{filepath}`")


def _save_cloude(results: dict, wavelengths: np.ndarray) -> None:
    out = _output_path()
    save_data = {'wavelengths': wavelengths, 'sample_names': list(results.keys())}
    for name, res in results.items():
        save_data[f'{name}_eigenvalues'] = res.eigenvalues
        save_data[f'{name}_M_components'] = res.M_components
        save_data[f'{name}_H_real'] = res.H.real
        save_data[f'{name}_H_imag'] = res.H.imag
    filepath = out / 'cloude_decomposition.npz'
    np.savez(filepath, **save_data)
    st.success(f"Saved to: `{filepath}`")


def _save_purity(results: dict, wavelengths: np.ndarray) -> None:
    out = _output_path()
    save_data = {'wavelengths': wavelengths, 'sample_names': list(results.keys())}
    for name, res in results.items():
        save_data[f'{name}_P_P'] = res.P_P
        save_data[f'{name}_P_S'] = res.P_S
        save_data[f'{name}_P_Delta'] = res.P_Delta
        save_data[f'{name}_D_vec'] = res.D_vec
        save_data[f'{name}_P_vec'] = res.P_vec
    filepath = out / 'purity_analysis.npz'
    np.savez(filepath, **save_data)
    st.success(f"Saved to: `{filepath}`")


def _export_differential_csv(results: dict, wavelengths: np.ndarray) -> None:
    import pandas as pd
    out = _output_path()
    for name, res in results.items():
        data = {'wavelength_nm': wavelengths}
        for k, (label, M) in enumerate((('L_m', res.L_m), ('L_u', res.L_u))):
            for i in range(4):
                for j in range(4):
                    data[f'{label}_{i+1}{j+1}'] = M[i, j, :]
        pd.DataFrame(data).to_csv(out / f'{name}_differential.csv', index=False)
    st.success(f"Exported {len(results)} sample(s) to `{out}`")


def _export_cloude_csv(results: dict, wavelengths: np.ndarray) -> None:
    import pandas as pd
    out = _output_path()
    for name, res in results.items():
        data = {'wavelength_nm': wavelengths}
        for k in range(4):
            data[f'lambda_{k}'] = res.eigenvalues[k, :]
        for k in range(4):
            for i in range(4):
                for j in range(4):
                    data[f'M{k}_{i+1}{j+1}'] = res.M_components[k, i, j, :]
        pd.DataFrame(data).to_csv(out / f'{name}_cloude.csv', index=False)
    st.success(f"Exported {len(results)} sample(s) to `{out}`")


def _export_purity_csv(results: dict, wavelengths: np.ndarray) -> None:
    import pandas as pd
    out = _output_path()
    for name, res in results.items():
        data = {
            'wavelength_nm': wavelengths,
            'P_P': res.P_P,
            'P_S': res.P_S,
            'P_Delta': res.P_Delta,
            'D_1': res.D_vec[0, :],
            'D_2': res.D_vec[1, :],
            'D_3': res.D_vec[2, :],
            'P_1': res.P_vec[0, :],
            'P_2': res.P_vec[1, :],
            'P_3': res.P_vec[2, :],
        }
        pd.DataFrame(data).to_csv(out / f'{name}_purity.csv', index=False)
    st.success(f"Exported {len(results)} sample(s) to `{out}`")


# ============================================================================
# MAIN PAGE CONTENT
# ============================================================================

def main():
    st.title("Parameters Extraction")

    st.markdown("""
    - Perform Lu-Chipman, Cloude, and Differential decomposition of Mueller matrices to analyze the fundamental polarization effects.
    - Visualize decomposed matrices, parameters, and purity space to gain insights into sample properties.
    """)

    st.error(
        "**Notes on decomposition results:**\n"
        "- Decompositions are mathematical tools that can provide insights into the sample's polarization properties, "
        "but they are not unique physical models.\n"
        "- Different decompositions may yield different interpretations of the same Mueller matrix. Some or all decomposition "
        "may be not suitable for a given sample at all!\n"
        "- Always interpret results within your experimental context."
    )

    soft_divider()

    # -------------------------------------------------
    # Prerequisites Check
    # -------------------------------------------------
    if not has_any_calibration():
        st.warning("Not calibrated. Please run a calibration (transmission or reflection) first.")
        st.stop()

    processed_samples = get_active_processed_samples()

    if not processed_samples:
        st.info("No processed samples available for the current mode. Process samples on the Sample Processing page first.")
        st.stop()

    # -------------------------------------------------
    # Top-level decomposition tabs
    # -------------------------------------------------
    tab_lc, tab_diff, tab_cloude, tab_purity = st.tabs([
        "Lu-Chipman", "Differential", "Cloude Spectral", "Purity Space",
    ])

    with tab_lc:
        _render_lu_chipman_tab()

    with tab_diff:
        _render_differential_tab(processed_samples)

    with tab_cloude:
        _render_cloude_tab(processed_samples)

    with tab_purity:
        _render_purity_tab(processed_samples)


# ============================================================================
# LU-CHIPMAN TAB (wraps existing helpers verbatim)
# ============================================================================

def _render_lu_chipman_tab():
    """Render the Lu-Chipman decomposition tab.

    Sequencing is identical to the pre-Part-4 page: sample selection →
    Run Decomposition → Decomposed Matrices → Decomposition Parameters →
    Summary Table → Export. Each section uses its existing helper.
    """
    lc_results = get_lu_chipman_results()
    has_results = len(lc_results) > 0

    st.markdown(
        "Lu-Chipman decomposition analyzes the polarization properties of a sample by breaking down its Mueller matrix into fundamental components.",
        unsafe_allow_html=True,
    )

    with st.expander("Sample Selection", expanded=not has_results):
        display_sample_checkboxes()

    soft_divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        selected = st.session_state.get('decomp_selected_samples', [])
        run_disabled = len(selected) == 0
        if st.button(
            "Run Decomposition",
            type="primary",
            use_container_width=True,
            disabled=run_disabled,
            help="Select samples first" if run_disabled else f"Decompose {len(selected)} sample(s)",
            key="lc_run_btn",
        ):
            run_decomposition(selected)

    if run_disabled:
        st.caption("Select samples above to enable decomposition")
    else:
        st.caption(f"{len(selected)} sample(s) selected")

    # Show transient decomposition feedback
    if st.session_state.get('_decomp_done'):
        count = st.session_state.get('_decomp_count', 0)
        total = st.session_state.get('_decomp_total', 0)
        errors = st.session_state.get('_decomp_errors', [])
        if count > 0:
            st.success(f"Decomposed {count}/{total} samples")
        elif total > 0:
            st.error(f"Failed to decompose all {total} samples")
        if errors:
            with st.expander("Decomposition Errors", expanded=True):
                for err in errors:
                    st.error(err)
        del st.session_state['_decomp_done']
        del st.session_state['_decomp_count']
        del st.session_state['_decomp_total']
        del st.session_state['_decomp_errors']

    if has_results:
        with st.expander("Decomposed Matrices", expanded=True):
            display_decomposed_matrices()
        with st.expander("Decomposition Parameters", expanded=True):
            display_parameter_plots()
        with st.expander("Summary Table", expanded=True):
            display_summary_table()

    soft_divider()
    st.subheader("Export")
    col1, col2 = st.columns(2)
    export_disabled = not has_results
    with col1:
        if st.button(
            "Save Decomposition (.npz)",
            use_container_width=True,
            disabled=export_disabled,
            key="lc_save_btn",
        ):
            save_decomposition()
    with col2:
        if st.button(
            "Export Data (.csv)",
            use_container_width=True,
            disabled=export_disabled,
            key="lc_csv_btn",
        ):
            st.session_state['_show_decomp_csv_export'] = True

    if export_disabled:
        st.caption("Run decomposition to enable export options")

    if st.session_state.get('_show_decomp_csv_export', False) and has_results:
        export_decomposition_csv()


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
