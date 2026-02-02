"""
Lu-Chipman Polar Decomposition

Decomposes a Mueller matrix into physically meaningful components:
    M = M_Δ · M_R · M_D

where:
    M_D  - Diattenuator (first in optical path)
    M_R  - Retarder (middle)
    M_Δ  - Depolarizer (last in optical path)

Theory
------
The Lu-Chipman decomposition (1996) factors any physically realizable
Mueller matrix into a product of three canonical forms. The decomposition
proceeds:

1. Extract diattenuation vector d from first row of M
2. Construct M_D and compute M' = M · M_D⁻¹
3. Extract rotation matrix from polar decomposition of M'(1:3,1:3) submatrix
4. Compute M_Δ = M · (M_R · M_D)⁻¹

Key Parameters
--------------
D : float
    Net diattenuation magnitude, range [0, 1].
    D = 0: No diattenuation (equal transmission for all polarizations)
    D = 1: Ideal polarizer (only one polarization transmitted)

R : float
    Net retardance in radians, range [0, π].
    R = 0: No retardation
    R = π/2: Quarter-wave plate (QWP)
    R = π: Half-wave plate (HWP)

DI : float
    Depolarization Index, range [0, 1].
    DI = 0: Total depolarization
    DI = 1: Non-depolarizing (ideal optical element)

ψ : float
    Retarder fast-axis azimuth angle.

χ : float
    Retarder ellipticity angle.
    χ = 0: Linear retarder
    |χ| = π/4: Circular retarder

References
----------
[1] Lu & Chipman, "Interpretation of Mueller matrices based on polar
    decomposition", J. Opt. Soc. Am. A 13, 1106-1113 (1996)
[2] Chipman et al., "Polarized Light and Optical Systems" (2018)
"""

import numpy as np
from numpy import ndarray
from dataclasses import dataclass
from typing import Tuple
import warnings


# =============================================================================
# DATA CLASS
# =============================================================================

