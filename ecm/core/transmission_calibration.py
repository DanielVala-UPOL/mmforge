"""
ECM Transmission Mode Calibration

This module provides the main orchestration function for performing a complete
ECM calibration in transmission mode. It integrates all the core ECM functions
to produce calibrated PSG (W) and PSA (A) matrices.

Functions
---------
calibrate_transmission(cfg)
    Perform complete ECM calibration in transmission mode

Theory
------
The Eigenvalue Calibration Method (ECM) determines the modulation matrices
W (PSG) and A (PSA) from a set of calibration measurements using known
optical elements (polarizers, retarders).

**Calibration Samples (Transmission Mode):**
1. Air (straight-through): Reference with M = I
2. Polarizer at 0°: M = M_pol(θ=0°, τ)
3. Polarizer at 45°: M = M_pol(θ=45°, τ)
4. Retarder at 90°: M = M_ret(θ=90°, δ, τ)
5. Retarder at 45° (optional): M = M_ret(θ=45°, δ, τ)

**Algorithm Steps:**
1. Build modulation basis matrix from instrument configuration
2. Load calibration measurements and build intensity matrices B
3. Extract sample parameters (τ, δ, Ψ) from eigenvalue analysis
4. For each wavelength:
   a. Build H matrices from Mueller matrices and B matrices
   b. Accumulate K = Σᵢ H_Mᵢᵀ @ H_Mᵢ
   c. Solve eigenvalue problem: K @ vec(W) = λ₁₆ @ vec(W)
   d. Compute A = B_air @ W⁻¹
5. Return calibration matrices and diagnostics

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999)

[2] Rosales et al., "Extended eigenvalue calibration method for spectroscopic
    Mueller matrix ellipsometry", Opt. Lett. 49, 1165-1168 (2024)
"""

import numpy as np
from numpy import ndarray
from scipy.interpolate import PchipInterpolator
from dataclasses import dataclass, field
from typing import Tuple, Optional, Callable, Dict, Any, TYPE_CHECKING
from pathlib import Path
from tqdm import tqdm

if TYPE_CHECKING:
    from ecm.config.ecm_config import ECMConfig

# Local imports
from ecm.core.file_discovery import discover_calibration_files, CalibrationFiles
from ecm.core.modulation import build_modulation_basis, build_intensity_matrix, ModulationBasis
from ecm.core.ecm_matrices import build_H_matrix, build_K_matrix
from ecm.core.ecm_solver import solve_W, solve_A, WDiagnostics, ADiagnostics
from ecm.core.parameter_extraction import (
    extract_sample_params,
    PolarizerParams,
    RetarderParams
)
from ecm.utils.io import load_spectral_data, load_wavelengths
from ecm.utils.mueller_matrices import polarizer, retarder, identity, elliptic_retarder
from ecm.core.ecm_optimization import (
    OptimizationFlags,
    FixedParams,
    optimize_ecm_parameters,
    build_initial_x,
    precompute_kron_C_matrices
)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RetarderCalibrationParams:
    """
    Calibration parameters for a retarder sample.

    Attributes
    ----------
    tau : ndarray, shape (n_wavelengths,)
        Transmission coefficient at each wavelength.

    delta : ndarray, shape (n_wavelengths,)
        Retardation in radians at each wavelength.

    theta : ndarray, shape (n_wavelengths,)
        Optimized orientation angle in radians at each wavelength.

    psi : ndarray, shape (n_wavelengths,)
        Ellipsometric angle in radians at each wavelength.
        For ideal linear retarder: psi ≈ π/4 (45°).
    """
    tau: ndarray
    delta: ndarray
    theta: ndarray
    psi: ndarray


