"""
ECM Reflection Mode Calibration

This module provides the main orchestration function for performing a complete
ECM calibration in reflection mode. It integrates all the core ECM functions
to produce calibrated PSG (W) and PSA (A) matrices using calibration wafer standards.

Functions
---------
calibrate_reflection(cfg)
    Perform complete ECM calibration in reflection mode

Theory
------
In reflection mode, there is no straight-through (air) path. Instead, a
wafer with known optical properties serves as the reference measurement.

**Calibration Measurements (Reflection Mode):**
1. Wafer 25 nm (bare): Reference measurement, B_ref = A · M_R1 · W
2. Wafer 25 nm + polarizer before: B = A · (M_R1 · M_pol) · W
3. Wafer 25 nm + polarizer after:  B = A · (M_pol · M_R1) · W
4. Wafer 10 nm (bare):             B = A · M_R2 · W

**ECM Constraints (Mueller matrix ratios relative to wafer 25 nm):**
1. Pol before:  M_ratio = M_pol(45°)
2. Pol after:   M_ratio = M_R1⁻¹ · M_pol(45°) · M_R1
3. Wafer 10 nm: M_ratio = M_R1⁻¹ · M_R2

**A Recovery:**
    A = B_ref · (M_R1 · W)⁻¹

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999)
"""

import warnings
import numpy as np
from numpy import ndarray
import scipy.linalg
from scipy.interpolate import PchipInterpolator
from scipy.optimize import minimize, minimize_scalar, differential_evolution
from dataclasses import dataclass, field
from typing import Tuple, Optional, Callable, Dict, Any, TYPE_CHECKING
from pathlib import Path
from tqdm import tqdm

if TYPE_CHECKING:
    from ecm.config.ecm_config import ECMConfig

# Local imports
from ecm.core.file_discovery import (
    discover_reflection_calibration_files,
    ReflectionCalibrationFiles,
    CalibrationFiles,
)
from ecm.core.modulation import build_modulation_basis, build_intensity_matrix
from ecm.core.ecm_matrices import build_H_matrix, build_K_matrix, compute_kron_C_matrix
from ecm.core.ecm_solver import solve_W, solve_A_reflection
from ecm.utils.io import load_spectral_data, load_wavelengths, detect_angular_positions
from ecm.utils.mueller_matrices import polarizer, reflector
from ecm.core.transmission_calibration import (
    CalibrationResult,
    RetarderCalibrationParams,
)
from ecm.utils.terminal_colors import bold, green, yellow, red, cyan, dim


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ReflectionCalibrationDiagnostics:
    """
    Diagnostic information from reflection calibration process.

    Attributes
    ----------
    eigenvalue_ratio : ndarray, shape (n_wavelengths,)
        Quality metric at each wavelength (λ₁₆/λ₁₅).

    cond_W : ndarray, shape (n_wavelengths,)
        Condition number of W at each wavelength.

    cond_A : ndarray, shape (n_wavelengths,)
        Condition number of A at each wavelength.

    B_ref1 : ndarray, shape (4, 4, n_wavelengths)
        Wafer 25 nm intensity matrices.

    B_pol_before : ndarray, shape (4, 4, n_wavelengths)
        Wafer 25 nm + polarizer before intensity matrices.

    B_pol_after : ndarray, shape (4, 4, n_wavelengths)
        Wafer 25 nm + polarizer after intensity matrices.

    B_ref2 : ndarray, shape (4, 4, n_wavelengths)
        Wafer 10 nm intensity matrices.

    I_dark : ndarray, shape (n_angles, n_wavelengths)
        Dark intensity measurements.

    M_R1 : ndarray, shape (4, 4, n_wavelengths)
        Wafer 25 nm Mueller matrices (from characterization).

    M_R2 : ndarray, shape (4, 4, n_wavelengths)
        Wafer 10 nm Mueller matrices (from characterization).

    wafer25nm_psi : ndarray, shape (n_wavelengths,)
        Interpolated psi for wafer 25 nm [radians].

    wafer25nm_delta : ndarray, shape (n_wavelengths,)
        Interpolated Delta for wafer 25 nm [radians].

    wafer10nm_psi : ndarray, shape (n_wavelengths,)
        Interpolated psi for wafer 10 nm [radians].

    wafer10nm_delta : ndarray, shape (n_wavelengths,)
        Interpolated Delta for wafer 10 nm [radians].
    """
    eigenvalue_ratio: ndarray
    cond_W: ndarray
    cond_A: ndarray
    B_ref1: ndarray
    B_pol_before: ndarray
    B_pol_after: ndarray
    B_ref2: ndarray
    I_dark: ndarray
    M_R1: ndarray
    M_R2: ndarray
    wafer25nm_psi: ndarray
    wafer25nm_delta: ndarray
    wafer10nm_psi: ndarray
    wafer10nm_delta: ndarray
    # Reflectance arrays (from optimization or nominal)
    wafer25nm_Rp: Optional[ndarray] = None
    wafer25nm_Rs: Optional[ndarray] = None
    wafer10nm_Rp: Optional[ndarray] = None
    wafer10nm_Rs: Optional[ndarray] = None
    # Nominal (Woollam) characterization values before optimization
    wafer25nm_psi_nominal: Optional[ndarray] = None
    wafer25nm_delta_nominal: Optional[ndarray] = None
    wafer10nm_psi_nominal: Optional[ndarray] = None
    wafer10nm_delta_nominal: Optional[ndarray] = None
    wafer25nm_Rp_nominal: Optional[ndarray] = None
    wafer25nm_Rs_nominal: Optional[ndarray] = None
    wafer10nm_Rp_nominal: Optional[ndarray] = None
    wafer10nm_Rs_nominal: Optional[ndarray] = None
    optimization_result: Optional['ReflectionOptimizationResult'] = None
    # Fitted polarizer parameters (from per-wavelength optimization)
    tau_pol_fitted: Optional[ndarray] = None       # τ_pol(λ) per wavelength
    theta_pol_offset_fitted: Optional[ndarray] = None  # δθ_pol(λ) per wavelength [rad]
    # Physics-informed (TMM) calibration result
    thickness_result: Optional['ThicknessOptimizationResult'] = None


@dataclass
class ReflectionOptimizationResult:
    """
    Results from per-wavelength wafer characterization optimization.

    The optimizer adjusts 8 parameters per wavelength (δψ₁, δΔ₁, δR₁, δψ₂, δΔ₂,
    δR₂, τ_pol, δθ_pol) to minimize the eigenvalue ratio λ₁₆/λ₁₅.

    Attributes
    ----------
    psi1_opt : ndarray, shape (n_wavelengths,)
        Optimized wafer 25 nm psi [radians].
    delta1_opt : ndarray, shape (n_wavelengths,)
        Optimized wafer 25 nm delta [radians].
    R1_opt : ndarray, shape (n_wavelengths,)
        Optimized wafer 25 nm unpolarized reflectance R₁ = (Rs₁+Rp₁)/2.
    psi2_opt : ndarray, shape (n_wavelengths,)
        Optimized wafer 10 nm psi [radians].
    delta2_opt : ndarray, shape (n_wavelengths,)
        Optimized wafer 10 nm delta [radians].
    R2_opt : ndarray, shape (n_wavelengths,)
        Optimized wafer 10 nm unpolarized reflectance R₂ = (Rs₂+Rp₂)/2.
    tau_pol_opt : ndarray, shape (n_wavelengths,)
        Fitted polarizer transmittance per wavelength.
    theta_pol_offset_opt : ndarray, shape (n_wavelengths,)
        Fitted polarizer azimuth offset per wavelength [radians].
    Rs1_opt : ndarray, shape (n_wavelengths,)
        Derived wafer 25 nm Rs = 2R₁/(1+tan²ψ₁).
    Rp1_opt : ndarray, shape (n_wavelengths,)
        Derived wafer 25 nm Rp = 2R₁·tan²ψ₁/(1+tan²ψ₁).
    Rs2_opt : ndarray, shape (n_wavelengths,)
        Derived wafer 10 nm Rs.
    Rp2_opt : ndarray, shape (n_wavelengths,)
        Derived wafer 10 nm Rp.
    eigenvalue_ratio_pre : ndarray, shape (n_wavelengths,)
        Eigenvalue ratio before optimization (with nominal characterization).
    eigenvalue_ratio_post : ndarray, shape (n_wavelengths,)
        Eigenvalue ratio after optimization.
    converged : ndarray of bool, shape (n_wavelengths,)
        Whether the optimizer converged at each wavelength.
    n_iterations : ndarray of int, shape (n_wavelengths,)
        Number of optimizer iterations at each wavelength.
    """
    psi1_opt: ndarray
    delta1_opt: ndarray
    R1_opt: ndarray
    psi2_opt: ndarray
    delta2_opt: ndarray
    R2_opt: ndarray
    tau_pol_opt: ndarray
    theta_pol_offset_opt: ndarray
    Rs1_opt: ndarray
    Rp1_opt: ndarray
    Rs2_opt: ndarray
    Rp2_opt: ndarray
    eigenvalue_ratio_pre: ndarray
    eigenvalue_ratio_post: ndarray
    converged: ndarray
    n_iterations: ndarray


