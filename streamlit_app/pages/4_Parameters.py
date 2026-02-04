"""
Parameters Extraction Page - Lu-Chipman polar decomposition of Mueller matrices.

This page handles:
- Sample selection for decomposition
- Running Lu-Chipman decomposition
- Mueller matrix visualization (M_D, M_R, M_Delta)
- Parameter visualization (DI, D, R with unit selector)
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
)
from utils.session_state import (
    initialize_session_state,
    is_calibrated,
    get_processed_samples,
    get_lu_chipman_results,
    add_lu_chipman_result,
    get_calibration_result,
)

# ECM imports
from ecm.postprocessing import lu_chipman_decomposition


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="ECM - Parameters",
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
    processed = get_processed_samples()

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
    processed = get_processed_samples()
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
    cal_result = get_calibration_result()

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

    # Matrix selection tabs (order: Diattenuator → Depolarizer → Retarder)
    matrix_tabs = st.tabs(["M_D (Diattenuator)", "M_Δ (Depolarizer)", "M_R (Retarder)"])

    matrix_keys = ['M_D', 'M_Delta', 'M_R']
    matrix_names = ['M<sub>D</sub>', 'M<sub>Δ</sub>', 'M<sub>R</sub>']

    for tab_idx, tab in enumerate(matrix_tabs):
        with tab:
            matrix_key = matrix_keys[tab_idx]
            matrix_name = matrix_names[tab_idx]

            if view_mode == "Compare Samples":
                # Multi-sample comparison mode
                st.markdown("**Select samples to compare:**")

                # Sample selection checkboxes for comparison
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Select All", key=f"matrix_compare_select_{matrix_key}", use_container_width=True):
                        for name in sample_names:
                            st.session_state[f"matrix_compare_cb_{matrix_key}_{name}"] = True
                        st.rerun()
                with col2:
                    if st.button("Clear All", key=f"matrix_compare_clear_{matrix_key}", use_container_width=True):
                        for name in sample_names:
                            st.session_state[f"matrix_compare_cb_{matrix_key}_{name}"] = False
                        st.rerun()

                selected_for_compare = []
                cols = st.columns(min(3, len(sample_names)))
                for idx, name in enumerate(sample_names):
                    with cols[idx % len(cols)]:
                        if st.checkbox(name, key=f"matrix_compare_cb_{matrix_key}_{name}"):
                            selected_for_compare.append(name)

                if len(selected_for_compare) >= 2:
                    # Build samples dictionary for comparison plot
                    samples_dict = {}
                    for name in selected_for_compare:
                        result = lc_results[name]
                        M = getattr(result, matrix_key)
                        # For comparison, m00 is None since decomposed matrices don't have unnormalized transmission
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
                # Single sample view modes
                current = st.session_state.get('decomp_current_sample')
                if current not in sample_names:
                    current = sample_names[0]
                    st.session_state['decomp_current_sample'] = current

                selected_sample = st.selectbox(
                    "Select Sample",
                    sample_names,
                    index=sample_names.index(current) if current in sample_names else 0,
                    key=f"matrix_sample_selector_{matrix_key}"
                )

                if selected_sample != current:
                    st.session_state['decomp_current_sample'] = selected_sample

                result = lc_results[selected_sample]
                M = getattr(result, matrix_key)

                if view_mode == "4x4 Grid":
                    fig = create_mueller_matrix_plot(
                        M,
                        wavelengths,
                        title=f"{matrix_name} - {selected_sample}",
                        m00=None  # Decomposed matrices don't have unnormalized M00
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
    cal_result = get_calibration_result()

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

        st.markdown("---")

    # Parameter tabs (now use unified `selected` list)
    param_tabs = st.tabs(["Diattenuation (D)", "Depolarization Index (DI)", "Retardance (R)", "Fast Axis (ν, χ)"])

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

    with param_tabs[3]:  # Fast Axis (ν, χ)
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

    cal_result = get_calibration_result()
    wavelengths = cal_result.wavelengths if cal_result else None

    output_dir = st.session_state.get('output_dir_path', str(Path.cwd() / 'decomposition_output'))
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
    cal_result = get_calibration_result()

    output_dir = st.session_state.get('output_dir_path', str(Path.cwd() / 'decomposition_output'))
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
    cal_result = get_calibration_result()
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
# MAIN PAGE CONTENT
# ============================================================================

def main():
    st.title("Parameters Extraction")

    st.markdown("""
    Perform **Lu-Chipman polar decomposition** of Mueller matrices to extract physical parameters:
    - **Diattenuation (D)**: Differential attenuation of polarization states [0, 1]
    - **Depolarization Index (DI)**: Measure of polarization preservation [0, 1]
    - **Retardance (R)**: Phase shift between polarization components
    - **Fast-axis angles (ν, χ)**: Orientation of optical axes
    """)

    st.markdown("---")

    # -------------------------------------------------
    # Prerequisites Check
    # -------------------------------------------------
    if not is_calibrated():
        st.warning("Not calibrated. Please run calibration first.")
        st.stop()

    processed_samples = get_processed_samples()

    if not processed_samples:
        st.info("No processed samples available. Process samples on the Sample Processing page first.")
        st.stop()

    lc_results = get_lu_chipman_results()
    has_results = len(lc_results) > 0

    # -------------------------------------------------
    # Sample Selection Section
    # -------------------------------------------------
    with st.expander("Sample Selection", expanded=not has_results):
        display_sample_checkboxes()

    # -------------------------------------------------
    # Run Decomposition Button
    # -------------------------------------------------
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        selected = st.session_state.get('decomp_selected_samples', [])
        run_disabled = len(selected) == 0

        if st.button(
            "Run Decomposition",
            use_container_width=True,
            disabled=run_disabled,
            help="Select samples first" if run_disabled else f"Decompose {len(selected)} sample(s)"
        ):
            run_decomposition(selected)

    if run_disabled:
        st.caption("Select samples above to enable decomposition")
    else:
        st.caption(f"{len(selected)} sample(s) selected")

    # Show decomposition results (persisted in session state across rerun)
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

        # Clear the flags after displaying
        del st.session_state['_decomp_done']
        del st.session_state['_decomp_count']
        del st.session_state['_decomp_total']
        del st.session_state['_decomp_errors']

    # -------------------------------------------------
    # Decomposed Matrices Section
    # -------------------------------------------------
    if has_results:
        with st.expander("Decomposed Matrices", expanded=True):
            display_decomposed_matrices()

    # -------------------------------------------------
    # Decomposition Parameters Section
    # -------------------------------------------------
    if has_results:
        with st.expander("Decomposition Parameters", expanded=True):
            display_parameter_plots()

    # -------------------------------------------------
    # Summary Section
    # -------------------------------------------------
    if has_results:
        with st.expander("Summary Table", expanded=True):
            display_summary_table()

    # -------------------------------------------------
    # Export Section
    # -------------------------------------------------
    st.markdown("---")
    st.subheader("Export")

    col1, col2 = st.columns(2)

    export_disabled = not has_results

    with col1:
        if st.button(
            "Save Decomposition (.npz)",
            use_container_width=True,
            disabled=export_disabled
        ):
            save_decomposition()

    with col2:
        if st.button(
            "Export Data (.csv)",
            use_container_width=True,
            disabled=export_disabled
        ):
            st.session_state['_show_decomp_csv_export'] = True

    if export_disabled:
        st.caption("Run decomposition to enable export options")

    # Show CSV export dialog if requested
    if st.session_state.get('_show_decomp_csv_export', False) and has_results:
        export_decomposition_csv()


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
