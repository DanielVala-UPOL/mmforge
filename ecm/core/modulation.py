"""
Modulation Basis Construction for Dual Rotating Compensator Polarimetry

This module builds the modulation basis matrix that relates the 16 intensity
matrix elements to the measured intensity modulation in a dual rotating
compensator Mueller matrix polarimeter.

Functions
---------
build_modulation_basis(cfg)
    Construct the modulation basis matrix W_mod and its pseudo-inverse
build_intensity_matrix(intensity, inv_W_mod)
    Convert angular intensity measurements to 4×4 intensity matrices

Theory
------
For a dual rotating compensator system with PSG at angle θ_PSG = a·ω and
PSA at angle θ_PSA = b·ω (where ω is the fundamental rotation angle from
0 to 2π), the detected intensity can be written as:

    I(ω) = Σᵢⱼ Bᵢⱼ · wᵢⱼ(ω)

where Bᵢⱼ are the 16 elements of the intensity matrix B = A·M·W,
and wᵢⱼ(ω) are basis functions (products of trigonometric terms).

For a 1:5 frequency ratio system (a=1, b=5), the 16 basis functions are
products of:
    PSG: {1, sin(2aω), cos(4aω), sin(4aω)}
    PSA: {1, sin(2bω), cos(4bω), sin(4bω)}

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999)

[2] Smith, "Optimization of a dual-rotating-retarder Mueller matrix
    polarimeter", Appl. Opt. 41, 2488-2493 (2002)
"""

import numpy as np
from numpy import ndarray
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ecm.config.ecm_config import ECMConfig


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ModulationBasis:
    """
    Result of modulation basis construction.

    Contains the modulation basis matrix and its pseudo-inverse for
    converting between angular intensity measurements and 4×4 intensity matrices.

    Attributes
    ----------
    W_mod : ndarray, shape (n_angles, 16)
        Modulation basis matrix. Each column is a basis function evaluated
        at n_angles angular positions.

    inv_W_mod : ndarray, shape (16, n_angles)
        Pseudo-inverse of W_mod, computed as (W_mod.T @ W_mod)^(-1) @ W_mod.T.
        Used to extract intensity matrices: B_vec = inv_W_mod @ intensity.

    condition_number : float
        Condition number of W_mod. Should be < 10 for well-conditioned systems.
        High values indicate near-singular basis (poor angular sampling).

    omega : ndarray, shape (n_angles,)
        Angular positions in radians, from 0 to 2π (exclusive).

    freq_ratio_psg : int
        PSG frequency ratio (typically 1). PSG rotates at a·ω.

    freq_ratio_psa : int
        PSA frequency ratio (typically 5). PSA rotates at b·ω.

    Notes
    -----
    The basis functions follow column-major ordering to match MATLAB convention:
    - Columns 0-3:   PSA modulation only (PSG at DC)
    - Columns 4-7:   sin(2aω) × PSA modulation
    - Columns 8-11:  cos(4aω) × PSA modulation
    - Columns 12-15: sin(4aω) × PSA modulation
    """
    W_mod: ndarray
    inv_W_mod: ndarray
    condition_number: float
    omega: ndarray
    freq_ratio_psg: int
    freq_ratio_psa: int


# =============================================================================
# MODULATION BASIS CONSTRUCTION
# =============================================================================

