"""
Tests for ECM Sample Processing Module

Tests the extract_mueller_matrix and process_sample functions that
extract Mueller matrices from calibrated measurements.

References
----------
[1] Compain et al., Appl. Opt. 38, 3490-3502 (1999), Eq. 16
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

from ecm.core.sample_processing import (
    MuellerMatrixResult,
    extract_mueller_matrix,
    process_sample,
    normalize_mueller_matrix,
    validate_mueller_matrix,
)
from ecm.utils.mueller_matrices import identity, polarizer, retarder


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def calibration_matrices():
    """Create realistic calibration matrices A and W."""
    # Realistic PSG matrix W
    W = np.array([
        [1.0, 0.15, 0.0, 0.0],
        [0.1, 0.85, 0.05, 0.0],
        [0.0, 0.0, 0.75, 0.1],
        [0.0, 0.0, -0.1, 0.7]
    ])

    # Realistic PSA matrix A
    A = np.array([
        [1.0, 0.1, 0.0, 0.0],
        [0.12, 0.9, 0.0, 0.05],
        [0.0, 0.0, 0.8, 0.0],
        [0.0, -0.05, 0.0, 0.75]
    ])

    return A, W


@pytest.fixture
def identity_calibration():
    """Create identity calibration (A = W = I)."""
    A = np.eye(4)
    W = np.eye(4)
    return A, W


# =============================================================================
# TEST: extract_mueller_matrix
# =============================================================================

class TestExtractMuellerMatrix:
    """Tests for extract_mueller_matrix function."""

    def test_output_shape_single(self, identity_calibration):
        """Should return [4 × 4] for single wavelength."""
        A, W = identity_calibration
        B_sample = np.eye(4)

        M = extract_mueller_matrix(B_sample, A, W)

        assert M.shape == (4, 4)

    def test_output_shape_multi(self, identity_calibration):
        """Should return [4 × 4 × n_wl] for multiple wavelengths."""
        A, W = identity_calibration
        n_wavelengths = 10
        B_sample = np.stack([np.eye(4) for _ in range(n_wavelengths)], axis=2)

        M = extract_mueller_matrix(B_sample, A, W)

        assert M.shape == (4, 4, n_wavelengths)

    def test_identity_calibration_identity_sample(self, identity_calibration):
        """With A=W=I and B=I, should get M=I."""
        A, W = identity_calibration
        B_sample = np.eye(4)

        M = extract_mueller_matrix(B_sample, A, W)

        assert_allclose(M, np.eye(4), rtol=1e-10)

    def test_identity_calibration_polarizer_sample(self, identity_calibration):
        """With A=W=I, M = B (no transformation)."""
        A, W = identity_calibration
        M_expected = polarizer(theta=np.pi/4, tau=0.5)
        B_sample = M_expected.copy()  # B = A @ M @ W = I @ M @ I = M

        M = extract_mueller_matrix(B_sample, A, W)

        assert_allclose(M, M_expected, rtol=1e-10)

    def test_measurement_equation_consistency(self, calibration_matrices):
        """Should satisfy M = A^(-1) @ B @ W^(-1)."""
        A, W = calibration_matrices
        M_true = polarizer(theta=np.pi/6, tau=0.6)

        # Generate B from measurement equation: B = A @ M @ W
        B_sample = A @ M_true @ W

        # Extract M
        M_recovered = extract_mueller_matrix(B_sample, A, W)

        # Use absolute tolerance for small values
        assert_allclose(M_recovered, M_true, rtol=1e-6, atol=1e-10)

    def test_retarder_recovery(self, calibration_matrices):
        """Should correctly recover retarder Mueller matrix."""
        A, W = calibration_matrices
        M_true = retarder(theta=np.pi/2, delta=np.pi/4, tau=0.9)

        B_sample = A @ M_true @ W
        M_recovered = extract_mueller_matrix(B_sample, A, W)

        # Use absolute tolerance for small values
        assert_allclose(M_recovered, M_true, rtol=1e-6, atol=1e-10)

    def test_multi_wavelength_extraction(self, calibration_matrices):
        """Should handle multiple wavelengths."""
        A, W = calibration_matrices
        n_wavelengths = 5

        # Create per-wavelength A and W (stacked)
        A_all = np.stack([A] * n_wavelengths, axis=2)
        W_all = np.stack([W] * n_wavelengths, axis=2)

        # Create different samples for each wavelength
        B_sample = np.zeros((4, 4, n_wavelengths))
        M_expected = np.zeros((4, 4, n_wavelengths))

        for i in range(n_wavelengths):
            M_i = polarizer(theta=i * np.pi/10, tau=0.5 + 0.1*i)
            M_expected[:, :, i] = M_i
            B_sample[:, :, i] = A @ M_i @ W

        M_recovered = extract_mueller_matrix(B_sample, A_all, W_all)

        # Use absolute tolerance for small values
        assert_allclose(M_recovered, M_expected, rtol=1e-6, atol=1e-10)

    def test_singular_A_raises(self, identity_calibration):
        """Should raise error for singular A."""
        _, W = identity_calibration
        A_singular = np.zeros((4, 4))
        B_sample = np.eye(4)

        with pytest.raises(ValueError, match="poorly conditioned"):
            extract_mueller_matrix(B_sample, A_singular, W)

    def test_singular_W_raises(self, identity_calibration):
        """Should raise error for singular W."""
        A, _ = identity_calibration
        W_singular = np.zeros((4, 4))
        B_sample = np.eye(4)

        with pytest.raises(ValueError, match="poorly conditioned"):
            extract_mueller_matrix(B_sample, A, W_singular)


# =============================================================================
# TEST: normalize_mueller_matrix
# =============================================================================

class TestNormalizeMuellerMatrix:
    """Tests for normalize_mueller_matrix function."""

    def test_m00_becomes_one(self):
        """M[0,0] should become 1 after normalization."""
        M = polarizer(theta=0, tau=0.5)
        M_norm = normalize_mueller_matrix(M)

        assert_allclose(M_norm[0, 0], 1.0, rtol=1e-10)

    def test_preserves_ratios(self):
        """Element ratios should be preserved."""
        M = polarizer(theta=0, tau=0.5)
        M_norm = normalize_mueller_matrix(M)

        # M[0,1] / M[0,0] should be preserved
        expected_ratio = M[0, 1] / M[0, 0]
        actual_ratio = M_norm[0, 1] / M_norm[0, 0]

        assert_allclose(actual_ratio, expected_ratio, rtol=1e-10)

    def test_multi_wavelength(self):
        """Should handle multiple wavelengths."""
        n_wavelengths = 5
        M = np.zeros((4, 4, n_wavelengths))

        for i in range(n_wavelengths):
            M[:, :, i] = polarizer(theta=0, tau=0.3 + 0.1*i)

        M_norm = normalize_mueller_matrix(M)

        for i in range(n_wavelengths):
            assert_allclose(M_norm[0, 0, i], 1.0, rtol=1e-10)

    def test_zero_m00_unchanged(self):
        """Matrix with M[0,0] = 0 should be returned unchanged."""
        M = np.zeros((4, 4))
        M[1, 1] = 1.0

        M_norm = normalize_mueller_matrix(M)

        assert_allclose(M_norm, M, rtol=1e-10)


# =============================================================================
# TEST: validate_mueller_matrix
# =============================================================================

class TestValidateMuellerMatrix:
    """Tests for validate_mueller_matrix function."""

    def test_valid_identity(self):
        """Identity matrix should be valid."""
        M = np.eye(4)
        result = validate_mueller_matrix(M)

        assert result['is_valid']
        assert result['m00_positive']

    def test_valid_polarizer(self):
        """Normalized polarizer should be valid."""
        M = polarizer(theta=0, tau=0.5)
        M_norm = M / M[0, 0]

        result = validate_mueller_matrix(M_norm)

        assert result['is_valid']

    def test_valid_retarder(self):
        """Normalized retarder should be valid."""
        M = retarder(theta=np.pi/2, delta=np.pi/4, tau=1.0)
        M_norm = M / M[0, 0]

        result = validate_mueller_matrix(M_norm)

        assert result['is_valid']

    def test_negative_m00_invalid(self):
        """Negative M[0,0] should be flagged."""
        M = -np.eye(4)

        result = validate_mueller_matrix(M)

        assert not result['m00_positive']
        assert not result['is_valid']

    def test_returns_dict(self):
        """Should return dictionary with expected keys."""
        M = np.eye(4)
        result = validate_mueller_matrix(M)

        assert 'is_valid' in result
        assert 'm00_positive' in result
        assert 'trace_constraint' in result
        assert 'frobenius_constraint' in result
        assert 'messages' in result


# =============================================================================
# TEST: process_sample
# =============================================================================

class TestProcessSample:
    """Tests for process_sample function."""

    def test_output_type(self, identity_calibration):
        """Should return MuellerMatrixResult."""
        A, W = identity_calibration
        from ecm.config.ecm_config import ECMConfig
        from ecm.core.modulation import build_modulation_basis

        cfg = ECMConfig()
        basis = build_modulation_basis(cfg)

        n_angles = cfg.acquisition.n_angular_positions
        n_wavelengths = 10
        sample_data = np.random.rand(n_angles, n_wavelengths) * 1000

        result = process_sample(
            sample_data=sample_data,
            A=A,
            W=W,
            inv_W_mod=basis.inv_W_mod
        )

        assert isinstance(result, MuellerMatrixResult)

    def test_result_fields(self, identity_calibration):
        """MuellerMatrixResult should have expected fields."""
        A, W = identity_calibration
        from ecm.config.ecm_config import ECMConfig
        from ecm.core.modulation import build_modulation_basis

        cfg = ECMConfig()
        basis = build_modulation_basis(cfg)

        n_angles = cfg.acquisition.n_angular_positions
        sample_data = np.random.rand(n_angles, 10) * 1000

        result = process_sample(sample_data, A, W, basis.inv_W_mod)

        assert hasattr(result, 'M')
        assert hasattr(result, 'M_normalized')
        assert hasattr(result, 'm00')

    def test_m00_extraction(self, identity_calibration):
        """m00 should equal M[0,0] for each wavelength."""
        A, W = identity_calibration
        from ecm.config.ecm_config import ECMConfig
        from ecm.core.modulation import build_modulation_basis

        cfg = ECMConfig()
        basis = build_modulation_basis(cfg)

        n_angles = cfg.acquisition.n_angular_positions
        n_wavelengths = 5
        sample_data = np.random.rand(n_angles, n_wavelengths) * 1000

        result = process_sample(sample_data, A, W, basis.inv_W_mod)

        for i in range(n_wavelengths):
            assert_allclose(result.m00[i], result.M[0, 0, i], rtol=1e-10)

    def test_normalization_correct(self, identity_calibration):
        """M_normalized should have m00 = 1."""
        A, W = identity_calibration
        from ecm.config.ecm_config import ECMConfig
        from ecm.core.modulation import build_modulation_basis

        cfg = ECMConfig()
        basis = build_modulation_basis(cfg)

        n_angles = cfg.acquisition.n_angular_positions
        sample_data = np.random.rand(n_angles, 10) * 1000 + 100  # Ensure positive

        result = process_sample(sample_data, A, W, basis.inv_W_mod)

        # Check normalization
        for i in range(result.M_normalized.shape[2]):
            if np.abs(result.m00[i]) > 1e-12:
                assert_allclose(result.M_normalized[0, 0, i], 1.0, rtol=1e-10)

    def test_dark_subtraction(self, identity_calibration):
        """Dark subtraction should be applied correctly."""
        A, W = identity_calibration
        from ecm.config.ecm_config import ECMConfig
        from ecm.core.modulation import build_modulation_basis

        cfg = ECMConfig()
        basis = build_modulation_basis(cfg)

        n_angles = cfg.acquisition.n_angular_positions
        n_wavelengths = 5

        dark = np.full((n_angles, n_wavelengths), 100.0)
        sample = np.random.rand(n_angles, n_wavelengths) * 1000 + 200

        # With dark subtraction
        result_with_dark = process_sample(sample, A, W, basis.inv_W_mod, dark=dark)

        # Without dark (sample - dark)
        result_no_dark = process_sample(sample - dark, A, W, basis.inv_W_mod)

        # Results should be similar (not exact due to clamping)
        assert_allclose(result_with_dark.M, result_no_dark.M, rtol=1e-6)


# =============================================================================
# TEST: Edge Cases
# =============================================================================

class TestSampleProcessingEdgeCases:
    """Edge case tests for sample processing."""

    def test_single_wavelength(self, identity_calibration):
        """Should handle single wavelength input."""
        A, W = identity_calibration
        from ecm.config.ecm_config import ECMConfig
        from ecm.core.modulation import build_modulation_basis

        cfg = ECMConfig()
        basis = build_modulation_basis(cfg)

        n_angles = cfg.acquisition.n_angular_positions
        sample_data = np.random.rand(n_angles, 1) * 1000 + 100  # Ensure positive

        result = process_sample(sample_data, A, W, basis.inv_W_mod)

        # Single wavelength still returns 3D array for consistency
        assert result.M.shape[0] == 4
        assert result.M.shape[1] == 4

    def test_per_wavelength_calibration(self):
        """Should handle per-wavelength A and W matrices."""
        from ecm.config.ecm_config import ECMConfig
        from ecm.core.modulation import build_modulation_basis

        cfg = ECMConfig()
        basis = build_modulation_basis(cfg)

        n_angles = cfg.acquisition.n_angular_positions
        n_wavelengths = 5

        # Per-wavelength calibration matrices
        A = np.stack([np.eye(4) * (1 + 0.1*i) for i in range(n_wavelengths)], axis=2)
        W = np.stack([np.eye(4) * (1 - 0.05*i) for i in range(n_wavelengths)], axis=2)

        sample_data = np.random.rand(n_angles, n_wavelengths) * 1000

        result = process_sample(sample_data, A, W, basis.inv_W_mod)

        assert result.M.shape == (4, 4, n_wavelengths)
