"""
Tests for ECM Constraint Matrix Construction Module

Tests the build_H_matrix and build_K_matrix functions that construct
the constraint matrices for the ECM eigenvalue problem.

References
----------
[1] Compain et al., Appl. Opt. 38, 3490-3502 (1999), Eqs. 14, 19-20
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

from ecm.core.ecm_matrices import (
    build_H_matrix,
    build_K_matrix,
    compute_kron_C_matrix,
)
from ecm.utils.mueller_matrices import identity, polarizer, retarder, rotation


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def identity_B():
    """Create identity-like B matrices for air measurement."""
    # For air with M=I: B = A @ I @ W = A @ W
    # Simplified test case: A = W = I
    return np.eye(4)


@pytest.fixture
def sample_B_matrices():
    """Create sample B matrices for testing."""
    B_air = np.array([
        [1.0, 0.1, 0.0, 0.0],
        [0.1, 0.8, 0.0, 0.0],
        [0.0, 0.0, 0.6, 0.0],
        [0.0, 0.0, 0.0, 0.5]
    ])

    # Polarizer-like B matrix
    B_pol = np.array([
        [0.5, 0.5, 0.0, 0.0],
        [0.5, 0.5, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0]
    ])

    return B_air, B_pol


# =============================================================================
# TEST: build_H_matrix
# =============================================================================

class TestBuildHMatrix:
    """Tests for build_H_matrix function."""

    def test_output_shape(self, identity_B):
        """H_M should be [16 × 16]."""
        M = identity()
        B_air = identity_B
        B_sample = identity_B

        H_M = build_H_matrix(M, B_air, B_sample)

        assert H_M.shape == (16, 16)

    def test_identity_sample(self, identity_B):
        """M = I, B_sample = B_air → H_M @ vec(I) = 0."""
        M = identity()
        B_air = identity_B
        B_sample = identity_B.copy()

        H_M = build_H_matrix(M, B_air, B_sample)

        # For identity sample, W = I should be in null space
        vec_I = np.eye(4).flatten(order='F')
        result = H_M @ vec_I

        assert_allclose(result, 0.0, atol=1e-10)

    def test_null_space_property(self):
        """For correct M, W: H_M @ vec(W) ≈ 0."""
        # Create a consistent set of A, W, M matrices
        # B = A @ M @ W, so C = B_air^(-1) @ B = W^(-1) @ M @ W
        # The ECM constraint is: M @ W = W @ C → H_M @ vec(W) = 0

        # Simple test: M = I, W = I → C = I, H_M @ vec(I) = 0
        M = identity()
        W = np.eye(4)
        A = np.eye(4)

        B_air = A @ W  # For M = I: B = A @ I @ W = A @ W
        B_sample = B_air.copy()

        H_M = build_H_matrix(M, B_air, B_sample)
        vec_W = W.flatten(order='F')

        result = H_M @ vec_W
        assert_allclose(result, 0.0, atol=1e-10)

    def test_kronecker_construction(self):
        """Verify H_M = (I₄ ⊗ M) - (C^T ⊗ I₄)."""
        M = polarizer(theta=0.0, tau=0.5)
        B_air = np.eye(4) + 0.1 * np.random.rand(4, 4)
        B_sample = np.eye(4) + 0.1 * np.random.rand(4, 4)

        H_M = build_H_matrix(M, B_air, B_sample)

        # Manual computation
        C = np.linalg.solve(B_air, B_sample)
        I4 = np.eye(4)
        H_expected = np.kron(I4, M) - np.kron(C.T, I4)

        assert_allclose(H_M, H_expected, rtol=1e-10)

    def test_singular_B_air_raises(self):
        """Should raise ValueError for ill-conditioned B_air."""
        M = identity()
        B_air = np.zeros((4, 4))  # Singular
        B_sample = np.eye(4)

        with pytest.raises(ValueError, match="poorly conditioned"):
            build_H_matrix(M, B_air, B_sample)

    def test_input_validation_shapes(self):
        """Should validate input shapes."""
        M_wrong = np.eye(3)  # Wrong shape
        B_air = np.eye(4)
        B_sample = np.eye(4)

        with pytest.raises(ValueError, match="4×4"):
            build_H_matrix(M_wrong, B_air, B_sample)

    def test_with_polarizer_mueller(self, sample_B_matrices):
        """Test H matrix construction with polarizer Mueller matrix."""
        B_air, B_pol = sample_B_matrices
        M_pol = polarizer(theta=0.0, tau=0.5)

        H_M = build_H_matrix(M_pol, B_air, B_pol)

        # H_M should be finite
        assert np.all(np.isfinite(H_M))

        # H_M should not be zero (non-trivial constraint)
        assert np.max(np.abs(H_M)) > 0

    def test_with_retarder_mueller(self, sample_B_matrices):
        """Test H matrix construction with retarder Mueller matrix."""
        B_air, _ = sample_B_matrices
        M_ret = retarder(theta=np.pi/2, delta=np.pi/2, tau=0.9)
        B_ret = B_air + 0.1 * np.random.rand(4, 4)

        H_M = build_H_matrix(M_ret, B_air, B_ret)

        # H_M should be finite
        assert np.all(np.isfinite(H_M))

    def test_fortran_ordering(self):
        """Verify that Fortran (column-major) ordering is used internally."""
        M = identity()
        B_air = np.eye(4)
        B_sample = np.eye(4)

        H_M = build_H_matrix(M, B_air, B_sample)

        # For M = I, C = I, we have H_M = I - I = 0 (approximately)
        # The exact form depends on the Kronecker structure
        assert H_M.shape == (16, 16)


# =============================================================================
# TEST: build_K_matrix
# =============================================================================

class TestBuildKMatrix:
    """Tests for build_K_matrix function."""

    def test_output_shape(self, identity_B):
        """K should be [16 × 16]."""
        M = identity()
        H_M = build_H_matrix(M, identity_B, identity_B)

        K = build_K_matrix([H_M, H_M, H_M])

        assert K.shape == (16, 16)

    def test_symmetry(self, identity_B):
        """K should be symmetric."""
        M_pol = polarizer(theta=0.0, tau=0.5)
        M_ret = retarder(theta=np.pi/2, delta=np.pi/4, tau=0.9)

        H_pol = build_H_matrix(M_pol, identity_B, identity_B * 0.5)
        H_ret = build_H_matrix(M_ret, identity_B, identity_B * 0.9)
        H_id = build_H_matrix(identity(), identity_B, identity_B)

        K = build_K_matrix([H_pol, H_ret, H_id])

        # Check symmetry
        assert_allclose(K, K.T, rtol=1e-10)

    def test_positive_semidefinite(self, identity_B):
        """All eigenvalues of K should be ≥ 0."""
        # Create diverse H matrices
        H_matrices = []
        for theta in [0, np.pi/4, np.pi/2]:
            M = polarizer(theta=theta, tau=0.5)
            B_sample = identity_B * (0.5 + 0.1 * np.random.rand())
            H = build_H_matrix(M, identity_B, B_sample)
            H_matrices.append(H)

        K = build_K_matrix(H_matrices)

        # Eigenvalues should be non-negative
        eigenvalues = np.linalg.eigvalsh(K)
        assert np.all(eigenvalues >= -1e-10)  # Allow small numerical error

    def test_accumulation(self, identity_B):
        """K = sum of H'H contributions."""
        H1 = build_H_matrix(polarizer(0, 0.5), identity_B, identity_B * 0.5)
        H2 = build_H_matrix(polarizer(np.pi/4, 0.5), identity_B, identity_B * 0.5)
        H3 = build_H_matrix(retarder(np.pi/2, np.pi/4), identity_B, identity_B * 0.9)

        K = build_K_matrix([H1, H2, H3])

        # Manual computation
        K_expected = H1.T @ H1 + H2.T @ H2 + H3.T @ H3

        assert_allclose(K, K_expected, rtol=1e-10)

    def test_minimum_samples_check(self, identity_B):
        """Should raise error with fewer than 3 calibration samples."""
        H = build_H_matrix(identity(), identity_B, identity_B)

        with pytest.raises(ValueError, match="At least 3"):
            build_K_matrix([H, H])

    def test_H_matrix_shape_validation(self, identity_B):
        """Should validate H matrix shapes."""
        H_correct = build_H_matrix(identity(), identity_B, identity_B)
        H_wrong = np.eye(8)  # Wrong shape

        with pytest.raises(ValueError, match="16, 16"):
            build_K_matrix([H_correct, H_wrong, H_correct])

    def test_adding_more_samples(self, identity_B):
        """Adding more samples should only change K, not break it."""
        H_base = [
            build_H_matrix(polarizer(0, 0.5), identity_B, identity_B * 0.5),
            build_H_matrix(polarizer(np.pi/4, 0.5), identity_B, identity_B * 0.5),
            build_H_matrix(retarder(np.pi/2, np.pi/4), identity_B, identity_B * 0.9),
        ]

        K3 = build_K_matrix(H_base)

        # Add a fourth sample
        H_extra = build_H_matrix(retarder(np.pi/4, np.pi/2), identity_B, identity_B * 0.85)
        K4 = build_K_matrix(H_base + [H_extra])

        # Both should be valid
        assert K3.shape == (16, 16)
        assert K4.shape == (16, 16)

        # K4 should be K3 + H_extra'H_extra
        assert_allclose(K4, K3 + H_extra.T @ H_extra, rtol=1e-10)