@dataclass
class CalibrationResult:
    """
    Complete results from ECM calibration.

    Attributes
    ----------
    W : ndarray, shape (4, 4, n_wavelengths)
        PSG modulation matrices for each wavelength.

    A : ndarray, shape (4, 4, n_wavelengths)
        PSA modulation matrices for each wavelength.

    wavelengths : ndarray, shape (n_wavelengths,)
        Wavelength values in nm.

    pol_theta : ndarray, shape (2, n_wavelengths)
        Polarizer angles in radians.
        pol_theta[0, :] = pol_0 angles, pol_theta[1, :] = pol_45 angles.

    ret_params : RetarderCalibrationParams
        Primary retarder (FP1) calibration parameters.

    ret45_params : RetarderCalibrationParams, optional
        Secondary retarder (FP2) calibration parameters (if used).

    inv_W_mod : ndarray, shape (16, n_angles)
        Pseudo-inverse of modulation basis matrix.
        Used for processing additional samples.

    wl_indices : ndarray, shape (n_wavelengths,)
        Indices into full wavelength array.

    cal_files : CalibrationFiles
        Paths to calibration files used.

    use_ret45 : bool
        Whether second retarder was used in calibration.

    Notes
    -----
    **Using the Calibration:**

    To process a sample measurement after calibration:

    >>> from ecm.core import process_sample
    >>> result = process_sample(sample_data, A, W, inv_W_mod)
    >>> M = result.M_normalized  # Normalized Mueller matrices
    """
    W: ndarray
    A: ndarray
    wavelengths: ndarray
    pol_theta: ndarray
    ret_params: RetarderCalibrationParams
    ret45_params: Optional[RetarderCalibrationParams]
    inv_W_mod: ndarray
    wl_indices: ndarray
    cal_files: CalibrationFiles
    use_ret45: bool


@dataclass
class CalibrationDiagnostics:
    """
    Diagnostic information from calibration process.

    Attributes
    ----------
    eigenvalue_ratio : ndarray, shape (n_wavelengths,)
        Quality metric at each wavelength (ratio of smallest to second-smallest eigenvalue).
        - < 1e-4: Excellent calibration
        - < 1e-3: Good calibration
        - < 1e-2: Acceptable calibration
        - < 0.1: Marginal calibration
        - >= 0.1: Poor calibration (check data quality)

    cond_W : ndarray, shape (n_wavelengths,)
        Condition number of W at each wavelength.
        Should be < 100 for well-aligned system.

    cond_A : ndarray, shape (n_wavelengths,)
        Condition number of A at each wavelength.
        Should be < 100 for well-aligned system.

    B_air : ndarray, shape (4, 4, n_wavelengths)
        Air intensity matrices.

    B_pol0 : ndarray, shape (4, 4, n_wavelengths)
        Polarizer 0° intensity matrices.

    B_pol45 : ndarray, shape (4, 4, n_wavelengths)
        Polarizer 45° intensity matrices.

    B_ret : ndarray, shape (4, 4, n_wavelengths)
        Primary retarder intensity matrices.

    B_ret45 : ndarray, shape (4, 4, n_wavelengths), optional
        Secondary retarder intensity matrices (if used).

    I_dark : ndarray, shape (n_angles, n_wavelengths)
        Dark intensity measurements (for sample processing).

    pol0_params : Dict
        Polarizer 0° extracted parameters.

    pol45_params : Dict
        Polarizer 45° extracted parameters.
    """
    eigenvalue_ratio: ndarray
    cond_W: ndarray
    cond_A: ndarray
    B_air: ndarray
    B_pol0: ndarray
    B_pol45: ndarray
    B_ret: ndarray
    B_ret45: Optional[ndarray]
    I_dark: ndarray
    pol0_params: Dict[str, Any] = field(default_factory=dict)
    pol45_params: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# MAIN CALIBRATION FUNCTION
# =============================================================================

