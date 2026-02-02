"""
Tests for ECM Fourier Coefficient Extraction Module

Tests the extract_fourier_coefficients function that provides an alternative
analysis path using FFT for harmonic extraction.

References
----------
[1] Compain et al., Appl. Opt. 38, 3490-3502 (1999)
[2] Azzam, Opt. Lett. 2, 148-150 (1978)
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

from ecm.config.ecm_config import ECMConfig
from ecm.core.fourier import (
    FourierCoefficients,
    extract_fourier_coefficients,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def default_config():
    """Create default ECM configuration."""
    return ECMConfig()


@pytest.fixture
def n_angles():
    """Default number of angular positions."""
    return 96


@pytest.fixture
def theta(n_angles):
    """Angular positions in radians."""
    return np.linspace(0, 2 * np.pi, n_angles, endpoint=False)


# =============================================================================
# TEST: extract_fourier_coefficients
# =============================================================================

class TestExtractFourierCoefficients:
    """Tests for extract_fourier_coefficients function."""

    def test_output_type(self, default_config, theta):
        """Should return FourierCoefficients dataclass."""
        intensity = np.ones(len(theta))
        result = extract_fourier_coefficients(intensity, default_config)
        assert isinstance(result, FourierCoefficients)

    def test_pure_dc_signal(self, default_config, theta):
        """DC signal: a0 = DC value, all an, bn = 0."""
        dc_value = 1234.5
        intensity = np.full(len(theta), dc_value)

        result = extract_fourier_coefficients(intensity, default_config)

        # DC component should equal the signal value
        assert_allclose(result.a0, dc_value, rtol=1e-10)

        # All harmonic coefficients should be zero
        assert_allclose(result.an, 0.0, atol=1e-10)
        assert_allclose(result.bn, 0.0, atol=1e-10)

    def test_single_cosine_harmonic(self, default_config, theta):
        """I = A0 + A2·cos(2θ) should give a2 = A2, b2 = 0."""
        a0 = 1000.0
        a2 = 100.0
        intensity = a0 + a2 * np.cos(2 * theta)

        result = extract_fourier_coefficients(intensity, default_config)

        # Check DC component
        assert_allclose(result.a0, a0, rtol=1e-10)

        # Find index of harmonic 2
        idx_2 = np.where(result.harmonics == 2)[0][0]

        # Cosine coefficient for n=2 should be a2
        assert_allclose(result.an[idx_2], a2, rtol=1e-10)

        # Sine coefficient for n=2 should be 0
        assert_allclose(result.bn[idx_2], 0.0, atol=1e-10)

    def test_single_sine_harmonic(self, default_config, theta):
        """I = A0 + B4·sin(4θ) should give a4 = 0, b4 = B4."""
        a0 = 500.0
        b4 = 75.0
        intensity = a0 + b4 * np.sin(4 * theta)

        result = extract_fourier_coefficients(intensity, default_config)

        # Check DC component
        assert_allclose(result.a0, a0, rtol=1e-10)

        # Find index of harmonic 4
        idx_4 = np.where(result.harmonics == 4)[0][0]

        # Cosine coefficient for n=4 should be 0
        assert_allclose(result.an[idx_4], 0.0, atol=1e-10)

        # Sine coefficient for n=4 should be b4
        assert_allclose(result.bn[idx_4], b4, rtol=1e-10)

    def test_multiple_harmonics(self, default_config, theta):
        """Test with multiple harmonics: n=2, 4, 6."""
        a0 = 1000.0
        a2, b2 = 50.0, 30.0
        a4, b4 = 25.0, 15.0
        a6, b6 = 10.0, 8.0

        intensity = (
            a0 +
            a2 * np.cos(2 * theta) + b2 * np.sin(2 * theta) +
            a4 * np.cos(4 * theta) + b4 * np.sin(4 * theta) +
            a6 * np.cos(6 * theta) + b6 * np.sin(6 * theta)
        )

        result = extract_fourier_coefficients(intensity, default_config)

        # Check DC
        assert_allclose(result.a0, a0, rtol=1e-10)

        # Check each harmonic
        for n, (an_exp, bn_exp) in [(2, (a2, b2)), (4, (a4, b4)), (6, (a6, b6))]:
            if n in result.harmonics:
                idx = np.where(result.harmonics == n)[0][0]
                assert_allclose(result.an[idx], an_exp, rtol=1e-10)
                assert_allclose(result.bn[idx], bn_exp, rtol=1e-10)

    def test_all_mueller_harmonics(self, default_config, theta):
        """Test with all Mueller harmonics n=2,4,6,8,10,12."""
        coeffs = {
            2: (50, 30),
            4: (40, 25),
            6: (30, 20),
            8: (20, 15),
            10: (15, 10),
            12: (10, 5)
        }

        a0 = 1000.0
        intensity = np.full(len(theta), a0)

        for n, (an, bn) in coeffs.items():
            intensity = intensity + an * np.cos(n * theta) + bn * np.sin(n * theta)

        result = extract_fourier_coefficients(intensity, default_config)

        # Check DC
        assert_allclose(result.a0, a0, rtol=1e-10)

        # Check each harmonic
        for n, (an_exp, bn_exp) in coeffs.items():
            if n in result.harmonics:
                idx = np.where(result.harmonics == n)[0][0]
                assert_allclose(result.an[idx], an_exp, rtol=1e-9)
                assert_allclose(result.bn[idx], bn_exp, rtol=1e-9)

    def test_harmonics_array_correct(self, default_config, theta):
        """harmonics array should match config settings."""
        intensity = np.ones(len(theta))
        result = extract_fourier_coefficients(intensity, default_config)

        expected_harmonics = np.array(default_config.fourier.mueller_harmonics)
        assert_allclose(result.harmonics, expected_harmonics)

    def test_phase_relationship(self, default_config, theta):
        """Test correct phase extraction for shifted signals."""
        a0 = 500.0
        amplitude = 100.0
        phase = np.pi / 3  # 60 degrees
        n = 4  # Harmonic number

        # I = A0 + amp * cos(n*θ - phase)
        # = A0 + amp * cos(phase) * cos(n*θ) + amp * sin(phase) * sin(n*θ)
        intensity = a0 + amplitude * np.cos(n * theta - phase)

        result = extract_fourier_coefficients(intensity, default_config)

        idx = np.where(result.harmonics == n)[0][0]

        expected_an = amplitude * np.cos(phase)
        expected_bn = amplitude * np.sin(phase)

        assert_allclose(result.an[idx], expected_an, rtol=1e-9)
        assert_allclose(result.bn[idx], expected_bn, rtol=1e-9)

    def test_multiple_wavelengths(self, default_config, theta):
        """Should handle multiple wavelengths."""
        n_wavelengths = 10
        a0 = np.linspace(1000, 2000, n_wavelengths)
        a2 = np.linspace(50, 100, n_wavelengths)

        # Build intensity array [n_angles × n_wavelengths]
        intensity = np.outer(np.ones(len(theta)), a0) + \
                   np.outer(np.cos(2 * theta), a2)

        result = extract_fourier_coefficients(intensity, default_config)

        # Check shapes
        n_harmonics = len(default_config.fourier.mueller_harmonics)
        assert result.a0.shape == (n_wavelengths,)
        assert result.an.shape == (n_harmonics, n_wavelengths)
        assert result.bn.shape == (n_harmonics, n_wavelengths)

        # Check values
        assert_allclose(result.a0, a0, rtol=1e-9)

        idx_2 = np.where(result.harmonics == 2)[0][0]
        assert_allclose(result.an[idx_2, :], a2, rtol=1e-9)

    def test_1d_input(self, default_config, theta):
        """Should handle 1D input (single wavelength)."""
        intensity = 1000.0 + 50.0 * np.cos(4 * theta)

        result = extract_fourier_coefficients(intensity, default_config)

        # For 1D input, output should be scalar or 1D
        assert np.isscalar(result.a0) or result.a0.ndim == 0
        assert result.an.ndim == 1
        assert result.bn.ndim == 1

    def test_linearity(self, default_config, theta):
        """Fourier transform should be linear."""
        I1 = 500.0 + 30.0 * np.cos(2 * theta)
        I2 = 300.0 + 20.0 * np.sin(4 * theta)

        result1 = extract_fourier_coefficients(I1, default_config)
        result2 = extract_fourier_coefficients(I2, default_config)
        result_sum = extract_fourier_coefficients(I1 + I2, default_config)

        # DC should add
        assert_allclose(result_sum.a0, result1.a0 + result2.a0, rtol=1e-10)

        # Harmonic coefficients should add
        assert_allclose(result_sum.an, result1.an + result2.an, atol=1e-10)
        assert_allclose(result_sum.bn, result1.bn + result2.bn, atol=1e-10)


# =============================================================================
# TEST: Edge cases and error handling
# =============================================================================

class TestFourierEdgeCases:
    """Edge case and error handling tests."""

    def test_nyquist_limit_check(self, default_config):
        """Should enforce Nyquist limit."""
        # Create config with harmonic exceeding Nyquist
        cfg = ECMConfig()
        cfg.fourier.mueller_harmonics = (2, 4, 6, 8, 10, 12, 100)  # 100 > 96/2

        theta = np.linspace(0, 2 * np.pi, 96, endpoint=False)
        intensity = np.ones(96)

        with pytest.raises(ValueError, match="Nyquist"):
            extract_fourier_coefficients(intensity, cfg)

    def test_small_angular_sampling(self):
        """Should work with minimum viable angular sampling."""
        cfg = ECMConfig()
        cfg.fourier.mueller_harmonics = (2, 4, 6)  # Lower harmonics only

        n_angles = 24  # Nyquist limit = 12
        theta = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)
        intensity = 1000.0 + 50.0 * np.cos(2 * theta)

        result = extract_fourier_coefficients(intensity, cfg)

        assert result.a0 is not None
        idx_2 = np.where(result.harmonics == 2)[0][0]
        assert_allclose(result.an[idx_2], 50.0, rtol=1e-9)

    def test_zero_intensity(self, default_config, theta):
        """Should handle zero intensity gracefully."""
        intensity = np.zeros(len(theta))

        result = extract_fourier_coefficients(intensity, default_config)

        assert_allclose(result.a0, 0.0, atol=1e-15)
        assert_allclose(result.an, 0.0, atol=1e-15)
        assert_allclose(result.bn, 0.0, atol=1e-15)

    def test_negative_intensity(self, default_config, theta):
        """Should handle negative intensity (physically unusual but mathematically valid)."""
        intensity = -100.0 + 50.0 * np.cos(2 * theta)

        result = extract_fourier_coefficients(intensity, default_config)

        assert_allclose(result.a0, -100.0, rtol=1e-10)

    def test_very_large_values(self, default_config, theta):
        """Should handle very large intensity values."""
        intensity = 1e10 + 1e9 * np.cos(4 * theta)

        result = extract_fourier_coefficients(intensity, default_config)

        assert_allclose(result.a0, 1e10, rtol=1e-9)
        idx_4 = np.where(result.harmonics == 4)[0][0]
        assert_allclose(result.an[idx_4], 1e9, rtol=1e-9)


# =============================================================================
# TEST: Sign convention
# =============================================================================

class TestFourierSignConvention:
    """Tests for correct FFT sign convention."""

    def test_bn_sign_convention(self, default_config, theta):
        """
        Critical test: verify the NEGATIVE sign in bn extraction.

        The FFT convention gives: H[k] = Σ x[n] exp(-2πi·k·n/N)
        For real Fourier series: I(θ) = a₀ + Σ [aₙ cos(nθ) + bₙ sin(nθ)]

        The relationship requires: bₙ = -(2/N) · Im(H[n])
        """
        a0 = 1000.0
        b2 = 100.0  # Positive sine coefficient

        # I = a0 + b2 * sin(2θ)
        intensity = a0 + b2 * np.sin(2 * theta)

        result = extract_fourier_coefficients(intensity, default_config)

        idx_2 = np.where(result.harmonics == 2)[0][0]

        # The extracted b2 should be POSITIVE (matching our input)
        # If the sign convention is wrong, this will be negative
        assert result.bn[idx_2] > 0, "Sign convention error: bn should be positive"
        assert_allclose(result.bn[idx_2], b2, rtol=1e-9)

    def test_combined_cos_sin(self, default_config, theta):
        """Test combined cosine and sine with specific amplitudes."""
        a0 = 500.0
        # Use specific values that clearly distinguish cos and sin
        a4 = 100.0   # Cosine amplitude
        b4 = -75.0   # Negative sine amplitude

        intensity = a0 + a4 * np.cos(4 * theta) + b4 * np.sin(4 * theta)

        result = extract_fourier_coefficients(intensity, default_config)

        idx_4 = np.where(result.harmonics == 4)[0][0]

        # Both signs should be preserved correctly
        assert_allclose(result.an[idx_4], a4, rtol=1e-9)
        assert_allclose(result.bn[idx_4], b4, rtol=1e-9)