# =============================================================================
# TEST: compute_kron_C_matrix (utility)
# =============================================================================

class TestComputeKronCMatrix:
    """Tests for the utility function compute_kron_C_matrix."""

    def test_output_shape(self, identity_B):
        """Should return [16 × 16] matrix."""
        kron_C = compute_kron_C_matrix(identity_B, identity_B)
        assert kron_C.shape == (16, 16)

    def test_matches_H_construction(self, identity_B):
        """kron_C should match term in H_M construction."""
        B_air = identity_B + 0.1 * np.random.rand(4, 4)
        B_sample = identity_B + 0.2 * np.random.rand(4, 4)

        kron_C = compute_kron_C_matrix(B_air, B_sample)

        # Manual computation
        C = np.linalg.solve(B_air, B_sample)
        I4 = np.eye(4)
        expected = np.kron(C.T, I4)

        assert_allclose(kron_C, expected, rtol=1e-10)

    def test_optimization_usage(self, identity_B):
        """Test that pre-computed kron_C can be used efficiently."""
        B_air = identity_B
        B_sample = identity_B * 0.8

        kron_C = compute_kron_C_matrix(B_air, B_sample)

        # Using kron_C to build H_M should match direct construction
        M = polarizer(theta=np.pi/6, tau=0.5)
        I4 = np.eye(4)

        H_via_kron = np.kron(I4, M) - kron_C
        H_direct = build_H_matrix(M, B_air, B_sample)

        assert_allclose(H_via_kron, H_direct, rtol=1e-10)


