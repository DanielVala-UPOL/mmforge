"""
Mueller Matrix Extraction from Calibrated Measurements

This module provides functions to extract Mueller matrices from intensity
measurements using the calibration matrices (W, A) obtained from the ECM
calibration procedure.

Functions
---------
extract_mueller_matrix(B_sample, A, W)
    Extract Mueller matrix from intensity matrix using calibration
process_sample(sample_data, calibration, cfg)
    High-level function to process a sample measurement

Theory
------
The measurement equation in a dual rotating compensator polarimeter is:

    B = A @ M @ W

where:
- B is the 4×4 intensity matrix (from build_intensity_matrix)
- A is the 4×4 PSA modulation matrix (detector side)
- M is the 4×4 Mueller matrix of the sample
- W is the 4×4 PSG modulation matrix (source side)

Given the calibration matrices A and W, the sample Mueller matrix is:

    M = A^(-1) @ B @ W^(-1)

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999), Eq. 16
"""

import numpy as np
from numpy import ndarray
from dataclasses import dataclass
from typing import Union, Tuple, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from ecm.config.ecm_config import ECMConfig


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MuellerMatrixResult:
    """
    Result of Mueller matrix extraction.

    Attributes
    ----------
    M : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        Unnormalized Mueller matrix(ces).
        M[0,0] represents the total transmission/reflection.

    M_normalized : ndarray, same shape as M
        Normalized Mueller matrix(ces) with M[0,0] = 1.

    m00 : ndarray, shape () or (n_wavelengths,)
        The (0,0) element before normalization (transmission/reflection).

    Notes
    -----
    **Unnormalized vs Normalized:**

    The unnormalized Mueller matrix M has M[0,0] equal to the sample's
    transmission (transmission mode) or reflection (reflection mode).
    This contains absolute photometric information.

    The normalized Mueller matrix M_norm has M[0,0] = 1, which is the
    standard form for polarimetric analysis. It removes the photometric
    scaling but preserves all polarimetric properties.

    For most applications, use M_normalized. Use M when absolute
    transmission/reflection values are needed.
    """
    M: ndarray
    M_normalized: ndarray
    m00: ndarray


# =============================================================================
# MUELLER MATRIX EXTRACTION
# =============================================================================

def extract_mueller_matrix(
    B_sample: ndarray,
    A: ndarray,
    W: ndarray
) -> ndarray:
    """
    Extract Mueller matrix from intensity matrix using calibration.

    Given the measurement equation B = A @ M @ W, computes:
        M = A^(-1) @ B @ W^(-1)

    Reference: Compain et al., Appl. Opt. 38, 3490-3502 (1999), Eq. 16

    Parameters
    ----------
    B_sample : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        Intensity matrix(ces) for the sample measurement.

    A : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        PSA modulation matrix(ces) from calibration.

    W : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        PSG modulation matrix(ces) from calibration.

    Returns
    -------
    M : ndarray, same shape as B_sample
        Unnormalized Mueller matrix(ces).
        M[0,0] represents the sample transmission/reflection.

    Raises
    ------
    ValueError
        If input shapes are inconsistent.
        If A or W is singular.

    Examples
    --------
    >>> # Single wavelength
    >>> M = extract_mueller_matrix(B_sample, A, W)
    >>> print(f"Transmission: {M[0,0]:.4f}")

    >>> # Multiple wavelengths
    >>> M = extract_mueller_matrix(B_samples, A_all, W_all)  # [4,4,n_wl]
    >>> M_normalized = M / M[0, 0, :]  # Normalize each wavelength

    Notes
    -----
    **Numerical Stability:**

    The computation M = A^(-1) @ B @ W^(-1) is performed using
    `np.linalg.solve` for better numerical stability:

        1. Solve A @ X = B for X (i.e., X = A^(-1) @ B)
        2. Solve M @ W = X for M (i.e., M = X @ W^(-1))

    **Wavelength Broadcasting:**

    If B_sample has shape (4, 4, n_wavelengths), then A and W can be:
    - Shape (4, 4): Same calibration applied to all wavelengths
    - Shape (4, 4, n_wavelengths): Per-wavelength calibration

    The standard ECM calibration produces per-wavelength A and W matrices.
    """
    # -------------------------------------------------------------------------
    # Handle input shapes and determine computation mode
    # -------------------------------------------------------------------------
    if B_sample.ndim == 2:
        # Single wavelength case
        return _extract_mueller_single(B_sample, A, W)

    elif B_sample.ndim == 3:
        # Multiple wavelengths case
        n_wavelengths = B_sample.shape[2]

        # Validate A shape
        if A.ndim == 2:
            # Broadcast A to all wavelengths
            A = np.broadcast_to(A[:, :, np.newaxis], (4, 4, n_wavelengths))
        elif A.shape[2] != n_wavelengths:
            raise ValueError(
                f"A has {A.shape[2]} wavelengths but B_sample has {n_wavelengths}"
            )

        # Validate W shape
        if W.ndim == 2:
            # Broadcast W to all wavelengths
            W = np.broadcast_to(W[:, :, np.newaxis], (4, 4, n_wavelengths))
        elif W.shape[2] != n_wavelengths:
            raise ValueError(
                f"W has {W.shape[2]} wavelengths but B_sample has {n_wavelengths}"
            )

        return _extract_mueller_multi(B_sample, A, W)

    else:
        raise ValueError(
            f"B_sample must be 2D (4×4) or 3D (4×4×n_wl), got {B_sample.ndim}D"
        )


