"""
Session State Management - Initialize and access session state.

Provides centralized session state management for:
- Configuration (ECMConfig)
- Calibration results and diagnostics
- Processed samples
- Lu-Chipman results
- UI state (current sample, selected elements)

Author: Daniel Vala
"""

import streamlit as st
from typing import Optional, Dict, Any

# ============================================================================
# SESSION STATE KEYS (as specified in requirements)
# ============================================================================

SESSION_KEYS = {
    'config': None,                    # ECMConfig object
    'is_calibrated': False,            # Boolean
    'calibration_result': None,        # CalibrationResult object
    'calibration_diag': None,          # CalibrationDiagnostics object
    'processed_samples': {},           # Dict[sample_name, MuellerMatrixResult]
    'lu_chipman_results': {},          # Dict[sample_name, LuChipmanResult]
    'current_sample': None,            # Currently selected sample name
    'selected_elements': [],           # List of (i,j) tuples for MM elements
    # Path settings (persisted across pages)
    'data_dir_path': '',               # Transmission data directory
    'output_dir_path': '',             # Output directory path
    'sample_dir_path': '',             # Sample directory path
    # Calibration mode and auto-detected settings
    'calibration_mode': 'Transmission',  # Transmission, Reflection, or Tutorial Data
    'n_positions': None,               # Auto-detected from calibration files
    # Tutorial mode flags
    'tutorial_mode': False,            # True when using bundled tutorial data
    'saving_disabled': False,          # True in tutorial mode (no persistence)
    # ---- Widget-bound keys (pre-initialized so widgets can use `key=` without `value=`/`index=`) ----
    'wavelength_range': (400, 1000),   # Wavelength slider on Configuration page
    # ---- Reflection-mode state ----
    'refl_data_dir_path': '',          # Reflection calibration + samples directory
    'refl_aoi_deg': 70.0,              # Angle of incidence for reflection (preset)
    'refl_is_calibrated': False,       # Boolean
    'refl_calibration_result': None,   # CalibrationResult from reflection calibration
    'refl_calibration_diag': None,     # ReflectionCalibrationDiagnostics
    'refl_discovered_files': None,     # ReflectionCalibrationFiles
    'refl_processed_samples': {},      # Dict[name, MuellerMatrixResult]
    'refl_ellipsometry_results': {},   # Dict[name, EllipsometricResult]
    'refl_current_sample': None,       # Currently selected reflection sample
    'refl_discovered_samples': None,   # SampleFiles from discover_sample_files
    'refl_selected_samples': [],       # List[str] selected for processing
    'refl_view_mode': '4x4 Grid',      # Display mode for reflection results
    # ---- Decomposition results (mode-agnostic; keyed by sample name) ----
    'differential_results': {},        # Dict[name, DifferentialDecompositionResult]
    'cloude_results': {},              # Dict[name, CloudeDecompositionResult]
    'purity_results': {},              # Dict[name, PurityResult]
}


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_session_state():
    """
    Initialize all session state keys with default values.

    Call this at the start of each page to ensure all keys exist.
    Only initializes keys that don't already exist (preserves state).

    Also includes a workaround for the Streamlit multi-page widget-state
    gotcha: when a page is navigated away from, Streamlit garbage-collects
    session_state entries that were bound to widgets via ``key=...``. By
    re-assigning every existing key to itself here, we mark them as
    non-widget-owned so they survive page changes. Without this, the
    Calibration Mode dropdown (and any other widget-bound state) would
    silently reset to its default whenever the user clicks a different page
    in the sidebar.
    """
    # Persist explicitly-managed keys against Streamlit's page-navigation
    # cleanup. IMPORTANT: only the keys we actually own (i.e. those in
    # SESSION_KEYS) get re-bound here. Transient widget keys created
    # elsewhere (buttons, checkboxes inside components, etc.) must NOT be
    # touched, because Streamlit's widget-state-machine refuses
    # programmatic assignment to widget-owned keys after the widget has
    # been instantiated in a previous run — see
    # ``StreamlitValueAssignmentNotAllowedError``.
    for k in SESSION_KEYS:
        if k in st.session_state:
            st.session_state[k] = st.session_state[k]

    # Initialize any missing keys with their defaults
    for key, default_value in SESSION_KEYS.items():
        if key not in st.session_state:
            # Use copy for mutable defaults to avoid shared state
            if isinstance(default_value, dict):
                st.session_state[key] = {}
            elif isinstance(default_value, list):
                st.session_state[key] = []
            else:
                st.session_state[key] = default_value


