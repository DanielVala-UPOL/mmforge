"""
ECM Calibration Optimization Module

This module provides optimization functions for the ECM calibration algorithm.
The optimization minimizes the eigenvalue ratio λ₁₆/λ₁₅ of the K matrix by
adjusting calibration sample parameters (polarizer angles, retarder orientations).

Functions
---------
ecm_cost_function(x, fixed_params, kron_C_matrices, opt_flags)
    Cost function for ECM optimization (eigenvalue ratio λ₁₆/λ₁₅)

optimize_ecm_parameters(initial_params, fixed_params, kron_C_matrices, opt_flags, cfg)
    Run optimization to minimize eigenvalue ratio

Theory
------
The ECM calibration quality depends on how accurately the Mueller matrices of
calibration samples match the measured intensity matrices. The eigenvalue ratio
of the K matrix quantifies this match:
- ratio < 1e-4: Excellent match
- ratio < 1e-3: Good match
- ratio < 1e-2: Acceptable match
- ratio < 0.1: Marginal match
- ratio >= 0.1: Poor match

By optimizing the sample parameters (angles), we find the values that best
explain the measured data, improving calibration quality.

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999)
"""

import numpy as np
from numpy import ndarray
from dataclasses import dataclass
from typing import Tuple, Dict, Optional, Any
from scipy.optimize import minimize

from ecm.utils.mueller_matrices import polarizer, elliptic_retarder


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class OptimizationFlags:
    """
    Flags controlling which parameters to optimize.

    Attributes
    ----------
    optimize_polarizer_angles : bool
        Optimize both polarizer orientation angles (θ_pol0, θ_pol45).

    optimize_retarder_theta : bool
        Optimize primary retarder (FP1) orientation angle.

    optimize_retarder_psi : bool
        Optimize primary retarder ellipsometric angle (usually kept fixed at 45°).

    optimize_ret45_theta : bool
        Optimize secondary retarder (FP2) orientation angle (if FP2 is used).
    """
    optimize_polarizer_angles: bool = True
    optimize_retarder_theta: bool = True
    optimize_retarder_psi: bool = False
    optimize_ret45_theta: bool = False


@dataclass
class FixedParams:
    """
    Fixed parameters for ECM optimization.

    These parameters are not optimized but are needed to build Mueller matrices.

    Attributes
    ----------
    pol_theta_nominal : ndarray, shape (2,)
        Nominal polarizer angles [θ_pol0, θ_pol45] in radians.

    pol_tau : ndarray, shape (2,)
        Polarizer transmission coefficients [τ_pol0, τ_pol45].

    ret_theta_nominal : float
        Nominal primary retarder (FP1) orientation in radians.

    ret_tau : float
        Primary retarder transmission coefficient.

    ret_delta : float
        Primary retarder retardation in radians (from characterization).

    ret_psi : float
        Primary retarder ellipsometric angle in radians.

    ret45_theta_nominal : float, optional
        Nominal secondary retarder (FP2) orientation in radians.

    ret45_tau : float, optional
        Secondary retarder transmission coefficient.

    ret45_delta : float, optional
        Secondary retarder retardation in radians.

    ret45_psi : float, optional
        Secondary retarder ellipsometric angle in radians.

    use_ret45 : bool
        Whether secondary retarder is used.
    """
    pol_theta_nominal: ndarray
    pol_tau: ndarray
    ret_theta_nominal: float
    ret_tau: float
    ret_delta: float
    ret_psi: float
    ret45_theta_nominal: Optional[float] = None
    ret45_tau: Optional[float] = None
    ret45_delta: Optional[float] = None
    ret45_psi: Optional[float] = None
    use_ret45: bool = False


@dataclass
class OptimizationResult:
    """
    Results from ECM parameter optimization.

    Attributes
    ----------
    pol_theta : ndarray, shape (2,)
        Optimized polarizer angles [θ_pol0, θ_pol45] in radians.

    ret_theta : float
        Optimized primary retarder orientation in radians.

    ret_psi : float
        Optimized (or fixed) primary retarder ellipsometric angle in radians.

    ret45_theta : float, optional
        Optimized secondary retarder orientation in radians.

    final_cost : float
        Final eigenvalue ratio after optimization.

    success : bool
        Whether optimization converged successfully.

    n_iterations : int
        Number of iterations used.
    """
    pol_theta: ndarray
    ret_theta: float
    ret_psi: float
    ret45_theta: Optional[float]
    final_cost: float
    success: bool
    n_iterations: int


# =============================================================================
# COST FUNCTION
# =============================================================================