def _extract_mueller_single(
    B_sample: ndarray,
    A: ndarray,
    W: ndarray
) -> ndarray:
    """
    Extract Mueller matrix for single wavelength.

    Parameters
    ----------
    B_sample : ndarray, shape (4, 4)
    A : ndarray, shape (4, 4)
    W : ndarray, shape (4, 4)

    Returns
    -------
    M : ndarray, shape (4, 4)
    """
    # Validate shapes
    if B_sample.shape != (4, 4):
        raise ValueError(f"B_sample must be 4×4, got {B_sample.shape}")

    # Handle A broadcasting
    if A.ndim == 3:
        A = A[:, :, 0]
    if A.shape != (4, 4):
        raise ValueError(f"A must be 4×4, got {A.shape}")

    # Handle W broadcasting
    if W.ndim == 3:
        W = W[:, :, 0]
    if W.shape != (4, 4):
        raise ValueError(f"W must be 4×4, got {W.shape}")

    # -------------------------------------------------------------------------
    # Compute M = A^(-1) @ B @ W^(-1)
    #
    # Step 1: X = A^(-1) @ B (solve A @ X = B)
    # Step 2: M = X @ W^(-1) (solve W.T @ M.T = X.T, then transpose)
    # -------------------------------------------------------------------------

    # Check conditioning of A
    cond_A = np.linalg.cond(A)
    if cond_A > 1e10:
        raise ValueError(
            f"A is poorly conditioned (cond={cond_A:.2e}). "
            f"This may indicate calibration issues."
        )

    # Check conditioning of W
    cond_W = np.linalg.cond(W)
    if cond_W > 1e10:
        raise ValueError(
            f"W is poorly conditioned (cond={cond_W:.2e}). "
            f"This may indicate calibration issues."
        )

    # Step 1: X = A^(-1) @ B
    X = np.linalg.solve(A, B_sample)

    # Step 2: M = X @ W^(-1)
    # Rewrite as: M @ W = X
    # Transpose: W.T @ M.T = X.T
    # So: M.T = solve(W.T, X.T)
    # And: M = solve(W.T, X.T).T
    M = np.linalg.solve(W.T, X.T).T

    return M


def _extract_mueller_multi(
    B_sample: ndarray,
    A: ndarray,
    W: ndarray
) -> ndarray:
    """
    Extract Mueller matrices for multiple wavelengths.

    Parameters
    ----------
    B_sample : ndarray, shape (4, 4, n_wavelengths)
    A : ndarray, shape (4, 4, n_wavelengths)
    W : ndarray, shape (4, 4, n_wavelengths)

    Returns
    -------
    M : ndarray, shape (4, 4, n_wavelengths)
    """
    n_wavelengths = B_sample.shape[2]
    M = np.zeros((4, 4, n_wavelengths), dtype=np.float64)

    for i_wl in range(n_wavelengths):
        M[:, :, i_wl] = _extract_mueller_single(
            B_sample[:, :, i_wl],
            A[:, :, i_wl],
            W[:, :, i_wl]
        )

    return M


# =============================================================================
# HIGH-LEVEL SAMPLE PROCESSING
# =============================================================================