def build_modulation_basis(cfg: 'ECMConfig') -> ModulationBasis:
    """
    Build the modulation basis matrix for dual rotating compensator.

    Constructs the matrix W_mod that relates the 16 intensity matrix elements
    to the N measured intensities. Also computes its pseudo-inverse for
    least-squares extraction of intensity matrices.

    Reference: Smith, Appl. Opt. 41, 2488-2493 (2002)

    Parameters
    ----------
    cfg : ECMConfig
        ECM configuration containing:
        - cfg.acquisition.n_angular_positions : int
            Number of angular measurement positions (typically 96)
        - cfg.instrument.psg_freq_ratio : int
            PSG frequency ratio 'a' (typically 1)
        - cfg.instrument.psa_freq_ratio : int
            PSA frequency ratio 'b' (typically 5)

    Returns
    -------
    ModulationBasis
        Dataclass containing:
        - W_mod: Modulation basis matrix [n_angles × 16]
        - inv_W_mod: Pseudo-inverse [16 × n_angles]
        - condition_number: Condition number of W_mod
        - omega: Angular positions [n_angles] in radians
        - freq_ratio_psg, freq_ratio_psa: Frequency ratios

    Examples
    --------
    >>> from ecm.config import ECMConfig
    >>> cfg = ECMConfig()
    >>> basis = build_modulation_basis(cfg)
    >>> print(f"W_mod shape: {basis.W_mod.shape}")
    W_mod shape: (96, 16)
    >>> print(f"Condition number: {basis.condition_number:.2f}")
    Condition number: 2.00

    Notes
    -----
    **Column Ordering (CRITICAL for MATLAB compatibility):**

    The 16 columns of W_mod are ordered to match MATLAB's column-major
    vectorization convention for the 4×4 intensity matrix B:

    - Column 0:  1                    (B[0,0])
    - Column 1:  sin(2bω)             (B[1,0])
    - Column 2:  cos(4bω)             (B[2,0])
    - Column 3:  sin(4bω)             (B[3,0])
    - Column 4:  sin(2aω)             (B[0,1])
    - Column 5:  sin(2aω)·sin(2bω)    (B[1,1])
    - Column 6:  sin(2aω)·cos(4bω)    (B[2,1])
    - Column 7:  sin(2aω)·sin(4bω)    (B[3,1])
    - Column 8:  cos(4aω)             (B[0,2])
    - Column 9:  cos(4aω)·sin(2bω)    (B[1,2])
    - Column 10: cos(4aω)·cos(4bω)    (B[2,2])
    - Column 11: cos(4aω)·sin(4bω)    (B[3,2])
    - Column 12: sin(4aω)             (B[0,3])
    - Column 13: sin(4aω)·sin(2bω)    (B[1,3])
    - Column 14: sin(4aω)·cos(4bω)    (B[2,3])
    - Column 15: sin(4aω)·sin(4bω)    (B[3,3])

    This ordering means that when we reshape the 16-element vector B_vec
    into a 4×4 matrix, we must use Fortran (column-major) order.
    """
    # -------------------------------------------------------------------------
    # Extract parameters from configuration
    # -------------------------------------------------------------------------
    n_angles = cfg.acquisition.n_angular_positions
    a = cfg.instrument.psg_freq_ratio  # PSG frequency ratio (typically 1)
    b = cfg.instrument.psa_freq_ratio  # PSA frequency ratio (typically 5)

    # -------------------------------------------------------------------------
    # Build angle vector
    # Angular positions from 0 to 2π, exclusive of 2π (since 0 ≡ 2π)
    # Using np.arange gives us indices 0, 1, ..., N-1
    # -------------------------------------------------------------------------
    omega = np.arange(n_angles, dtype=np.float64) * (2.0 * np.pi / n_angles)

    # -------------------------------------------------------------------------
    # Build trigonometric basis functions
    # PSG-related terms use frequencies 2a and 4a
    # PSA-related terms use frequencies 2b and 4b
    # -------------------------------------------------------------------------

    # PSG basis functions (column vector, n_angles rows)
    sin_2a = np.sin(2 * a * omega)  # sin(2aω)
    cos_4a = np.cos(4 * a * omega)  # cos(4aω)
    sin_4a = np.sin(4 * a * omega)  # sin(4aω)

    # PSA basis functions (column vector, n_angles rows)
    sin_2b = np.sin(2 * b * omega)  # sin(2bω)
    cos_4b = np.cos(4 * b * omega)  # cos(4bω)
    sin_4b = np.sin(4 * b * omega)  # sin(4bω)

    # -------------------------------------------------------------------------
    # Construct the 16-column modulation basis matrix
    #
    # Column ordering follows MATLAB convention for B matrix vectorization:
    #   - Columns 0-3:   PSA modulation with PSG at DC (constant)
    #   - Columns 4-7:   sin(2aω) × PSA modulation
    #   - Columns 8-11:  cos(4aω) × PSA modulation
    #   - Columns 12-15: sin(4aω) × PSA modulation
    # -------------------------------------------------------------------------

    # Pre-allocate W_mod matrix [n_angles × 16]
    W_mod = np.zeros((n_angles, 16), dtype=np.float64)

    # Columns 0-3: PSG at DC (constant = 1)
    W_mod[:, 0] = 1.0                # 1
    W_mod[:, 1] = sin_2b             # sin(2bω)
    W_mod[:, 2] = cos_4b             # cos(4bω)
    W_mod[:, 3] = sin_4b             # sin(4bω)

    # Columns 4-7: PSG at sin(2aω)
    W_mod[:, 4] = sin_2a             # sin(2aω)
    W_mod[:, 5] = sin_2a * sin_2b    # sin(2aω)·sin(2bω)
    W_mod[:, 6] = sin_2a * cos_4b    # sin(2aω)·cos(4bω)
    W_mod[:, 7] = sin_2a * sin_4b    # sin(2aω)·sin(4bω)

    # Columns 8-11: PSG at cos(4aω)
    W_mod[:, 8] = cos_4a             # cos(4aω)
    W_mod[:, 9] = cos_4a * sin_2b    # cos(4aω)·sin(2bω)
    W_mod[:, 10] = cos_4a * cos_4b   # cos(4aω)·cos(4bω)
    W_mod[:, 11] = cos_4a * sin_4b   # cos(4aω)·sin(4bω)

    # Columns 12-15: PSG at sin(4aω)
    W_mod[:, 12] = sin_4a            # sin(4aω)
    W_mod[:, 13] = sin_4a * sin_2b   # sin(4aω)·sin(2bω)
    W_mod[:, 14] = sin_4a * cos_4b   # sin(4aω)·cos(4bω)
    W_mod[:, 15] = sin_4a * sin_4b   # sin(4aω)·sin(4bω)

    # -------------------------------------------------------------------------
    # Compute pseudo-inverse using normal equations
    # inv_W_mod = (W_mod.T @ W_mod)^(-1) @ W_mod.T
    #
    # This is the least-squares solution matrix.
    # For numerical stability, we use solve instead of explicit inverse.
    # -------------------------------------------------------------------------

    # Compute W_mod.T @ W_mod (16×16 Gram matrix)
    gram_matrix = W_mod.T @ W_mod

    # Compute inv_W_mod = gram_matrix^(-1) @ W_mod.T
    # Using solve for numerical stability: solve(A, B) computes A^(-1) @ B
    inv_W_mod = np.linalg.solve(gram_matrix, W_mod.T)

    # -------------------------------------------------------------------------
    # Compute condition number for diagnostics
    # -------------------------------------------------------------------------
    condition_number = np.linalg.cond(W_mod)

    # -------------------------------------------------------------------------
    # Return result as dataclass
    # -------------------------------------------------------------------------
    return ModulationBasis(
        W_mod=W_mod,
        inv_W_mod=inv_W_mod,
        condition_number=condition_number,
        omega=omega,
        freq_ratio_psg=a,
        freq_ratio_psa=b
    )