def ecm_cost_function(
    x: ndarray,
    fixed_params: FixedParams,
    kron_C_pol0: ndarray,
    kron_C_pol45: ndarray,
    kron_C_ret: ndarray,
    kron_C_ret45: Optional[ndarray],
    opt_flags: OptimizationFlags
) -> float:
    """
    Cost function for ECM optimization.

    Computes the eigenvalue ratio λ₁₆/λ₁₅ of the K matrix for given parameters.
    This is the quantity to be minimized.

    Parameters
    ----------
    x : ndarray
        Optimization variables (packed according to opt_flags).

    fixed_params : FixedParams
        Fixed parameters not being optimized.

    kron_C_pol0 : ndarray, shape (16, 16)
        Pre-computed kron(C_pol0.T, I4) where C = B_air^(-1) @ B_pol0.

    kron_C_pol45 : ndarray, shape (16, 16)
        Pre-computed kron(C_pol45.T, I4).

    kron_C_ret : ndarray, shape (16, 16)
        Pre-computed kron(C_ret.T, I4).

    kron_C_ret45 : ndarray or None
        Pre-computed kron(C_ret45.T, I4) if FP2 is used.

    opt_flags : OptimizationFlags
        Flags indicating which parameters are being optimized.

    Returns
    -------
    cost : float
        Eigenvalue ratio λ₁₆/λ₁₅. Returns inf if K is singular.

    Notes
    -----
    The cost function builds K = Σ H_M^T @ H_M where:
        H_M = kron(I4, M) - kron(C.T, I4)

    The eigenvalues of K are sorted in descending order, and the ratio
    λ₁₆/λ₁₅ measures how close the smallest eigenvalue is to zero.
    """
    # -------------------------------------------------------------------------
    # Unpack optimization variables
    # -------------------------------------------------------------------------
    idx = 0

    # Polarizer angles
    if opt_flags.optimize_polarizer_angles:
        theta_pol0 = x[idx]
        theta_pol45 = x[idx + 1]
        idx += 2
    else:
        theta_pol0 = fixed_params.pol_theta_nominal[0]
        theta_pol45 = fixed_params.pol_theta_nominal[1]

    # Primary retarder theta
    if opt_flags.optimize_retarder_theta:
        theta_ret = x[idx]
        idx += 1
    else:
        theta_ret = fixed_params.ret_theta_nominal

    # Primary retarder psi
    if opt_flags.optimize_retarder_psi:
        psi_ret = x[idx]
        idx += 1
    else:
        psi_ret = fixed_params.ret_psi

    # Secondary retarder theta
    if opt_flags.optimize_ret45_theta and fixed_params.use_ret45:
        theta_ret45 = x[idx]
    else:
        theta_ret45 = fixed_params.ret45_theta_nominal

    # -------------------------------------------------------------------------
    # Get fixed parameters
    # -------------------------------------------------------------------------
    pol_tau = fixed_params.pol_tau
    ret_tau = fixed_params.ret_tau
    ret_delta = fixed_params.ret_delta

    # -------------------------------------------------------------------------
    # Build K matrix
    # K = Σ H_M^T @ H_M
    # H_M = kron(I4, M) - kron(C.T, I4)
    # -------------------------------------------------------------------------
    I4 = np.eye(4)
    K = np.zeros((16, 16), dtype=np.float64)

    # Polarizer 0°
    M_pol0 = polarizer(theta=theta_pol0, tau=pol_tau[0])
    kron_I_M_pol0 = np.kron(I4, M_pol0)
    H_pol0 = kron_I_M_pol0 - kron_C_pol0
    K += H_pol0.T @ H_pol0

    # Polarizer 45°
    M_pol45 = polarizer(theta=theta_pol45, tau=pol_tau[1])
    kron_I_M_pol45 = np.kron(I4, M_pol45)
    H_pol45 = kron_I_M_pol45 - kron_C_pol45
    K += H_pol45.T @ H_pol45

    # Primary retarder (FP1)
    M_ret = elliptic_retarder(theta=theta_ret, delta=ret_delta, psi=psi_ret, tau=ret_tau)
    kron_I_M_ret = np.kron(I4, M_ret)
    H_ret = kron_I_M_ret - kron_C_ret
    K += H_ret.T @ H_ret

    # Secondary retarder (FP2) if available
    if fixed_params.use_ret45 and kron_C_ret45 is not None:
        ret45_tau = fixed_params.ret45_tau
        ret45_psi = fixed_params.ret45_psi
        ret45_delta = fixed_params.ret45_delta

        M_ret45 = elliptic_retarder(
            theta=theta_ret45,
            delta=ret45_delta,
            psi=ret45_psi,
            tau=ret45_tau
        )
        kron_I_M_ret45 = np.kron(I4, M_ret45)
        H_ret45 = kron_I_M_ret45 - kron_C_ret45
        K += H_ret45.T @ H_ret45

    # -------------------------------------------------------------------------
    # Compute eigenvalue ratio
    # -------------------------------------------------------------------------
    eigenvalues = np.linalg.eigvalsh(K)  # Real symmetric matrix
    eigenvalues = np.sort(eigenvalues)[::-1]  # Sort descending

    # λ₁₆/λ₁₅ ratio (smallest / second-smallest in 1-indexed MATLAB notation)
    # In 0-indexed Python: eigenvalues[15] / eigenvalues[14]
    if eigenvalues[14] > 1e-15:
        cost = np.abs(eigenvalues[15]) / eigenvalues[14]
    else:
        cost = np.inf

    return cost


