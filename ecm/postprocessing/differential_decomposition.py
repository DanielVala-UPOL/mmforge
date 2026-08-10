"""
Differential Decomposition of Mueller Matrices

Decomposes the matrix logarithm of a Mueller matrix into G-antisymmetric
(polarization) and G-symmetric (depolarization) parts using the Minkowski
metric G = diag(1, -1, -1, -1):

    L = ln(M)
    L_m = (1/2)(L - G @ L^T @ G)    # polarization properties
    L_u = (1/2)(L + G @ L^T @ G)    # depolarization properties
    M_m = expm(L_m)                  # mean nondepolarizing Mueller matrix
    M_u = expm(L_u)                  # depolarization Mueller matrix

References
----------
[1] Gil & Ossikovski, "Polarized Light and the Mueller Matrix Approach"
    (2nd ed.), Section 9.4.1, Eqs. 9.75-9.80.
"""

import numpy as np
from numpy import ndarray
from scipy.linalg import logm, expm
from dataclasses import dataclass
import warnings

from ecm.postprocessing._validation import validate_mueller_input


# Minkowski metric
G = np.diag([1.0, -1.0, -1.0, -1.0])


@dataclass
class DifferentialDecompositionResult:
    """
    Result of differential decomposition of a Mueller matrix.

    Attributes
    ----------
    L_m : ndarray, shape (4, 4, n_wavelengths)
        G-antisymmetric part of matrix logarithm (polarization properties).
        Contains mean values of elementary polarization properties.
    L_u : ndarray, shape (4, 4, n_wavelengths)
        G-symmetric part of matrix logarithm (depolarization properties).
        Contains uncertainties of elementary polarization properties.
    M_m : ndarray, shape (4, 4, n_wavelengths)
        Mean nondepolarizing Mueller matrix: M_m = expm(L_m).
    M_u : ndarray, shape (4, 4, n_wavelengths)
        Depolarization Mueller matrix: M_u = expm(L_u).
        This is a generalized depolarizer (G-symmetric Mueller matrix).
    """
    L_m: ndarray
    L_u: ndarray
    M_m: ndarray
    M_u: ndarray


def differential_decomposition(M_norm: ndarray) -> DifferentialDecompositionResult:
    """
    Perform differential decomposition of Mueller matrix.

    Decomposes the matrix logarithm L = ln(M) into G-antisymmetric
    (polarization) and G-symmetric (depolarization) parts using the
    Minkowski metric G = diag(1, -1, -1, -1).

    Reference: Gil & Ossikovski, Section 9.4.1

    Parameters
    ----------
    M_norm : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        Normalized Mueller matrix(ces). Must be nonsingular.

    Returns
    -------
    DifferentialDecompositionResult

    Raises
    ------
    ValueError
        If input shape is not (4, 4) or (4, 4, n_wavelengths).
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    M_norm, single_wavelength = validate_mueller_input(M_norm)
    n_wl = M_norm.shape[2]

    # -------------------------------------------------------------------------
    # Pre-allocate outputs
    # -------------------------------------------------------------------------
    L_m = np.full((4, 4, n_wl), np.nan, dtype=np.float64)
    L_u = np.full((4, 4, n_wl), np.nan, dtype=np.float64)
    M_m = np.full((4, 4, n_wl), np.nan, dtype=np.float64)
    M_u = np.full((4, 4, n_wl), np.nan, dtype=np.float64)

    # -------------------------------------------------------------------------
    # Process each wavelength
    # -------------------------------------------------------------------------
    for k in range(n_wl):
        M = M_norm[:, :, k]

        # Check nonsingularity
        det_M = np.linalg.det(M)
        if np.abs(det_M) < 1e-15:
            warnings.warn(
                f"Singular Mueller matrix at wavelength index {k} "
                f"(det = {det_M:.2e}). Skipping (filled with NaN).",
                UserWarning
            )
            continue

        # Matrix logarithm
        L = logm(M)

        # Handle complex results (silently take real part)
        if np.iscomplexobj(L):
            L = L.real

        # G-antisymmetric part (polarization)
        L_m_k = 0.5 * (L - G @ L.T @ G)

        # G-symmetric part (depolarization)
        L_u_k = 0.5 * (L + G @ L.T @ G)

        # Reconstruct Mueller matrices
        M_m_k = expm(L_m_k)
        M_u_k = expm(L_u_k)

        # Handle any residual imaginary parts from expm
        L_m[:, :, k] = np.real(L_m_k)
        L_u[:, :, k] = np.real(L_u_k)
        M_m[:, :, k] = np.real(M_m_k)
        M_u[:, :, k] = np.real(M_u_k)

    # -------------------------------------------------------------------------
    # Remove wavelength dimension if single input
    # -------------------------------------------------------------------------
    if single_wavelength:
        L_m = L_m[:, :, 0]
        L_u = L_u[:, :, 0]
        M_m = M_m[:, :, 0]
        M_u = M_u[:, :, 0]

    return DifferentialDecompositionResult(
        L_m=L_m,
        L_u=L_u,
        M_m=M_m,
        M_u=M_u,
    )
