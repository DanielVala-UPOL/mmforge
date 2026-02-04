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
    'data_dir_path': '',               # Data directory path
    'output_dir_path': '',             # Output directory path
    'sample_dir_path': '',             # Sample directory path
}


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_session_state():
    """
    Initialize all session state keys with default values.

    Call this at the start of each page to ensure all keys exist.
    Only initializes keys that don't already exist (preserves state).
    """
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
    """Clear calibration from session state."""
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
