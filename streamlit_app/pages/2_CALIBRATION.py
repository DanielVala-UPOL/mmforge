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
from components.plots_plotly import (
    create_eigenvalue_plot,
    create_quality_breakdown_chart,
)
from utils.session_state import (
    initialize_session_state,
    is_calibrated,
    set_calibration,
    clear_calibration,
    get_calibration_result,
    get_calibration_diagnostics,
    set_config,
    get_config,
    is_reflection_calibrated,
    set_reflection_calibration,
    clear_reflection_calibration,
    get_reflection_calibration_result,
    get_reflection_calibration_diagnostics,
    has_any_calibration,
    full_session_reset,
    get_output_dir,
)
from utils.theme import sync_theme
from utils.styling import inject_custom_css, soft_divider

# ECM imports
from ecm.config import ECMConfig
from ecm.core import calibrate_transmission
from ecm.core.reflection_calibration import calibrate_reflection
from ecm.core.file_discovery import (
    discover_calibration_files,
    discover_reflection_calibration_files,
)
from ecm.io import save_calibration, load_calibration


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="MMForge - CALIBRATION",
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
# rebuilt with the new palette. Note this fires on the next rerun
# after the switch, not at the moment of switching — Streamlit does
# not re-run the script when the theme changes. Must run after
# initialize_session_state(), which creates the key it compares to.
sync_theme()


# ============================================================================
# SIDEBAR
# ============================================================================

render_sidebar()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_config_from_session() -> ECMConfig:
    """
    Build a transmission-mode ECMConfig from current session state values.

    Used for Transmission and Tutorial Data modes. For Reflection mode use
    :func:`build_reflection_config_from_session`.
    """
    data_dir = st.session_state.get('data_dir_path', '')
    output_dir = get_output_dir()
    wl_min = st.session_state.get('wl_min', 400)
    wl_max = st.session_state.get('wl_max', 1000)

    cfg = ECMConfig()
    cfg.mode = 'transmission'

    if data_dir:
        cfg.paths.data_dir = Path(data_dir)
    cfg.paths.calibration_output_dir = Path(output_dir)

    cfg.wavelength.range_nm = (float(wl_min), float(wl_max))
    cfg.wavelength.reference_nm = 633.0

    # Leave cfg.acquisition.n_angular_positions = None — backend auto-detects.
    return cfg


def build_reflection_config_from_session() -> ECMConfig:
    """
    Build a reflection-mode ECMConfig from current session state values.

    Pulls reflection data dir, AOI, output dir, and wavelength range from
    session state. The wafer-characterization (assets) directory is fixed
    to the bundled ``data/assets/`` folder shipped with MMForge — no user
    input required. The reflection-optimization and TMM-thickness-fit
    parameters use the recommended defaults from
    ``ReflectionOptConfig`` / ``ThicknessFitConfig`` (the same values used
    by ECM-PURE); they are baked in, not exposed in the UI. Leaves
    ``n_angular_positions`` as None so the backend auto-detects.
    """
    refl_data_dir = st.session_state.get('refl_data_dir_path', '')
    output_dir = get_output_dir()
    aoi_deg = float(st.session_state.get('refl_aoi_deg', 70.0))
    wl_min = st.session_state.get('wl_min', 400)
    wl_max = st.session_state.get('wl_max', 1000)

    # Bundled assets directory (data/assets/ at the project root)
    bundled_assets = Path(__file__).parent.parent.parent / 'data' / 'assets'

    cfg = ECMConfig()
    cfg.mode = 'reflection'

    if refl_data_dir:
        cfg.paths.calibration_reflection_dir = Path(refl_data_dir)
        # Also set data_dir so sample discovery can find reflection samples
        # in the same directory (page 3 uses cfg.paths.data_dir for fallback).
        cfg.paths.data_dir = Path(refl_data_dir)

    cfg.paths.assets_dir = bundled_assets
    cfg.spectrometer.wavelength_file = bundled_assets / 'BlackCommet_wavelengths.txt'
    cfg.paths.calibration_output_dir = Path(output_dir)

    cfg.reflection_cal.angle_of_incidence_deg = aoi_deg
    cfg.wavelength.range_nm = (float(wl_min), float(wl_max))
    cfg.wavelength.reference_nm = 633.0

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
    """Discover calibration files, auto-detect rotator steps, and display results."""
    cfg = build_config_from_session()

    if cfg.paths.data_dir is None:
        st.error("Data directory not set. Go to **CONFIGURATION** page and enter the path to your calibration data folder.")
        return None

    try:
        with st.spinner("Discovering calibration files..."):
            cal_files = discover_calibration_files(cfg)

        # Store in session state
        st.session_state['discovered_files'] = cal_files

        # Check if all required files found
        if not display_discovered_files(cal_files):
            return None

        # Auto-detect rotator steps from file dimensions
        n_positions = detect_rotator_steps(cal_files)

        if n_positions is not None:
            st.session_state['n_positions'] = n_positions

            # Display combined success message
            fp2_status = "FP2 included" if cal_files.ret_45 is not None else "FP2 not included (optional)"
            #st.success(f"Found all calibration files. Detected {n_positions} rotator steps. {fp2_status}")
            st.success(f"Found all calibration files. {fp2_status}")
        else:
            # Error already displayed by detect_rotator_steps
            return None

        return cal_files

    except ValueError as e:
        st.error(f"Multiple matching files found. Ensure each calibration type has only one .bin file in the directory. Error: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error during file discovery: {e}")
        return None