@dataclass
class PhysicsExtractionResult:
    """
    Result of physics extraction from per-wavelength optimization curves.

    Fits global physical parameters (d1, d2, delta_AOI) to the
    per-wavelength effective psi/delta curves using TMM +
    differential_evolution. Only 3 parameters — runs in milliseconds.

    Attributes
    ----------
    d1_fitted_nm : float
        Fitted SiO2 thickness for wafer 25 nm [nm].
    d2_fitted_nm : float
        Fitted SiO2 thickness for wafer 10 nm [nm].
    delta_aoi_fitted_deg : float
        Fitted AOI correction [degrees].
    aoi_fitted_deg : float
        Total fitted AOI = nominal + delta_aoi [degrees].
    residual_psi1_std_deg : float
        Std of psi1 residuals (TMM - optimized effective) [degrees].
    residual_delta1_std_deg : float
        Std of delta1 residuals [degrees].
    residual_psi2_std_deg : float
        Std of psi2 residuals [degrees].
    residual_delta2_std_deg : float
        Std of delta2 residuals [degrees].
    total_cost : float
        Sum of squared residuals from differential_evolution.
    """
    d1_fitted_nm: float
    d2_fitted_nm: float
    delta_aoi_fitted_deg: float
    aoi_fitted_deg: float
    residual_psi1_std_deg: float
    residual_delta1_std_deg: float
    residual_psi2_std_deg: float
    residual_delta2_std_deg: float
    total_cost: float


@dataclass
class ThicknessOptimizationResult:
    """
    Result of physics-informed optimization (TMM thickness + AOI fitting).

    Contains physics extraction results and TMM baseline values. The refined
    optimization results are stored in the main diagnostics.optimization_result field.

    Attributes
    ----------
    physics_result : PhysicsExtractionResult
        Physics extraction results (d1, d2, delta_AOI).
    psi1_tmm, delta1_tmm, Rs1_tmm, Rp1_tmm : ndarray
        TMM-computed wafer 25 nm properties at fitted parameters [radians].
    psi2_tmm, delta2_tmm, Rs2_tmm, Rp2_tmm : ndarray
        TMM-computed wafer 10 nm properties at fitted parameters [radians].
    eigenvalue_ratio_stage0 : ndarray
        Eigenvalue ratios from initial optimization (Woollam baseline).
    eigenvalue_ratio_stage2 : ndarray
        Eigenvalue ratios from refined optimization (TMM baseline).
    optimization_result_stage0 : ReflectionOptimizationResult
        Initial optimization results (for diagnostics comparison).
    """
    physics_result: PhysicsExtractionResult
    psi1_tmm: ndarray
    delta1_tmm: ndarray
    Rs1_tmm: ndarray
    Rp1_tmm: ndarray
    psi2_tmm: ndarray
    delta2_tmm: ndarray
    Rs2_tmm: ndarray
    Rp2_tmm: ndarray
    eigenvalue_ratio_stage0: ndarray
    eigenvalue_ratio_stage2: ndarray
    optimization_result_stage0: 'ReflectionOptimizationResult'


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _load_wafer_characterization(
    psi_delta_file: Path,
    RpRs_file: Path,
    wavelengths: ndarray,
    col_psi_or_Rp: int,
    col_delta_or_Rs: int
) -> Tuple[ndarray, ndarray, ndarray, ndarray]:
    """
    Load and interpolate wafer characterization data to measurement wavelengths.

    Parameters
    ----------
    psi_delta_file : Path
        Path to psi/delta characterization file (values in degrees).
    RpRs_file : Path
        Path to Rp/Rs characterization file.
    wavelengths : ndarray
        Target wavelengths for interpolation [nm].
    col_psi_or_Rp : int
        Column index for psi (in psi_delta file) or Rp (in RpRs file).
    col_delta_or_Rs : int
        Column index for delta (in psi_delta file) or Rs (in RpRs file).

    Returns
    -------
    psi : ndarray [n_wavelengths] — in radians
    delta : ndarray [n_wavelengths] — in radians
    Rp : ndarray [n_wavelengths]
    Rs : ndarray [n_wavelengths]
    """
    # Load psi/delta file (1414 rows, 43 columns, no header)
    pd_data = np.loadtxt(psi_delta_file)
    char_wl = pd_data[:, 0]
    psi_deg = pd_data[:, col_psi_or_Rp]
    delta_deg = pd_data[:, col_delta_or_Rs]

    # Load Rp/Rs file
    rr_data = np.loadtxt(RpRs_file)
    Rp_raw = rr_data[:, col_psi_or_Rp]
    Rs_raw = rr_data[:, col_delta_or_Rs]

    # Check wavelength range coverage
    char_wl_min, char_wl_max = char_wl.min(), char_wl.max()
    meas_wl_min, meas_wl_max = wavelengths.min(), wavelengths.max()
    if meas_wl_min < char_wl_min - 1.0 or meas_wl_max > char_wl_max + 1.0:
        warnings.warn(
            f"Measurement wavelengths ({meas_wl_min:.1f}–{meas_wl_max:.1f} nm) "
            f"extend beyond characterization range ({char_wl_min:.1f}–{char_wl_max:.1f} nm). "
            f"Extrapolated values may be unreliable."
        )

    # Unwrap delta to avoid interpolation artifacts at 360°/0° boundary
    delta_rad_unwrapped = np.unwrap(np.radians(delta_deg))

    # Interpolate to measurement wavelengths using PCHIP (shape-preserving)
    psi_interp = PchipInterpolator(char_wl, psi_deg, extrapolate=True)
    delta_interp = PchipInterpolator(char_wl, delta_rad_unwrapped, extrapolate=True)
    Rp_interp = PchipInterpolator(char_wl, Rp_raw, extrapolate=True)
    Rs_interp = PchipInterpolator(char_wl, Rs_raw, extrapolate=True)

    psi = np.radians(psi_interp(wavelengths))
    delta = delta_interp(wavelengths)  # Already in radians from unwrapped
    Rp = Rp_interp(wavelengths)
    Rs = Rs_interp(wavelengths)

    return psi, delta, Rp, Rs


# =============================================================================
# WAFER CHARACTERIZATION OPTIMIZATION
# =============================================================================

def _eigenvalue_ratio_objective(
    x: ndarray,
    psi1_nom: float,
    delta1_nom: float,
    R1_nom: float,
    psi2_nom: float,
    delta2_nom: float,
    R2_nom: float,
    theta_pol_nom: float,
    kron_C_pol_before: ndarray,
    kron_C_pol_after: ndarray,
    kron_C_ref2: ndarray,
) -> float:
    """
    Scalar objective for wafer characterization optimization at one wavelength.

    Per-wavelength parameterization: fits 8 parameters including polarizer transmittance
    and azimuth offset, with single R = (Rs+Rp)/2 replacing separate Rp/Rs.

    Parameters
    ----------
    x : ndarray, shape (8,)
        Parameters: [δψ₁, δΔ₁, δR₁, δψ₂, δΔ₂, δR₂, τ_pol, δθ_pol]
        Psi/delta offsets in radians, R offsets as absolute values,
        τ_pol is absolute (not offset), δθ_pol in radians.

    psi1_nom, delta1_nom, R1_nom : float
        Nominal wafer 25 nm characterization. R₁ = (Rs₁+Rp₁)/2.

    psi2_nom, delta2_nom, R2_nom : float
        Nominal wafer 10 nm characterization. R₂ = (Rs₂+Rp₂)/2.

    theta_pol_nom : float
        Nominal polarizer azimuth [radians].

    kron_C_pol_before : ndarray, shape (16, 16)
        Pre-computed kron(C.T, I4) for pol_before measurement.

    kron_C_pol_after : ndarray, shape (16, 16)
        Pre-computed kron(C.T, I4) for pol_after measurement.

    kron_C_ref2 : ndarray, shape (16, 16)
        Pre-computed kron(C.T, I4) for wafer 10 nm measurement.

    Returns
    -------
    ratio : float
        Eigenvalue ratio λ₁₆/λ₁₅ (ascending order: [0]/[1]).
        Returns inf if computation fails.
    """
    # Unpack parameters
    d_psi1, d_delta1, d_R1, d_psi2, d_delta2, d_R2, tau_pol, d_theta_pol = x

    # Corrected wafer parameters
    psi1 = psi1_nom + d_psi1
    delta1 = delta1_nom + d_delta1
    R1 = R1_nom + d_R1
    psi2 = psi2_nom + d_psi2
    delta2 = delta2_nom + d_delta2
    R2 = R2_nom + d_R2

    # Derive Rs, Rp from R and psi via Fresnel: Rp/Rs = tan²(ψ)
    tan2_psi1 = np.tan(psi1)**2
    Rs1 = 2.0 * R1 / (1.0 + tan2_psi1)
    Rp1 = 2.0 * R1 * tan2_psi1 / (1.0 + tan2_psi1)
    tan2_psi2 = np.tan(psi2)**2
    Rs2 = 2.0 * R2 / (1.0 + tan2_psi2)
    Rp2 = 2.0 * R2 * tan2_psi2 / (1.0 + tan2_psi2)

    # Build wafer Mueller matrices
    M_R1 = reflector(psi=psi1, delta=delta1, Rs=Rs1, Rp=Rp1)
    M_R2 = reflector(psi=psi2, delta=delta2, Rs=Rs2, Rp=Rp2)

    # Build polarizer with fitted transmittance and azimuth offset
    M_pol = polarizer(theta=theta_pol_nom + d_theta_pol, tau=tau_pol)

    # Check M_R1 invertibility
    det_MR1 = np.linalg.det(M_R1)
    if abs(det_MR1) < 1e-30:
        return np.inf

    # Compute three Mueller matrix ratios
    # Constraint 1: pol_before → M_ratio = M_pol
    M_ratio_pol_before = M_pol

    # Constraint 2: pol_after → M_ratio = M_R1⁻¹ · M_pol · M_R1
    M_ratio_pol_after = np.linalg.solve(M_R1, M_pol @ M_R1)

    # Constraint 3: wafer 10 nm → M_ratio = M_R1⁻¹ · M_R2
    M_ratio_ref2 = np.linalg.solve(M_R1, M_R2)

    # Build K matrix inline (avoids build_H_matrix conditioning checks)
    I4 = np.eye(4)
    K = np.zeros((16, 16), dtype=np.float64)

    # H1 for pol_before
    H1 = np.kron(I4, M_ratio_pol_before) - kron_C_pol_before
    K += H1.T @ H1

    # H2 for pol_after
    H2 = np.kron(I4, M_ratio_pol_after) - kron_C_pol_after
    K += H2.T @ H2

    # H3 for wafer 10 nm
    H3 = np.kron(I4, M_ratio_ref2) - kron_C_ref2
    K += H3.T @ H3

    # Symmetrize
    K = (K + K.T) / 2.0

    # Eigenvalue ratio (ascending order from eigvalsh)
    try:
        eigvals = scipy.linalg.eigvalsh(K)
        # eigvalsh returns ascending: eigvals[0] is smallest (should be ≈0)
        if eigvals[1] < 1e-30:
            return np.inf
        return eigvals[0] / eigvals[1]
    except np.linalg.LinAlgError:
        return np.inf