# ============================================================================
# CALIBRATION STATE HELPERS
# ============================================================================

def is_calibrated() -> bool:
    """
    Check if calibration has been loaded or completed.

    Returns
    -------
    calibrated : bool
        True if calibration is available.
    """
    return st.session_state.get('is_calibrated', False)


def set_calibration(result, diagnostics):
    """
    Store calibration results in session state.

    Parameters
    ----------
    result : CalibrationResult
        Calibration matrices and parameters.
    diagnostics : CalibrationDiagnostics
        Quality metrics and intermediate data.
    """
    st.session_state.calibration_result = result
    st.session_state.calibration_diag = diagnostics
    st.session_state.is_calibrated = True


def clear_calibration():
    """Clear transmission calibration from session state.

    Reflection state is independent — see :func:`clear_reflection_calibration`.
    """
    st.session_state.calibration_result = None
    st.session_state.calibration_diag = None
    st.session_state.is_calibrated = False
    # Also clear dependent data
    st.session_state.processed_samples = {}
    st.session_state.lu_chipman_results = {}


def get_calibration_info() -> Optional[Dict[str, Any]]:
    """
    Get summary information about the current calibration.

    Returns
    -------
    info : dict or None
        Dictionary with calibration summary, or None if not calibrated.
    """
    if not is_calibrated():
        return None

    result = st.session_state.calibration_result
    diag = st.session_state.calibration_diag

    if result is None:
        return None

    import numpy as np

    return {
        'n_wavelengths': len(result.wavelengths),
        'wl_min': float(result.wavelengths.min()),
        'wl_max': float(result.wavelengths.max()),
        'mean_ratio': float(np.mean(diag.eigenvalue_ratio)) if diag else None,
        'use_ret45': getattr(result, 'use_ret45', False),
    }


def get_calibration_result():
    """
    Get the current CalibrationResult from session state.

    Returns
    -------
    result : CalibrationResult or None
        Calibration result, or None if not calibrated.
    """
    return st.session_state.get('calibration_result', None)


def get_calibration_diagnostics():
    """
    Get the current CalibrationDiagnostics from session state.

    Returns
    -------
    diagnostics : CalibrationDiagnostics or None
        Calibration diagnostics, or None if not calibrated.
    """
    return st.session_state.get('calibration_diag', None)


# ============================================================================
# CONFIGURATION HELPERS
# ============================================================================

def get_config():
    """
    Get the current ECMConfig from session state.

    Returns
    -------
    config : ECMConfig or None
        Current configuration, or None if not set.
    """
    return st.session_state.get('config', None)


def set_config(config):
    """
    Store ECMConfig in session state.

    Parameters
    ----------
    config : ECMConfig
        Configuration object.
    """
    st.session_state.config = config


# ============================================================================
# SAMPLE STATE HELPERS
# ============================================================================

def get_processed_samples() -> Dict:
    """Get dictionary of processed samples."""
    return st.session_state.get('processed_samples', {})


def add_processed_sample(name: str, result):
    """Add a processed sample result."""
    if 'processed_samples' not in st.session_state:
        st.session_state.processed_samples = {}
    st.session_state.processed_samples[name] = result


def get_current_sample() -> Optional[str]:
    """Get the currently selected sample name."""
    return st.session_state.get('current_sample', None)


def set_current_sample(name: str):
    """Set the currently selected sample."""
    st.session_state.current_sample = name


# ============================================================================
# LU-CHIPMAN STATE HELPERS
# ============================================================================

def get_lu_chipman_results() -> Dict:
    """Get dictionary of Lu-Chipman decomposition results."""
    return st.session_state.get('lu_chipman_results', {})


def add_lu_chipman_result(name: str, result):
    """Add a Lu-Chipman decomposition result."""
    if 'lu_chipman_results' not in st.session_state:
        st.session_state.lu_chipman_results = {}
    st.session_state.lu_chipman_results[name] = result


# ============================================================================
# UI STATE HELPERS
# ============================================================================

def get_selected_elements():
    """Get list of selected Mueller matrix elements."""
    return st.session_state.get('selected_elements', [])


