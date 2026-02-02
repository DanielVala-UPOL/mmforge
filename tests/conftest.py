"""
pytest Configuration and Fixtures for ECM Tests

This module provides shared fixtures and configuration for the ECM test suite.

Fixtures
--------
sample_config
    Returns a default ECMConfig for testing
tolerance
    Returns the numerical tolerance for matrix comparisons (1e-12)
"""

import pytest
import numpy as np
from pathlib import Path


# =============================================================================
# CONSTANTS
# =============================================================================

# Numerical tolerance for matrix comparisons
# This is the same tolerance used in the MATLAB tests
NUMERICAL_TOLERANCE = 1e-12


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def tolerance() -> float:
    """
    Return the numerical tolerance for floating-point comparisons.

    This tolerance (1e-12) matches the MATLAB test suite and is appropriate
    for double-precision floating-point arithmetic.

    Returns
    -------
    float
        Tolerance value for numerical comparisons.
    """
    return NUMERICAL_TOLERANCE


@pytest.fixture
def project_root() -> Path:
    """
    Return the project root directory.

    Returns
    -------
    Path
        Path to the project root (ecm_calibration 6.5.5 PYTHON).
    """
    # tests/conftest.py -> tests/ -> project root
    return Path(__file__).parent.parent


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    """
    Return the data directory path.

    Returns
    -------
    Path
        Path to the data directory.
    """
    return project_root / "data"


@pytest.fixture
def assets_dir(data_dir: Path) -> Path:
    """
    Return the assets directory path.

    Returns
    -------
    Path
        Path to the assets directory containing wavelength files.
    """
    return data_dir / "assets"


# =============================================================================
# REFERENCE MATRICES FOR VALIDATION
# =============================================================================

@pytest.fixture
def horizontal_polarizer_expected() -> np.ndarray:
    """
    Expected Mueller matrix for horizontal polarizer (theta=0, tau=1).

    Compain Eq. 2: P(1,0) = 0.5 * [[1,1,0,0], [1,1,0,0], [0,0,0,0], [0,0,0,0]]

    Returns
    -------
    np.ndarray
        4x4 Mueller matrix for horizontal polarizer.
    """
    return 0.5 * np.array([
        [1.0, 1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0]
    ])


@pytest.fixture
def vertical_polarizer_expected() -> np.ndarray:
    """
    Expected Mueller matrix for vertical polarizer (theta=pi/2, tau=1).

    Returns
    -------
    np.ndarray
        4x4 Mueller matrix for vertical polarizer.
    """
    return 0.5 * np.array([
        [1.0, -1.0, 0.0, 0.0],
        [-1.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0]
    ])


@pytest.fixture
def polarizer_45_expected() -> np.ndarray:
    """
    Expected Mueller matrix for +45 degree polarizer (theta=pi/4, tau=1).

    Returns
    -------
    np.ndarray
        4x4 Mueller matrix for +45 degree polarizer.
    """
    return 0.5 * np.array([
        [1.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
        [1.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 0.0]
    ])


@pytest.fixture
def qwp_horizontal_expected() -> np.ndarray:
    """
    Expected Mueller matrix for QWP with fast axis horizontal (theta=0, delta=pi/2).

    Returns
    -------
    np.ndarray
        4x4 Mueller matrix for quarter-wave plate.
    """
    return np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
        [0.0, 0.0, -1.0, 0.0]
    ])


@pytest.fixture
def hwp_horizontal_expected() -> np.ndarray:
    """
    Expected Mueller matrix for HWP with fast axis horizontal (theta=0, delta=pi).

    Returns
    -------
    np.ndarray
        4x4 Mueller matrix for half-wave plate.
    """
    return np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, -1.0, 0.0],
        [0.0, 0.0, 0.0, -1.0]
    ])