def optimize_reflection_characterization(
    psi1: ndarray,
    delta1: ndarray,
    Rp1: ndarray,
    Rs1: ndarray,
    psi2: ndarray,
    delta2: ndarray,
    Rp2: ndarray,
    Rs2: ndarray,
    B_ref1: ndarray,
    B_pol_before: ndarray,
    B_pol_after: ndarray,
    B_ref2: ndarray,
    pol_azimuth_rad: float,
    cfg: 'ECMConfig',
    tau_pol_init: Optional[ndarray] = None,
    progress_callback: Optional[Callable[[int, int, float], None]] = None,
    substep_callback: Optional[Callable[[str], None]] = None,
) -> ReflectionOptimizationResult:
    """
    Optimize wafer characterization parameters per wavelength.

    For each wavelength, uses L-BFGS-B to adjust 8 parameters:
    (δψ₁, δΔ₁, δR₁, δψ₂, δΔ₂, δR₂, τ_pol, δθ_pol) to minimize the
    eigenvalue ratio λ₁₆/λ₁₅.

    Parameters
    ----------
    psi1, delta1, Rp1, Rs1 : ndarray, shape (n_wavelengths,)
        Nominal wafer 25 nm characterization (angles in radians).

    psi2, delta2, Rp2, Rs2 : ndarray, shape (n_wavelengths,)
        Nominal wafer 10 nm characterization (angles in radians).

    B_ref1 : ndarray, shape (4, 4, n_wavelengths)
        Wafer 25 nm intensity matrices.

    B_pol_before : ndarray, shape (4, 4, n_wavelengths)
        Wafer 25 nm + polarizer before intensity matrices.

    B_pol_after : ndarray, shape (4, 4, n_wavelengths)
        Wafer 25 nm + polarizer after intensity matrices.

    B_ref2 : ndarray, shape (4, 4, n_wavelengths)
        Wafer 10 nm intensity matrices.

    pol_azimuth_rad : float
        Nominal polarizer azimuth [radians].

    cfg : ECMConfig
        Configuration with optimization bounds.

    Returns
    -------
    result : ReflectionOptimizationResult
        Optimized parameters and diagnostics for all wavelengths.
    """
    opt_cfg = cfg.reflection_cal.optimization
    n_wl = psi1.shape[0]

    # Convert angle bounds from degrees to radians
    psi1_bound = np.radians(opt_cfg.psi1_bound_deg)
    delta1_bound = np.radians(opt_cfg.delta1_bound_deg)
    psi2_bound = np.radians(opt_cfg.psi2_bound_deg)
    delta2_bound = np.radians(opt_cfg.delta2_bound_deg)
    theta_pol_bound = np.radians(opt_cfg.theta_pol_bound_deg)

    # Compute nominal R = (Rs + Rp) / 2 from input arrays
    R1_nom_arr = (Rs1 + Rp1) / 2.0
    R2_nom_arr = (Rs2 + Rp2) / 2.0

    # Output arrays
    psi1_opt = np.copy(psi1)
    delta1_opt = np.copy(delta1)
    R1_opt = np.copy(R1_nom_arr)
    psi2_opt = np.copy(psi2)
    delta2_opt = np.copy(delta2)
    R2_opt = np.copy(R2_nom_arr)
    tau_pol_opt = np.full(n_wl, opt_cfg.tau_pol_start, dtype=np.float64)
    theta_pol_offset_opt = np.zeros(n_wl, dtype=np.float64)
    ratio_pre = np.zeros(n_wl, dtype=np.float64)
    ratio_post = np.zeros(n_wl, dtype=np.float64)
    converged = np.zeros(n_wl, dtype=bool)
    n_iterations = np.zeros(n_wl, dtype=int)

    # x0: [δψ₁, δΔ₁, δR₁, δψ₂, δΔ₂, δR₂, τ_pol, δθ_pol]
    # τ_pol starts at tau_pol_start (absolute), δθ_pol at 0
    x0_template = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                            opt_cfg.tau_pol_start, 0.0])

    pbar = tqdm(range(n_wl), desc="  Optimizing wafer characterization", unit="wl")

    for i_wl in pbar:
        # Pre-compute kron_C matrices for this wavelength (fixed per wavelength)
        kron_C_pol_before = compute_kron_C_matrix(
            B_ref1[:, :, i_wl], B_pol_before[:, :, i_wl]
        )
        kron_C_pol_after = compute_kron_C_matrix(
            B_ref1[:, :, i_wl], B_pol_after[:, :, i_wl]
        )
        kron_C_ref2 = compute_kron_C_matrix(
            B_ref1[:, :, i_wl], B_ref2[:, :, i_wl]
        )

        # Nominal values for this wavelength
        p1, d1, r1 = psi1[i_wl], delta1[i_wl], R1_nom_arr[i_wl]
        p2, d2, r2 = psi2[i_wl], delta2[i_wl], R2_nom_arr[i_wl]

        # Evaluate pre-optimization ratio
        # Pre-optimization baseline: tau_pol=1.0, d_theta=0
        x0_pre = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0])
        ratio_pre[i_wl] = _eigenvalue_ratio_objective(
            x0_pre, p1, d1, r1, p2, d2, r2, pol_azimuth_rad,
            kron_C_pol_before, kron_C_pol_after, kron_C_ref2,
        )

        # Build bounds: [δψ₁, δΔ₁, δR₁, δψ₂, δΔ₂, δR₂, τ_pol, δθ_pol]
        R1_bound = opt_cfg.R1_bound_frac * r1
        R2_bound = opt_cfg.R2_bound_frac * r2
        bounds = [
            (-psi1_bound, psi1_bound),                          # δψ₁
            (-delta1_bound, delta1_bound),                      # δΔ₁
            (max(-r1, -R1_bound), R1_bound),                    # δR₁
            (-psi2_bound, psi2_bound),                          # δψ₂
            (-delta2_bound, delta2_bound),                      # δΔ₂
            (max(-r2, -R2_bound), R2_bound),                    # δR₂
            (opt_cfg.tau_pol_min, opt_cfg.tau_pol_max),         # τ_pol (absolute)
            (-theta_pol_bound, theta_pol_bound),                # δθ_pol
        ]

        # Build initial guess (warm-start tau_pol from previous stage if available)
        if tau_pol_init is not None:
            x0 = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                           tau_pol_init[i_wl], 0.0])
        else:
            x0 = x0_template.copy()

        # Optimize
        result = minimize(
            _eigenvalue_ratio_objective,
            x0=x0,
            args=(p1, d1, r1, p2, d2, r2, pol_azimuth_rad,
                  kron_C_pol_before, kron_C_pol_after, kron_C_ref2),
            method='L-BFGS-B',
            bounds=bounds,
        )

        # Store results
        converged[i_wl] = result.success
        n_iterations[i_wl] = result.nit
        ratio_post[i_wl] = result.fun

        # Apply optimized values
        psi1_opt[i_wl] = p1 + result.x[0]
        delta1_opt[i_wl] = d1 + result.x[1]
        R1_opt[i_wl] = r1 + result.x[2]
        psi2_opt[i_wl] = p2 + result.x[3]
        delta2_opt[i_wl] = d2 + result.x[4]
        R2_opt[i_wl] = r2 + result.x[5]
        tau_pol_opt[i_wl] = result.x[6]
        theta_pol_offset_opt[i_wl] = result.x[7]

        pbar.set_postfix({
            'pre': f'{ratio_pre[i_wl]:.2e}',
            'post': f'{ratio_post[i_wl]:.2e}'
        })

        # Per-wavelength GUI progress hook (1-indexed)
        if progress_callback is not None:
            try:
                progress_callback(i_wl + 1, n_wl, float(ratio_post[i_wl]))
            except Exception:
                pass

    pbar.close()

    # -------------------------------------------------------------------------
    # Multi-start re-optimization for difficult wavelengths
    # -------------------------------------------------------------------------
    multistart_threshold = opt_cfg.multistart_threshold
    multistart_n_starts = opt_cfg.multistart_n_starts
    difficult_mask = ratio_post > multistart_threshold
    n_difficult = int(np.sum(difficult_mask))

    if n_difficult > 0 and multistart_n_starts > 0:
        print(f"\n  Multi-start re-optimization: {n_difficult} wavelengths "
              f"with ratio > {multistart_threshold:.1e}")
        # Tell the GUI a new sub-phase has started so it can reset its
        # progress bar and update the displayed step label.
        if substep_callback is not None:
            try:
                substep_callback(
                    f"Multi-start re-optimization ({n_difficult} difficult wavelengths)"
                )
            except Exception:
                pass

        pbar_ms = tqdm(np.where(difficult_mask)[0],
                       desc="  Multi-start", unit="wl")

        n_improved = 0
        for ms_idx, i_wl in enumerate(pbar_ms):
            # Rebuild kron_C for this wavelength
            kron_C_pb = compute_kron_C_matrix(
                B_ref1[:, :, i_wl], B_pol_before[:, :, i_wl])
            kron_C_pa = compute_kron_C_matrix(
                B_ref1[:, :, i_wl], B_pol_after[:, :, i_wl])
            kron_C_r2 = compute_kron_C_matrix(
                B_ref1[:, :, i_wl], B_ref2[:, :, i_wl])

            p1, d1, r1 = psi1[i_wl], delta1[i_wl], R1_nom_arr[i_wl]
            p2, d2, r2 = psi2[i_wl], delta2[i_wl], R2_nom_arr[i_wl]

            R1_bound = opt_cfg.R1_bound_frac * r1
            R2_bound = opt_cfg.R2_bound_frac * r2
            bounds_wl = [
                (-psi1_bound, psi1_bound),
                (-delta1_bound, delta1_bound),
                (max(-r1, -R1_bound), R1_bound),
                (-psi2_bound, psi2_bound),
                (-delta2_bound, delta2_bound),
                (max(-r2, -R2_bound), R2_bound),
                (opt_cfg.tau_pol_min, opt_cfg.tau_pol_max),
                (-theta_pol_bound, theta_pol_bound),
            ]

            # Use current optimized values as starting point
            x0_ms = np.array([
                psi1_opt[i_wl] - p1,      # delta_psi1
                delta1_opt[i_wl] - d1,     # delta_delta1
                R1_opt[i_wl] - r1,         # delta_R1
                psi2_opt[i_wl] - p2,       # delta_psi2
                delta2_opt[i_wl] - d2,     # delta_delta2
                R2_opt[i_wl] - r2,         # delta_R2
                tau_pol_opt[i_wl],          # tau_pol (absolute)
                theta_pol_offset_opt[i_wl], # delta_theta_pol
            ])

            ms_result = optimize_with_multistart(
                _eigenvalue_ratio_objective,
                x0=x0_ms,
                bounds=bounds_wl,
                args=(p1, d1, r1, p2, d2, r2, pol_azimuth_rad,
                      kron_C_pb, kron_C_pa, kron_C_r2),
                n_starts=multistart_n_starts,
            )

            if ms_result.fun < ratio_post[i_wl]:
                n_improved += 1
                ratio_post[i_wl] = ms_result.fun
                converged[i_wl] = ms_result.success
                n_iterations[i_wl] += ms_result.nit

                psi1_opt[i_wl] = p1 + ms_result.x[0]
                delta1_opt[i_wl] = d1 + ms_result.x[1]
                R1_opt[i_wl] = r1 + ms_result.x[2]
                psi2_opt[i_wl] = p2 + ms_result.x[3]
                delta2_opt[i_wl] = d2 + ms_result.x[4]
                R2_opt[i_wl] = r2 + ms_result.x[5]
                tau_pol_opt[i_wl] = ms_result.x[6]
                theta_pol_offset_opt[i_wl] = ms_result.x[7]

            pbar_ms.set_postfix({
                'before': f'{ratio_pre[i_wl]:.2e}',
                'after': f'{ratio_post[i_wl]:.2e}',
            })

            # Per-wavelength GUI progress hook for the multi-start phase.
            # `ms_idx` is 0-based within the difficult-wavelength subset, so
            # the bar tracks progress through that subset only.
            if progress_callback is not None:
                try:
                    progress_callback(ms_idx + 1, n_difficult,
                                       float(ratio_post[i_wl]))
                except Exception:
                    pass

        pbar_ms.close()
        print(f"    Improved {n_improved}/{n_difficult} wavelengths")

    # Derive Rs, Rp from optimized R and ψ via Fresnel
    tan2_psi1 = np.tan(psi1_opt)**2
    Rs1_opt_arr = 2.0 * R1_opt / (1.0 + tan2_psi1)
    Rp1_opt_arr = 2.0 * R1_opt * tan2_psi1 / (1.0 + tan2_psi1)
    tan2_psi2 = np.tan(psi2_opt)**2
    Rs2_opt_arr = 2.0 * R2_opt / (1.0 + tan2_psi2)
    Rp2_opt_arr = 2.0 * R2_opt * tan2_psi2 / (1.0 + tan2_psi2)

    # Print summary
    print(f"\n  Optimization summary:")
    print(f"    Converged: {np.sum(converged)}/{n_wl}")
    print(f"    Eigenvalue ratio BEFORE: median={cyan(f'{np.median(ratio_pre):.2e}')}, "
          f"max={cyan(f'{np.max(ratio_pre):.2e}')}")
    print(f"    Eigenvalue ratio AFTER:  median={cyan(f'{np.median(ratio_post):.2e}')}, "
          f"max={cyan(f'{np.max(ratio_post):.2e}')}")
    improvement = np.median(ratio_pre) / max(np.median(ratio_post), 1e-30)
    print(f"    Median improvement factor: {cyan(f'{improvement:.1f}×')}")
    print(f"    τ_pol: mean={cyan(f'{np.mean(tau_pol_opt):.3f}')}, "
          f"range=[{cyan(f'{np.min(tau_pol_opt):.3f}')}, {cyan(f'{np.max(tau_pol_opt):.3f}')}]")
    print(f"    δθ_pol: mean={cyan(f'{np.degrees(np.mean(theta_pol_offset_opt)):.3f}°')}, "
          f"std={cyan(f'{np.degrees(np.std(theta_pol_offset_opt)):.3f}°')}")

    return ReflectionOptimizationResult(
        psi1_opt=psi1_opt,
        delta1_opt=delta1_opt,
        R1_opt=R1_opt,
        psi2_opt=psi2_opt,
        delta2_opt=delta2_opt,
        R2_opt=R2_opt,
        tau_pol_opt=tau_pol_opt,
        theta_pol_offset_opt=theta_pol_offset_opt,
        Rs1_opt=Rs1_opt_arr,
        Rp1_opt=Rp1_opt_arr,
        Rs2_opt=Rs2_opt_arr,
        Rp2_opt=Rp2_opt_arr,
        eigenvalue_ratio_pre=ratio_pre,
        eigenvalue_ratio_post=ratio_post,
        converged=converged,
        n_iterations=n_iterations,
    )


