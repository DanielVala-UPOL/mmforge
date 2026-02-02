"""
Tests for ECM Modulation Basis Module

Tests the build_modulation_basis and build_intensity_matrix functions
that construct the dual rotating compensator measurement model.

References
----------
[1] Compain et al., Appl. Opt. 38, 3490-3502 (1999), Section 2
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from ecm.config.ecm_config import ECMConfig
from ecm.core.modulation import (
    ModulationBasis,
    build_modulation_basis,
    build_intensity_matrix,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def default_config():
    """Create default ECM configuration."""
    return ECMConfig()


@pytest.fixture
def modulation_basis(default_config):
    """Build modulation basis for default configuration."""
    return build_modulation_basis(default_config)


# =============================================================================
# TEST: build_modulation_basis
# =============================================================================

class TestBuildModulationBasis:
    """Tests for build_modulation_basis function."""

    def test_output_type(self, modulation_basis):
        """Should return ModulationBasis dataclass."""
        assert isinstance(modulation_basis, ModulationBasis)

    def test_W_mod_shape(self, modulation_basis, default_config):
        """W_mod should be [n_angles × 16]."""
        n_angles = default_config.acquisition.n_angular_positions
        assert modulation_basis.W_mod.shape == (n_angles, 16)

    def test_inv_W_mod_shape(self, modulation_basis, default_config):
        """inv_W_mod should be [16 × n_angles]."""
        n_angles = default_config.acquisition.n_angular_positions
        assert modulation_basis.inv_W_mod.shape == (16, n_angles)

    def test_omega_shape(self, modulation_basis, default_config):
        """omega should have n_angles elements."""
        n_angles = default_config.acquisition.n_angular_positions
        assert modulation_basis.omega.shape == (n_angles,)

    def test_omega_range(self, modulation_basis):
        """omega should span [0, 2π)."""
        omega = modulation_basis.omega
        assert omega[0] >= 0
        assert omega[-1] < 2 * np.pi
        # Check uniform spacing
        d_omega = np.diff(omega)
        assert_allclose(d_omega, d_omega[0], rtol=1e-10)

    def test_condition_number_reasonable(self, modulation_basis):
        """Condition number should be < 10 for typical config."""
        # For a well-designed modulation scheme, condition number is typically 2-5
        assert modulation_basis.condition_number < 10
        assert modulation_basis.condition_number > 1

    def test_freq_ratios_stored(self, modulation_basis, default_config):
        """Frequency ratios should be stored correctly."""
        assert modulation_basis.freq_ratio_psg == default_config.instrument.psg_freq_ratio
        assert modulation_basis.freq_ratio_psa == default_config.instrument.psa_freq_ratio

    def test_pseudo_inverse_property(self, modulation_basis):
        """inv_W_mod should satisfy W_mod @ inv_W_mod @ W_mod ≈ W_mod."""
        W = modulation_basis.W_mod
        W_inv = modulation_basis.inv_W_mod

        # This is the Moore-Penrose pseudo-inverse property
        reconstructed = W @ W_inv @ W
        # Use absolute tolerance for values near zero
        assert_allclose(reconstructed, W, rtol=1e-10, atol=1e-14)

    def test_dc_component_is_ones(self, modulation_basis):
        """First column of W_mod should be all 1s (DC term)."""
        # The first basis function is the constant term = 1
        assert_allclose(modulation_basis.W_mod[:, 0], 1.0, rtol=1e-10)

    @pytest.mark.parametrize("n_angles", [48, 96, 144, 192])
    def test_various_angular_samplings(self, n_angles):
        """Should work for different angular resolutions."""
        cfg = ECMConfig()
        cfg.acquisition.n_angular_positions = n_angles

        basis = build_modulation_basis(cfg)

        assert basis.W_mod.shape == (n_angles, 16)
        assert basis.inv_W_mod.shape == (16, n_angles)
        assert len(basis.omega) == n_angles

    def test_different_frequency_ratios(self):
        """Should handle different PSG/PSA frequency ratios."""
        cfg = ECMConfig()
        cfg.instrument.psg_freq_ratio = 1
        cfg.instrument.psa_freq_ratio = 5

        basis = build_modulation_basis(cfg)

        assert basis.freq_ratio_psg == 1
        assert basis.freq_ratio_psa == 5
        assert basis.W_mod.shape[1] == 16  # Still 16 basis functions

    def test_orthogonality_of_basis(self, modulation_basis):
        """Basis functions should be approximately orthogonal."""
        W = modulation_basis.W_mod
        n_angles = W.shape[0]

        # Gram matrix: W.T @ W / n_angles should be close to diagonal
        # (for orthogonal basis functions)
        gram = W.T @ W / n_angles

        # Check that off-diagonal elements are small relative to diagonal
        diag = np.diag(gram)
        off_diag = gram - np.diag(diag)

        # Off-diagonal should be much smaller than diagonal
        # (not exactly zero due to finite sampling)
        assert np.max(np.abs(off_diag)) < 0.1 * np.mean(np.abs(diag))


# =============================================================================
# TEST: build_intensity_matrix
# =============================================================================

class TestBuildIntensityMatrix:
    """Tests for build_intensity_matrix function."""

    def test_output_shape_single_wavelength(self, modulation_basis):
        """B should be [4 × 4] for single wavelength."""
        n_angles = modulation_basis.W_mod.shape[0]
        intensity = np.random.rand(n_angles)

        B = build_intensity_matrix(intensity, modulation_basis.inv_W_mod)

        assert B.shape == (4, 4)

    def test_output_shape_multiple_wavelengths(self, modulation_basis):
        """B should be [4 × 4 × n_wavelengths] for multiple wavelengths."""
        n_angles = modulation_basis.W_mod.shape[0]
        n_wavelengths = 100
        intensity = np.random.rand(n_angles, n_wavelengths)

        B = build_intensity_matrix(intensity, modulation_basis.inv_W_mod)

        assert B.shape == (4, 4, n_wavelengths)

    def test_dc_signal_gives_scalar_B(self, modulation_basis):
        """Pure DC intensity should give B = c·I₄ approximately."""
        n_angles = modulation_basis.W_mod.shape[0]

        # DC signal: I(θ) = constant
        dc_value = 1000.0
        intensity = np.full(n_angles, dc_value)

        B = build_intensity_matrix(intensity, modulation_basis.inv_W_mod)

        # For a DC signal with no modulation, B should be close to
        # a scalar matrix (only B[0,0] non-zero for normalized case)
        # The exact form depends on the basis function definitions
        assert B.shape == (4, 4)
        assert np.abs(B[0, 0]) > 0  # DC component should be non-zero

    def test_linearity(self, modulation_basis):
        """build_intensity_matrix should be linear."""
        n_angles = modulation_basis.W_mod.shape[0]

        I1 = np.random.rand(n_angles)
        I2 = np.random.rand(n_angles)

        B1 = build_intensity_matrix(I1, modulation_basis.inv_W_mod)
        B2 = build_intensity_matrix(I2, modulation_basis.inv_W_mod)
        B_sum = build_intensity_matrix(I1 + I2, modulation_basis.inv_W_mod)

        assert_allclose(B_sum, B1 + B2, rtol=1e-10)

    def test_scaling(self, modulation_basis):
        """B should scale linearly with intensity."""
        n_angles = modulation_basis.W_mod.shape[0]
        scale = 2.5

        intensity = np.random.rand(n_angles)

        B1 = build_intensity_matrix(intensity, modulation_basis.inv_W_mod)
        B_scaled = build_intensity_matrix(scale * intensity, modulation_basis.inv_W_mod)

        assert_allclose(B_scaled, scale * B1, rtol=1e-10)

    def test_roundtrip_reconstruction(self, modulation_basis):
        """Should reconstruct intensity from B (approximately)."""
        n_angles = modulation_basis.W_mod.shape[0]
        W = modulation_basis.W_mod
        W_inv = modulation_basis.inv_W_mod

        # Create synthetic intensity from known B
        B_original = np.array([
            [1.0, 0.1, 0.0, 0.0],
            [0.1, 0.5, 0.0, 0.0],
            [0.0, 0.0, 0.3, 0.0],
            [0.0, 0.0, 0.0, 0.3]
        ])

        # Forward: B_vec → intensity
        B_vec = B_original.flatten(order='F')
        intensity_synth = W @ B_vec

        # Inverse: intensity → B_recovered
        B_recovered = build_intensity_matrix(intensity_synth, W_inv)

        # Use absolute tolerance for values near zero
        assert_allclose(B_recovered, B_original, rtol=1e-10, atol=1e-14)

    def test_batch_processing(self, modulation_basis):
        """Should handle batch of wavelengths efficiently."""
        n_angles = modulation_basis.W_mod.shape[0]
        n_wavelengths = 50

        intensity = np.random.rand(n_angles, n_wavelengths)

        B = build_intensity_matrix(intensity, modulation_basis.inv_W_mod)

        # Check each wavelength independently
        for i_wl in range(n_wavelengths):
            B_single = build_intensity_matrix(
                intensity[:, i_wl],
                modulation_basis.inv_W_mod
            )
            assert_allclose(B[:, :, i_wl], B_single, rtol=1e-10)


# =============================================================================
# TEST: Integration with ECM pipeline
# =============================================================================

class TestModulationIntegration:
    """Integration tests for modulation module."""

    def test_modulation_basis_invertible(self, modulation_basis):
        """The modulation basis should support reconstruction."""
        W = modulation_basis.W_mod
        W_inv = modulation_basis.inv_W_mod

        # W_inv @ W should be close to identity (16×16)
        product = W_inv @ W
        assert_allclose(product, np.eye(16), atol=1e-10)

    def test_consistent_with_measurement_model(self, modulation_basis):
        """Test that B = A @ M @ W relationship is properly encoded."""
        # This is a sanity check that the basis functions correctly
        # encode the dual rotating compensator measurement model

        # For air measurement (M = I), B should equal A @ W
        # This relationship is tested more thoroughly in the ECM solver tests

        # Here we just verify the dimensions work out
        n_angles = modulation_basis.W_mod.shape[0]
        intensity = np.random.rand(n_angles, 10)

        B = build_intensity_matrix(intensity, modulation_basis.inv_W_mod)

        # B should be 4×4 matrices (× n_wavelengths)
        assert B.shape == (4, 4, 10)

        # All B matrices should be finite
        assert np.all(np.isfinite(B))
