"""
Cloude (Spectral) Decomposition of Mueller Matrices

Decomposes a Mueller matrix via the coherency matrix eigendecomposition:

    H = (1/4) Σ m_ij (σ_i ⊗ σ_j*)     — coherency matrix from Pauli basis
    H = Σ λ_k · u_k @ u_k†            — eigendecomposition (λ_0 ≥ λ_1 ≥ λ_2 ≥ λ_3)
    M = Σ λ_k · M_k                   — Mueller matrix reconstruction

Each eigenvector u_k defines a rank-1 coherency matrix H_k = u_k @ u_k†
which maps back to a nondepolarizing (Jones) Mueller matrix M_k.

Pauli Matrix Convention
-----------------------
Following Gil & Ossikovski (2022) and Cloude (1986):
    σ₀ = I₂ = [[1,0],[0,1]]
    σ₁ = [[1,0],[0,-1]]       (Pauli Z, diagonal)
    σ₂ = [[0,1],[1,0]]        (Pauli X, anti-diagonal real)
    σ₃ = [[0,-j],[j,0]]       (Pauli Y, anti-diagonal imaginary)

References
----------
[1] Cloude, "Group theory and polarisation algebra", Optik 75, 26-36 (1986)
[2] Gil & Ossikovski, "Polarized Light and the Mueller Matrix Approach"
    (2nd ed.), Chapter 5.
"""

import numpy as np
from numpy import ndarray
from dataclasses import dataclass

from ecm.postprocessing._validation import validate_mueller_input

# =============================================================================
# PAULI MATRICES (polarimetry convention)
# =============================================================================

SIGMA = np.array([
    # σ₀ = Identity
    [[1, 0],
     [0, 1]],
    # σ₁ = diag(1, -1)
    [[1, 0],
     [0, -1]],
    # σ₂ = anti-diagonal real
    [[0, 1],
     [1, 0]],
    # σ₃ = anti-diagonal imaginary
    [[0, -1j],
     [1j, 0]],
], dtype=np.complex128)

# Pre-compute the 16 Kronecker products σ_i ⊗ σ_j* (each is 4×4 complex)
# The conjugate on σ_j is required per Gil & Ossikovski Eq. 5.18 for the
# coherency matrix to be positive semi-definite for physical Mueller matrices.
# BASIS[i, j] = kron(σ_i, conj(σ_j)), shape (4, 4, 4, 4)
BASIS = np.zeros((4, 4, 4, 4), dtype=np.complex128)
for _i in range(4):
    for _j in range(4):
        BASIS[_i, _j] = np.kron(SIGMA[_i], SIGMA[_j].conj())


@dataclass
class CloudeDecompositionResult:
    """
    Result of Cloude (spectral) decomposition of a Mueller matrix.

    Attributes
    ----------
    eigenvalues : ndarray, shape (4, n_wavelengths)
        Coherency matrix eigenvalues, sorted descending: λ_0 ≥ λ_1 ≥ λ_2 ≥ λ_3.
        For physical Mueller matrices, all eigenvalues are non-negative.
    M_components : ndarray, shape (4, 4, 4, n_wavelengths)
        Component Mueller matrices M_0, M_1, M_2, M_3.
        M_components[k, :, :, i_wl] = M_k at wavelength i_wl.
        First index is the component index (0-3).
    H : ndarray, shape (4, 4, n_wavelengths), complex
        Coherency matrices.
    """
    eigenvalues: ndarray
    M_components: ndarray
    H: ndarray


def cloude_decomposition(M_norm: ndarray) -> CloudeDecompositionResult:
    """
    Perform Cloude (spectral) decomposition of Mueller matrix.

    Transforms the Mueller matrix to the coherency matrix via the Pauli
    basis, eigendecomposes it, and converts each rank-1 component back
    to a nondepolarizing Mueller matrix.

    Parameters
    ----------
    M_norm : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        Normalized Mueller matrix(ces).

    Returns
    -------
    CloudeDecompositionResult

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
    # Pre-allocate outputs
    # -------------------------------------------------------------------------
    eigenvalues = np.zeros((4, n_wl), dtype=np.float64)
    M_components = np.zeros((4, 4, 4, n_wl), dtype=np.float64)
    H_all = np.zeros((4, 4, n_wl), dtype=np.complex128)

    # -------------------------------------------------------------------------
    # Process each wavelength
    # -------------------------------------------------------------------------
    for k in range(n_wl):
        M = M_norm[:, :, k]

        # -----------------------------------------------------------------
        # Step 1: Mueller matrix → Coherency matrix
        # H = (1/4) Σ_{i,j} m_ij * (σ_i ⊗ σ_j*)
        # -----------------------------------------------------------------
        H = np.einsum('ij,ijkl->kl', M, BASIS) * 0.25

        # Enforce Hermiticity (numerical symmetrization)
        H = (H + H.conj().T) / 2.0

        H_all[:, :, k] = H

        # -----------------------------------------------------------------
        # Step 2: Eigendecomposition
        # eigh returns ascending order; reverse for descending
        # -----------------------------------------------------------------
        evals, evecs = np.linalg.eigh(H)
        evals = evals[::-1]
        evecs = evecs[:, ::-1]

        eigenvalues[:, k] = evals

        # -----------------------------------------------------------------
        # Step 3: Component Mueller matrices
        # For each eigenvector u_k:
        #   H_k = u_k @ u_k†  (rank-1 coherency)
        #   (M_k)_{jl} = Re(tr[(σ_j ⊗ σ_l) @ H_k])
        # -----------------------------------------------------------------
        for comp in range(4):
            u = evecs[:, comp:comp+1]  # Column vector (4, 1)
            H_comp = u @ u.conj().T    # Rank-1 outer product (4, 4)

            M_comp = np.real(np.einsum('ijkl,lk->ij', BASIS, H_comp))
            M_components[comp, :, :, k] = M_comp

    # -------------------------------------------------------------------------
    # Remove wavelength dimension if single input
    # -------------------------------------------------------------------------
    if single_wavelength:
        eigenvalues = eigenvalues[:, 0]
        M_components = M_components[:, :, :, 0]
        H_all = H_all[:, :, 0]

    return CloudeDecompositionResult(
        eigenvalues=eigenvalues,
        M_components=M_components,
        H=H_all,
    )