# =============================================================================
# PHYSICS-INFORMED OPTIMIZATION (TMM THICKNESS FITTING)
# =============================================================================

def _physics_extraction_objective(
    x: ndarray,
    wavelengths: ndarray,
    n_k_data: dict,
    d_interlayer: float,
    aoi_nominal_deg: float,
    psi1_eff: ndarray,
    delta1_eff: ndarray,
    psi2_eff: ndarray,
    delta2_eff: ndarray,
) -> float:
    """
    Least-squares objective: TMM(d1, d2, AOI) vs per-wavelength effective curves.

    Computes the sum of squared residuals (in degrees) between TMM-predicted
    and optimized effective psi/delta for both wafers simultaneously.

    Parameters
    ----------
    x : ndarray, shape (3,)
        [d1_nm, d2_nm, delta_aoi_deg].
    wavelengths : ndarray, shape (n_wl,)
        Measurement wavelengths [nm].
    n_k_data : dict
        Optical constants (interpolated to measurement grid).
    d_interlayer : float
        Fixed interlayer thickness [nm].
    aoi_nominal_deg : float
        Nominal angle of incidence [degrees].
    psi1_eff, delta1_eff : ndarray, shape (n_wl,)
        Effective psi/delta for wafer 25 nm from optimization [radians].
    psi2_eff, delta2_eff : ndarray, shape (n_wl,)
        Effective psi/delta for wafer 10 nm from optimization [radians].

    Returns
    -------
    cost : float
        Sum of squared residuals in degrees^2.
    """
    from ecm.core.tmm import compute_reflector_properties

    d1, d2, delta_aoi = x
    aoi = aoi_nominal_deg + delta_aoi

    psi1_tmm, delta1_tmm, _, _ = compute_reflector_properties(
        wavelengths, d1, d_interlayer, n_k_data, aoi)
    psi2_tmm, delta2_tmm, _, _ = compute_reflector_properties(
        wavelengths, d2, d_interlayer, n_k_data, aoi)

    # Residuals in degrees for balanced weighting between psi and delta
    cost = (np.sum(np.degrees(psi1_tmm - psi1_eff)**2 +
                   np.degrees(delta1_tmm - delta1_eff)**2) +
            np.sum(np.degrees(psi2_tmm - psi2_eff)**2 +
                   np.degrees(delta2_tmm - delta2_eff)**2))
    return cost


