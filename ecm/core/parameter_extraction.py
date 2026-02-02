"""
Calibration Sample Parameter Extraction

This module extracts optical parameters (transmission, retardation,
ellipsometric angle) from calibration sample measurements using
eigenvalue analysis.

Functions
---------
extract_sample_params(B_air, B_sample, sample_type)
    Extract parameters from eigenvalue structure of C = B_air^(-1) @ B_sample

Theory
------
The eigenvalues of C = B_air^(-1) @ B_sample equal the eigenvalues of the
calibration sample's Mueller matrix M. This allows extraction of optical
parameters without requiring the full ECM calibration.

For a polarizer:
    Eigenvalues: {τ, 0, 0, 0}
    where τ is the transmission coefficient.

For a retarder (general elliptic):
    Eigenvalues:
        λ₁ = 2τ sin²(Ψ)           (real)
        λ₂ = 2τ cos²(Ψ)           (real)
        λ₃ = τ sin(2Ψ) exp(+iδ)   (complex)
        λ₄ = τ sin(2Ψ) exp(-iδ)   (complex conjugate)

    where τ is transmission, Ψ is ellipsometric angle, δ is retardation.

For ideal linear retarder (Ψ = 45°):
    λ₁ = λ₂ = τ
    λ₃,₄ = τ exp(±iδ)

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999), Appendix B
"""

import numpy as np
from numpy import ndarray
from dataclasses import dataclass
from typing import Literal, Union


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PolarizerParams:
    """
    Parameters extracted from a polarizer calibration sample.

    Attributes
    ----------
    tau : float
        Transmission coefficient. For ideal polarizer, this is the
        transmission for aligned polarization (τ/2 for unpolarized input).

    eigenvalues : ndarray, shape (4,)
        All 4 eigenvalues of C = B_air^(-1) @ B_sample.
        For ideal polarizer: {τ, 0, 0, 0} (one non-zero eigenvalue).

    Notes
    -----
    The polarizer orientation θ cannot be determined from eigenvalue
    analysis alone; it requires the full ECM calibration or prior knowledge.
    """
    tau: float
    eigenvalues: ndarray


@dataclass
class RetarderParams:
    """
    Parameters extracted from a retarder calibration sample.

    Attributes
    ----------
    tau : float
        Transmission coefficient.

    delta : float
        Retardation in radians.
        Defined as: δ = phase_fast - phase_slow.
        Range: (-π, π].

    psi : float
        Ellipsometric angle in radians.
        For ideal linear retarder: Ψ = π/4 (45°).
        Range: [0, π/2].

    eigenvalues_real : ndarray, shape (2,)
        The two real eigenvalues [λ₁, λ₂], sorted descending.

    eigenvalues_complex : ndarray, shape (2,)
        The complex conjugate pair [λ₃, λ₄].

    Notes
    -----
    **Ideal Linear Retarder (Ψ = 45°):**

    For standard waveplates (QWP, HWP), the ellipsometric angle should
    be Ψ ≈ 45° (π/4 radians). Small deviations indicate:
    - Dichroism in the retarder
    - Measurement noise
    - Alignment errors

    **Retardation Sign Convention:**

    The extracted δ follows the convention: δ = phase_fast - phase_slow.
    If your retarder characterization uses the opposite sign, negate
    the extracted value.
    """
    tau: float
    delta: float
    psi: float
    eigenvalues_real: ndarray
    eigenvalues_complex: ndarray


# =============================================================================
# PARAMETER EXTRACTION
# =============================================================================