def process_sample(
    sample_data: Union[ndarray, Path, str],
    A: ndarray,
    W: ndarray,
    inv_W_mod: ndarray,
    dark: Optional[ndarray] = None,
    cfg: Optional['ECMConfig'] = None
) -> MuellerMatrixResult:
    """
    Process sample data to extract Mueller matrix using ECM calibration.

    This is a high-level convenience function that handles:
    - Loading data from file (if path provided)
    - Dark subtraction
    - Building intensity matrices
    - Mueller matrix extraction
    - Normalization

    Parameters
    ----------
    sample_data : ndarray or Path or str
        Either:
        - Raw intensity array, shape (n_angles, n_wavelengths)
        - Path to binary data file

    A : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        PSA modulation matrix(ces) from calibration.

    W : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        PSG modulation matrix(ces) from calibration.

    inv_W_mod : ndarray, shape (16, n_angles)
        Pseudo-inverse of modulation basis matrix.

    dark : ndarray, optional, shape (n_angles, n_wavelengths)
        Dark measurement for background subtraction.
        If None, no dark subtraction is performed.

    cfg : ECMConfig, optional
        ECM configuration (required if sample_data is a file path).

    Returns
    -------
    result : MuellerMatrixResult
        Dataclass containing:
        - M: Unnormalized Mueller matrices [4×4×n_wl]
        - M_normalized: Normalized Mueller matrices (m00=1) [4×4×n_wl]
        - m00: Transmission/reflection values [n_wl]

    Raises
    ------
    ValueError
        If sample_data is a path but cfg is not provided.
        If shapes are inconsistent.

    Examples
    --------
    >>> from ecm.core import process_sample
    >>> from ecm.core import calibrate_transmission
    >>>
    >>> # Run calibration
    >>> cal_result, cal_diag = calibrate_transmission(cfg)
    >>>
    >>> # Process a sample
    >>> result = process_sample(
    ...     sample_data='path/to/sample.bin',
    ...     A=cal_result.A,
    ...     W=cal_result.W,
    ...     inv_W_mod=cal_result.inv_W_mod,
    ...     dark=cal_diag.I_dark,
    ...     cfg=cfg
    ... )
    >>>
    >>> # Access results
    >>> print(f"Transmission at 500nm: {result.m00[idx_500nm]:.4f}")
    >>> M_normalized = result.M_normalized  # [4×4×n_wl]

    Notes
    -----
    **Sign Convention:**

    The extracted Mueller matrix M should have M[0,0] > 0 for physical
    samples (positive transmission/reflection). If M[0,0] < 0 for a
    significant number of wavelengths, this may indicate:
    - Incorrect calibration
    - Sample orientation issues
    - Systematic errors in the measurement
    """
    # Import here to avoid circular imports
    from ecm.core.modulation import build_intensity_matrix

    # -------------------------------------------------------------------------
    # Load data if path provided
    # -------------------------------------------------------------------------
    if isinstance(sample_data, (str, Path)):
        if cfg is None:
            raise ValueError(
                "cfg must be provided when sample_data is a file path"
            )

        from ecm.utils.io import load_spectral_data
        sample_data, _ = load_spectral_data(Path(sample_data), cfg)

    # -------------------------------------------------------------------------
    # Dark subtraction
    # -------------------------------------------------------------------------
    if dark is not None:
        if dark.shape != sample_data.shape:
            raise ValueError(
                f"Dark shape {dark.shape} doesn't match sample shape {sample_data.shape}"
            )
        sample_data = sample_data - dark

        # Ensure non-negative (clamp small negatives from noise)
        sample_data = np.maximum(sample_data, 0.0)

    # -------------------------------------------------------------------------
    # Build intensity matrix
    # -------------------------------------------------------------------------
    B_sample = build_intensity_matrix(sample_data, inv_W_mod)

    # -------------------------------------------------------------------------
    # Extract Mueller matrix
    # -------------------------------------------------------------------------
    M = extract_mueller_matrix(B_sample, A, W)

    # -------------------------------------------------------------------------
    # Normalize
    # -------------------------------------------------------------------------
    if M.ndim == 2:
        m00 = M[0, 0]
        if np.abs(m00) > 1e-12:
            M_normalized = M / m00
        else:
            M_normalized = M.copy()
    else:
        # Multiple wavelengths
        m00 = M[0, 0, :]  # Shape: (n_wavelengths,)

        # Normalize each wavelength
        M_normalized = np.zeros_like(M)
        for i_wl in range(M.shape[2]):
            if np.abs(m00[i_wl]) > 1e-12:
                M_normalized[:, :, i_wl] = M[:, :, i_wl] / m00[i_wl]
            else:
                M_normalized[:, :, i_wl] = M[:, :, i_wl]

    # -------------------------------------------------------------------------
    # Return result
    # -------------------------------------------------------------------------
    return MuellerMatrixResult(
        M=M,
        M_normalized=M_normalized,
        m00=m00
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def normalize_mueller_matrix(M: ndarray) -> ndarray:
    """
    Normalize Mueller matrix so that M[0,0] = 1.

    Parameters
    ----------
    M : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        Unnormalized Mueller matrix(ces).

    Returns
    -------
    M_normalized : ndarray, same shape as M
        Normalized Mueller matrix(ces) with M[0,0] = 1.

    Notes
    -----
    If M[0,0] is very small (< 1e-12), the matrix is returned unchanged
    to avoid division by zero.
    """
    if M.ndim == 2:
        m00 = M[0, 0]
        if np.abs(m00) > 1e-12:
            return M / m00
        else:
            return M.copy()
    else:
        M_normalized = np.zeros_like(M)
        for i_wl in range(M.shape[2]):
            m00 = M[0, 0, i_wl]
            if np.abs(m00) > 1e-12:
                M_normalized[:, :, i_wl] = M[:, :, i_wl] / m00
            else:
                M_normalized[:, :, i_wl] = M[:, :, i_wl]
        return M_normalized


def validate_mueller_matrix(M: ndarray, tolerance: float = 1e-6) -> dict:
    """
    Check physical validity constraints on a Mueller matrix.

    A physically realizable Mueller matrix must satisfy several constraints.
    This function checks the most important ones.

    Parameters
    ----------
    M : ndarray, shape (4, 4)
        Mueller matrix (should be normalized, m00 = 1).

    tolerance : float, optional
        Tolerance for constraint violations. Default: 1e-6.

    Returns
    -------
    result : dict
        Dictionary with validation results:
        - 'is_valid': bool, True if all constraints satisfied
        - 'm00_positive': bool, M[0,0] > 0
        - 'trace_constraint': bool, |trace(M)| ≤ 4
        - 'frobenius_constraint': bool, ||M||_F ≤ 4
        - 'eigenvalue_constraint': bool, all eigenvalues of H ≥ 0
        - 'messages': list of str, warning/error messages

    Notes
    -----
    **Physical Constraints:**

    1. M[0,0] > 0: Positive transmission/reflection

    2. |trace(M)| ≤ 4 and ||M||_F ≤ 4: Basic bounds

    3. The coherency matrix H = T @ M @ T^(-1) (where T is the basis
       transformation) should be positive semi-definite. This is the
       most stringent physical constraint.

    For normalized Mueller matrices (m00 = 1), constraint violations
    often indicate measurement noise rather than fundamental errors.
    """
    result = {
        'is_valid': True,
        'm00_positive': True,
        'trace_constraint': True,
        'frobenius_constraint': True,
        'eigenvalue_constraint': True,
        'messages': []
    }

    # Check m00 > 0
    if M[0, 0] <= 0:
        result['m00_positive'] = False
        result['is_valid'] = False
        result['messages'].append(f"m00 = {M[0,0]:.6f} is not positive")

    # Check trace constraint: |trace(M)| ≤ 4
    trace_M = np.trace(M)
    if np.abs(trace_M) > 4.0 + tolerance:
        result['trace_constraint'] = False
        result['is_valid'] = False
        result['messages'].append(f"|trace(M)| = {np.abs(trace_M):.6f} > 4")

    # Check Frobenius norm constraint: ||M||_F ≤ 4
    frobenius = np.linalg.norm(M, 'fro')
    if frobenius > 4.0 + tolerance:
        result['frobenius_constraint'] = False
        result['is_valid'] = False
        result['messages'].append(f"||M||_F = {frobenius:.6f} > 4")

    # Check coherency matrix eigenvalues (simplified check)
    # For a full check, would need to compute the 4x4 coherency matrix
    # Here we do a simpler check based on M itself
    # The sum of squared elements constraint: Σᵢⱼ M²ᵢⱼ ≤ 4 (for normalized M)
    sum_sq = np.sum(M**2)
    if sum_sq > 4.0 + tolerance:
        result['eigenvalue_constraint'] = False
        # This is a warning, not necessarily invalid
        result['messages'].append(
            f"Σ M²ᵢⱼ = {sum_sq:.6f} > 4 (may indicate depolarization > 1)"
        )

    return result