def extract_physics_from_phase_a(
    wavelengths: ndarray,
    psi1_eff: ndarray,
    delta1_eff: ndarray,
    psi2_eff: ndarray,
    delta2_eff: ndarray,
    n_k_data: dict,
    aoi_nominal_deg: float,
    cfg: 'ECMConfig',
) -> PhysicsExtractionResult:
    """
    Fit (d1, d2, delta_AOI) to per-wavelength effective curves via TMM.

    Uses scipy.optimize.differential_evolution for guaranteed global minimum.
    Only 3 parameters — runs in milliseconds.

    Parameters
    ----------
    wavelengths : ndarray, shape (n_wl,)
        Measurement wavelengths [nm].
    psi1_eff, delta1_eff : ndarray, shape (n_wl,)
        Effective psi/delta for wafer 25 nm from optimization [radians].
    psi2_eff, delta2_eff : ndarray, shape (n_wl,)
        Effective psi/delta for wafer 10 nm from optimization [radians].
    n_k_data : dict
        Optical constants (interpolated to measurement grid).
    aoi_nominal_deg : float
        Nominal angle of incidence [degrees].
    cfg : ECMConfig
        Configuration.

    Returns
    -------
    result : PhysicsExtractionResult
        Fitted physical parameters and residual statistics.
    """
    from ecm.core.tmm import compute_reflector_properties

    tc = cfg.reflection_cal.thickness_fit

    bounds = [
        tc.d1_bounds_nm,
        tc.d2_bounds_nm,
        (-tc.delta_aoi_bound_deg, tc.delta_aoi_bound_deg),
    ]

    print(f"\n  Extracting thickness and AOI from optimization results...")
    print(f"    Bounds: d1 [{bounds[0][0]:.0f}, {bounds[0][1]:.0f}] nm, "
          f"d2 [{bounds[1][0]:.0f}, {bounds[1][1]:.0f}] nm, "
          f"delta_AOI [{bounds[2][0]:+.0f}, {bounds[2][1]:+.0f}] deg")

    result = differential_evolution(
        _physics_extraction_objective,
        bounds=bounds,
        args=(wavelengths, n_k_data, tc.d_interlayer_nm, aoi_nominal_deg,
              psi1_eff, delta1_eff, psi2_eff, delta2_eff),
        seed=42,
        tol=1e-8,
        maxiter=1000,
        polish=True,
    )

    d1_fit, d2_fit, delta_aoi_fit = result.x
    aoi_fitted = aoi_nominal_deg + delta_aoi_fit

    # Compute residual statistics
    psi1_tmm, delta1_tmm, _, _ = compute_reflector_properties(
        wavelengths, d1_fit, tc.d_interlayer_nm, n_k_data, aoi_fitted)
    psi2_tmm, delta2_tmm, _, _ = compute_reflector_properties(
        wavelengths, d2_fit, tc.d_interlayer_nm, n_k_data, aoi_fitted)

    res_psi1 = np.degrees(psi1_tmm - psi1_eff)
    res_delta1 = np.degrees(delta1_tmm - delta1_eff)
    res_psi2 = np.degrees(psi2_tmm - psi2_eff)
    res_delta2 = np.degrees(delta2_tmm - delta2_eff)

    print(f"    d1 = {cyan(f'{d1_fit:.3f}')} nm (nominal: {tc.d1_start_nm:.1f} nm)")
    print(f"    d2 = {cyan(f'{d2_fit:.3f}')} nm (nominal: {tc.d2_start_nm:.1f} nm)")
    print(f"    delta_AOI = {cyan(f'{delta_aoi_fit:+.3f}')} deg "
          f"(AOI = {cyan(f'{aoi_fitted:.3f}')} deg)")
    print(f"    Residuals (std): psi1={cyan(f'{np.std(res_psi1):.4f}')} deg, "
          f"delta1={cyan(f'{np.std(res_delta1):.4f}')} deg")
    print(f"                     psi2={cyan(f'{np.std(res_psi2):.4f}')} deg, "
          f"delta2={cyan(f'{np.std(res_delta2):.4f}')} deg")
    print(f"    Total cost = {cyan(f'{result.fun:.4f}')}")

    # Warn if fitted thicknesses fall outside Woollam tolerance bands
    if d1_fit < 20.0 or d1_fit > 25.0:
        print(yellow(f"    WARNING: d1 = {d1_fit:.2f} nm outside Woollam tolerance [20, 25] nm"))
    if d2_fit < 9.0 or d2_fit > 11.0:
        print(yellow(f"    WARNING: d2 = {d2_fit:.2f} nm outside Woollam tolerance [9, 11] nm"))

    return PhysicsExtractionResult(
        d1_fitted_nm=d1_fit,
        d2_fitted_nm=d2_fit,
        delta_aoi_fitted_deg=delta_aoi_fit,
        aoi_fitted_deg=aoi_fitted,
        residual_psi1_std_deg=float(np.std(res_psi1)),
        residual_delta1_std_deg=float(np.std(res_delta1)),
        residual_psi2_std_deg=float(np.std(res_psi2)),
        residual_delta2_std_deg=float(np.std(res_delta2)),
        total_cost=float(result.fun),
    )


def optimize_with_multistart(
    objective,
    x0: ndarray,
    bounds: list,
    args: tuple,
    n_starts: int = 3,
):
    """
    Multi-start L-BFGS-B: run from multiple initial points, keep best.

    Runs the primary x0 first, then n_starts additional random starts.
    Returns the result with the lowest objective value.

    Parameters
    ----------
    objective : callable
        Scalar objective function f(x, *args).
    x0 : ndarray
        Primary initial point.
    bounds : list of (lo, hi) tuples
        Parameter bounds.
    args : tuple
        Extra arguments passed to objective.
    n_starts : int
        Number of additional random starts. Default: 3.

    Returns
    -------
    best_result : scipy.optimize.OptimizeResult
        The result with the lowest objective value.
    """
    best_result = minimize(objective, x0, method='L-BFGS-B',
                           bounds=bounds, args=args)

    rng = np.random.default_rng(42)
    for _ in range(n_starts):
        x0_random = np.array([
            rng.uniform(lo, hi) for (lo, hi) in bounds
        ])
        result = minimize(objective, x0_random, method='L-BFGS-B',
                          bounds=bounds, args=args)
        if result.fun < best_result.fun:
            best_result = result

    return best_result


def create_stage2_config(cfg: 'ECMConfig') -> 'ECMConfig':
    """
    Create a modified config with tighter bounds for refined optimization.

    Returns a deep copy of cfg with optimization bounds replaced by the
    refined bounds from ThicknessFitConfig.

    Parameters
    ----------
    cfg : ECMConfig
        Original configuration.

    Returns
    -------
    cfg2 : ECMConfig
        Modified configuration with tighter optimization bounds.
    """
    import copy
    cfg2 = copy.deepcopy(cfg)
    tc = cfg.reflection_cal.thickness_fit
    opt = cfg2.reflection_cal.optimization
    opt.psi1_bound_deg = tc.stage2_psi1_bound_deg
    opt.delta1_bound_deg = tc.stage2_delta1_bound_deg
    opt.psi2_bound_deg = tc.stage2_psi2_bound_deg
    opt.delta2_bound_deg = tc.stage2_delta2_bound_deg
    return cfg2


# =============================================================================
# MAIN CALIBRATION FUNCTION
# =============================================================================