def calibrate_transmission(
    cfg: 'ECMConfig',
    progress_callback: Optional[Callable[[int, int, float], None]] = None
) -> Tuple[CalibrationResult, CalibrationDiagnostics]:
    """
    Perform complete ECM calibration in transmission mode.

    This is the main orchestration function that:
    1. Discovers calibration files
    2. Loads wavelengths and builds modulation basis
    3. Loads calibration measurements (dark, air, polarizers, retarders)
    4. Extracts sample parameters from eigenvalue analysis
    5. For each wavelength, builds ECM matrices and solves for W and A
    6. Returns calibration matrices and comprehensive diagnostics

    Reference: Compain et al., Appl. Opt. 38, 3490-3502 (1999)

    Parameters
    ----------
    cfg : ECMConfig
        ECM configuration with all necessary settings.

    progress_callback : callable, optional
        Callback function for progress updates.
        Signature: callback(current_wl, total_wl, eigenvalue_ratio)
        If None, uses tqdm for progress display.

    Returns
    -------
    result : CalibrationResult
        Calibration matrices (W, A) and associated parameters.

    diagnostics : CalibrationDiagnostics
        Quality metrics and intermediate results.

    Raises
    ------
    FileNotFoundError
        If required calibration files are not found.

    ValueError
        If calibration data is invalid or inconsistent.

    Examples
    --------
    >>> from ecm.config import ECMConfig
    >>> from ecm.core import calibrate_transmission
    >>>
    >>> # Load configuration
    >>> cfg = ECMConfig()
    >>> cfg.paths.data_dir = Path('/path/to/calibration/data')
    >>>
    >>> # Run calibration
    >>> result, diagnostics = calibrate_transmission(cfg)
    >>>
    >>> # Check quality
    >>> print(f"Mean eigenvalue ratio: {np.mean(diagnostics.eigenvalue_ratio):.2e}")
    >>> print(f"Wavelengths calibrated: {len(result.wavelengths)}")

    Notes
    -----
    **Progress Display:**

    Progress is displayed using tqdm by default. For custom progress
    handling (e.g., GUI integration), provide a progress_callback function.

    **Quality Metrics:**

    The eigenvalue ratio λ₁₆/λ₁₅ is the primary quality indicator:
    - Values < 1e-3 indicate good calibration
    - Values > 0.1 suggest measurement or alignment issues

    **Second Retarder:**

    If a second retarder measurement (FP2 at 45°) is available, it is
    automatically included in the calibration for improved robustness.
    """
    # =========================================================================
    # INITIALIZATION
    # =========================================================================
    print()
    print("=" * 60)
    print("ECM CALIBRATION - TRANSMISSION MODE")
    print("=" * 60)

    # =========================================================================
    # STEP 1: DISCOVER CALIBRATION FILES
    # =========================================================================
    print("\n[1/7] Discovering calibration files...")
    cal_files = discover_calibration_files(cfg)
    use_ret45 = cal_files.has_second_retarder

    # =========================================================================
    # STEP 2: LOAD WAVELENGTHS
    # =========================================================================
    print("\n[2/7] Loading wavelength calibration...")
    wavelengths, wl_indices, wl_info = load_wavelengths(cfg)
    n_wavelengths = len(wavelengths)
    print(f"  Wavelength range: {wavelengths.min():.1f} - {wavelengths.max():.1f} nm")
    print(f"  Number of wavelengths: {n_wavelengths}")

    # =========================================================================
    # STEP 2.5: LOAD RETARDER CHARACTERIZATION (if available)
    # =========================================================================
    # Load wavelength-dependent retardation from characterization files
    # These provide more accurate retardation values than eigenvalue extraction
    use_ret_char = False
    use_ret45_char = False
    ret_delta_char = None
    ret45_delta_char = None

    if cal_files.ret_90_char is not None and cal_files.ret_90_char.exists():
        try:
            # Load characterization file: [wavelength_nm, retardation_deg]
            char_data = np.loadtxt(cal_files.ret_90_char)
            char_wl = char_data[:, 0]
            char_delta_deg = char_data[:, 1]

            # Interpolate to measurement wavelengths using PCHIP (shape-preserving)
            interpolator = PchipInterpolator(char_wl, char_delta_deg, extrapolate=True)
            ret_delta_char = np.radians(interpolator(wavelengths))
            use_ret_char = True
            print(f"  Loaded FP1 characterization: {cal_files.ret_90_char.name}")
            print(f"    Retardation range: {np.degrees(ret_delta_char.min()):.1f}° - {np.degrees(ret_delta_char.max()):.1f}°")
        except Exception as e:
            print(f"  Warning: Could not load FP1 characterization: {e}")

    if use_ret45 and cal_files.ret_45_char is not None and cal_files.ret_45_char.exists():
        try:
            char_data = np.loadtxt(cal_files.ret_45_char)
            char_wl = char_data[:, 0]
            char_delta_deg = char_data[:, 1]

            interpolator = PchipInterpolator(char_wl, char_delta_deg, extrapolate=True)
            ret45_delta_char = np.radians(interpolator(wavelengths))
            use_ret45_char = True
            print(f"  Loaded FP2 characterization: {cal_files.ret_45_char.name}")
            print(f"    Retardation range: {np.degrees(ret45_delta_char.min()):.1f}° - {np.degrees(ret45_delta_char.max()):.1f}°")
        except Exception as e:
            print(f"  Warning: Could not load FP2 characterization: {e}")

    # =========================================================================
    # STEP 3: BUILD MODULATION BASIS
    # =========================================================================
    print("\n[3/7] Building modulation basis matrix...")
    basis = build_modulation_basis(cfg)
    print(f"  Angular positions: {len(basis.omega)}")
    print(f"  Condition number: {basis.condition_number:.2f}")

    if basis.condition_number > 10:
        print(f"  WARNING: High condition number may affect accuracy")

    # =========================================================================
    # STEP 4: LOAD CALIBRATION DATA
    # =========================================================================
    print("\n[4/7] Loading calibration measurements...")

    # Load dark
    print(f"  Loading dark...")
    I_dark_full, _ = load_spectral_data(cal_files.dark, cfg)
    I_dark = I_dark_full[:, wl_indices]

    # Load air (straight-through)
    print(f"  Loading air (straight-through)...")
    I_air_full, _ = load_spectral_data(cal_files.air, cfg)
    I_air = I_air_full[:, wl_indices] - I_dark

    # Load polarizer 0°
    print(f"  Loading polarizer 0°...")
    I_pol0_full, _ = load_spectral_data(cal_files.pol_0, cfg)
    I_pol0 = I_pol0_full[:, wl_indices] - I_dark

    # Load polarizer 45°
    print(f"  Loading polarizer 45°...")
    I_pol45_full, _ = load_spectral_data(cal_files.pol_45, cfg)
    I_pol45 = I_pol45_full[:, wl_indices] - I_dark

    # Load primary retarder (FP1 at 90°)
    print(f"  Loading retarder FP1 (90°)...")
    I_ret_full, _ = load_spectral_data(cal_files.ret_90, cfg)
    I_ret = I_ret_full[:, wl_indices] - I_dark

    # Load secondary retarder (FP2 at 45°) if available
    I_ret45 = None
    if use_ret45:
        print(f"  Loading retarder FP2 (45°)...")
        I_ret45_full, _ = load_spectral_data(cal_files.ret_45, cfg)
        I_ret45 = I_ret45_full[:, wl_indices] - I_dark

    print(f"  All measurements loaded successfully")

    # =========================================================================
    # STEP 5: BUILD INTENSITY MATRICES
    # =========================================================================
    print("\n[5/7] Building intensity matrices...")

    B_air = build_intensity_matrix(I_air, basis.inv_W_mod)
    B_pol0 = build_intensity_matrix(I_pol0, basis.inv_W_mod)
    B_pol45 = build_intensity_matrix(I_pol45, basis.inv_W_mod)
    B_ret = build_intensity_matrix(I_ret, basis.inv_W_mod)

    B_ret45 = None
    if use_ret45:
        B_ret45 = build_intensity_matrix(I_ret45, basis.inv_W_mod)

    print(f"  Intensity matrices built: B_air, B_pol0, B_pol45, B_ret" +
          (", B_ret45" if use_ret45 else ""))

    # =========================================================================
    # STEP 6: EXTRACT SAMPLE PARAMETERS
    # =========================================================================
    print("\n[6/7] Extracting sample parameters...")

    # Initialize arrays for extracted parameters
    pol0_tau = np.zeros(n_wavelengths)
    pol45_tau = np.zeros(n_wavelengths)
    ret_tau = np.zeros(n_wavelengths)
    ret_delta = np.zeros(n_wavelengths)
    ret_psi = np.zeros(n_wavelengths)

    ret45_tau = np.zeros(n_wavelengths) if use_ret45 else None
    ret45_delta = np.zeros(n_wavelengths) if use_ret45 else None
    ret45_psi = np.zeros(n_wavelengths) if use_ret45 else None

    # Extract parameters at each wavelength
    print(f"  Extracting parameters for {n_wavelengths} wavelengths...")

    # Get configured transmittance values as fallbacks
    pol0_tau_cfg = cfg.calibration_samples['pol_0'].transmittance
    pol45_tau_cfg = cfg.calibration_samples['pol_45'].transmittance
    ret_tau_cfg = cfg.calibration_samples['ret_90'].transmittance
    ret45_tau_cfg = cfg.calibration_samples['ret_45'].transmittance if use_ret45 else 1.0

    for i_wl in range(n_wavelengths):
        # Polarizer 0° parameters
        params = extract_sample_params(
            B_air[:, :, i_wl],
            B_pol0[:, :, i_wl],
            'polarizer'
        )
        # Use extracted tau if valid (0 < tau <= 1), otherwise use configured value
        tau_extracted = params.tau
        if 0.01 < tau_extracted < 1.5:
            pol0_tau[i_wl] = tau_extracted
        else:
            pol0_tau[i_wl] = pol0_tau_cfg

        # Polarizer 45° parameters
        params = extract_sample_params(
            B_air[:, :, i_wl],
            B_pol45[:, :, i_wl],
            'polarizer'
        )
        tau_extracted = params.tau
        if 0.01 < tau_extracted < 1.5:
            pol45_tau[i_wl] = tau_extracted
        else:
            pol45_tau[i_wl] = pol45_tau_cfg

        # Primary retarder parameters
        params = extract_sample_params(
            B_air[:, :, i_wl],
            B_ret[:, :, i_wl],
            'retarder'
        )
        # Use extracted tau if valid (allow slight exceedance of 1 due to noise)
        tau_extracted = params.tau
        if 0.01 < tau_extracted < 1.5:
            ret_tau[i_wl] = tau_extracted
        else:
            ret_tau[i_wl] = ret_tau_cfg

        # Use characterized retardation if available, otherwise use extracted
        if use_ret_char:
            ret_delta[i_wl] = ret_delta_char[i_wl]
        else:
            ret_delta[i_wl] = params.delta

        # For linear retarders, psi should be ~45° (π/4 radians)
        # Always use extracted psi from eigenvalues (with validation)
        # Fallback to ideal 45° only if extracted value is invalid
        extracted_psi = params.psi
        if np.isnan(extracted_psi) or extracted_psi < 0 or extracted_psi > np.pi/2:
            ret_psi[i_wl] = np.pi / 4  # Fallback to ideal linear retarder
        else:
            ret_psi[i_wl] = extracted_psi

        # Secondary retarder parameters (if available)
        if use_ret45:
            params = extract_sample_params(
                B_air[:, :, i_wl],
                B_ret45[:, :, i_wl],
                'retarder'
            )
            tau_extracted = params.tau
            if 0.01 < tau_extracted < 1.5:
                ret45_tau[i_wl] = tau_extracted
            else:
                ret45_tau[i_wl] = ret45_tau_cfg

            # Use characterized retardation if available
            if use_ret45_char:
                ret45_delta[i_wl] = ret45_delta_char[i_wl]
            else:
                ret45_delta[i_wl] = params.delta

            # Always use extracted psi from eigenvalues (with validation)
            # Fallback to ideal 45° only if extracted value is invalid
            extracted_psi = params.psi
            if np.isnan(extracted_psi) or extracted_psi < 0 or extracted_psi > np.pi/2:
                ret45_psi[i_wl] = np.pi / 4  # Fallback to ideal linear retarder
            else:
                ret45_psi[i_wl] = extracted_psi

    print(f"  Polarizer 0° transmission: {np.mean(pol0_tau):.4f} (mean)")
    print(f"  Polarizer 45° transmission: {np.mean(pol45_tau):.4f} (mean)")
    delta_source = "characterized" if use_ret_char else "extracted"
    print(f"  Retarder FP1 retardation: {np.degrees(np.mean(ret_delta)):.1f}° (mean, {delta_source})")
    print(f"  Retarder FP1 ellipsometric angle: {np.degrees(np.mean(ret_psi)):.1f}° (mean)")

    if use_ret45:
        delta45_source = "characterized" if use_ret45_char else "extracted"
        print(f"  Retarder FP2 retardation: {np.degrees(np.mean(ret45_delta)):.1f}° (mean, {delta45_source})")

    # =========================================================================
    # STEP 7: MAIN ECM CALIBRATION LOOP (WITH OPTIMIZATION)
    # =========================================================================
    print(f"\n[7/7] Performing ECM calibration with optimization...")

    # Initialize output arrays
    W_all = np.zeros((4, 4, n_wavelengths), dtype=np.float64)
    A_all = np.zeros((4, 4, n_wavelengths), dtype=np.float64)
    eigenvalue_ratio = np.zeros(n_wavelengths, dtype=np.float64)
    cond_W = np.zeros(n_wavelengths, dtype=np.float64)
    cond_A = np.zeros(n_wavelengths, dtype=np.float64)

    # Nominal angles from configuration
    pol_theta_nominal = np.array([
        np.radians(cfg.calibration_samples['pol_0'].orientation_deg),
        np.radians(cfg.calibration_samples['pol_45'].orientation_deg)
    ])
    ret_theta_nominal = np.radians(cfg.calibration_samples['ret_90'].orientation_deg)
    ret45_theta_nominal = np.radians(cfg.calibration_samples['ret_45'].orientation_deg)

    # Optimized angles (will be updated during calibration)
    pol_theta = np.zeros((2, n_wavelengths), dtype=np.float64)
    ret_theta = np.zeros(n_wavelengths, dtype=np.float64)
    ret45_theta = np.zeros(n_wavelengths, dtype=np.float64) if use_ret45 else None

    # Setup optimization flags
    opt_flags = OptimizationFlags(
        optimize_polarizer_angles=cfg.ecm.optimize_polarizer_angles,
        optimize_retarder_theta=cfg.ecm.optimize_retarder_angle,
        optimize_retarder_psi=cfg.ecm.optimize_retarder_psi,
        optimize_ret45_theta=cfg.ecm.optimize_retarder_angle and use_ret45
    )

    # Count optimization parameters
    n_opt_params = 0
    if opt_flags.optimize_polarizer_angles:
        n_opt_params += 2
    if opt_flags.optimize_retarder_theta:
        n_opt_params += 1
    if opt_flags.optimize_retarder_psi:
        n_opt_params += 1
    if opt_flags.optimize_ret45_theta:
        n_opt_params += 1

    # Print optimization settings
    print(f"\n--- Optimization Settings ---")
    print(f"  Optimize polarizer angles: {opt_flags.optimize_polarizer_angles}")
    print(f"  Optimize FP1 θ:            {opt_flags.optimize_retarder_theta}")
    print(f"  Optimize FP2 θ:            {opt_flags.optimize_ret45_theta}")
    print(f"  Optimize retarder Ψ:       {opt_flags.optimize_retarder_psi}")
    print(f"  Total parameters:          {n_opt_params}")
    print(f"  Warm start:                {cfg.ecm.use_warm_start}")
    print(f"  Bounds (degrees):          ±{cfg.ecm.bounds.theta_tolerance_deg}")

    # Warm start state
    warm_start = None

    # Progress bar
    pbar = tqdm(range(n_wavelengths), desc="  Calibrating", unit="wl")

    for i_wl in pbar:
        # ---------------------------------------------------------------------
        # Setup fixed parameters for this wavelength
        # ---------------------------------------------------------------------
        fixed_params = FixedParams(
            pol_theta_nominal=pol_theta_nominal,
            pol_tau=np.array([pol0_tau[i_wl], pol45_tau[i_wl]]),
            ret_theta_nominal=ret_theta_nominal,
            ret_tau=ret_tau[i_wl],
            ret_delta=ret_delta[i_wl],
            ret_psi=ret_psi[i_wl],
            ret45_theta_nominal=ret45_theta_nominal if use_ret45 else None,
            ret45_tau=ret45_tau[i_wl] if use_ret45 else None,
            ret45_delta=ret45_delta[i_wl] if use_ret45 else None,
            ret45_psi=ret45_psi[i_wl] if use_ret45 else None,
            use_ret45=use_ret45
        )

        # ---------------------------------------------------------------------
        # Pre-compute Kronecker products (done once per wavelength)
        # ---------------------------------------------------------------------
        kron_C_pol0, kron_C_pol45, kron_C_ret, kron_C_ret45 = precompute_kron_C_matrices(
            B_air[:, :, i_wl],
            B_pol0[:, :, i_wl],
            B_pol45[:, :, i_wl],
            B_ret[:, :, i_wl],
            B_ret45[:, :, i_wl] if use_ret45 else None
        )

        # ---------------------------------------------------------------------
        # Optimization (if enabled)
        # ---------------------------------------------------------------------
        if n_opt_params > 0:
            # Build initial guess
            initial_x = build_initial_x(
                fixed_params,
                opt_flags,
                warm_start if cfg.ecm.use_warm_start else None
            )

            # Run optimization
            opt_result = optimize_ecm_parameters(
                initial_x=initial_x,
                fixed_params=fixed_params,
                kron_C_pol0=kron_C_pol0,
                kron_C_pol45=kron_C_pol45,
                kron_C_ret=kron_C_ret,
                kron_C_ret45=kron_C_ret45,
                opt_flags=opt_flags,
                bounds_deg=cfg.ecm.bounds.theta_tolerance_deg,
                tolerance=cfg.ecm.optimization_tolerance,
                max_iterations=cfg.ecm.optimization_max_iterations
            )

            # Extract optimized values
            theta_pol_opt = opt_result.pol_theta
            theta_ret_opt = opt_result.ret_theta
            psi_ret_opt = opt_result.ret_psi
            theta_ret45_opt = opt_result.ret45_theta

            # Update warm start for next wavelength
            warm_start = {
                'pol_theta': theta_pol_opt,
                'ret_theta': theta_ret_opt,
                'ret_psi': psi_ret_opt,
                'ret45_theta': theta_ret45_opt
            }
        else:
            # No optimization - use nominal values
            theta_pol_opt = pol_theta_nominal
            theta_ret_opt = ret_theta_nominal
            psi_ret_opt = ret_psi[i_wl]
            theta_ret45_opt = ret45_theta_nominal

        # Store optimized angles
        pol_theta[:, i_wl] = theta_pol_opt
        ret_theta[i_wl] = theta_ret_opt
        ret_psi[i_wl] = psi_ret_opt  # Update with optimized psi if applicable
        if use_ret45:
            ret45_theta[i_wl] = theta_ret45_opt

        # ---------------------------------------------------------------------
        # Build final Mueller matrices with optimized parameters
        # ---------------------------------------------------------------------
        M_pol0 = polarizer(theta=theta_pol_opt[0], tau=pol0_tau[i_wl])
        M_pol45 = polarizer(theta=theta_pol_opt[1], tau=pol45_tau[i_wl])
        M_ret = elliptic_retarder(
            theta=theta_ret_opt,
            delta=ret_delta[i_wl],
            psi=psi_ret_opt,
            tau=ret_tau[i_wl]
        )

        # ---------------------------------------------------------------------
        # Build H matrices with optimized parameters
        # ---------------------------------------------------------------------
        H_matrices = []

        H_pol0 = build_H_matrix(M_pol0, B_air[:, :, i_wl], B_pol0[:, :, i_wl])
        H_matrices.append(H_pol0)

        H_pol45 = build_H_matrix(M_pol45, B_air[:, :, i_wl], B_pol45[:, :, i_wl])
        H_matrices.append(H_pol45)

        H_ret = build_H_matrix(M_ret, B_air[:, :, i_wl], B_ret[:, :, i_wl])
        H_matrices.append(H_ret)

        if use_ret45:
            M_ret45 = elliptic_retarder(
                theta=theta_ret45_opt,
                delta=ret45_delta[i_wl],
                psi=ret45_psi[i_wl],
                tau=ret45_tau[i_wl]
            )
            H_ret45 = build_H_matrix(M_ret45, B_air[:, :, i_wl], B_ret45[:, :, i_wl])
            H_matrices.append(H_ret45)

        # ---------------------------------------------------------------------
        # Build K matrix and solve for W
        # ---------------------------------------------------------------------
        K = build_K_matrix(H_matrices)
        W, w_diag = solve_W(K)

        # Store results
        W_all[:, :, i_wl] = W
        eigenvalue_ratio[i_wl] = w_diag.ratio_16_15
        cond_W[i_wl] = w_diag.condition_number

        # ---------------------------------------------------------------------
        # Solve for A
        # ---------------------------------------------------------------------
        A, a_diag = solve_A(W, B_air[:, :, i_wl])

        # Store results
        A_all[:, :, i_wl] = A
        cond_A[i_wl] = a_diag.condition_number

        # ---------------------------------------------------------------------
        # Update progress
        # ---------------------------------------------------------------------
        if progress_callback:
            progress_callback(i_wl + 1, n_wavelengths, eigenvalue_ratio[i_wl])

        # Update progress bar postfix
        pbar.set_postfix({
            'λ': f'{wavelengths[i_wl]:.0f}nm',
            'ratio': f'{eigenvalue_ratio[i_wl]:.1e}'
        })

    pbar.close()

    # =========================================================================
    # BUILD RESULTS
    # =========================================================================

    # Retarder parameters
    ret_params = RetarderCalibrationParams(
        tau=ret_tau,
        delta=ret_delta,
        theta=ret_theta,
        psi=ret_psi
    )

    ret45_params = None
    if use_ret45:
        ret45_params = RetarderCalibrationParams(
            tau=ret45_tau,
            delta=ret45_delta,
            theta=ret45_theta,
            psi=ret45_psi
        )

    # Calibration result
    result = CalibrationResult(
        W=W_all,
        A=A_all,
        wavelengths=wavelengths,
        pol_theta=pol_theta,
        ret_params=ret_params,
        ret45_params=ret45_params,
        inv_W_mod=basis.inv_W_mod,
        wl_indices=wl_indices,
        cal_files=cal_files,
        use_ret45=use_ret45
    )

    # Diagnostics
    diagnostics = CalibrationDiagnostics(
        eigenvalue_ratio=eigenvalue_ratio,
        cond_W=cond_W,
        cond_A=cond_A,
        B_air=B_air,
        B_pol0=B_pol0,
        B_pol45=B_pol45,
        B_ret=B_ret,
        B_ret45=B_ret45,
        I_dark=I_dark,
        pol0_params={'tau': pol0_tau},
        pol45_params={'tau': pol45_tau}
    )

    # =========================================================================
    # PRINT SUMMARY
    # =========================================================================
    _print_calibration_summary(result, diagnostics)

    return result, diagnostics


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _print_calibration_summary(
    result: CalibrationResult,
    diagnostics: CalibrationDiagnostics
) -> None:
    """
    Print calibration summary statistics.
    """
    print()
    print("=" * 60)
    print("CALIBRATION SUMMARY")
    print("=" * 60)

    n_wl = len(result.wavelengths)
    ratio = diagnostics.eigenvalue_ratio

    print(f"\nWavelengths calibrated: {n_wl}")
    print(f"Wavelength range: {result.wavelengths.min():.1f} - {result.wavelengths.max():.1f} nm")
    print(f"Second retarder used: {result.use_ret45}")

    print(f"\nEigenvalue ratio λ₁₆/λ₁₅:")
    print(f"  Mean:   {np.mean(ratio):.2e}")
    print(f"  Median: {np.median(ratio):.2e}")
    print(f"  Min:    {np.min(ratio):.2e}")
    print(f"  Max:    {np.max(ratio):.2e}")

    # Quality assessment (thresholds: Excellent < 1e-4, Good < 1e-3, Acceptable < 1e-2, Marginal < 0.1)
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
        print(f"\n  WARNING: High W condition number at some wavelengths")
    if np.max(diagnostics.cond_A) > 100:
        print(f"\n  WARNING: High A condition number at some wavelengths")

    print(f"\nOptimized polarizer orientations (mean ± std):")
    print(f"  Polarizer 0°:  {np.degrees(np.mean(result.pol_theta[0, :])):.2f}° ± {np.degrees(np.std(result.pol_theta[0, :])):.2f}°")
    print(f"  Polarizer 45°: {np.degrees(np.mean(result.pol_theta[1, :])):.2f}° ± {np.degrees(np.std(result.pol_theta[1, :])):.2f}°")

    print(f"\nRetarder FP1 parameters:")
    print(f"  θ:            {np.degrees(np.mean(result.ret_params.theta)):.2f}° ± {np.degrees(np.std(result.ret_params.theta)):.2f}°")
    print(f"  Ψ:            {np.degrees(np.mean(result.ret_params.psi)):.2f}° ± {np.degrees(np.std(result.ret_params.psi)):.2f}° (ideal: 45°)")
    print(f"  τ:            {np.mean(result.ret_params.tau):.4f} ± {np.std(result.ret_params.tau):.4f}")
    print(f"  δ:            {np.degrees(np.mean(result.ret_params.delta)):.1f}° ± {np.degrees(np.std(result.ret_params.delta)):.1f}°")

    if result.use_ret45 and result.ret45_params is not None:
        print(f"\nRetarder FP2 parameters:")
        print(f"  θ:            {np.degrees(np.mean(result.ret45_params.theta)):.2f}° ± {np.degrees(np.std(result.ret45_params.theta)):.2f}°")
        print(f"  Ψ:            {np.degrees(np.mean(result.ret45_params.psi)):.2f}° ± {np.degrees(np.std(result.ret45_params.psi)):.2f}°")
        print(f"  τ:            {np.mean(result.ret45_params.tau):.4f} ± {np.std(result.ret45_params.tau):.4f}")
        print(f"  δ:            {np.degrees(np.mean(result.ret45_params.delta)):.1f}° ± {np.degrees(np.std(result.ret45_params.delta)):.1f}°")

    print()
    print("=" * 60)
    print("CALIBRATION COMPLETE")
    print("=" * 60)
    print()