def discover_reflection_files_and_display():
    """Discover reflection calibration + wafer characterization files and display."""
    cfg = build_reflection_config_from_session()

    if cfg.paths.calibration_reflection_dir is None:
        st.error("Reflection data directory not set. Go to **CONFIGURATION** page and enter the path to your reflection calibration data folder.")
        return None
    if cfg.paths.assets_dir is None:
        st.error("Wafer characterization (assets) directory not set. Go to **CONFIGURATION** page and enter the path to the Woollam VASE files.")
        return None

    try:
        with st.spinner("Discovering reflection files..."):
            refl_files = discover_reflection_calibration_files(cfg)

        st.session_state['refl_discovered_files'] = refl_files
        display_reflection_discovered_files(refl_files)
        st.success("Found all reflection calibration files and wafer characterization assets.")
        return refl_files

    except FileNotFoundError as e:
        st.error(f"Missing reflection file: {e}")
        return None
    except ValueError as e:
        st.error(f"Ambiguous reflection file match: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error during reflection file discovery: {e}")
        return None


def display_reflection_discovered_files(refl_files) -> None:
    """Display the 5 user-supplied reflection calibration measurement files.

    The Woollam Ψ/Δ and Rp/Rs wafer characterization files live in the
    bundled ``data/assets/`` directory; they are auto-discovered and used
    by the backend but not part of the user-facing file list.
    """
    st.markdown("**Reflection Calibration Files**")
    measurement_rows = [
        ("DARK", refl_files.dark),
        ("WAFER 25 nm (bare)", refl_files.wafer25nm),
        ("WAFER 25 nm + Pol BEFORE", refl_files.wafer25nm_pol_before),
        ("WAFER 25 nm + Pol AFTER", refl_files.wafer25nm_pol_after),
        ("WAFER 10 nm (bare)", refl_files.wafer10nm),
    ]
    for name, path in measurement_rows:
        cols = st.columns([2, 5])
        cols[0].write(f"**{name}**")
        cols[1].write(Path(path).name if path is not None else "—")


def display_discovered_files(cal_files) -> bool:
    """
    Display discovered files in the same tabular layout as the reflection
    discovery (label on the left, filename on the right). Returns True if
    all required files found, False otherwise.
    """
    file_info = [
        ("Background (DARK)", cal_files.dark, True),
        ("Air, straight-through (ST)", cal_files.air, True),
        ("Polarizer 0° (P0)", cal_files.pol_0, True),
        ("Polarizer 45° (P45)", cal_files.pol_45, True),
        ("Retarder 90° (FP1)", cal_files.ret_90, True),
        ("Retarder 45° (FP2, optional)", cal_files.ret_45, False),
    ]

    required_found = sum(1 for _, path, req in file_info if req and path is not None)
    required_total = sum(1 for _, _, req in file_info if req)
    missing_required = [name for name, path, req in file_info if req and path is None]

    st.markdown("**Transmission Calibration Files**")
    for name, path, req in file_info:
        cols = st.columns([2, 5])
        cols[0].write(f"**{name}**")
        if path is not None:
            cols[1].write(Path(path).name)
        elif req:
            cols[1].markdown(":red[— missing —]")
        else:
            cols[1].write("—")

    if required_found < required_total:
        missing_str = ", ".join(missing_required)
        st.error(
            f"Missing required calibration files: **{missing_str}**. "
            f"Found {required_found}/{required_total} required. "
            "Check that all calibration .bin files are in the data directory."
        )
        return False

    return True