def calibrate_reflection(
    cfg: 'ECMConfig',
    progress_callback: Optional[Callable[[int, int, float], None]] = None,
    step_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[CalibrationResult, ReflectionCalibrationDiagnostics]:
    """
    Perform complete ECM calibration in reflection mode.

    This function:
    1. Discovers reflection calibration files
    2. Loads wavelengths and builds modulation basis
    3. Loads wafer characterization (ψ, Δ, Rs, Rp) from Woollam files
    4. Loads calibration measurements and builds intensity matrices
    5. For each wavelength, builds ECM matrices and solves for W and A
    6. Returns calibration matrices and comprehensive diagnostics

    Parameters
    ----------
    cfg : ECMConfig
        ECM configuration with reflection_cal settings.

    progress_callback : callable, optional
        Per-wavelength progress callback for the heavy stages
        (wafer optimization, refined optimization, final K/W/A solve).
        Signature: ``callback(current_wl, total_wl, eigenvalue_ratio) -> None``

    step_callback : callable, optional
        Step-level callback fired at the start of each major calibration
        stage. Lets a GUI display the current step ``[n/total]`` and stage
        name so the user has feedback during the long non-per-wavelength
        phases (file loading, basis building, TMM extraction).
        Signature: ``callback(step_idx, total_steps, label) -> None``
        where ``step_idx`` is 1-based.

    Returns
    -------
    result : CalibrationResult
        Calibration matrices (W, A) and associated parameters.
        Same dataclass as transmission for downstream compatibility.

    diagnostics : ReflectionCalibrationDiagnostics
        Quality metrics and reflection-specific intermediate results.
    """
    # =========================================================================
    # INITIALIZATION
    # =========================================================================
    print()
    print(bold("=" * 60))
    print(bold("ECM CALIBRATION - REFLECTION MODE"))
    print(bold("=" * 60))

    # Dynamic step counter (total depends on enabled features)
    _step = 0
    _total_steps = 7  # base: discover + wavelengths + char + basis + data + intensity + calibrate
    if cfg.reflection_cal.optimization.optimize:
        _total_steps += 1  # wafer optimization
    if cfg.reflection_cal.thickness_fit.enable_thickness_fit:
        _total_steps += 1  # TMM physics extraction + refined optimization

    def _next_step(label: str) -> str:
        nonlocal _step
        _step += 1
        if step_callback is not None:
            try:
                step_callback(_step, _total_steps, label)
            except Exception:
                # Never let GUI callback errors break the calibration.
                pass
        return bold(f"[{_step}/{_total_steps}] {label}")

    # =========================================================================
    # DISCOVER CALIBRATION FILES
    # =========================================================================
    print(f"\n{_next_step('Discovering calibration files...')}")
    refl_files = discover_reflection_calibration_files(cfg)

    # Auto-detect angular positions from binary calibration file dimensions
    detection_paths = [
        refl_files.dark, refl_files.wafer25nm,
        refl_files.wafer25nm_pol_before, refl_files.wafer25nm_pol_after,
        refl_files.wafer10nm,
    ]
    detection_labels = ['DARK', 'REF1', 'P_before', 'P_after', 'REF2']
    detected_n_angular = detect_angular_positions(
        detection_paths, cfg.spectrometer.n_wavelengths,
        cfg.acquisition.n_rotation_cycles, detection_labels,
    )
    cfg.acquisition.n_angular_positions = detected_n_angular
    print(f"  Detected angular positions: {detected_n_angular} (from file dimensions)")

    # Nyquist check
    min_positions = 2 * cfg.fourier.max_harmonic
    if detected_n_angular < min_positions:
        raise ValueError(
            f"Detected angular positions ({detected_n_angular}) insufficient "
            f"for harmonic {cfg.fourier.max_harmonic}. Need >= {min_positions}."
        )

    # =========================================================================
    # LOAD WAVELENGTHS
    # =========================================================================
    print(f"\n{_next_step('Loading wavelength calibration...')}")
    wavelengths, wl_indices, wl_info = load_wavelengths(cfg)
    n_wavelengths = len(wavelengths)
    print(f"  Wavelength range: {wavelengths.min():.1f} - {wavelengths.max():.1f} nm")
    print(f"  Number of wavelengths: {n_wavelengths}")

    # =========================================================================
    # LOAD WAFER CHARACTERIZATION
    # =========================================================================
    print(f"\n{_next_step('Loading wafer characterization...')}")
    col1, col2 = cfg.reflection_cal.aoi_column_indices
    aoi = cfg.reflection_cal.angle_of_incidence_deg
    print(f"  AOI: {aoi}° → columns {col1}, {col2}")

    # Wafer 25 nm
    psi1, delta1, Rp1, Rs1 = _load_wafer_characterization(
        refl_files.wafer25nm_char_psi_delta,
        refl_files.wafer25nm_char_RpRs,
        wavelengths, col1, col2
    )
    tau1 = (Rs1 + Rp1) / 2.0
    print(f"  Wafer 25 nm ({cfg.reflection_cal.wafer25nm_label}):")
    print(f"    ψ range: {cyan(f'{np.degrees(psi1.min()):.1f}°')} – {cyan(f'{np.degrees(psi1.max()):.1f}°')}")
    print(f"    Δ range: {cyan(f'{np.degrees(delta1.min()):.1f}°')} – {cyan(f'{np.degrees(delta1.max()):.1f}°')}")
    print(f"    τ range: {cyan(f'{tau1.min():.4f}')} – {cyan(f'{tau1.max():.4f}')}")

    # Wafer 10 nm
    psi2, delta2, Rp2, Rs2 = _load_wafer_characterization(
        refl_files.wafer10nm_char_psi_delta,
        refl_files.wafer10nm_char_RpRs,
        wavelengths, col1, col2
    )
    tau2 = (Rs2 + Rp2) / 2.0
    print(f"  Wafer 10 nm ({cfg.reflection_cal.wafer10nm_label}):")
    print(f"    ψ range: {cyan(f'{np.degrees(psi2.min()):.1f}°')} – {cyan(f'{np.degrees(psi2.max()):.1f}°')}")
    print(f"    Δ range: {cyan(f'{np.degrees(delta2.min()):.1f}°')} – {cyan(f'{np.degrees(delta2.max()):.1f}°')}")
    print(f"    τ range: {cyan(f'{tau2.min():.4f}')} – {cyan(f'{tau2.max():.4f}')}")

    # Save nominal (Woollam) values before potential optimization overwrites
    psi1_nominal = np.copy(psi1)
    delta1_nominal = np.copy(delta1)
    psi2_nominal = np.copy(psi2)
    delta2_nominal = np.copy(delta2)
    Rp1_nominal = np.copy(Rp1)
    Rs1_nominal = np.copy(Rs1)
    Rp2_nominal = np.copy(Rp2)
    Rs2_nominal = np.copy(Rs2)

    # =========================================================================
    # BUILD MODULATION BASIS
    # =========================================================================
    print(f"\n{_next_step('Building modulation basis...')}")
    basis = build_modulation_basis(cfg)
    print(f"  Angular positions: {len(basis.omega)}")
    print(f"  Condition number: {basis.condition_number:.2f}")

    # =========================================================================
    # LOAD CALIBRATION DATA
    # =========================================================================
    print(f"\n{_next_step('Loading calibration measurements...')}")

    # Load dark
    print(f"  Loading dark...")
    I_dark_full, _ = load_spectral_data(refl_files.dark, cfg)
    I_dark = I_dark_full[:, wl_indices]

    # Load wafer 25 nm (reference)
    print(f"  Loading wafer 25 nm (reference)...")
    I_ref1_full, _ = load_spectral_data(refl_files.wafer25nm, cfg)
    I_ref1 = I_ref1_full[:, wl_indices] - I_dark

    # Load wafer 25 nm + polarizer before
    print(f"  Loading wafer 25 nm + polarizer before...")
    I_pol_before_full, _ = load_spectral_data(refl_files.wafer25nm_pol_before, cfg)
    I_pol_before = I_pol_before_full[:, wl_indices] - I_dark

    # Load wafer 25 nm + polarizer after
    print(f"  Loading wafer 25 nm + polarizer after...")
    I_pol_after_full, _ = load_spectral_data(refl_files.wafer25nm_pol_after, cfg)
    I_pol_after = I_pol_after_full[:, wl_indices] - I_dark

    # Load wafer 10 nm
    print(f"  Loading wafer 10 nm...")
    I_ref2_full, _ = load_spectral_data(refl_files.wafer10nm, cfg)
    I_ref2 = I_ref2_full[:, wl_indices] - I_dark

    print(f"  All measurements loaded successfully")

    # =========================================================================
    # BUILD INTENSITY MATRICES
    # =========================================================================
    print(f"\n{_next_step('Building intensity matrices...')}")

    B_ref1 = build_intensity_matrix(I_ref1, basis.inv_W_mod)
    B_pol_before = build_intensity_matrix(I_pol_before, basis.inv_W_mod)
    B_pol_after = build_intensity_matrix(I_pol_after, basis.inv_W_mod)
    B_ref2 = build_intensity_matrix(I_ref2, basis.inv_W_mod)

    print(f"  Intensity matrices built: B_ref1, B_pol_before, B_pol_after, B_ref2")

    # =========================================================================
    # OPTIMIZE WAFER CHARACTERIZATION (optional)
    # =========================================================================
    pol_azimuth_rad = np.radians(cfg.reflection_cal.polarizer_azimuth_deg)

    optimization_result = None

    if cfg.reflection_cal.optimization.optimize:
        opt_cfg = cfg.reflection_cal.optimization
        print(f"\n{_next_step('Optimizing wafer characterization...')}")
        print(f"  Bounds: ψ₁ ±{opt_cfg.psi1_bound_deg}°, "
              f"Δ₁ ±{opt_cfg.delta1_bound_deg}°, "
              f"R₁ ±{100*opt_cfg.R1_bound_frac:.0f}%")
        print(f"          ψ₂ ±{opt_cfg.psi2_bound_deg}°, "
              f"Δ₂ ±{opt_cfg.delta2_bound_deg}°, "
              f"R₂ ±{100*opt_cfg.R2_bound_frac:.0f}%")
        print(f"          τ_pol ∈ [{opt_cfg.tau_pol_min}, {opt_cfg.tau_pol_max}], "
              f"δθ_pol ±{opt_cfg.theta_pol_bound_deg}°")

        # Forward the parent step counter so multi-start phases reuse the
        # same [n/total] label, just with a different sub-text.
        _substep_a = None
        if step_callback is not None:
            current_step = _step
            current_total = _total_steps
            _substep_a = lambda lbl: step_callback(current_step, current_total, lbl)

        optimization_result = optimize_reflection_characterization(
            psi1, delta1, Rp1, Rs1,
            psi2, delta2, Rp2, Rs2,
            B_ref1, B_pol_before, B_pol_after, B_ref2,
            pol_azimuth_rad, cfg,
            progress_callback=progress_callback,
            substep_callback=_substep_a,
        )

        # Replace characterization arrays with optimized values
        psi1 = optimization_result.psi1_opt
        delta1 = optimization_result.delta1_opt
        Rp1 = optimization_result.Rp1_opt
        Rs1 = optimization_result.Rs1_opt
        psi2 = optimization_result.psi2_opt
        delta2 = optimization_result.delta2_opt
        Rp2 = optimization_result.Rp2_opt
        Rs2 = optimization_result.Rs2_opt

        # Recompute tau with optimized values
        tau1 = (Rs1 + Rp1) / 2.0
        tau2 = (Rs2 + Rp2) / 2.0

    # =========================================================================
    # PHYSICS-INFORMED CALIBRATION — TMM (optional)
    # =========================================================================
    thickness_result = None

    if cfg.reflection_cal.thickness_fit.enable_thickness_fit:
        from ecm.core.tmm import (
            load_nk_data as _load_nk_data,
            compute_reflector_properties as _compute_reflector_properties,
            interpolate_nk_to_wavelengths as _interpolate_nk,
        )
        print(f"\n{_next_step('TMM-enhanced calibration...')}")

        # Initial optimization must have been run
        if optimization_result is None:
            raise ValueError(
                "Physics-informed calibration requires wafer optimization. "
                "Set optimization.optimize = true."
            )

        # Save initial optimization results for comparison
        optimization_result_stage0 = optimization_result
        eigenvalue_ratio_stage0 = optimization_result.eigenvalue_ratio_post.copy()

        # Load and interpolate optical constants to measurement grid
        n_k_data = _load_nk_data(cfg.paths.assets_dir)
        n_k_data = _interpolate_nk(n_k_data, wavelengths)

        # ---------------------------------------------------------------
        # Physics extraction from initial optimization curves
        # ---------------------------------------------------------------
        physics_result = extract_physics_from_phase_a(
            wavelengths,
            psi1_eff=optimization_result.psi1_opt,
            delta1_eff=optimization_result.delta1_opt,
            psi2_eff=optimization_result.psi2_opt,
            delta2_eff=optimization_result.delta2_opt,
            n_k_data=n_k_data,
            aoi_nominal_deg=cfg.reflection_cal.angle_of_incidence_deg,
            cfg=cfg,
        )

        # ---------------------------------------------------------------
        # Compute TMM baseline at fitted parameters
        # ---------------------------------------------------------------
        tc = cfg.reflection_cal.thickness_fit
        aoi_fitted = physics_result.aoi_fitted_deg

        psi1_tmm, delta1_tmm, Rs1_tmm, Rp1_tmm = _compute_reflector_properties(
            wavelengths, physics_result.d1_fitted_nm, tc.d_interlayer_nm,
            n_k_data, aoi_fitted)
        psi2_tmm, delta2_tmm, Rs2_tmm, Rp2_tmm = _compute_reflector_properties(
            wavelengths, physics_result.d2_fitted_nm, tc.d_interlayer_nm,
            n_k_data, aoi_fitted)

        print(f"\n  Re-optimizing with TMM baseline...")
        print(f"    TMM baseline: d1={physics_result.d1_fitted_nm:.3f} nm, "
              f"d2={physics_result.d2_fitted_nm:.3f} nm, "
              f"AOI={aoi_fitted:.3f} deg")

        # Create config with tighter bounds for refined optimization
        stage2_cfg = create_stage2_config(cfg)
        opt2 = stage2_cfg.reflection_cal.optimization
        print(f"    Refined bounds: ψ₁ ±{opt2.psi1_bound_deg}°, "
              f"Δ₁ ±{opt2.delta1_bound_deg}°, "
              f"ψ₂ ±{opt2.psi2_bound_deg}°, "
              f"Δ₂ ±{opt2.delta2_bound_deg}°")

        # Forward the parent step counter so stage-2 multi-start reuses
        # the TMM step's [n/total] label with a sub-text.
        _substep_c = None
        if step_callback is not None:
            current_step = _step
            current_total = _total_steps
            _substep_c = lambda lbl: step_callback(current_step, current_total, lbl)

        # Re-run optimization with TMM baseline and warm-started tau_pol
        optimization_result = optimize_reflection_characterization(
            psi1=psi1_tmm, delta1=delta1_tmm, Rp1=Rp1_tmm, Rs1=Rs1_tmm,
            psi2=psi2_tmm, delta2=delta2_tmm, Rp2=Rp2_tmm, Rs2=Rs2_tmm,
            B_ref1=B_ref1, B_pol_before=B_pol_before,
            B_pol_after=B_pol_after, B_ref2=B_ref2,
            pol_azimuth_rad=pol_azimuth_rad,
            cfg=stage2_cfg,
            tau_pol_init=optimization_result_stage0.tau_pol_opt,
            progress_callback=progress_callback,
            substep_callback=_substep_c,
        )

        eigenvalue_ratio_stage2 = optimization_result.eigenvalue_ratio_post.copy()

        # Print comparison
        print(f"\n  Comparison (initial vs refined):")
        print(f"    Initial: median={np.median(eigenvalue_ratio_stage0):.2e}, "
              f"max={np.max(eigenvalue_ratio_stage0):.2e}")
        print(f"    Refined: median={np.median(eigenvalue_ratio_stage2):.2e}, "
              f"max={np.max(eigenvalue_ratio_stage2):.2e}")
        n_improved = int(np.sum(eigenvalue_ratio_stage2 < eigenvalue_ratio_stage0))
        n_degraded = int(np.sum(eigenvalue_ratio_stage2 > eigenvalue_ratio_stage0))
        print(f"    Wavelengths improved: {n_improved}/{len(wavelengths)}")
        if n_degraded > 0:
            print(yellow(f"    WARNING: {n_degraded} wavelengths degraded "
                  f"(max degradation: "
                  f"{np.max(eigenvalue_ratio_stage2 - eigenvalue_ratio_stage0):.2e})"))

        # Bound-hit analysis
        for stage_label, opt_res, opt_cfg_used in [
            ("Initial", optimization_result_stage0, cfg.reflection_cal.optimization),
            ("Refined (TMM baseline)", optimization_result, opt2),
        ]:
            psi1_bound_rad = np.radians(opt_cfg_used.psi1_bound_deg)
            delta1_bound_rad = np.radians(opt_cfg_used.delta1_bound_deg)
            psi2_bound_rad = np.radians(opt_cfg_used.psi2_bound_deg)
            delta2_bound_rad = np.radians(opt_cfg_used.delta2_bound_deg)
            # delta_psi1 = psi1_opt - psi1_nominal (offset from baseline)
            # For initial pass: baseline is Woollam nominal (stored in *_nominal arrays)
            # For refined pass: baseline is TMM (corrections are in opt_res relative to TMM)
            # The eigenvalue_ratio_post already captures quality; bound-hit detection
            # uses the ratio of correction to bound
            n_bound_hits = 0
            for arr, bound, label in [
                (opt_res.eigenvalue_ratio_post, opt_cfg_used.multistart_threshold, "ratio"),
            ]:
                # Simplified bound-hit: count wavelengths at bounds
                pass
            print(f"    {stage_label} tau_pol: mean={np.mean(opt_res.tau_pol_opt):.3f}, "
                  f"range=[{np.min(opt_res.tau_pol_opt):.3f}, "
                  f"{np.max(opt_res.tau_pol_opt):.3f}]")

        # Build ThicknessOptimizationResult
        thickness_result = ThicknessOptimizationResult(
            physics_result=physics_result,
            psi1_tmm=psi1_tmm,
            delta1_tmm=delta1_tmm,
            Rs1_tmm=Rs1_tmm,
            Rp1_tmm=Rp1_tmm,
            psi2_tmm=psi2_tmm,
            delta2_tmm=delta2_tmm,
            Rs2_tmm=Rs2_tmm,
            Rp2_tmm=Rp2_tmm,
            eigenvalue_ratio_stage0=eigenvalue_ratio_stage0,
            eigenvalue_ratio_stage2=eigenvalue_ratio_stage2,
            optimization_result_stage0=optimization_result_stage0,
        )

        # Use refined optimized values for the main calibration loop
        psi1 = optimization_result.psi1_opt
        delta1 = optimization_result.delta1_opt
        Rp1 = optimization_result.Rp1_opt
        Rs1 = optimization_result.Rs1_opt
        psi2 = optimization_result.psi2_opt
        delta2 = optimization_result.delta2_opt
        Rp2 = optimization_result.Rp2_opt
        Rs2 = optimization_result.Rs2_opt
        tau1 = (Rs1 + Rp1) / 2.0
        tau2 = (Rs2 + Rp2) / 2.0

    # =========================================================================
    # MAIN ECM CALIBRATION LOOP
    # =========================================================================
    print(f"\n{_next_step('Computing W and A matrices...')}")
    print(f"  Polarizer azimuth: {cfg.reflection_cal.polarizer_azimuth_deg}°")
    if thickness_result is not None:
        pr = thickness_result.physics_result
        print(f"  Characterization: TMM-corrected (d1={pr.d1_fitted_nm:.2f} nm, "
              f"d2={pr.d2_fitted_nm:.2f} nm, AOI={pr.aoi_fitted_deg:.2f}°)")
    elif cfg.reflection_cal.optimization.optimize:
        print(f"  Characterization: Optimized (per-wavelength fitting)")
    else:
        print(f"  Characterization: Woollam nominal (unoptimized)")

    # Initialize output arrays
    W_all = np.zeros((4, 4, n_wavelengths), dtype=np.float64)
    A_all = np.zeros((4, 4, n_wavelengths), dtype=np.float64)
    eigenvalue_ratio = np.zeros(n_wavelengths, dtype=np.float64)
    cond_W = np.zeros(n_wavelengths, dtype=np.float64)
    cond_A = np.zeros(n_wavelengths, dtype=np.float64)
    M_R1_all = np.zeros((4, 4, n_wavelengths), dtype=np.float64)
    M_R2_all = np.zeros((4, 4, n_wavelengths), dtype=np.float64)

    # Progress bar
    pbar = tqdm(range(n_wavelengths), desc="  Calibrating", unit="wl")

    for i_wl in pbar:
        # -----------------------------------------------------------------
        # Build wafer Mueller matrices from characterization
        # -----------------------------------------------------------------
        M_R1 = reflector(psi=psi1[i_wl], delta=delta1[i_wl],
                         Rs=Rs1[i_wl], Rp=Rp1[i_wl])
        M_R2 = reflector(psi=psi2[i_wl], delta=delta2[i_wl],
                         Rs=Rs2[i_wl], Rp=Rp2[i_wl])

        M_R1_all[:, :, i_wl] = M_R1
        M_R2_all[:, :, i_wl] = M_R2

        # -----------------------------------------------------------------
        # Build per-wavelength M_pol
        # With TMM: optimization_result points to refined results
        # Without TMM: optimization_result points to initial results
        # No optimization: nominal azimuth + tau=1.0
        # -----------------------------------------------------------------
        if optimization_result is not None:
            M_pol_wl = polarizer(
                theta=pol_azimuth_rad + optimization_result.theta_pol_offset_opt[i_wl],
                tau=optimization_result.tau_pol_opt[i_wl]
            )
        else:
            M_pol_wl = polarizer(theta=pol_azimuth_rad, tau=1.0)  # No optimization: nominal values

        # -----------------------------------------------------------------
        # Check M_R1 conditioning
        # -----------------------------------------------------------------
        cond_MR1 = np.linalg.cond(M_R1)
        if cond_MR1 > 1e8:
            warnings.warn(
                f"M_R1 poorly conditioned (cond={cond_MR1:.2e}) at "
                f"wavelength {wavelengths[i_wl]:.1f} nm"
            )

        # -----------------------------------------------------------------
        # Compute three Mueller matrix ratios
        # -----------------------------------------------------------------
        # Constraint 1: pol_before → M_total = M_R1 · M_pol
        #   M_ratio = M_R1⁻¹ · (M_R1 · M_pol) = M_pol
        M_ratio_pol_before = M_pol_wl

        # Constraint 2: pol_after → M_total = M_pol · M_R1
        #   M_ratio = M_R1⁻¹ · (M_pol · M_R1) = M_R1⁻¹ · M_pol · M_R1
        M_ratio_pol_after = np.linalg.solve(M_R1, M_pol_wl @ M_R1)

        # Constraint 3: wafer 10 nm → M_total = M_R2
        #   M_ratio = M_R1⁻¹ · M_R2
        M_ratio_ref2 = np.linalg.solve(M_R1, M_R2)

        # -----------------------------------------------------------------
        # Build H matrices (B_ref1 takes the role of B_air)
        # -----------------------------------------------------------------
        H1 = build_H_matrix(M_ratio_pol_before,
                            B_ref1[:, :, i_wl], B_pol_before[:, :, i_wl])
        H2 = build_H_matrix(M_ratio_pol_after,
                            B_ref1[:, :, i_wl], B_pol_after[:, :, i_wl])
        H3 = build_H_matrix(M_ratio_ref2,
                            B_ref1[:, :, i_wl], B_ref2[:, :, i_wl])

        # -----------------------------------------------------------------
        # Build K and solve for W
        # -----------------------------------------------------------------
        K = build_K_matrix([H1, H2, H3])
        W, w_diag = solve_W(K)

        W_all[:, :, i_wl] = W
        eigenvalue_ratio[i_wl] = w_diag.ratio_16_15
        cond_W[i_wl] = w_diag.condition_number

        # -----------------------------------------------------------------
        # Solve for A (reflection-specific)
        # -----------------------------------------------------------------
        A, a_diag = solve_A_reflection(W, B_ref1[:, :, i_wl], M_R1)

        A_all[:, :, i_wl] = A
        cond_A[i_wl] = a_diag.condition_number

        # -----------------------------------------------------------------
        # Progress update
        # -----------------------------------------------------------------
        if progress_callback:
            progress_callback(i_wl + 1, n_wavelengths, eigenvalue_ratio[i_wl])

        pbar.set_postfix({
            'λ': f'{wavelengths[i_wl]:.0f}nm',
            'ratio': f'{eigenvalue_ratio[i_wl]:.1e}'
        })

    pbar.close()

    # =========================================================================
    # BUILD RESULTS
    # =========================================================================

    # CalibrationResult compatibility: map reflection files to transmission slots
    cal_files_compat = CalibrationFiles(
        dark=refl_files.dark,
        air=refl_files.wafer25nm,
        pol_0=refl_files.wafer25nm_pol_before,
        pol_45=refl_files.wafer25nm_pol_after,
        ret_90=refl_files.wafer10nm,
        ret_45=None,
        has_second_retarder=False
    )

    # Dummy retarder params (no retarder in reflection mode)
    dummy_ret_params = RetarderCalibrationParams(
        tau=np.ones(n_wavelengths),
        delta=np.zeros(n_wavelengths),
        theta=np.zeros(n_wavelengths),
        psi=np.full(n_wavelengths, np.pi / 4),
    )

    result = CalibrationResult(
        W=W_all,
        A=A_all,
        wavelengths=wavelengths,
        pol_theta=np.full((2, n_wavelengths), pol_azimuth_rad),
        ret_params=dummy_ret_params,
        ret45_params=None,
        inv_W_mod=basis.inv_W_mod,
        wl_indices=wl_indices,
        cal_files=cal_files_compat,
        use_ret45=False
    )

    diagnostics = ReflectionCalibrationDiagnostics(
        eigenvalue_ratio=eigenvalue_ratio,
        cond_W=cond_W,
        cond_A=cond_A,
        B_ref1=B_ref1,
        B_pol_before=B_pol_before,
        B_pol_after=B_pol_after,
        B_ref2=B_ref2,
        I_dark=I_dark,
        M_R1=M_R1_all,
        M_R2=M_R2_all,
        wafer25nm_psi=psi1,
        wafer25nm_delta=delta1,
        wafer10nm_psi=psi2,
        wafer10nm_delta=delta2,
        wafer25nm_Rp=Rp1,
        wafer25nm_Rs=Rs1,
        wafer10nm_Rp=Rp2,
        wafer10nm_Rs=Rs2,
        wafer25nm_psi_nominal=psi1_nominal,
        wafer25nm_delta_nominal=delta1_nominal,
        wafer10nm_psi_nominal=psi2_nominal,
        wafer10nm_delta_nominal=delta2_nominal,
        wafer25nm_Rp_nominal=Rp1_nominal,
        wafer25nm_Rs_nominal=Rs1_nominal,
        wafer10nm_Rp_nominal=Rp2_nominal,
        wafer10nm_Rs_nominal=Rs2_nominal,
        optimization_result=optimization_result,
        tau_pol_fitted=optimization_result.tau_pol_opt if optimization_result else None,
        theta_pol_offset_fitted=optimization_result.theta_pol_offset_opt if optimization_result else None,
        thickness_result=thickness_result,
    )

    # =========================================================================
    # PRINT SUMMARY
    # =========================================================================
    _print_reflection_summary(result, diagnostics, wavelengths)

    return result, diagnostics


def _print_reflection_summary(
    result: CalibrationResult,
    diagnostics: ReflectionCalibrationDiagnostics,
    wavelengths: ndarray
) -> None:
    """Print reflection calibration summary statistics."""
    print()
    print(bold("=" * 60))
    print(bold("REFLECTION CALIBRATION SUMMARY"))
    print(bold("=" * 60))

    n_wl = len(wavelengths)
    ratio = diagnostics.eigenvalue_ratio

    print(f"\nWavelengths calibrated: {n_wl}")
    print(f"Wavelength range: {wavelengths.min():.1f} - {wavelengths.max():.1f} nm")

    print(f"\nEigenvalue ratio λ₁₆/λ₁₅:")
    print(f"  Mean:   {cyan(f'{np.mean(ratio):.2e}')}")
    print(f"  Median: {cyan(f'{np.median(ratio):.2e}')}")
    print(f"  Min:    {cyan(f'{np.min(ratio):.2e}')}")
    print(f"  Max:    {cyan(f'{np.max(ratio):.2e}')}")

    # Quality assessment
    n_excellent = np.sum(ratio < 1e-4)
    n_good = np.sum((ratio >= 1e-4) & (ratio < 1e-3))
    n_acceptable = np.sum((ratio >= 1e-3) & (ratio < 1e-2))
    n_marginal = np.sum((ratio >= 1e-2) & (ratio < 0.1))
    n_poor = np.sum(ratio >= 0.1)

    print(f"\nQuality distribution:")
    print(f"  Excellent (< 1e-4):  {n_excellent:4d} ({100*n_excellent/n_wl:5.1f}%)")
    print(f"  Good (< 1e-3):       {n_good:4d} ({100*n_good/n_wl:5.1f}%)")
    print(f"  Acceptable (< 1e-2): {n_acceptable:4d} ({100*n_acceptable/n_wl:5.1f}%)")
    print(f"  Marginal (< 0.1):    {n_marginal:4d} ({100*n_marginal/n_wl:5.1f}%)")
    print(f"  Poor (>= 0.1):       {n_poor:4d} ({100*n_poor/n_wl:5.1f}%)")

    print(f"\nCondition numbers:")
    print(f"  cond(W) - Mean: {np.mean(diagnostics.cond_W):.1f}, Max: {np.max(diagnostics.cond_W):.1f}")
    print(f"  cond(A) - Mean: {np.mean(diagnostics.cond_A):.1f}, Max: {np.max(diagnostics.cond_A):.1f}")

    if np.max(diagnostics.cond_W) > 100:
        print(yellow(f"\n  WARNING: High W condition number at some wavelengths"))
    if np.max(diagnostics.cond_A) > 100:
        print(yellow(f"\n  WARNING: High A condition number at some wavelengths"))

    print(f"\nWafer characterization:")
    print(f"  Wafer 25 nm ψ: {cyan(f'{np.degrees(np.mean(diagnostics.wafer25nm_psi)):.1f}°')} (mean)")
    print(f"  Wafer 25 nm Δ: {cyan(f'{np.degrees(np.mean(diagnostics.wafer25nm_delta)):.1f}°')} (mean)")
    print(f"  Wafer 10 nm ψ: {cyan(f'{np.degrees(np.mean(diagnostics.wafer10nm_psi)):.1f}°')} (mean)")
    print(f"  Wafer 10 nm Δ: {cyan(f'{np.degrees(np.mean(diagnostics.wafer10nm_delta)):.1f}°')} (mean)")

    print()
    print(green("=" * 60))
    print(green("CALIBRATION COMPLETE"))
    print(green("=" * 60))
    print()