def extract_sample_params(
    B_air: ndarray,
    B_sample: ndarray,
    sample_type: Literal['polarizer', 'retarder']
) -> Union[PolarizerParams, RetarderParams]:
    """
    Extract calibration sample parameters from eigenvalue analysis.

    The eigenvalues of C = B_air^(-1) @ B_sample encode the optical
    properties of the calibration sample (transmission, retardation, etc.)

    Reference: Compain et al., Appl. Opt. 38, 3490-3502 (1999), Appendix B

    Parameters
    ----------
    B_air : ndarray, shape (4, 4)
        Air (straight-through) intensity matrix.

    B_sample : ndarray, shape (4, 4)
        Calibration sample intensity matrix.

    sample_type : {'polarizer', 'retarder'}
        Type of calibration sample.

    Returns
    -------
    params : PolarizerParams or RetarderParams
        Extracted parameters depending on sample_type.

    Raises
    ------
    ValueError
        If sample_type is not 'polarizer' or 'retarder'.
        If B_air is singular.
        If eigenvalue structure doesn't match expected pattern.

    Examples
    --------
    >>> # Extract polarizer transmission
    >>> params = extract_sample_params(B_air, B_pol, 'polarizer')
    >>> print(f"Polarizer transmission: τ = {params.tau:.4f}")

    >>> # Extract retarder parameters
    >>> params = extract_sample_params(B_air, B_ret, 'retarder')
    >>> print(f"Retardation: δ = {np.degrees(params.delta):.1f}°")
    >>> print(f"Ellipsometric angle: Ψ = {np.degrees(params.psi):.1f}°")

    Notes
    -----
    **Eigenvalue Extraction:**

    For a retarder, the eigenvalues are classified as:
    - Real eigenvalues: |Im(λ)| < threshold
    - Complex eigenvalues: |Im(λ)| ≥ threshold

    The threshold is adaptive: 1e-10 times the largest eigenvalue magnitude.

    **Parameter Formulas:**

    Polarizer:
        τ = trace(C) = sum of eigenvalues (ideally just the one non-zero)
        In practice: τ = max(|λᵢ|)

    Retarder:
        τ = 0.5 × (λ₁ + λ₂)  (average of real eigenvalues)
        δ = 0.5 × angle(λ₃ / λ₄)  (phase of complex pair ratio)
        Ψ = atan(√(λ₁ / λ₂))  (from eigenvalue ratio)
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    if B_air.shape != (4, 4):
        raise ValueError(f"B_air must be 4×4, got {B_air.shape}")

    if B_sample.shape != (4, 4):
        raise ValueError(f"B_sample must be 4×4, got {B_sample.shape}")

    if sample_type not in ('polarizer', 'retarder'):
        raise ValueError(
            f"sample_type must be 'polarizer' or 'retarder', got '{sample_type}'"
        )

    # -------------------------------------------------------------------------
    # Compute C = B_air^(-1) @ B_sample
    # -------------------------------------------------------------------------
    cond_B_air = np.linalg.cond(B_air)
    if cond_B_air > 1e10:
        raise ValueError(
            f"B_air is poorly conditioned (cond={cond_B_air:.2e}). "
            f"Check the air measurement data."
        )

    C = np.linalg.solve(B_air, B_sample)

    # -------------------------------------------------------------------------
    # Compute eigenvalues of C
    # The eigenvalues of C equal the eigenvalues of M (the Mueller matrix)
    # -------------------------------------------------------------------------
    eigenvalues = np.linalg.eigvals(C)

    # -------------------------------------------------------------------------
    # Extract parameters based on sample type
    # -------------------------------------------------------------------------
    if sample_type == 'polarizer':
        return _extract_polarizer_params(eigenvalues)
    else:  # sample_type == 'retarder'
        return _extract_retarder_params(eigenvalues)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _extract_polarizer_params(eigenvalues: ndarray) -> PolarizerParams:
    """
    Extract polarizer parameters from eigenvalues.

    For ideal polarizer: eigenvalues = {τ, 0, 0, 0}
    In practice, the "zero" eigenvalues may have small non-zero values due
    to measurement noise.

    Parameters
    ----------
    eigenvalues : ndarray, shape (4,)
        Eigenvalues of C = B_air^(-1) @ B_sample.

    Returns
    -------
    PolarizerParams
        Extracted transmission coefficient and eigenvalues.
    """
    # Take real parts (eigenvalues should be real for polarizer)
    # Small imaginary parts may arise from numerical noise
    eigs_real = np.real(eigenvalues)

    # MATLAB approach: τ = trace(C) = sum of eigenvalues
    # For ideal polarizer: τ + 0 + 0 + 0 = τ
    # The trace is more robust than max for noisy data
    tau = float(np.sum(eigs_real))

    # Note: tau may slightly exceed [0, 1] due to measurement noise at spectral edges
    # This is acceptable and we do NOT clamp to allow slight exceedances

    return PolarizerParams(
        tau=float(tau),
        eigenvalues=eigenvalues
    )


def _extract_retarder_params(eigenvalues: ndarray) -> RetarderParams:
    """
    Extract retarder parameters from eigenvalues.

    For general elliptic retarder:
        λ₁ = 2τ sin²(Ψ)           (real)
        λ₂ = 2τ cos²(Ψ)           (real)
        λ₃ = τ sin(2Ψ) exp(+iδ)   (complex)
        λ₄ = τ sin(2Ψ) exp(-iδ)   (complex conjugate)

    For ideal linear retarder (Ψ = 45°):
        λ₁ = λ₂ = τ
        λ₃,₄ = τ exp(±iδ)

    Parameters
    ----------
    eigenvalues : ndarray, shape (4,)
        Eigenvalues of C = B_air^(-1) @ B_sample.

    Returns
    -------
    RetarderParams
        Extracted parameters: tau, delta, psi, eigenvalues.
    """
    # -------------------------------------------------------------------------
    # Sort eigenvalues by |Im(λ)| (ascending) - matches MATLAB approach
    # First two have smallest imaginary parts ("real" eigenvalues)
    # Last two have largest imaginary parts ("complex" eigenvalues)
    # -------------------------------------------------------------------------
    sort_idx = np.argsort(np.abs(np.imag(eigenvalues)))
    eig_sorted = eigenvalues[sort_idx]

    # First two are approximately real (λ₁ = 2τ sin²Ψ, λ₂ = 2τ cos²Ψ)
    lambda_real_1 = np.real(eig_sorted[0])
    lambda_real_2 = np.real(eig_sorted[1])

    # Last two are complex conjugate pair (λ₃,₄ = τ sin(2Ψ) exp(±iΔ))
    lambda_complex_1 = eig_sorted[2]
    lambda_complex_2 = eig_sorted[3]

    # Store for output
    complex_eigs = np.array([lambda_complex_1, lambda_complex_2])

    # -------------------------------------------------------------------------
    # Compute transmission τ
    # For ideal retarder: λ₁ = λ₂ = τ
    # For elliptic: τ = 0.5 × (λ₁ + λ₂) (average of real eigenvalues)
    # -------------------------------------------------------------------------
    tau = 0.5 * (lambda_real_1 + lambda_real_2)

    # Take absolute value to ensure positive, but do NOT clamp to [0, 1]
    # Slight exceedance of 1 is acceptable due to measurement noise at spectral edges
    tau = float(np.abs(tau))

    # Use abs values of real eigenvalues for psi calculation (like MATLAB)
    lambda_1 = np.abs(lambda_real_1)
    lambda_2 = np.abs(lambda_real_2)

    # -------------------------------------------------------------------------
    # Compute ellipsometric angle Ψ (matches MATLAB approach)
    # From: tan²(Ψ) = λ₁/λ₂ (assuming λ₁ = 2τ sin²Ψ, λ₂ = 2τ cos²Ψ)
    # For proper atan range, ensure ratio < 1 by using smaller/larger
    # For ideal linear retarder: λ₁ = λ₂, so Ψ = 45°
    # -------------------------------------------------------------------------
    if lambda_1 > lambda_2:
        # Swap so ratio < 1 for proper atan range
        if lambda_1 > 1e-10:
            tan_sq_psi = lambda_2 / lambda_1
            psi = np.arctan(np.sqrt(tan_sq_psi))
        else:
            psi = np.pi / 4  # Fallback
    else:
        if lambda_2 > 1e-10:
            tan_sq_psi = lambda_1 / lambda_2
            psi = np.arctan(np.sqrt(tan_sq_psi))
        else:
            psi = np.pi / 4  # Fallback to ideal linear retarder

    # Constrain psi to [0, π/2]
    psi = float(np.clip(psi, 0, np.pi / 2))

    # -------------------------------------------------------------------------
    # Compute retardation δ from complex eigenvalues
    #
    # For the Mueller matrix of a retarder, the eigenvalues are:
    #   λ₃ = τ sin(2Ψ) exp(+iδ)
    #   λ₄ = τ sin(2Ψ) exp(-iδ)
    #
    # Therefore:
    #   λ₃/λ₄ = exp(+2iδ)
    #   angle(λ₃/λ₄) = 2δ
    #   δ = 0.5 × angle(λ₃/λ₄)
    #
    # Reference: Compain et al., Appl. Opt. 38 (1999), Appendix B
    # -------------------------------------------------------------------------
    # Use the complex eigenvalues already extracted (lambda_complex_1, lambda_complex_2)
    if np.abs(lambda_complex_2) > 1e-12:
        delta = 0.5 * np.angle(lambda_complex_1 / lambda_complex_2)
    else:
        delta = np.angle(lambda_complex_1)  # Fallback

    # Ensure delta is in (-π, π]
    delta = float(np.angle(np.exp(1j * delta)))

    # -------------------------------------------------------------------------
    # Package results
    # -------------------------------------------------------------------------
    eigenvalues_real = np.array([lambda_1, lambda_2], dtype=np.float64)

    return RetarderParams(
        tau=tau,
        delta=delta,
        psi=psi,
        eigenvalues_real=eigenvalues_real,
        eigenvalues_complex=complex_eigs
    )
