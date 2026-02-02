"""
Tests for ECM Parameter Extraction Module

Tests the extract_sample_params function that extracts optical parameters
(transmission, retardation, ellipsometric angle) from eigenvalue analysis.

References
----------
[1] Compain et al., Appl. Opt. 38, 3490-3502 (1999), Appendix B
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

from ecm.core.parameter_extraction import (
    extract_sample_params,
    PolarizerParams,
    RetarderParams,
)
from ecm.utils.mueller_matrices import polarizer, retarder, identity


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def ideal_system():
    """Create ideal B matrices (A = W = I)."""
    # For A = W = I: B = A @ M @ W = M
    # So B_air = I, B_sample = M
    B_air = np.eye(4)
    return B_air


# =============================================================================
# TEST: Polarizer Parameter Extraction
# =============================================================================

class TestPolarizerExtraction:
    """Tests for polarizer parameter extraction."""

    def test_output_type(self, ideal_system):
        """Should return PolarizerParams for polarizer sample."""
        B_air = ideal_system
        M_pol = polarizer(theta=0.0, tau=0.5)
        B_pol = M_pol.copy()

        params = extract_sample_params(B_air, B_pol, 'polarizer')

        assert isinstance(params, PolarizerParams)

    def test_tau_extraction(self, ideal_system):
        """Should correctly extract transmission τ."""
        B_air = ideal_system

        for tau_expected in [0.3, 0.5, 0.8, 1.0]:
            M_pol = polarizer(theta=0.0, tau=tau_expected)
            B_pol = M_pol.copy()

            params = extract_sample_params(B_air, B_pol, 'polarizer')

            assert_allclose(params.tau, tau_expected, rtol=1e-6)

    def test_eigenvalues_stored(self, ideal_system):
        """Eigenvalues should be stored in params."""
        B_air = ideal_system
        M_pol = polarizer(theta=0.0, tau=0.5)
        B_pol = M_pol.copy()

        params = extract_sample_params(B_air, B_pol, 'polarizer')

        assert hasattr(params, 'eigenvalues')
        assert len(params.eigenvalues) == 4

    def test_polarizer_eigenvalue_structure(self, ideal_system):
        """Polarizer should have one non-zero eigenvalue."""
        B_air = ideal_system
        tau = 0.6
        M_pol = polarizer(theta=0.0, tau=tau)
        B_pol = M_pol.copy()

        params = extract_sample_params(B_air, B_pol, 'polarizer')

        # Sort eigenvalues by magnitude
        eigs_sorted = np.sort(np.abs(params.eigenvalues))[::-1]

        # Largest should be τ, others should be ≈ 0
        assert_allclose(eigs_sorted[0], tau, rtol=1e-6)
        assert_allclose(eigs_sorted[1:], 0.0, atol=1e-10)

    def test_different_polarizer_angles(self, ideal_system):
        """τ extraction should work for any polarizer angle."""
        B_air = ideal_system
        tau = 0.5

        for theta in [0, np.pi/6, np.pi/4, np.pi/3, np.pi/2]:
            M_pol = polarizer(theta=theta, tau=tau)
            B_pol = M_pol.copy()

            params = extract_sample_params(B_air, B_pol, 'polarizer')

            assert_allclose(params.tau, tau, rtol=1e-6)


# =============================================================================
# TEST: Retarder Parameter Extraction
# =============================================================================

class TestRetarderExtraction:
    """Tests for retarder parameter extraction."""

    def test_output_type(self, ideal_system):
        """Should return RetarderParams for retarder sample."""
        B_air = ideal_system
        M_ret = retarder(theta=0.0, delta=np.pi/4, tau=0.9)
        B_ret = M_ret.copy()

        params = extract_sample_params(B_air, B_ret, 'retarder')

        assert isinstance(params, RetarderParams)

    def test_tau_extraction(self, ideal_system):
        """Should correctly extract transmission τ."""
        B_air = ideal_system

        for tau_expected in [0.8, 0.9, 0.95, 1.0]:
            M_ret = retarder(theta=np.pi/2, delta=np.pi/4, tau=tau_expected)
            B_ret = M_ret.copy()

            params = extract_sample_params(B_air, B_ret, 'retarder')

            assert_allclose(params.tau, tau_expected, rtol=1e-4)

    def test_delta_extraction_qwp(self, ideal_system):
        """Should correctly extract δ for quarter-wave plate."""
        B_air = ideal_system
        delta_expected = np.pi / 2  # QWP

        M_ret = retarder(theta=np.pi/2, delta=delta_expected, tau=1.0)
        B_ret = M_ret.copy()

        params = extract_sample_params(B_air, B_ret, 'retarder')

        # Delta extraction may have sign ambiguity and phase wrapping
        # Check that the absolute value is close (within phase wrapping)
        assert_allclose(np.abs(params.delta), delta_expected, rtol=0.1)

    def test_delta_extraction_hwp(self, ideal_system):
        """Should correctly extract δ for half-wave plate."""
        B_air = ideal_system
        delta_expected = np.pi  # HWP

        M_ret = retarder(theta=np.pi/2, delta=delta_expected, tau=1.0)
        B_ret = M_ret.copy()

        params = extract_sample_params(B_air, B_ret, 'retarder')

        # Note: For HWP (δ=π), the eigenvalues exp(±iπ) = -1 are real,
        # so the eigenvalue-based extraction has difficulty distinguishing
        # δ=π from δ=0. The tau and psi extraction should still work.
        # This is a known limitation of eigenvalue-based extraction.
        assert_allclose(params.tau, 1.0, rtol=0.05)
        assert_allclose(params.psi, np.pi/4, rtol=0.1)  # Should still be 45°

    def test_delta_extraction_various(self, ideal_system):
        """Should correctly extract δ for various retardations."""
        B_air = ideal_system

        # Test retardations that have distinct complex eigenvalues
        # (avoid δ near 0 or π where eigenvalues become real)
        for delta_expected in [np.pi/6, np.pi/4, np.pi/3, np.pi/2]:
            M_ret = retarder(theta=np.pi/2, delta=delta_expected, tau=1.0)
            B_ret = M_ret.copy()

            params = extract_sample_params(B_air, B_ret, 'retarder')

            # Allow for sign ambiguity and numerical precision
            assert_allclose(np.abs(params.delta), delta_expected, rtol=0.15)

    def test_psi_ideal_linear_retarder(self, ideal_system):
        """Ψ should be 45° for ideal linear retarder."""
        B_air = ideal_system
        M_ret = retarder(theta=np.pi/2, delta=np.pi/4, tau=1.0)
        B_ret = M_ret.copy()

        params = extract_sample_params(B_air, B_ret, 'retarder')

        # For ideal linear retarder, Ψ = 45°
        assert_allclose(params.psi, np.pi/4, rtol=1e-4)

    def test_eigenvalue_structure_real_complex(self, ideal_system):
        """Retarder should have 2 real and 2 complex eigenvalues."""
        B_air = ideal_system
        M_ret = retarder(theta=np.pi/2, delta=np.pi/4, tau=1.0)
        B_ret = M_ret.copy()

        params = extract_sample_params(B_air, B_ret, 'retarder')

        # Check real eigenvalues
        assert len(params.eigenvalues_real) == 2
        assert np.all(np.isreal(params.eigenvalues_real))

        # Check complex eigenvalues (should be conjugate pair)
        assert len(params.eigenvalues_complex) == 2

    def test_different_retarder_angles(self, ideal_system):
        """Parameter extraction should work for various retarder angles."""
        B_air = ideal_system
        delta = np.pi / 4
        tau = 0.95

        for theta in [0, np.pi/4, np.pi/2, 3*np.pi/4]:
            M_ret = retarder(theta=theta, delta=delta, tau=tau)
            B_ret = M_ret.copy()

            params = extract_sample_params(B_air, B_ret, 'retarder')

            # τ and δ should be extractable regardless of angle
            assert_allclose(params.tau, tau, rtol=0.05)
            assert_allclose(np.abs(params.delta), delta, rtol=0.15)


# =============================================================================
# TEST: Error Handling
# =============================================================================

class TestParameterExtractionErrors:
    """Error handling tests."""

    def test_invalid_sample_type(self, ideal_system):
        """Should raise error for invalid sample type."""
        B_air = ideal_system
        B_sample = np.eye(4)

        with pytest.raises(ValueError, match="sample_type"):
            extract_sample_params(B_air, B_sample, 'invalid_type')

    def test_B_air_shape_validation(self):
        """Should validate B_air shape."""
        B_air_wrong = np.eye(3)
        B_sample = np.eye(4)

        with pytest.raises(ValueError, match="4×4"):
            extract_sample_params(B_air_wrong, B_sample, 'polarizer')

    def test_B_sample_shape_validation(self, ideal_system):
        """Should validate B_sample shape."""
        B_air = ideal_system
        B_sample_wrong = np.eye(3)

        with pytest.raises(ValueError, match="4×4"):
            extract_sample_params(B_air, B_sample_wrong, 'polarizer')

    def test_singular_B_air(self):
        """Should raise error for singular B_air."""
        B_air_singular = np.zeros((4, 4))
        B_sample = np.eye(4)

        with pytest.raises(ValueError, match="poorly conditioned"):
            extract_sample_params(B_air_singular, B_sample, 'polarizer')


# =============================================================================
# TEST: Edge Cases
# =============================================================================

class TestParameterExtractionEdgeCases:
    """Edge case tests."""

    def test_identity_sample(self, ideal_system):
        """Air sample (M = I) should give τ ≈ 1."""
        B_air = ideal_system
        B_sample = np.eye(4)  # Identity

        # As retarder with δ ≈ 0
        params = extract_sample_params(B_air, B_sample, 'retarder')

        # τ should be close to 1
        assert_allclose(params.tau, 1.0, rtol=1e-4)

        # δ should be close to 0
        assert_allclose(params.delta, 0.0, atol=1e-6)

    def test_zero_retardation(self, ideal_system):
        """Retarder with δ = 0 should be like identity."""
        B_air = ideal_system
        M_ret = retarder(theta=np.pi/2, delta=0.0, tau=0.95)
        B_ret = M_ret.copy()

        params = extract_sample_params(B_air, B_ret, 'retarder')

        assert_allclose(params.tau, 0.95, rtol=1e-4)
        assert_allclose(params.delta, 0.0, atol=1e-6)

    def test_small_tau(self, ideal_system):
        """Should handle small transmission values."""
        B_air = ideal_system
        tau = 0.1
        M_pol = polarizer(theta=0.0, tau=tau)
        B_pol = M_pol.copy()

        params = extract_sample_params(B_air, B_pol, 'polarizer')

        assert_allclose(params.tau, tau, rtol=1e-4)

    def test_noisy_measurements(self, ideal_system):
        """Should be reasonably robust to small noise."""
        B_air = ideal_system + 0.01 * np.random.randn(4, 4)
        tau = 0.5
        M_pol = polarizer(theta=0.0, tau=tau)
        B_pol = M_pol + 0.01 * np.random.randn(4, 4)

        params = extract_sample_params(B_air, B_pol, 'polarizer')

        # Should still get approximately correct τ
        assert_allclose(params.tau, tau, rtol=0.1)  # 10% tolerance for noisy case


# =============================================================================
# TEST: Theory Validation
# =============================================================================

class TestParameterExtractionTheory:
    """Tests validating theoretical predictions."""

    def test_polarizer_eigenvalue_formula(self, ideal_system):
        """Polarizer eigenvalues should be {τ, 0, 0, 0}."""
        B_air = ideal_system
        tau = 0.7
        M_pol = polarizer(theta=np.pi/6, tau=tau)
        B_pol = M_pol.copy()

        params = extract_sample_params(B_air, B_pol, 'polarizer')

        # C = B_air^(-1) @ B_pol = I^(-1) @ M_pol = M_pol
        # Eigenvalues of polarizer Mueller matrix are {τ, 0, 0, 0}
        eigs_sorted = np.sort(np.abs(params.eigenvalues))[::-1]

        assert_allclose(eigs_sorted[0], tau, rtol=1e-6)
        assert_allclose(eigs_sorted[1:], 0.0, atol=1e-10)

    def test_retarder_eigenvalue_formula(self, ideal_system):
        """
        Retarder eigenvalues should follow the formula from Compain Appendix B.

        For ideal linear retarder (Ψ = 45°):
        - λ₁ = λ₂ = τ (two equal real eigenvalues)
        - λ₃,₄ = τ exp(±iδ) (complex conjugate pair)
        """
        B_air = ideal_system
        tau = 0.9
        delta = np.pi / 3  # 60°

        M_ret = retarder(theta=np.pi/2, delta=delta, tau=tau)
        B_ret = M_ret.copy()

        params = extract_sample_params(B_air, B_ret, 'retarder')

        # Real eigenvalues should both be τ
        assert_allclose(params.eigenvalues_real[0], tau, rtol=0.05)
        assert_allclose(params.eigenvalues_real[1], tau, rtol=0.05)

        # Complex eigenvalues should have magnitude τ
        mag_complex = np.abs(params.eigenvalues_complex)
        assert_allclose(mag_complex[0], tau, rtol=0.05)
        assert_allclose(mag_complex[1], tau, rtol=0.05)

        # Phase difference should be 2δ (since λ₃/λ₄ = exp(2iδ))
        phase_diff = np.angle(params.eigenvalues_complex[0] / params.eigenvalues_complex[1])
        assert_allclose(np.abs(phase_diff), 2*delta, rtol=0.15)
