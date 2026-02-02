"""
ECM Constraint Matrix Construction

This module builds the H and K matrices that encode the eigenvalue constraint
at the heart of the ECM (Eigenvalue Calibration Method) algorithm.

Functions
---------
build_H_matrix(M, B_air, B_sample)
    Build the ECM constraint matrix H_M for one calibration sample
build_K_matrix(H_matrices)
    Accumulate H matrices into the combined K matrix

Theory
------
The ECM method exploits the fact that for a calibration sample with known
Mueller matrix M, the PSG matrix W lies in the null space of a mapping H_M:

    H_M(W) = M @ W - W @ C = 0

where C = B_air^(-1) @ B_sample.

When this is vectorized using Kronecker products:

    vec(M @ W) = (I₄ ⊗ M) @ vec(W)
    vec(W @ C) = (C^T ⊗ I₄) @ vec(W)

So the constraint becomes:

    H_M @ vec(W) = 0
    where H_M = (I₄ ⊗ M) - (C^T ⊗ I₄)

Multiple calibration samples (polarizers at different angles, retarder) each
contribute an H_M matrix. These are combined into a single K matrix:

    K = Σᵢ H_Mᵢ^T @ H_Mᵢ

The PSG matrix W is found as the eigenvector of K corresponding to its
smallest eigenvalue (which should be approximately zero for a correct solution).

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999), Eqs. 14, 19-20
"""

import numpy as np
from numpy import ndarray
from typing import List


# =============================================================================
# H MATRIX CONSTRUCTION
# =============================================================================