def detect_rotator_steps(cal_files) -> int | None:
    """
    Auto-detect rotator steps from calibration file dimensions.

    Thin wrapper around :func:`ecm.utils.io.detect_angular_positions` that
    converts backend ``ValueError`` into a Streamlit error message.

    Returns
    -------
    n_positions : int or None
        Detected number of rotator steps, or None on error.
    """
    from ecm.utils.io import detect_angular_positions

    n_wavelengths = st.session_state.get('n_wavelengths', 2048)

    paths = [
        cal_files.dark, cal_files.air,
        cal_files.pol_0, cal_files.pol_45, cal_files.ret_90,
    ]
    labels = ['DARK', 'ST', 'P0', 'P45', 'RET90_FP1']
    if cal_files.ret_45 is not None:
        paths.append(cal_files.ret_45)
        labels.append('RET45_FP2')

    try:
        return detect_angular_positions(
            paths, n_wavelengths,
            n_rotation_cycles=1,
            file_labels=labels,
        )
    except ValueError as e:
        st.error(str(e))
        return None


def run_calibration_workflow():
    """Dispatch calibration to the right backend based on calibration_mode."""
    mode = st.session_state.get('calibration_mode', 'Transmission')
    if mode in ('Transmission', 'Tutorial Data'):
        run_transmission_workflow()
    elif mode == 'Reflection':
        run_reflection_workflow()
    else:
        st.error(f"Unknown calibration mode: '{mode}'. Choose Transmission, Reflection, or Tutorial Data.")


def run_transmission_workflow():
    """Execute transmission ECM calibration with step + progress display.

    Mirrors the reflection workflow's three-line layout:
      * ``Steps [k/total] completed.`` — completion counter
      * ``Step [n/total]: <name>`` — current step label
      * progress bar — fills during the per-wavelength final K/W/A solve;
        sits at 0% during the fast early steps.
    """
    cfg = build_config_from_session()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        completed_container = st.empty()
        step_container = st.empty()
        progress_container = st.empty()
        progress_bar = progress_container.progress(0, text="0%")

    def step_callback(step_idx, total_steps, label):
        # When step_idx begins, step_idx − 1 steps are now complete.
        completed_container.markdown(
            f"_Steps [{step_idx - 1}/{total_steps}] completed._"
        )
        step_container.markdown(
            f"**Step [{step_idx}/{total_steps}]:** {label}"
        )
        progress_bar.progress(0, text="0%")

    def progress_callback(current_wl, total_wl, eigenvalue_ratio):
        if total_wl > 0:
            progress = current_wl / total_wl
            progress_bar.progress(progress, text=f"{int(progress * 100)}%")

    try:
        result, diagnostics = calibrate_transmission(
            cfg,
            progress_callback=progress_callback,
            step_callback=step_callback,
        )

        set_calibration(result, diagnostics)
        set_config(cfg)

        completed_container.empty()
        step_container.empty()
        progress_container.empty()

        st.success(
            f"Calibration complete! "
            f"{len(result.wavelengths)} wavelengths calibrated. "
            f"Mean eigenvalue ratio: {np.mean(diagnostics.eigenvalue_ratio):.2e}"
        )

        st.rerun()

    except Exception as e:
        completed_container.empty()
        step_container.empty()
        progress_container.empty()
        st.error(f"Calibration failed: {e}. Check that calibration files are valid and not corrupted.")


