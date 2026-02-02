"""
ECM Eigenvalue Solver for PSG and PSA Matrix Extraction

This module solves the eigenvalue problem at the core of the ECM algorithm
to extract the PSG (W) and PSA (A) modulation matrices.

Functions
---------
solve_W(K)
    Extract PSG matrix W from eigenvalue decomposition of K
solve_A(W, B_air)
    Compute PSA matrix A from W and air measurement

Theory
------
The ECM method determines the PSG matrix W as the eigenvector of the
accumulated constraint matrix K corresponding to its smallest eigenvalue:

    K @ vec(W) = λ₁₆ @ vec(W)

where λ₁₆ ≈ 0 for a consistent calibration. The 4×4 matrix W is obtained
by reshaping the 16-element eigenvector using column-major (Fortran) order.

Once W is known, the PSA matrix A is computed from the air measurement
(M = I for air):

    B_air = A @ I @ W = A @ W
    A = B_air @ W^(-1)

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999), Eqs. 16, 20-21
"""

import numpy as np
import scipy.linalg
from numpy import ndarray
from dataclasses import dataclass
from typing import Tuple


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class WDiagnostics:
    """
    Diagnostics from PSG matrix (W) solution.

    Contains eigenvalue information and quality metrics from the
    eigenvalue decomposition of K.

    Attributes
    ----------
    eigenvalues : ndarray, shape (16,)
        All 16 eigenvalues of K, sorted in DESCENDING order.
        eigenvalues[0] is the largest, eigenvalues[15] is the smallest.

    lambda_16 : float
        Smallest eigenvalue (should be ≈ 0 for good calibration).
        This is the eigenvalue whose eigenvector gives W.

    lambda_15 : float
        Second smallest eigenvalue (reference for quality metric).
        Should be significantly larger than lambda_16.

    ratio_16_15 : float
        Quality metric: λ₁₆/λ₁₅.
        - < 1e-5: Excellent calibration
        - < 1e-3: Good calibration
        - < 0.1: Acceptable calibration
        - > 0.1: Poor calibration (check data quality)

    condition_number : float
        Condition number of W. Should be < 100 for well-aligned system.
        High values indicate near-singular W (alignment issues).

    Notes
    -----
    The eigenvalue ratio λ₁₆/λ₁₅ is the primary quality metric. A small ratio
    indicates that the calibration samples provide consistent constraints,
    and W lies cleanly in the null space of the K matrix.
    """
    eigenvalues: ndarray
    lambda_16: float
    lambda_15: float
    ratio_16_15: float
    condition_number: float


@dataclass
class ADiagnostics:
    """
    Diagnostics from PSA matrix (A) solution.

    Contains condition number and determinant information for A.

    Attributes
    ----------
    condition_number : float
        Condition number of A. Should be < 100 for well-aligned system.
        High values indicate alignment or measurement issues.

    determinant : float
        Determinant of A. For a physical PSA matrix, |det(A)| should be
        close to 1 (within a few percent).

    cond_W : float
        Condition number of W (copied for convenience).
    """
    condition_number: float
    determinant: float
    cond_W: float


# =============================================================================
# PSG MATRIX (W) SOLVER
# =============================================================================