# =============================================================================
# INTENSITY MATRIX CONSTRUCTION
# =============================================================================

def build_intensity_matrix(
    intensity: ndarray,
    inv_W_mod: ndarray
) -> ndarray:
    """
    Convert angular intensity measurements to 4×4 intensity matrices.

    Transforms raw intensity data at one or more wavelengths into 4×4
    intensity matrices using least-squares inversion of the modulation basis.

    The intensity matrix B (also called measurement matrix) is related to
    the PSA matrix A, sample Mueller matrix M, and PSG matrix W by:

        B = A @ M @ W

    Reference: Compain et al., Appl. Opt. 38, 3490-3502 (1999), Eq. (11)

    Parameters
    ----------
    intensity : ndarray, shape (n_angles, n_wavelengths) or (n_angles,)
        Intensity data with rows as angular positions and columns as wavelengths.
        For a single wavelength, can be 1D array of length n_angles.

    inv_W_mod : ndarray, shape (16, n_angles)
        Pseudo-inverse of modulation basis matrix from build_modulation_basis().

    Returns
    -------
    B : ndarray, shape (4, 4, n_wavelengths) or (4, 4)
        Intensity matrices. B[:,:,k] is the intensity matrix for wavelength k.
        For single wavelength input, returns 2D array (4, 4).

    Raises
    ------
    ValueError
        If dimensions of intensity and inv_W_mod are incompatible.

    Examples
    --------
    >>> from ecm.config import ECMConfig
    >>> cfg = ECMConfig()
    >>> basis = build_modulation_basis(cfg)
    >>>
    >>> # Create synthetic DC-only intensity (should give scaled identity B)
    >>> intensity = np.ones((96, 10)) * 1000  # 10 wavelengths, DC only
    >>> B = build_intensity_matrix(intensity, basis.inv_W_mod)
    >>> print(f"B shape: {B.shape}")
    B shape: (4, 4, 10)

    Notes
    -----
    **Fortran (Column-Major) Ordering:**

    The intensity matrix B is stored in column-major order to maintain
    compatibility with MATLAB. When the 16-element vector B_vec is reshaped
    to a 4×4 matrix, we use `order='F'` (Fortran order):

    - B_vec[0:4]   → B[:, 0]  (first column)
    - B_vec[4:8]   → B[:, 1]  (second column)
    - B_vec[8:12]  → B[:, 2]  (third column)
    - B_vec[12:16] → B[:, 3]  (fourth column)

    This is CRITICAL for the ECM algorithm to work correctly.
    """
    # -------------------------------------------------------------------------
    # Handle 1D input (single wavelength)
    # -------------------------------------------------------------------------
    squeeze_output = False
    if intensity.ndim == 1:
        intensity = intensity.reshape(-1, 1)
        squeeze_output = True

    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    n_angles, n_wavelengths = intensity.shape
    n_elements, n_angles_inv = inv_W_mod.shape

    if n_elements != 16:
        raise ValueError(
            f"inv_W_mod must have 16 rows (one for each B matrix element), "
            f"but got {n_elements} rows. Check that inv_W_mod is from "
            f"build_modulation_basis()."
        )

    if n_angles != n_angles_inv:
        raise ValueError(
            f"Dimension mismatch: intensity has {n_angles} angular positions "
            f"but inv_W_mod expects {n_angles_inv}. Ensure the modulation basis "
            f"was built with the same n_angular_positions as the data."
        )

    # -------------------------------------------------------------------------
    # Compute intensity matrix coefficients via least-squares
    # B_vec = inv_W_mod @ intensity
    # Result shape: (16, n_wavelengths)
    # -------------------------------------------------------------------------
    B_vec = inv_W_mod @ intensity

    # -------------------------------------------------------------------------
    # Reshape to 4×4×n_wavelengths using Fortran (column-major) order
    #
    # CRITICAL: Use order='F' to match MATLAB's column-major convention!
    #
    # In MATLAB, B(:) fills columns first:
    #   B_vec[0:4] → B(:,1), B_vec[4:8] → B(:,2), etc.
    #
    # NumPy's reshape with order='F' replicates this behavior.
    # -------------------------------------------------------------------------

    # For multiple wavelengths, we need to handle the reshape carefully.
    # B_vec is (16, n_wavelengths), we want (4, 4, n_wavelengths).
    #
    # For each wavelength column, reshape the 16 elements to 4×4.
    # We can do this by reshaping with Fortran order.

    if n_wavelengths == 1:
        # Single wavelength: reshape (16,) to (4, 4)
        B = B_vec[:, 0].reshape((4, 4), order='F')
    else:
        # Multiple wavelengths: process each column
        # Pre-allocate output array
        B = np.zeros((4, 4, n_wavelengths), dtype=np.float64)

        for i_wl in range(n_wavelengths):
            # Reshape the 16-element vector to 4×4 using Fortran order
            B[:, :, i_wl] = B_vec[:, i_wl].reshape((4, 4), order='F')

    # -------------------------------------------------------------------------
    # Return result, squeezing if input was 1D
    # -------------------------------------------------------------------------
    if squeeze_output:
        return B  # Already 2D for single wavelength
    else:
        return B