@dataclass
class LuChipmanResult:
    """
    Result of Lu-Chipman polar decomposition.

    The decomposition factors a Mueller matrix as:
        M = M_Δ · M_R · M_D

    Attributes
    ----------
    M_D : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        Diattenuator Mueller matrices.

    M_R : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        Retarder Mueller matrices.

    M_Delta : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        Depolarizer Mueller matrices.

    D : ndarray, shape (n_wavelengths,)
        Net diattenuation magnitude, range [0, 1].
        Measures the differential transmission of orthogonal polarizations.

    R_rad : ndarray, shape (n_wavelengths,)
        Net retardance in radians, range [0, π].
        Phase difference between fast and slow eigenpolarizations.

    R_deg : ndarray, shape (n_wavelengths,)
        Net retardance in degrees.

    R_waves : ndarray, shape (n_wavelengths,)
        Net retardance in waves (1 wave = 360°).
        QWP ≈ 0.25 waves, HWP ≈ 0.5 waves.

    DI : ndarray, shape (n_wavelengths,)
        Depolarization Index, range [0, 1].
        DI = 1 for non-depolarizing elements.

    psi_deg : ndarray, shape (n_wavelengths,)
        Retarder fast-axis azimuth in degrees, range [-90°, 90°].

    chi_deg : ndarray, shape (n_wavelengths,)
        Retarder ellipticity angle in degrees, range [-45°, 45°].
        χ = 0° for linear retarders.

    Notes
    -----
    **Diattenuation Vector:**

    The diattenuation vector d = [d₁, d₂, d₃] is extracted from the first
    row of the Mueller matrix. Its magnitude D = |d| represents the net
    diattenuation, and its direction encodes the type of diattenuation:

    - d ∝ [1, 0, 0]: Horizontal/vertical linear diattenuation
    - d ∝ [0, 1, 0]: ±45° linear diattenuation
    - d ∝ [0, 0, 1]: Circular diattenuation

    **Retardance Axis:**

    The retardance axis on the Poincaré sphere is:
        r = [cos(2ψ)cos(2χ), sin(2ψ)cos(2χ), sin(2χ)]

    For linear retarders (χ = 0), ψ gives the fast-axis orientation.
    """
    M_D: ndarray
    M_R: ndarray
    M_Delta: ndarray
    D: ndarray
    R_rad: ndarray
    R_deg: ndarray
    R_waves: ndarray
    DI: ndarray
    psi_deg: ndarray
    chi_deg: ndarray


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def lu_chipman_decomposition(M_norm: ndarray) -> LuChipmanResult:
    """
    Perform Lu-Chipman polar decomposition of Mueller matrix.

    Decomposes a normalized Mueller matrix into diattenuation, retardation,
    and depolarization components:

        M = M_Δ · M_R · M_D

    Reference: Lu & Chipman, J. Opt. Soc. Am. A 13, 1106-1113 (1996)

    Parameters
    ----------
    M_norm : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        Normalized Mueller matrix(ces). Should have M[0,0] = 1.
        For multi-wavelength input, wavelength varies along axis 2.

    Returns
    -------
    result : LuChipmanResult
        Decomposed matrices and extracted parameters.

    Raises
    ------
    ValueError
        If input shape is not (4, 4) or (4, 4, n_wavelengths).

    Warns
    -----
    UserWarning
        If M[0,0] deviates significantly from 1.0 (unnormalized input).

    Examples
    --------
    >>> import numpy as np
    >>> from ecm.postprocessing import lu_chipman_decomposition
    >>> from ecm.utils.mueller_matrices import retarder
    >>>
    >>> # Create a QWP Mueller matrix
    >>> M_qwp = retarder(theta=0, delta=np.pi/2, tau=1.0)
    >>> result = lu_chipman_decomposition(M_qwp)
    >>> print(f"Retardance: {result.R_deg[0]:.1f}°")
    Retardance: 90.0°
    >>> print(f"Diattenuation: {result.D[0]:.4f}")
    Diattenuation: 0.0000

    Notes
    -----
    **Algorithm:**

    1. **Extract Diattenuator M_D:**
       The diattenuation vector d = M[0, 1:4] / M[0,0] encodes the
       differential transmission. M_D is constructed from d.

    2. **Remove Diattenuation:**
       Compute M' = M @ M_D⁻¹ to isolate retardation and depolarization.

    3. **Extract Retarder M_R via Polar Decomposition:**
       The 3×3 submatrix of M' contains both rotation (retardation) and
       scaling (depolarization). SVD extracts the rotation component.

    4. **Compute Depolarizer:**
       M_Δ = M @ (M_R @ M_D)⁻¹

    **Numerical Considerations:**

    - Very small diattenuation (D < 1e-12) is treated as zero to avoid
      division instabilities.
    - Very small retardance (sin(R) < 1e-10) leads to undefined axis
      parameters (returned as NaN).
    - The SVD-based rotation extraction ensures det(M_R) = +1 (proper rotation).
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    M_norm = np.asarray(M_norm, dtype=np.float64)

    if M_norm.ndim == 2:
        if M_norm.shape != (4, 4):
            raise ValueError(
                f"M_norm must be 4×4 or 4×4×n_wavelengths, got shape {M_norm.shape}"
            )
        # Reshape to 3D for uniform processing
        M_norm = M_norm[:, :, np.newaxis]
        single_wavelength = True
    elif M_norm.ndim == 3:
        if M_norm.shape[:2] != (4, 4):
            raise ValueError(
                f"M_norm must be 4×4 or 4×4×n_wavelengths, got shape {M_norm.shape}"
            )
        single_wavelength = False
    else:
        raise ValueError(
            f"M_norm must be 4×4 or 4×4×n_wavelengths, got {M_norm.ndim}D array"
        )

    n_wl = M_norm.shape[2]

    # -------------------------------------------------------------------------
    # Pre-allocate outputs
    # -------------------------------------------------------------------------
    M_D = np.zeros((4, 4, n_wl), dtype=np.float64)
    M_R = np.zeros((4, 4, n_wl), dtype=np.float64)
    M_Delta = np.zeros((4, 4, n_wl), dtype=np.float64)

    D = np.zeros(n_wl, dtype=np.float64)
    R_rad = np.zeros(n_wl, dtype=np.float64)
    DI = np.zeros(n_wl, dtype=np.float64)
    psi_deg = np.zeros(n_wl, dtype=np.float64)
    chi_deg = np.zeros(n_wl, dtype=np.float64)

    # -------------------------------------------------------------------------
    # Process each wavelength
    # -------------------------------------------------------------------------
    for k in range(n_wl):
        # Use real values only (discard any numerical imaginary components)
        M = np.real(M_norm[:, :, k])

        # Check normalization
        if np.abs(M[0, 0] - 1.0) > 0.01:
            warnings.warn(
                f"M[0,0] = {M[0,0]:.4f} at wavelength index {k}. "
                f"Expected 1.0 for normalized Mueller matrix. Renormalizing.",
                UserWarning
            )
            if np.abs(M[0, 0]) > 1e-12:
                M = M / M[0, 0]

        # ---------------------------------------------------------------------
        # Step 1: Extract Diattenuator M_D
        #
        # Diattenuation vector from first row: d = M[0, 1:4]
        # (assuming M[0,0] = 1 after normalization)
        # ---------------------------------------------------------------------
        d = M[0, 1:4].copy()  # Diattenuation vector [3]
        D_mag = np.linalg.norm(d)

        # Clamp to physical range [0, 1)
        D_mag = np.clip(D_mag, 0.0, 1.0 - 1e-12)
        D[k] = D_mag

        # Build diattenuator Mueller matrix
        # Reference: Lu & Chipman (1996), Eq. 9-11
        M_D_k = np.eye(4)
        M_D_k[0, 1:4] = d
        M_D_k[1:4, 0] = d

        if D_mag > 1e-12:
            d_hat = d / D_mag  # Unit diattenuation vector
            c = np.sqrt(1.0 - D_mag**2)
            # 3×3 submatrix: c·I + (1-c)·d̂d̂ᵀ
            M_D_k[1:4, 1:4] = c * np.eye(3) + (1.0 - c) * np.outer(d_hat, d_hat)
        else:
            M_D_k[1:4, 1:4] = np.eye(3)

        M_D[:, :, k] = M_D_k

        # ---------------------------------------------------------------------
        # Step 2: Remove diattenuation to get M' = M @ M_D⁻¹
        # ---------------------------------------------------------------------
        try:
            M_prime = M @ np.linalg.inv(M_D_k)
        except np.linalg.LinAlgError:
            # Fallback if M_D is singular (shouldn't happen for D < 1)
            M_prime = M.copy()

        # ---------------------------------------------------------------------
        # Step 3: Extract Retarder M_R via polar decomposition
        #
        # The 3×3 submatrix of M' contains rotation (from retarder) and
        # scaling (from depolarizer). Extract rotation via SVD.
        # ---------------------------------------------------------------------
        A = M_prime[1:4, 1:4]

        # SVD: A = U @ S @ V^T
        # Rotation: R = U @ V^T
        U, S, Vt = np.linalg.svd(A)
        R3 = U @ Vt

        # Ensure proper rotation (det = +1)
        if np.linalg.det(R3) < 0:
            U[:, 2] = -U[:, 2]
            R3 = U @ Vt

        # Build retarder Mueller matrix (rotation on Poincaré sphere)
        M_R_k = np.eye(4)
        M_R_k[1:4, 1:4] = R3
        M_R[:, :, k] = M_R_k

        # ---------------------------------------------------------------------
        # Step 4: Compute Depolarizer M_Δ = M @ (M_R @ M_D)⁻¹
        # ---------------------------------------------------------------------
        try:
            M_Delta_k = M @ np.linalg.inv(M_R_k @ M_D_k)
        except np.linalg.LinAlgError:
            M_Delta_k = np.eye(4)
        M_Delta[:, :, k] = M_Delta_k

        # ---------------------------------------------------------------------
        # Step 5: Extract retardance parameters from M_R
        # ---------------------------------------------------------------------
        R_k, psi_k, chi_k = _extract_retardance_params(M_R_k)
        R_rad[k] = R_k
        psi_deg[k] = psi_k
        chi_deg[k] = chi_k

        # ---------------------------------------------------------------------
        # Step 6: Compute Depolarization Index
        #
        # DI = √(Σᵢⱼ Mᵢⱼ² - M₀₀²) / √3
        #
        # For normalized M (M[0,0] = 1):
        #   DI = √(Σᵢⱼ mᵢⱼ² - 1) / √3
        #
        # Range: [0, 1]
        #   DI = 0: Total depolarization
        #   DI = 1: Non-depolarizing (preserves degree of polarization)
        # ---------------------------------------------------------------------
        sum_sq = np.sum(M**2)
        DI_k = np.sqrt(max(0.0, sum_sq - 1.0)) / np.sqrt(3.0)
        DI[k] = np.clip(DI_k, 0.0, 1.0)

    # -------------------------------------------------------------------------
    # Compute derived quantities
    # -------------------------------------------------------------------------
    R_deg = np.rad2deg(R_rad)
    R_waves = R_deg / 360.0

    # -------------------------------------------------------------------------
    # Remove wavelength dimension if single input
    # -------------------------------------------------------------------------
    if single_wavelength:
        M_D = M_D[:, :, 0]
        M_R = M_R[:, :, 0]
        M_Delta = M_Delta[:, :, 0]

    return LuChipmanResult(
        M_D=M_D,
        M_R=M_R,
        M_Delta=M_Delta,
        D=D,
        R_rad=R_rad,
        R_deg=R_deg,
        R_waves=R_waves,
        DI=DI,
        psi_deg=psi_deg,
        chi_deg=chi_deg
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _extract_retardance_params(M_R: ndarray) -> Tuple[float, float, float]:
    """
    Extract retardance parameters from retarder Mueller matrix.

    The retarder Mueller matrix represents a rotation on the Poincaré sphere.
    The rotation angle is the retardance Δ, and the rotation axis encodes
    the fast-axis orientation (ψ) and ellipticity (χ).

    Parameters
    ----------
    M_R : ndarray, shape (4, 4)
        Retarder Mueller matrix from polar decomposition.

    Returns
    -------
    Delta : float
        Net retardance in radians, range [0, π].

    psi_deg : float
        Fast-axis azimuth in degrees.
        NaN if retardance is near zero (axis undefined).

    chi_deg : float
        Ellipticity angle in degrees.
        NaN if retardance is near zero (axis undefined).

    Notes
    -----
    **Retardance from Trace:**

    For a 3×3 rotation matrix R, the trace is:
        tr(R) = 1 + 2·cos(Δ)

    Therefore:
        Δ = arccos((tr(R) - 1) / 2)

    **Rotation Axis:**

    The rotation axis unit vector u on the Poincaré sphere is extracted
    from the antisymmetric part of R:
        u = [R₃₂ - R₂₃, R₁₃ - R₃₁, R₂₁ - R₁₂] / (2·sin(Δ))

    **Mapping to Physical Angles:**

    The Poincaré sphere axis maps to physical angles:
        u = [cos(2ψ)·cos(2χ), sin(2ψ)·cos(2χ), sin(2χ)]

    Therefore:
        2χ = arcsin(u₃)
        2ψ = atan2(u₂, u₁)
    """
    R3 = M_R[1:4, 1:4]  # 3×3 rotation submatrix

    # -------------------------------------------------------------------------
    # Retardance from trace: tr(R3) = 1 + 2·cos(Δ)
    # -------------------------------------------------------------------------
    tr = np.trace(R3)
    # Clamp for numerical safety
    tr = np.clip(tr, -1.0, 3.0)

    cos_Delta = (tr - 1.0) / 2.0
    cos_Delta = np.clip(cos_Delta, -1.0, 1.0)
    Delta = np.arccos(cos_Delta)  # Range [0, π]

    sin_Delta = np.sin(Delta)

    # -------------------------------------------------------------------------
    # Rotation axis (if retardance is significant)
    # -------------------------------------------------------------------------
    if sin_Delta < 1e-10:
        # Near-zero retardance: axis is undefined
        return float(Delta), np.nan, np.nan

    # Extract rotation axis from antisymmetric part
    # u = (R - R^T) / (2·sin(Δ)) gives the axis scaled by sin(Δ)
    u = np.array([
        R3[2, 1] - R3[1, 2],  # u₁
        R3[0, 2] - R3[2, 0],  # u₂
        R3[1, 0] - R3[0, 1],  # u₃
    ]) / (2.0 * sin_Delta)

    # Normalize for numerical stability
    u_norm = np.linalg.norm(u)
    if u_norm > 0:
        u = u / u_norm

    # -------------------------------------------------------------------------
    # Map Poincaré sphere axis to physical angles (ψ, χ)
    #
    # u = [cos(2ψ)·cos(2χ), sin(2ψ)·cos(2χ), sin(2χ)]
    # -------------------------------------------------------------------------

    # Ellipticity angle from u₃
    two_chi = np.arcsin(np.clip(u[2], -1.0, 1.0))
    chi = 0.5 * two_chi

    # Azimuth angle from u₁ and u₂
    two_psi = np.arctan2(u[1], u[0])
    psi = 0.5 * two_psi

    psi_deg = np.rad2deg(psi)
    chi_deg = np.rad2deg(chi)

    return float(Delta), float(psi_deg), float(chi_deg)