def run_reflection_workflow():
    """Execute reflection ECM calibration with step + progress display.

    The reflection calibration is multi-stage and can take a couple of
    minutes. We surface three pieces of feedback, stacked top-to-bottom:

    * A *completed counter* — ``Steps [k/total] completed.`` — k ticks up
      every time a new step begins, so the user can watch the fast early
      steps fly by.
    * A *current step indicator* — ``Step [n/total]: <name>`` — updated
      at the start of each major stage by the backend's ``step_callback``.
    * A *progress bar* showing per-wavelength progress within the heavy
      stages (wafer optimization, refined optimization, final K/W/A
      solve). Non-per-wavelength stages reset the bar to 0% and rely on
      the step name for "what's happening now" feedback.
    """
    cfg = build_reflection_config_from_session()

    # Re-run discovery defensively in case Discover Files wasn't pressed.
    try:
        refl_files = discover_reflection_calibration_files(cfg)
        st.session_state['refl_discovered_files'] = refl_files
    except (FileNotFoundError, ValueError) as e:
        st.error(f"Reflection file discovery failed: {e}")
        return

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        completed_container = st.empty()
        step_container = st.empty()
        progress_container = st.empty()
        progress_bar = progress_container.progress(0, text="0%")

    # Track the parent step index so multi-start sub-phases don't bump
    # the completed counter (they share the parent step's index).
    last_parent_step = {'value': 0, 'total': 0}

    def step_callback(step_idx, total_steps, label):
        # When step_idx begins, step_idx − 1 steps are now complete.
        # Only update the completed counter when we advance to a new
        # parent step — multi-start sub-phases reuse the parent's index
        # and should not change the count.
        if step_idx != last_parent_step['value']:
            completed_container.markdown(
                f"_Steps [{step_idx - 1}/{total_steps}] completed._"
            )
            last_parent_step['value'] = step_idx
            last_parent_step['total'] = total_steps

        step_container.markdown(
            f"**Step [{step_idx}/{total_steps}]:** {label}"
        )
        progress_bar.progress(0, text="0%")

    def progress_callback(current_wl, total_wl, eigenvalue_ratio):
        if total_wl > 0:
            progress = current_wl / total_wl
            progress_bar.progress(
                progress, text=f"{int(progress * 100)}%"
            )

    try:
        result, diagnostics = calibrate_reflection(
            cfg,
            progress_callback=progress_callback,
            step_callback=step_callback,
        )

        set_reflection_calibration(result, diagnostics)
        set_config(cfg)

        completed_container.empty()
        step_container.empty()
        progress_container.empty()

        st.success(
            f"Reflection calibration complete! "
            f"{len(result.wavelengths)} wavelengths calibrated. "
            f"Mean eigenvalue ratio: {np.mean(diagnostics.eigenvalue_ratio):.2e}"
        )

        st.rerun()

    except Exception as e:
        completed_container.empty()
        step_container.empty()
        progress_container.empty()
        st.error(f"Reflection calibration failed: {e}. Check that wafer files and characterization assets are valid.")


def display_quality_summary(diagnostics, result, is_reflection: bool = False):
    """Display quality breakdown with metrics, chart, and eigenvalue plot.

    In reflection mode, also shows the TMM physics fit results
    (d₁, d₂, δAOI, AOI used) inside the summary.
    """
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

    # ----- Reflection-only: TMM physics fit + optimization summary -----
    if is_reflection:
        _display_reflection_physics(diagnostics)

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