# =============================================================================
# OPTIMIZATION WRAPPER
# =============================================================================

def optimize_ecm_parameters(
    initial_x: ndarray,
    fixed_params: FixedParams,
    kron_C_pol0: ndarray,
    kron_C_pol45: ndarray,
    kron_C_ret: ndarray,
    kron_C_ret45: Optional[ndarray],
    opt_flags: OptimizationFlags,
    bounds_deg: float = 5.0,
    tolerance: float = 1e-8,
    max_iterations: int = 100
) -> OptimizationResult:
    """
    Optimize ECM calibration parameters to minimize eigenvalue ratio.

    Uses scipy.optimize.minimize with L-BFGS-B method (bounded optimization)
    to find the parameter values that minimize λ₁₆/λ₁₅.

    Parameters
    ----------
    initial_x : ndarray
        Initial values for optimization variables.

    fixed_params : FixedParams
        Fixed parameters not being optimized.

    kron_C_pol0 : ndarray, shape (16, 16)
        Pre-computed kron(C_pol0.T, I4).

    kron_C_pol45 : ndarray, shape (16, 16)
        Pre-computed kron(C_pol45.T, I4).

    kron_C_ret : ndarray, shape (16, 16)
        Pre-computed kron(C_ret.T, I4).

    kron_C_ret45 : ndarray or None
        Pre-computed kron(C_ret45.T, I4) if FP2 is used.

    opt_flags : OptimizationFlags
        Flags indicating which parameters to optimize.

    bounds_deg : float, optional
        Allowed deviation from initial values in degrees. Default: 5.0.

    tolerance : float, optional
        Optimization tolerance. Default: 1e-8.

    max_iterations : int, optional
        Maximum number of iterations. Default: 100.

    Returns
    -------
    result : OptimizationResult
        Optimized parameters and convergence information.

    Notes
    -----
    The optimization uses bounded L-BFGS-B to match MATLAB's fmincon behavior.
    Bounds are set symmetrically around the initial values.
    """
    # -------------------------------------------------------------------------
    # Build bounds
    # -------------------------------------------------------------------------
    bounds_rad = np.radians(bounds_deg)
    bounds = [(x0 - bounds_rad, x0 + bounds_rad) for x0 in initial_x]

    # -------------------------------------------------------------------------
    # Define cost function wrapper
    # -------------------------------------------------------------------------
    def cost_wrapper(x):
        return ecm_cost_function(
            x,
            fixed_params,
            kron_C_pol0,
            kron_C_pol45,
            kron_C_ret,
            kron_C_ret45,
            opt_flags
        )

    # -------------------------------------------------------------------------
    # Run optimization
    # -------------------------------------------------------------------------
    result = minimize(
        cost_wrapper,
        initial_x,
        method='L-BFGS-B',
        bounds=bounds,
        options={
            'ftol': tolerance,
            'gtol': 1e-12,
            'maxiter': max_iterations,
        }
    )

    # -------------------------------------------------------------------------
    # Extract optimized values
    # -------------------------------------------------------------------------
    x_opt = result.x
    idx = 0

    # Polarizer angles
    if opt_flags.optimize_polarizer_angles:
        pol_theta_opt = np.array([x_opt[idx], x_opt[idx + 1]])
        idx += 2
    else:
        pol_theta_opt = fixed_params.pol_theta_nominal.copy()

    # Primary retarder theta
    if opt_flags.optimize_retarder_theta:
        ret_theta_opt = x_opt[idx]
        idx += 1
    else:
        ret_theta_opt = fixed_params.ret_theta_nominal

    # Primary retarder psi
    if opt_flags.optimize_retarder_psi:
        ret_psi_opt = x_opt[idx]
        idx += 1
    else:
        ret_psi_opt = fixed_params.ret_psi

    # Secondary retarder theta
    if opt_flags.optimize_ret45_theta and fixed_params.use_ret45:
        ret45_theta_opt = x_opt[idx]
    else:
        ret45_theta_opt = fixed_params.ret45_theta_nominal

    # -------------------------------------------------------------------------
    # Build result
    # -------------------------------------------------------------------------
    return OptimizationResult(
        pol_theta=pol_theta_opt,
        ret_theta=ret_theta_opt,
        ret_psi=ret_psi_opt,
        ret45_theta=ret45_theta_opt,
        final_cost=result.fun,
        success=result.success,
        n_iterations=result.nit
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def build_initial_x(
    fixed_params: FixedParams,
    opt_flags: OptimizationFlags,
    warm_start: Optional[Dict[str, Any]] = None
) -> ndarray:
    """
    Build initial optimization vector from parameters.

    Parameters
    ----------
    fixed_params : FixedParams
        Fixed and nominal parameter values.

    opt_flags : OptimizationFlags
        Flags indicating which parameters to optimize.

    warm_start : dict, optional
        Previous wavelength's optimized values for warm start.
        Keys: 'pol_theta', 'ret_theta', 'ret_psi', 'ret45_theta'

    Returns
    -------
    x0 : ndarray
        Initial optimization vector.
    """
    x0_list = []

    if opt_flags.optimize_polarizer_angles:
        if warm_start is not None and 'pol_theta' in warm_start:
            x0_list.extend(warm_start['pol_theta'])
        else:
            x0_list.extend(fixed_params.pol_theta_nominal)

    if opt_flags.optimize_retarder_theta:
        if warm_start is not None and 'ret_theta' in warm_start:
            x0_list.append(warm_start['ret_theta'])
        else:
            x0_list.append(fixed_params.ret_theta_nominal)

    if opt_flags.optimize_retarder_psi:
        if warm_start is not None and 'ret_psi' in warm_start:
            x0_list.append(warm_start['ret_psi'])
        else:
            x0_list.append(fixed_params.ret_psi)

    if opt_flags.optimize_ret45_theta and fixed_params.use_ret45:
        if warm_start is not None and 'ret45_theta' in warm_start:
            x0_list.append(warm_start['ret45_theta'])
        else:
            x0_list.append(fixed_params.ret45_theta_nominal)

    return np.array(x0_list)


def precompute_kron_C_matrices(
    B_air: ndarray,
    B_pol0: ndarray,
    B_pol45: ndarray,
    B_ret: ndarray,
    B_ret45: Optional[ndarray] = None
) -> Tuple[ndarray, ndarray, ndarray, Optional[ndarray]]:
    """
    Pre-compute Kronecker products of C matrices for optimization.

    The C matrices are C = B_air^(-1) @ B_sample, and we compute
    kron(C.T, I4) for each sample. This is done once per wavelength
    to avoid redundant computation during optimization iterations.

    Parameters
    ----------
    B_air : ndarray, shape (4, 4)
        Air intensity matrix.

    B_pol0 : ndarray, shape (4, 4)
        Polarizer 0° intensity matrix.

    B_pol45 : ndarray, shape (4, 4)
        Polarizer 45° intensity matrix.

    B_ret : ndarray, shape (4, 4)
        Primary retarder intensity matrix.

    B_ret45 : ndarray or None
        Secondary retarder intensity matrix (if used).

    Returns
    -------
    kron_C_pol0 : ndarray, shape (16, 16)
    kron_C_pol45 : ndarray, shape (16, 16)
    kron_C_ret : ndarray, shape (16, 16)
    kron_C_ret45 : ndarray or None
    """
    I4 = np.eye(4)

    # C = B_air^(-1) @ B_sample = solve(B_air, B_sample)
    C_pol0 = np.linalg.solve(B_air, B_pol0)
    C_pol45 = np.linalg.solve(B_air, B_pol45)
    C_ret = np.linalg.solve(B_air, B_ret)

    # kron(C.T, I4) - note the transpose on C
    kron_C_pol0 = np.kron(C_pol0.T, I4)
    kron_C_pol45 = np.kron(C_pol45.T, I4)
    kron_C_ret = np.kron(C_ret.T, I4)

    kron_C_ret45 = None
    if B_ret45 is not None:
        C_ret45 = np.linalg.solve(B_air, B_ret45)
        kron_C_ret45 = np.kron(C_ret45.T, I4)

    return kron_C_pol0, kron_C_pol45, kron_C_ret, kron_C_ret45