def build_H_matrix(
    M: ndarray,
    B_air: ndarray,
    B_sample: ndarray
) -> ndarray:
    """
    Build ECM constraint matrix H_M for a calibration sample.

    The matrix H_M encodes the constraint that the PSG matrix W lies in
    its null space: H_M @ vec(W) ≈ 0.

    Reference: Compain et al., Appl. Opt. 38, 3490-3502 (1999), Eq. 14

    Parameters
    ----------
    M : ndarray, shape (4, 4)
        Mueller matrix of the calibration sample.
        This should be the KNOWN Mueller matrix (from theory or characterization).

    B_air : ndarray, shape (4, 4)
        Intensity matrix for the straight-through (air) measurement.
        Must be invertible.

    B_sample : ndarray, shape (4, 4)
        Intensity matrix with the calibration sample in place.

    Returns
    -------
    H_M : ndarray, shape (16, 16)
        ECM constraint matrix.

    Raises
    ------
    ValueError
        If B_air is singular (condition number > 1e10).

    Examples
    --------
    >>> import numpy as np
    >>> from ecm.utils.mueller_matrices import polarizer, identity

    # For identity sample (air), H_M @ vec(I) should be zero
    >>> M = identity()
    >>> B_air = np.eye(4)  # Simplified example
    >>> B_sample = B_air.copy()
    >>> H_M = build_H_matrix(M, B_air, B_sample)
    >>> vec_I = np.eye(4).flatten(order='F')
    >>> np.allclose(H_M @ vec_I, 0)
    True

    Notes
    -----
    **Mathematical Derivation:**

    The ECM constraint is:

        M @ W = W @ C    where C = B_air^(-1) @ B_sample

    Rearranging: M @ W - W @ C = 0

    Using the vectorization identity vec(AXB) = (B^T ⊗ A) @ vec(X):

        vec(M @ W) = (I₄ ⊗ M) @ vec(W)
        vec(W @ C) = (C^T ⊗ I₄) @ vec(W)

    So: H_M @ vec(W) = 0 where H_M = (I₄ ⊗ M) - (C^T ⊗ I₄)

    **Numerical Stability:**

    We compute C = B_air^(-1) @ B_sample using np.linalg.solve for numerical
    stability rather than explicit matrix inversion.

    **Column-Major Vectorization:**

    The vectorization vec(W) uses column-major (Fortran) order to maintain
    compatibility with MATLAB. In Python, this means:

        vec_W = W.flatten(order='F')
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    if M.shape != (4, 4):
        raise ValueError(f"M must be 4×4, got {M.shape}")

    if B_air.shape != (4, 4):
        raise ValueError(f"B_air must be 4×4, got {B_air.shape}")

    if B_sample.shape != (4, 4):
        raise ValueError(f"B_sample must be 4×4, got {B_sample.shape}")

    # -------------------------------------------------------------------------
    # Check conditioning of B_air
    # -------------------------------------------------------------------------
    cond_B_air = np.linalg.cond(B_air)
    if cond_B_air > 1e10:
        raise ValueError(
            f"B_air is poorly conditioned (cond={cond_B_air:.2e}). "
            f"This may indicate a problem with the air measurement data. "
            f"Check that the measurement is not saturated or clipped."
        )

    # -------------------------------------------------------------------------
    # Compute C = B_air^(-1) @ B_sample using solve for numerical stability
    #
    # solve(A, B) computes A^(-1) @ B more stably than inv(A) @ B
    # -------------------------------------------------------------------------
    C = np.linalg.solve(B_air, B_sample)

    # -------------------------------------------------------------------------
    # Build H_M using Kronecker products
    #
    # H_M = (I₄ ⊗ M) - (C^T ⊗ I₄)
    #
    # Using numpy's kron function:
    #   np.kron(A, B) computes A ⊗ B
    # -------------------------------------------------------------------------
    I4 = np.eye(4, dtype=np.float64)

    # (I₄ ⊗ M): 16×16 block diagonal with M repeated 4 times
    term1 = np.kron(I4, M)

    # (C^T ⊗ I₄): 16×16 with I4 blocks scaled by elements of C^T
    term2 = np.kron(C.T, I4)

    # H_M = term1 - term2
    H_M = term1 - term2

    return H_M


# =============================================================================
# K MATRIX CONSTRUCTION
# =============================================================================

def build_K_matrix(H_matrices: List[ndarray]) -> ndarray:
    """
    Accumulate ECM constraint matrices into the combined K matrix.

    Combines constraints from multiple calibration samples (polarizers at
    different angles, retarder) into a single positive semi-definite matrix K.
    The PSG matrix W is found as the eigenvector of K corresponding to its
    smallest eigenvalue.

    Reference: Compain et al., Appl. Opt. 38, 3490-3502 (1999), Eqs. 19-20

    Parameters
    ----------
    H_matrices : List[ndarray]
        List of H_M matrices, each shape (16, 16), from build_H_matrix().
        Typically includes:
        - H_M for polarizer at 0°
        - H_M for polarizer at 45°
        - H_M for retarder at 90° (and optionally at 45°)

    Returns
    -------
    K : ndarray, shape (16, 16)
        Accumulated constraint matrix. Symmetric positive semi-definite.

    Raises
    ------
    ValueError
        If fewer than 3 H matrices are provided (minimum for unique solution).

    Examples
    --------
    >>> # Build H matrices for calibration samples
    >>> H_pol0 = build_H_matrix(M_pol0, B_air, B_pol0)
    >>> H_pol45 = build_H_matrix(M_pol45, B_air, B_pol45)
    >>> H_ret = build_H_matrix(M_ret, B_air, B_ret)
    >>>
    >>> K = build_K_matrix([H_pol0, H_pol45, H_ret])
    >>> print(f"K shape: {K.shape}")
    K shape: (16, 16)

    Notes
    -----
    **Mathematical Formula:**

        K = Σᵢ H_Mᵢ^T @ H_Mᵢ

    **Properties of K:**

    - K is 16×16, symmetric, positive semi-definite
    - Eigenvalue structure: λ₁ ≥ λ₂ ≥ ... ≥ λ₁₅ >> λ₁₆ ≈ 0
    - vec(W) is the eigenvector of K corresponding to λ₁₆ (smallest)

    **Quality Metric:**

    The ratio λ₁₆/λ₁₅ indicates calibration quality:
    - < 1e-5: Excellent
    - < 1e-3: Good
    - < 0.1: Acceptable
    - > 0.1: Poor (indicates inconsistent calibration data)

    **Minimum Number of Samples:**

    At least 3 calibration samples are required to uniquely determine W.
    The standard set is: polarizer at 0°, polarizer at 45°, retarder at 90°.
    Adding a second retarder at 45° improves robustness.
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    n_samples = len(H_matrices)

    if n_samples < 3:
        raise ValueError(
            f"At least 3 calibration samples required for unique solution, "
            f"got {n_samples}. Standard set: pol0, pol45, retarder."
        )

    for i, H in enumerate(H_matrices):
        if H.shape != (16, 16):
            raise ValueError(
                f"H_matrices[{i}] has shape {H.shape}, expected (16, 16). "
                f"Ensure all H matrices are from build_H_matrix()."
            )

    # -------------------------------------------------------------------------
    # Accumulate K = Σᵢ H_Mᵢ^T @ H_Mᵢ
    # -------------------------------------------------------------------------
    K = np.zeros((16, 16), dtype=np.float64)

    for H_M in H_matrices:
        # Add H_M^T @ H_M to K
        K += H_M.T @ H_M

    # -------------------------------------------------------------------------
    # Ensure symmetry (should already be symmetric, but enforce to avoid
    # numerical drift)
    # -------------------------------------------------------------------------
    K = (K + K.T) / 2.0

    return K


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def compute_kron_C_matrix(B_air: ndarray, B_sample: ndarray) -> ndarray:
    """
    Pre-compute the Kronecker term (C^T ⊗ I₄) for optimization efficiency.

    This function is useful during parameter optimization, where the Mueller
    matrix M changes but C remains fixed for each wavelength.

    Parameters
    ----------
    B_air : ndarray, shape (4, 4)
        Air intensity matrix.

    B_sample : ndarray, shape (4, 4)
        Sample intensity matrix.

    Returns
    -------
    kron_C : ndarray, shape (16, 16)
        Pre-computed (C^T ⊗ I₄) matrix.

    Notes
    -----
    During optimization, the cost function evaluates H_M for different M values.
    Since H_M = (I₄ ⊗ M) - (C^T ⊗ I₄), the second term can be pre-computed
    once per wavelength for efficiency.

    Usage in optimization:

        kron_C = compute_kron_C_matrix(B_air, B_sample)
        # In cost function:
        H_M = np.kron(np.eye(4), M) - kron_C
    """
    # Compute C = B_air^(-1) @ B_sample
    C = np.linalg.solve(B_air, B_sample)

    # Compute (C^T ⊗ I₄)
    I4 = np.eye(4, dtype=np.float64)
    kron_C = np.kron(C.T, I4)

    return kron_C