def set_selected_elements(elements):
    """Set selected Mueller matrix elements."""
    st.session_state.selected_elements = elements


# ============================================================================
# REFLECTION-MODE STATE HELPERS
# ============================================================================

def is_reflection_calibrated() -> bool:
    """Check if a reflection calibration is loaded."""
    return st.session_state.get('refl_is_calibrated', False)


def set_reflection_calibration(result, diagnostics):
    """Store reflection calibration results in session state.

    Parameters
    ----------
    result : CalibrationResult
        Reflection calibration matrices and parameters.
    diagnostics : ReflectionCalibrationDiagnostics
        Reflection quality metrics and intermediate data.
    """
    st.session_state.refl_calibration_result = result
    st.session_state.refl_calibration_diag = diagnostics
    st.session_state.refl_is_calibrated = True


def clear_reflection_calibration():
    """Clear reflection calibration and its dependent processed/ellipsometry data."""
    st.session_state.refl_calibration_result = None
    st.session_state.refl_calibration_diag = None
    st.session_state.refl_is_calibrated = False
    st.session_state.refl_processed_samples = {}
    st.session_state.refl_ellipsometry_results = {}


def get_reflection_calibration_result():
    """Get the current reflection CalibrationResult, or None."""
    return st.session_state.get('refl_calibration_result', None)


def get_reflection_calibration_diagnostics():
    """Get the current ReflectionCalibrationDiagnostics, or None."""
    return st.session_state.get('refl_calibration_diag', None)


def add_reflection_processed_sample(name: str, mueller_result, ellips_result=None):
    """Store a processed reflection sample (Mueller + optional ellipsometry)."""
    if 'refl_processed_samples' not in st.session_state:
        st.session_state.refl_processed_samples = {}
    if 'refl_ellipsometry_results' not in st.session_state:
        st.session_state.refl_ellipsometry_results = {}
    st.session_state.refl_processed_samples[name] = mueller_result
    if ellips_result is not None:
        st.session_state.refl_ellipsometry_results[name] = ellips_result


def clear_reflection_processed_samples():
    """Remove all reflection processed samples and ellipsometry results."""
    st.session_state.refl_processed_samples = {}
    st.session_state.refl_ellipsometry_results = {}


# ============================================================================
# MODE-AGNOSTIC ACCESSORS (post-processing pages)
# ============================================================================

def get_active_processed_samples() -> Dict:
    """Return the processed-samples dict for the currently active mode.

    Used by post-processing pages that work in both transmission and
    reflection modes (e.g. the decomposition tabs on page 4).
    """
    mode = st.session_state.get('calibration_mode', 'Transmission')
    if mode == 'Reflection':
        return st.session_state.get('refl_processed_samples', {})
    return st.session_state.get('processed_samples', {})


def has_any_calibration() -> bool:
    """True if either a transmission or a reflection calibration is loaded."""
    return is_calibrated() or is_reflection_calibrated()


def full_session_reset() -> None:
    """Clear ALL calibration- and sample-derived state for both modes.

    Used by the re-calibration dialog on the Calibration page: when the user
    confirms they want to re-calibrate (in the same or a different mode),
    everything sample-derived is dumped so the new calibration starts from a
    clean slate. Configuration values (paths, AOI, wavelength range, advanced
    settings) are preserved.
    """
    # Transmission calibration + dependents
    st.session_state.calibration_result = None
    st.session_state.calibration_diag = None
    st.session_state.is_calibrated = False
    st.session_state.processed_samples = {}
    st.session_state.lu_chipman_results = {}
    st.session_state.current_sample = None
    st.session_state.discovered_samples = None
    st.session_state.selected_samples = []

    # Reflection calibration + dependents
    st.session_state.refl_calibration_result = None
    st.session_state.refl_calibration_diag = None
    st.session_state.refl_is_calibrated = False
    st.session_state.refl_discovered_files = None
    st.session_state.refl_processed_samples = {}
    st.session_state.refl_ellipsometry_results = {}
    st.session_state.refl_current_sample = None
    st.session_state.refl_discovered_samples = None
    st.session_state.refl_selected_samples = []

    # Decomposition results (Lu-Chipman is cleared above; the three new ones)
    st.session_state.differential_results = {}
    st.session_state.cloude_results = {}
    st.session_state.purity_results = {}

    # Shared config object built by previous calibration
    st.session_state.config = None
