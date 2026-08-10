"""
Purity Space Analysis of Mueller Matrices

Computes the degrees of polarimetric purity from normalized Mueller matrices:

    P_P  — Degree of polarizance (from diattenuation and polarizance vectors)
    P_S  — Degree of spherical purity (from 3×3 submatrix)
    P_Δ  — Degree of polarimetric purity (overall measure)

These three quantities parametrize the "purity space" — a bounded 2D region
(P_S, P_P) that classifies the depolarization behavior of optical media.

References
----------
[1] Gil & Ossikovski, "Polarized Light and the Mueller Matrix Approach"
    (2nd ed.), Section 6.2, Eqs. 6.25, 6.71, 6.72.
"""

import numpy as np
from numpy import ndarray
from dataclasses import dataclass

from ecm.postprocessing._validation import validate_mueller_input


@dataclass
class PurityResult:
    """
    Result of purity space analysis.

    Attributes
    ----------
    P_P : ndarray, shape (n_wavelengths,)
        Degree of polarizance.
    P_S : ndarray, shape (n_wavelengths,)
        Degree of spherical purity.
    P_Delta : ndarray, shape (n_wavelengths,)
        Degree of polarimetric purity.
    D_vec : ndarray, shape (3, n_wavelengths)
        Diattenuation vector.
    P_vec : ndarray, shape (3, n_wavelengths)
        Polarizance vector.
    """
    P_P: ndarray
    P_S: ndarray
    P_Delta: ndarray
    D_vec: ndarray
    P_vec: ndarray


def purity_analysis(M_norm: ndarray) -> PurityResult:
    """
    Compute purity space coordinates from normalized Mueller matrices.

    Parameters
    ----------
    M_norm : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        Normalized Mueller matrix(ces). Should have M[0,0] = 1.

    Returns
    -------
    PurityResult

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
    # Extract vectors (0-based indexing)
    # -------------------------------------------------------------------------

    # Diattenuation vector: first row, columns 1-3
    D_vec = M_norm[0, 1:4, :]  # shape (3, n_wl)

    # Polarizance vector: rows 1-3, first column
    P_vec = M_norm[1:4, 0, :]  # shape (3, n_wl)

    # -------------------------------------------------------------------------
    # Degree of polarizance P_P
    # P_P = sqrt((||D||² + ||P||²) / 2)
    # -------------------------------------------------------------------------
    D_norm_sq = np.sum(D_vec**2, axis=0)  # shape (n_wl,)
    P_norm_sq = np.sum(P_vec**2, axis=0)  # shape (n_wl,)
    P_P = np.sqrt((D_norm_sq + P_norm_sq) / 2.0)

    # -------------------------------------------------------------------------
    # Degree of spherical purity P_S
    # P_S = sqrt(||m_sub||_F² / 3)
    # -------------------------------------------------------------------------
    m_sub = M_norm[1:4, 1:4, :]  # shape (3, 3, n_wl)
    m_sub_frob_sq = np.sum(m_sub**2, axis=(0, 1))  # shape (n_wl,)
    P_S = np.sqrt(m_sub_frob_sq / 3.0)

    # -------------------------------------------------------------------------
    # Degree of polarimetric purity P_Delta
    # P_Δ² = (2/3) P_P² + P_S²
    # -------------------------------------------------------------------------
    P_Delta = np.sqrt((2.0 / 3.0) * P_P**2 + P_S**2)

    # -------------------------------------------------------------------------
    # Squeeze if single wavelength
    # -------------------------------------------------------------------------
    if single_wavelength:
        P_P = P_P[0]
        P_S = P_S[0]
        P_Delta = P_Delta[0]
        D_vec = D_vec[:, 0]
        P_vec = P_vec[:, 0]

    return PurityResult(
        P_P=P_P,
        P_S=P_S,
        P_Delta=P_Delta,
        D_vec=D_vec,
        P_vec=P_vec,
    )