def _display_reflection_physics(diagnostics) -> None:
    """Reflection-only block inside the Quality Summary.

    Shows the TMM thickness fit: ``d1`` (nominal 25 nm, Woollam range
    20–25 nm), ``d2`` (nominal 10 nm, Woollam range 9–11 nm), AOI
    correction ``δAOI`` and the resulting effective AOI. Each thickness
    card carries a small status caption indicating whether the fitted
    value falls inside the Woollam tolerance range, so the user can spot
    unphysical fits at a glance.
    """
    # Woollam-measured tolerance bands for the two reference wafers.
    # Values come from the original Woollam VASE characterization of the
    # bundled reference samples.
    WOOLLAM_D1_RANGE = (20.0, 25.0)  # 25 nm wafer
    WOOLLAM_D2_RANGE = (9.0, 11.0)   # 10 nm wafer

    def _range_caption(value: float, low: float, high: float) -> str:
        if low <= value <= high:
            return f":green[✓ Within Woollam range ({low:g}–{high:g} nm)]"
        return f":red[⚠ Outside Woollam range ({low:g}–{high:g} nm)]"

    tr = getattr(diagnostics, 'thickness_result', None)
    if tr is not None:
        pr = tr.physics_result
        st.markdown("**Reflection physics (TMM fit)**")
        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "d₁ — 25 nm wafer",
            f"{pr.d1_fitted_nm:.2f} nm",
            delta=f"{pr.d1_fitted_nm - 25.0:+.2f} nm vs nominal",
            delta_color="off",
        )
        c1.caption(_range_caption(pr.d1_fitted_nm, *WOOLLAM_D1_RANGE))

        c2.metric(
            "d₂ — 10 nm wafer",
            f"{pr.d2_fitted_nm:.2f} nm",
            delta=f"{pr.d2_fitted_nm - 10.0:+.2f} nm vs nominal",
            delta_color="off",
        )
        c2.caption(_range_caption(pr.d2_fitted_nm, *WOOLLAM_D2_RANGE))

        c3.metric(
            "δAOI (correction)",
            f"{pr.delta_aoi_fitted_deg:+.2f}°",
        )
        c4.metric(
            "AOI (effective)",
            f"{pr.aoi_fitted_deg:.2f}°",
        )
    else:
        # No TMM step ran → at least show convergence
        opt = getattr(diagnostics, 'optimization_result', None)
        if opt is not None:
            converged_pct = float(np.mean(opt.converged) * 100.0)
            st.markdown("**Reflection physics**")
            st.metric("Wafer optimization converged", f"{converged_pct:.1f}%")