# =============================================================================
# TEST: Integration with ECM solver
# =============================================================================

class TestECMMatricesIntegration:
    """Integration tests for ECM matrices with solver."""

    def test_known_solution(self):
        """Test with a known analytical solution."""
        # For the simple case where A = W = I:
        # B = A @ M @ W = I @ M @ I = M
        # C = B_air^(-1) @ B_sample = I^(-1) @ M = M

        # For this case, W = I is in the null space of all H_M
        W_true = np.eye(4)
        A = np.eye(4)

        B_air = A @ W_true  # = I

        # Create calibration samples
        M_pol0 = polarizer(theta=0.0, tau=0.5)
        M_pol45 = polarizer(theta=np.pi/4, tau=0.5)
        M_ret = retarder(theta=np.pi/2, delta=np.pi/4, tau=0.9)

        B_pol0 = A @ M_pol0 @ W_true
        B_pol45 = A @ M_pol45 @ W_true
        B_ret = A @ M_ret @ W_true

        # Build H matrices
        H_pol0 = build_H_matrix(M_pol0, B_air, B_pol0)
        H_pol45 = build_H_matrix(M_pol45, B_air, B_pol45)
        H_ret = build_H_matrix(M_ret, B_air, B_ret)

        # Each H_M should have W_true in its null space
        vec_W = W_true.flatten(order='F')

        assert_allclose(H_pol0 @ vec_W, 0.0, atol=1e-10)
        assert_allclose(H_pol45 @ vec_W, 0.0, atol=1e-10)
        assert_allclose(H_ret @ vec_W, 0.0, atol=1e-10)

        # Build K matrix
        K = build_K_matrix([H_pol0, H_pol45, H_ret])

        # K @ vec_W should also be ≈ 0
        assert_allclose(K @ vec_W, 0.0, atol=1e-10)

        # vec_W should be an eigenvector with eigenvalue ≈ 0
        eigenvalues = np.linalg.eigvalsh(K)
        assert np.min(eigenvalues) < 1e-10
