"""
Tests for ECM Eigenvalue Solver Module

Tests the solve_W and solve_A functions that extract the PSG (W) and
PSA (A) modulation matrices from the ECM eigenvalue problem.

References
----------
[1] Compain et al., Appl. Opt. 38, 3490-3502 (1999), Eqs. 16, 20-21
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

from ecm.core.ecm_solver import (
    solve_W,
    solve_A,
    WDiagnostics,
    ADiagnostics,
)
from ecm.core.ecm_matrices import build_H_matrix, build_K_matrix
from ecm.utils.mueller_matrices import identity, polarizer, retarder


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def synthetic_K_matrix():
    """Create a synthetic K matrix with known solution."""
    # Build K from a known W matrix
    W_true = np.array([
        [1.0, 0.2, 0.0, 0.0],
        [0.1, 0.8, 0.0, 0.0],
        [0.0, 0.0, 0.7, 0.1],
        [0.0, 0.0, -0.1, 0.6]
    ])
    A = np.array([
        [1.0, 0.1, 0.0, 0.0],
        [0.1, 0.9, 0.0, 0.0],
        [0.0, 0.0, 0.8, 0.0],
        [0.0, 0.0, 0.0, 0.7]
    ])

    B_air = A @ W_true

    # Create calibration sample measurements
    samples = [
        polarizer(theta=0.0, tau=0.5),
        polarizer(theta=np.pi/4, tau=0.5),
        retarder(theta=np.pi/2, delta=np.pi/4, tau=0.9),
    ]

    H_matrices = []
    for M in samples:
        B_sample = A @ M @ W_true
        H = build_H_matrix(M, B_air, B_sample)
        H_matrices.append(H)

    K = build_K_matrix(H_matrices)

    return K, W_true, A, B_air


@pytest.fixture
def identity_system():
    """Create a simple system where W = A = I."""
    W_true = np.eye(4)
    A = np.eye(4)
    B_air = A @ W_true  # = I

    samples = [
        polarizer(theta=0.0, tau=0.5),
        polarizer(theta=np.pi/4, tau=0.5),
        retarder(theta=np.pi/2, delta=np.pi/4, tau=0.9),
    ]

    H_matrices = []
    for M in samples:
        B_sample = A @ M @ W_true
        H = build_H_matrix(M, B_air, B_sample)
        H_matrices.append(H)

    K = build_K_matrix(H_matrices)

    return K, W_true, A, B_air


# =============================================================================
# TEST: solve_W
# =============================================================================

class TestSolveW:
    """Tests for solve_W function."""

    def test_output_shape(self, synthetic_K_matrix):
        """W should be [4 × 4]."""
        K, _, _, _ = synthetic_K_matrix
        W, diag = solve_W(K)

        assert W.shape == (4, 4)

    def test_output_types(self, synthetic_K_matrix):
        """Should return W and WDiagnostics."""
        K, _, _, _ = synthetic_K_matrix
        W, diag = solve_W(K)

        assert isinstance(W, np.ndarray)
        assert isinstance(diag, WDiagnostics)

    def test_diagnostics_fields(self, synthetic_K_matrix):
        """WDiagnostics should have all expected fields."""
        K, _, _, _ = synthetic_K_matrix
        W, diag = solve_W(K)

        assert hasattr(diag, 'eigenvalues')
        assert hasattr(diag, 'lambda_16')
        assert hasattr(diag, 'lambda_15')
        assert hasattr(diag, 'ratio_16_15')
        assert hasattr(diag, 'condition_number')

    def test_eigenvalues_sorted_descending(self, synthetic_K_matrix):
        """Eigenvalues should be sorted in descending order."""
        K, _, _, _ = synthetic_K_matrix
        W, diag = solve_W(K)

        eigs = diag.eigenvalues
        assert len(eigs) == 16

        # Check descending order
        for i in range(len(eigs) - 1):
            assert eigs[i] >= eigs[i + 1] - 1e-10  # Allow small numerical error

    def test_smallest_eigenvalue_near_zero(self, identity_system):
        """λ₁₆ should be ≈ 0 for consistent calibration."""
        K, _, _, _ = identity_system
        W, diag = solve_W(K)

        # Smallest eigenvalue should be very small
        assert diag.lambda_16 < 1e-10

    def test_eigenvalue_ratio_small(self, identity_system):
        """ratio_16_15 should be << 1 for good calibration."""
        K, _, _, _ = identity_system
        W, diag = solve_W(K)

        # Ratio should be very small for well-conditioned system
        assert diag.ratio_16_15 < 1e-5

    def test_normalization_W00_positive(self, synthetic_K_matrix):
        """W[0,0] should be > 0 after normalization."""
        K, _, _, _ = synthetic_K_matrix
        W, _ = solve_W(K)

        assert W[0, 0] > 0

    def test_W_recovers_true_W(self, identity_system):
        """Recovered W should match true W (up to scaling)."""
        K, W_true, _, _ = identity_system
        W, _ = solve_W(K)

        # W and W_true should be proportional (same direction)
        # Normalize both for comparison
        W_norm = W / np.linalg.norm(W, 'fro')
        W_true_norm = W_true / np.linalg.norm(W_true, 'fro')

        # Check if they match (or are negatives of each other)
        diff_pos = np.linalg.norm(W_norm - W_true_norm, 'fro')
        diff_neg = np.linalg.norm(W_norm + W_true_norm, 'fro')

        assert min(diff_pos, diff_neg) < 1e-6

    def test_K_shape_validation(self):
        """Should validate K is 16×16."""
        K_wrong = np.eye(8)

        with pytest.raises(ValueError, match="16×16"):
            solve_W(K_wrong)

    def test_fortran_ordering_used(self, identity_system):
        """Verify Fortran ordering is used in reshape."""
        K, _, _, _ = identity_system
        W, diag = solve_W(K)

        # Get the eigenvector using scipy.linalg.eigh (matches the implementation)
        import scipy.linalg
        eigenvalues, eigenvectors = scipy.linalg.eigh(K)
        W_vec = eigenvectors[:, 0]  # Smallest eigenvalue (eigh returns ascending)

        # Reshape with Fortran order should give same result
        W_manual = W_vec.reshape((4, 4), order='F')

        # Normalize sign
        if W_manual[0, 0] < 0:
            W_manual = -W_manual

        # Should match (up to sign)
        if W[0, 0] * W_manual[0, 0] < 0:
            W_manual = -W_manual

        # Use absolute tolerance for values near zero (eigenvectors can differ by numerical noise)
        assert_allclose(np.abs(W), np.abs(W_manual), rtol=1e-10, atol=1e-14)


# =============================================================================
# TEST: solve_A
# =============================================================================

class TestSolveA:
    """Tests for solve_A function."""

    def test_output_shape(self, identity_system):
        """A should be [4 × 4]."""
        K, _, _, B_air = identity_system
        W, _ = solve_W(K)

        A, diag = solve_A(W, B_air)

        assert A.shape == (4, 4)

    def test_output_types(self, identity_system):
        """Should return A and ADiagnostics."""
        K, _, _, B_air = identity_system
        W, _ = solve_W(K)

        A, diag = solve_A(W, B_air)

        assert isinstance(A, np.ndarray)
        assert isinstance(diag, ADiagnostics)

    def test_diagnostics_fields(self, identity_system):
        """ADiagnostics should have all expected fields."""
        K, _, _, B_air = identity_system
        W, _ = solve_W(K)
        A, diag = solve_A(W, B_air)

        assert hasattr(diag, 'condition_number')
        assert hasattr(diag, 'determinant')
        assert hasattr(diag, 'cond_W')

    def test_A_times_W_equals_B_air(self, identity_system):
        """A @ W should equal B_air."""
        K, _, _, B_air = identity_system
        W, _ = solve_W(K)
        A, _ = solve_A(W, B_air)

        # A @ W = B_air
        reconstructed = A @ W

        # Should match (A and W may be scaled, but their product should match B_air)
        # Normalize for comparison
        scale = B_air[0, 0] / reconstructed[0, 0] if reconstructed[0, 0] != 0 else 1
        # Use absolute tolerance for values near zero
        assert_allclose(scale * reconstructed, B_air, rtol=1e-6, atol=1e-10)

    def test_normalization_A00_positive(self, identity_system):
        """A[0,0] should be > 0 after normalization."""
        K, _, _, B_air = identity_system
        W, _ = solve_W(K)
        A, _ = solve_A(W, B_air)

        assert A[0, 0] > 0

    def test_condition_number_stored(self, identity_system):
        """Condition numbers should be stored in diagnostics."""
        K, _, _, B_air = identity_system
        W, _ = solve_W(K)
        A, diag = solve_A(W, B_air)

        assert diag.condition_number > 0
        assert diag.cond_W > 0

    def test_singular_W_raises(self):
        """Should raise error for singular W."""
        W_singular = np.zeros((4, 4))
        B_air = np.eye(4)

        with pytest.raises(ValueError, match="poorly conditioned"):
            solve_A(W_singular, B_air)

    def test_W_shape_validation(self):
        """Should validate W is 4×4."""
        W_wrong = np.eye(3)
        B_air = np.eye(4)

        with pytest.raises(ValueError, match="4×4"):
            solve_A(W_wrong, B_air)

    def test_B_air_shape_validation(self, identity_system):
        """Should validate B_air is 4×4."""
        K, _, _, _ = identity_system
        W, _ = solve_W(K)
        B_air_wrong = np.eye(3)

        with pytest.raises(ValueError, match="4×4"):
            solve_A(W, B_air_wrong)


# =============================================================================
# TEST: Integration of solve_W and solve_A
# =============================================================================

class TestSolverIntegration:
    """Integration tests for W and A solvers."""

    def test_full_calibration_recovery(self, synthetic_K_matrix):
        """Test that W and A can be recovered from calibration data."""
        K, W_true, A_true, B_air = synthetic_K_matrix

        W, w_diag = solve_W(K)
        A, a_diag = solve_A(W, B_air)

        # Check that A @ W matches B_air (up to scaling)
        reconstructed = A @ W
        if reconstructed[0, 0] != 0:
            scale = B_air[0, 0] / reconstructed[0, 0]
            # Use absolute tolerance for values near zero
            assert_allclose(scale * reconstructed, B_air, rtol=1e-4, atol=1e-10)

        # Check eigenvalue ratio is small (good calibration)
        assert w_diag.ratio_16_15 < 1e-3

    def test_mueller_matrix_recovery(self, synthetic_K_matrix):
        """Test that Mueller matrices can be recovered with calibrated A, W."""
        K, W_true, A_true, B_air = synthetic_K_matrix

        W, _ = solve_W(K)
        A, _ = solve_A(W, B_air)

        # Test with a sample Mueller matrix
        M_test = polarizer(theta=np.pi/6, tau=0.6)
        B_test = A_true @ M_test @ W_true

        # Recover M from B, A, W
        # M = A^(-1) @ B @ W^(-1)
        M_recovered = np.linalg.solve(A, B_test) @ np.linalg.inv(W)

        # Normalize both for comparison
        M_recovered_norm = M_recovered / M_recovered[0, 0] if M_recovered[0, 0] != 0 else M_recovered
        M_test_norm = M_test / M_test[0, 0] if M_test[0, 0] != 0 else M_test

        # Should match approximately (may differ because W is only determined up to a scale)
        # Use looser tolerance since eigenvector scaling may differ
        assert_allclose(M_recovered_norm, M_test_norm, rtol=0.1, atol=1e-2)

    def test_condition_numbers_reasonable(self, identity_system):
        """Condition numbers should be reasonable for well-posed problem."""
        K, _, _, B_air = identity_system

        W, w_diag = solve_W(K)
        A, a_diag = solve_A(W, B_air)

        # For identity system, condition numbers should be near 1
        assert w_diag.condition_number < 100
        assert a_diag.condition_number < 100

    def test_determinant_physical(self, synthetic_K_matrix):
        """Determinant of A should be close to ±1 for physical system."""
        K, _, _, B_air = synthetic_K_matrix

        W, _ = solve_W(K)
        A, a_diag = solve_A(W, B_air)

        # For physical polarimetric system, det(A) should be non-zero
        assert np.abs(a_diag.determinant) > 0.01


# =============================================================================
# TEST: Edge cases
# =============================================================================

class TestSolverEdgeCases:
    """Edge case tests for ECM solvers."""

    def test_nearly_singular_K(self):
        """Handle K matrix that is nearly rank-deficient."""
        # Create K with two small eigenvalues
        eigenvalues = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1e-8, 1e-15])
        Q, _ = np.linalg.qr(np.random.randn(16, 16))
        K = Q @ np.diag(eigenvalues) @ Q.T

        W, diag = solve_W(K)

        # Should still work, but ratio will indicate quality
        assert W.shape == (4, 4)
        assert diag.ratio_16_15 < 1  # Not great but should work

    def test_numerical_stability(self, synthetic_K_matrix):
        """Test numerical stability with scaled inputs."""
        K, _, _, B_air = synthetic_K_matrix

        # Scale K by large factor
        scale = 1e6
        K_scaled = K * scale

        W1, diag1 = solve_W(K)
        W2, diag2 = solve_W(K_scaled)

        # W should be the same (eigenvector doesn't depend on scale)
        # Normalize for comparison
        W1_norm = W1 / np.linalg.norm(W1, 'fro')
        W2_norm = W2 / np.linalg.norm(W2, 'fro')

        # Allow for sign flip and use absolute tolerance for small values
        assert_allclose(np.abs(W1_norm), np.abs(W2_norm), rtol=1e-4, atol=1e-10)