def solve_W(K: ndarray) -> Tuple[ndarray, WDiagnostics]:
    """
    Solve for PSG modulation matrix W from accumulated constraint matrix K.

    W is found as the eigenvector of K corresponding to its smallest
    eigenvalue, reshaped to a 4×4 matrix.

    Reference: Compain et al., Appl. Opt. 38, 3490-3502 (1999), Eq. 20-21

    Parameters
    ----------
    K : ndarray, shape (16, 16)
        Accumulated constraint matrix from build_K_matrix().

    Returns
    -------
    W : ndarray, shape (4, 4)
        PSG modulation matrix. Normalized so W[0,0] > 0.

    diagnostics : WDiagnostics
        Eigenvalue information and quality metrics.

    Raises
    ------
    ValueError
        If K is not 16×16 or has negative eigenvalues.

    Examples
    --------
    >>> K = build_K_matrix([H_pol0, H_pol45, H_ret])
    >>> W, diag = solve_W(K)
    >>> print(f"Eigenvalue ratio: {diag.ratio_16_15:.2e}")
    >>> print(f"W condition number: {diag.condition_number:.2f}")

    Notes
    -----
    **Eigenvalue Ordering (CRITICAL):**

    SciPy's `scipy.linalg.eigh` returns eigenvalues in ASCENDING order.
    We reverse to get DESCENDING order for consistency with MATLAB,
    where we refer to λ₁ (largest) through λ₁₆ (smallest).

    After reversal:
    - eigenvalues[0] = λ₁ (largest)
    - eigenvalues[14] = λ₁₅ (second smallest)
    - eigenvalues[15] = λ₁₆ (smallest) → eigenvector gives W

    **Fortran (Column-Major) Reshaping:**

    The 16-element eigenvector is reshaped to 4×4 using Fortran order
    to match MATLAB's column-major convention:

        W = W_vec.reshape((4, 4), order='F')

    This is CRITICAL for correct results.

    **W Normalization:**

    W is normalized so that W[0,0] > 0. This fixes the sign ambiguity
    inherent in eigenvector solutions (if v is an eigenvector, so is -v).
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    if K.shape != (16, 16):
        raise ValueError(f"K must be 16×16, got {K.shape}")

    # -------------------------------------------------------------------------
    # Eigenvalue decomposition
    #
    # Use scipy.linalg.eigh for symmetric matrices:
    # - More numerically stable than np.linalg.eig
    # - Returns real eigenvalues
    # - Returns eigenvalues sorted in ASCENDING order
    # -------------------------------------------------------------------------
    eigenvalues, eigenvectors = scipy.linalg.eigh(K)

    # -------------------------------------------------------------------------
    # Reverse to get DESCENDING order (to match MATLAB convention)
    #
    # After reversal:
    #   eigenvalues[0] = largest = λ₁
    #   eigenvalues[15] = smallest = λ₁₆
    # -------------------------------------------------------------------------
    eigenvalues = eigenvalues[::-1]
    eigenvectors = eigenvectors[:, ::-1]

    # -------------------------------------------------------------------------
    # Extract W from eigenvector of smallest eigenvalue
    #
    # W_vec is the last column (index -1) after reversal
    # This corresponds to λ₁₆, the smallest eigenvalue
    # -------------------------------------------------------------------------
    W_vec = eigenvectors[:, -1]

    # -------------------------------------------------------------------------
    # Reshape to 4×4 using Fortran (column-major) order
    #
    # CRITICAL: order='F' matches MATLAB's column-major convention!
    #   W_vec[0:4] → W[:, 0]  (first column)
    #   W_vec[4:8] → W[:, 1]  (second column)
    #   etc.
    # -------------------------------------------------------------------------
    W = W_vec.reshape((4, 4), order='F')

    # -------------------------------------------------------------------------
    # Normalize so W[0,0] > 0
    #
    # This fixes the sign ambiguity: if v is an eigenvector, so is -v.
    # We choose the sign so that W[0,0] (related to total intensity) is positive.
    # -------------------------------------------------------------------------
    if W[0, 0] < 0:
        W = -W

    # -------------------------------------------------------------------------
    # Compute diagnostics
    # -------------------------------------------------------------------------
    lambda_16 = eigenvalues[-1]  # Smallest eigenvalue (last after reversal)
    lambda_15 = eigenvalues[-2]  # Second smallest

    # Quality metric: ratio of smallest to second-smallest eigenvalue
    # Small ratio indicates good calibration (W is cleanly in null space)
    if lambda_15 > 0:
        ratio_16_15 = np.abs(lambda_16) / lambda_15
    else:
        # Shouldn't happen for proper K, but handle gracefully
        ratio_16_15 = np.inf

    # Condition number of W
    condition_number = np.linalg.cond(W)

    # Package diagnostics
    diagnostics = WDiagnostics(
        eigenvalues=eigenvalues,
        lambda_16=lambda_16,
        lambda_15=lambda_15,
        ratio_16_15=ratio_16_15,
        condition_number=condition_number
    )

    return W, diagnostics


# =============================================================================
# PSA MATRIX (A) SOLVER
# =============================================================================

def solve_A(
    W: ndarray,
    B_air: ndarray
) -> Tuple[ndarray, ADiagnostics]:
    """
    Compute PSA modulation matrix A from W and air measurement.

    For the air (straight-through) measurement where M = I:
        B_air = A @ I @ W = A @ W
        A = B_air @ W^(-1)

    Reference: Compain et al., Appl. Opt. 38, 3490-3502 (1999), Eq. 16

    Parameters
    ----------
    W : ndarray, shape (4, 4)
        PSG modulation matrix from solve_W().

    B_air : ndarray, shape (4, 4)
        Air (straight-through) intensity matrix.

    Returns
    -------
    A : ndarray, shape (4, 4)
        PSA modulation matrix. Normalized so A[0,0] > 0.

    diagnostics : ADiagnostics
        Condition number and determinant information.

    Raises
    ------
    ValueError
        If W is singular (condition number > 1e10).

    Examples
    --------
    >>> W, _ = solve_W(K)
    >>> A, diag = solve_A(W, B_air)
    >>> print(f"A condition number: {diag.condition_number:.2f}")
    >>> print(f"det(A): {diag.determinant:.4f}")

    Notes
    -----
    **Numerical Stability:**

    We compute A = B_air @ W^(-1) using `solve` from the right:
        A @ W = B_air
        A = solve(W.T, B_air.T).T

    This is more numerically stable than explicit inversion.

    **A Normalization:**

    A is normalized so that A[0,0] > 0, consistent with the W normalization.
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    if W.shape != (4, 4):
        raise ValueError(f"W must be 4×4, got {W.shape}")

    if B_air.shape != (4, 4):
        raise ValueError(f"B_air must be 4×4, got {B_air.shape}")

    # -------------------------------------------------------------------------
    # Check conditioning of W
    # -------------------------------------------------------------------------
    cond_W = np.linalg.cond(W)
    if cond_W > 1e10:
        raise ValueError(
            f"W is poorly conditioned (cond={cond_W:.2e}). "
            f"This may indicate inconsistent calibration samples or "
            f"measurement issues. Check eigenvalue ratio diagnostics."
        )

    # -------------------------------------------------------------------------
    # Compute A = B_air @ W^(-1)
    #
    # For numerical stability, we solve the system A @ W = B_air
    # Rewriting: W.T @ A.T = B_air.T
    # So: A.T = solve(W.T, B_air.T)
    # And: A = solve(W.T, B_air.T).T
    # -------------------------------------------------------------------------
    A = np.linalg.solve(W.T, B_air.T).T

    # -------------------------------------------------------------------------
    # Normalize so A[0,0] > 0
    # -------------------------------------------------------------------------
    if A[0, 0] < 0:
        A = -A

    # -------------------------------------------------------------------------
    # Compute diagnostics
    # -------------------------------------------------------------------------
    condition_number = np.linalg.cond(A)
    determinant = np.linalg.det(A)

    diagnostics = ADiagnostics(
        condition_number=condition_number,
        determinant=determinant,
        cond_W=cond_W
    )

    return A, diagnostics