def save_current_calibration():
    """Save the calibration matching the current mode to file."""
    mode = st.session_state.get('calibration_mode', 'Transmission')
    if mode == 'Reflection':
        result = get_reflection_calibration_result()
        diagnostics = get_reflection_calibration_diagnostics()
    else:
        result = get_calibration_result()
        diagnostics = get_calibration_diagnostics()

    cfg = get_config()

    if result is None or diagnostics is None:
        st.error("No calibration data available for this mode. Run calibration first before saving.")
        return

    if cfg is None:
        if mode == 'Reflection':
            cfg = build_reflection_config_from_session()
        else:
            cfg = build_config_from_session()

    output_dir = get_output_dir()

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
    """Load calibration from file and dispatch state by saved mode."""
    try:
        with st.spinner("Loading calibration..."):
            result, diagnostics, cfg, metadata = load_calibration(
                Path(filepath),
                verbose=False
            )

        saved_mode = metadata.mode
        if saved_mode == 'reflection':
            set_reflection_calibration(result, diagnostics)
            set_config(cfg)
            # Repopulate the reflection session-state keys from the loaded cfg
            # so the Configuration page reflects the loaded state. The assets
            # dir is bundled with MMForge — no need to restore it from the file.
            if cfg.paths.calibration_reflection_dir is not None:
                st.session_state['refl_data_dir_path'] = str(cfg.paths.calibration_reflection_dir)
            st.session_state['refl_aoi_deg'] = float(cfg.reflection_cal.angle_of_incidence_deg)
            st.session_state['calibration_mode'] = 'Reflection'
        else:
            # Default to transmission for unknown / legacy 'transmission' values
            set_calibration(result, diagnostics)
            set_config(cfg)
            if saved_mode != 'transmission':
                st.warning(f"Unknown saved mode '{saved_mode}', treated as Transmission.")

        st.success(
            f"Loaded {saved_mode} calibration from {metadata.timestamp}\n\n"
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

    mode = st.session_state.get('calibration_mode', 'Transmission')
    is_reflection_mode = (mode == 'Reflection')

    # Mode-dependent state lookups
    if is_reflection_mode:
        mode_is_calibrated = is_reflection_calibrated()
        active_result = get_reflection_calibration_result()
        active_diagnostics = get_reflection_calibration_diagnostics()
        data_dir = st.session_state.get('refl_data_dir_path', '')
        discovered_key = 'refl_discovered_files'
        data_dir_label = "Reflection Data Directory"
        discover_button_label = "Discover Files (Reflection)"
        missing_dir_hint = "Set the Reflection Data Directory in Configuration first"
    else:
        mode_is_calibrated = is_calibrated()
        active_result = get_calibration_result()
        active_diagnostics = get_calibration_diagnostics()
        data_dir = st.session_state.get('data_dir_path', '')
        discovered_key = 'discovered_files'
        data_dir_label = "Transmission Data Directory"
        discover_button_label = "Discover Files (Transmission)"
        missing_dir_hint = "Set the Transmission Data Directory in Configuration first"

    # -------------------------------------------------
    # Calibration Files Section - full width file list
    # -------------------------------------------------
    with st.expander("Calibration Files", expanded=not mode_is_calibrated):
        st.markdown(f"Discover calibration files in your {data_dir_label.lower()}.")

        # Discovery only depends on the active mode's data dir. The wafer
        # characterization (assets) dir is bundled with MMForge so it never
        # blocks the Reflection discover button.
        discover_disabled = not data_dir

        if st.button(
            discover_button_label,
            use_container_width=False,
            disabled=discover_disabled,
            help=missing_dir_hint if discover_disabled else None
        ):
            if is_reflection_mode:
                discover_reflection_files_and_display()
            else:
                discover_and_display_files()

        if discover_disabled:
            st.caption(missing_dir_hint)

    # -------------------------------------------------
    # Run Calibration Section - centered wider button
    # -------------------------------------------------
    soft_divider()

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        has_files = bool(st.session_state.get(discovered_key))
        run_disabled = not has_files

        if st.button(
            "Run Calibration",
            type="primary",
            use_container_width=True,
            disabled=run_disabled,
            help="Discover calibration files first" if run_disabled else None
        ):
            # If ANY calibration is loaded (same or different mode), warn the
            # user that running a new calibration will wipe the session.
            if has_any_calibration():
                st.session_state['_show_recal_dialog'] = True
                st.rerun()
            else:
                run_calibration_workflow()

    if run_disabled:
        st.caption("Click 'Discover Files' first to find calibration files")

    # Add vertical spacing after Run Calibration section
    st.markdown("<br>", unsafe_allow_html=True)

    # Re-calibration confirmation dialog — full session reset on proceed
    @st.dialog("Re-calibrate? Session will be reset.")
    def confirm_recalibration():
        st.warning(
            "Running a new calibration will **reset the session**:\n\n"
            "- All current calibration data (transmission **and** reflection) will be cleared.\n"
            "- All processed samples and decomposition results will be removed.\n\n"
            "Configuration values (paths, AOI, wavelength range) are kept."
        )
        st.write("Do you want to proceed?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Proceed", use_container_width=True, type="primary"):
                full_session_reset()
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
    if mode_is_calibrated and active_result and active_diagnostics:
        with st.expander("Quality Summary", expanded=True):
            display_quality_summary(
                active_diagnostics, active_result,
                is_reflection=is_reflection_mode,
            )

    # -------------------------------------------------
    # Save/Load Calibration Section (moved to bottom)
    # -------------------------------------------------
    soft_divider()
    st.subheader("Save / Load Calibration")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Save Current Calibration**")
        tutorial_mode = st.session_state.get('tutorial_mode', False)
        save_disabled = not mode_is_calibrated or tutorial_mode
        if tutorial_mode:
            save_help = "Saving is disabled in Tutorial mode"
        elif not mode_is_calibrated:
            save_help = "Run calibration first to enable saving"
        else:
            save_help = None
        if st.button(
            "Save Calibration",
            use_container_width=True,
            disabled=save_disabled,
            help=save_help
        ):
            save_current_calibration()

    with col2:
        st.markdown("**Load Saved Calibration**")
        tutorial_mode = st.session_state.get('tutorial_mode', False)

        # File path input
        cal_file_path = st.text_input(
            "Calibration file path (.npz)",
            key="load_cal_path",
            placeholder="/path/to/calibration.npz",
            disabled=tutorial_mode
        )

        if tutorial_mode:
            st.caption("Loading is disabled in Tutorial mode.")
        elif cal_file_path:
            if st.button("Load Selected", use_container_width=True):
                load_calibration_from_file(cal_file_path)


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
