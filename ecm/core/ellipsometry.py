"""
Ellipsometric Parameter Extraction from Reflection Mueller Matrices

Extracts ellipsometric angles (Ψ, Δ), the complex ellipsometric ratio ρ,
pseudodielectric function ⟨ε⟩, and pseudo optical constants (⟨n⟩, ⟨k⟩) from
normalized Mueller matrices measured in reflection geometry.

Physics
-------
For an isotropic sample, the normalized Mueller matrix m = M/M₁₁ has a
block-diagonal structure. The NCS parameters are:

    N = -m₁₂ = cos(2Ψ)
    C =  m₃₃ = sin(2Ψ)cos(Δ)
    S =  m₃₄ = sin(2Ψ)sin(Δ)

where indices are 0-based: m₁₂ = M[0,1], m₃₃ = M[2,2], m₃₄ = M[2,3].

Ellipsometric angles:
    Ψ = (1/2) arccos(N)    ∈ [0, π/2]
    Δ = atan2(S, C)         ∈ (-π, π]

Complex ellipsometric ratio:
    ρ = tan(Ψ) · exp(iΔ)

Pseudodielectric function (angle of incidence φ):
    ⟨ε⟩ = sin²(φ) [1 + tan²(φ) ((1-ρ)/(1+ρ))²]

Pseudo optical constants:
    ⟨n⟩ + i⟨k⟩ = √⟨ε⟩   (principal square root)

References
----------
[1] Azzam & Bashara, "Ellipsometry and Polarized Light", North-Holland (1987)
[2] Fujiwara, "Spectroscopic Ellipsometry", Wiley (2007), Chapter 4
"""

from dataclasses import dataclass

import numpy as np
from numpy import ndarray


@dataclass
class EllipsometricResult:
    """
    Ellipsometric parameters extracted from reflection Mueller matrices.

    Attributes
    ----------
    psi_deg : ndarray, shape (n_wavelengths,)
        Ellipsometric angle Ψ [degrees].
    delta_deg : ndarray, shape (n_wavelengths,)
        Ellipsometric angle Δ [degrees].
    N : ndarray, shape (n_wavelengths,)
        NCS parameter N = cos(2Ψ).
    C : ndarray, shape (n_wavelengths,)
        NCS parameter C = sin(2Ψ)cos(Δ).
    S : ndarray, shape (n_wavelengths,)
        NCS parameter S = sin(2Ψ)sin(Δ).
    rho : ndarray, shape (n_wavelengths,), complex
        Complex ellipsometric ratio ρ = tan(Ψ)·exp(iΔ).
    pseudo_epsilon : ndarray, shape (n_wavelengths,), complex
        Pseudodielectric function ⟨ε⟩ = ⟨ε₁⟩ + i⟨ε₂⟩.
    pseudo_n : ndarray, shape (n_wavelengths,)
        Pseudo refractive index ⟨n⟩ = Re(√⟨ε⟩).
    pseudo_k : ndarray, shape (n_wavelengths,)
        Pseudo extinction coefficient ⟨k⟩ = Im(√⟨ε⟩).
    aoi_deg : float
        Angle of incidence used for pseudodielectric calculation [degrees].
    """
    psi_deg: ndarray
    delta_deg: ndarray
    N: ndarray
    C: ndarray
    S: ndarray
    rho: ndarray
    pseudo_epsilon: ndarray
    pseudo_n: ndarray
    pseudo_k: ndarray
    aoi_deg: float


def extract_ellipsometric_parameters(
    M_normalized: ndarray,
    aoi_deg: float,
) -> EllipsometricResult:
    """
    Extract ellipsometric parameters from normalized reflection Mueller matrices.

    Parameters
    ----------
    M_normalized : ndarray, shape (4, 4, n_wavelengths)
        Normalized Mueller matrices (M₁₁ = 1 for each wavelength).
    aoi_deg : float
        Angle of incidence [degrees].

    Returns
    -------
    EllipsometricResult
        Dataclass containing all ellipsometric parameters.

    Notes
    -----
    Uses 0-based indexing: m₁₂ = M_normalized[0, 1, :], etc.
    The minus sign in N = -m₁₂ follows the standard ellipsometric convention.
    """
    # -------------------------------------------------------------------------
    # Extract NCS parameters from normalized Mueller matrix (0-based indexing)
    # -------------------------------------------------------------------------
    N = -M_normalized[0, 1, :]    # N = -m₁₂ = cos(2Ψ)
    C = M_normalized[2, 2, :]     # C =  m₃₃ = sin(2Ψ)cos(Δ)
    S = M_normalized[2, 3, :]     # S =  m₃₄ = sin(2Ψ)sin(Δ)

    # -------------------------------------------------------------------------
    # Ellipsometric angles
    # -------------------------------------------------------------------------
    # Clip N to [-1, 1] to handle numerical noise before arccos
    psi_rad = 0.5 * np.arccos(np.clip(N, -1.0, 1.0))   # Ψ ∈ [0, π/2]
    delta_rad = np.arctan2(S, C)                          # Δ ∈ (-π, π]

    psi_deg = np.rad2deg(psi_rad)
    delta_deg = np.rad2deg(delta_rad)

    # -------------------------------------------------------------------------
    # Complex ellipsometric ratio
    # -------------------------------------------------------------------------
    rho = np.tan(psi_rad) * np.exp(1j * delta_rad)

    # -------------------------------------------------------------------------
    # Pseudodielectric function
    #   ⟨ε⟩ = sin²(φ) [1 + tan²(φ) ((1-ρ)/(1+ρ))²]
    # -------------------------------------------------------------------------
    phi = np.deg2rad(aoi_deg)
    sin_phi = np.sin(phi)
    tan_phi = np.tan(phi)

    ratio = (1.0 - rho) / (1.0 + rho)
    pseudo_epsilon = sin_phi**2 * (1.0 + tan_phi**2 * ratio**2)

    # -------------------------------------------------------------------------
    # Pseudo optical constants: ⟨n⟩ + i⟨k⟩ = √⟨ε⟩
    # np.sqrt on complex arrays returns the principal branch (Re ≥ 0)
    # -------------------------------------------------------------------------
    nk_complex = np.sqrt(pseudo_epsilon)
    pseudo_n = nk_complex.real
    pseudo_k = nk_complex.imag

    return EllipsometricResult(
        psi_deg=psi_deg,
        delta_deg=delta_deg,
        N=N,
        C=C,
        S=S,
        rho=rho,
        pseudo_epsilon=pseudo_epsilon,
        pseudo_n=pseudo_n,
        pseudo_k=pseudo_k,
        aoi_deg=aoi_deg,
    )
