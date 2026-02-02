"""
Tests for Lu-Chipman Polar Decomposition

Tests the lu_chipman_decomposition function that extracts physical parameters
(diattenuation, retardance, depolarization) from Mueller matrices.

References
----------
[1] Lu & Chipman, J. Opt. Soc. Am. A 13, 1106-1113 (1996)
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

from ecm.postprocessing.lu_chipman import (
    LuChipmanResult,
    lu_chipman_decomposition,
)
from ecm.utils.mueller_matrices import identity, polarizer, retarder


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def identity_matrix():
    """Normalized identity Mueller matrix."""
    return np.eye(4)


@pytest.fixture
def qwp_matrix():
    """Quarter-wave plate at 0° (δ = 90°)."""
    return retarder(theta=0.0, delta=np.pi/2, tau=1.0)


@pytest.fixture
def hwp_matrix():
    """Half-wave plate at 0° (δ = 180°)."""
    return retarder(theta=0.0, delta=np.pi, tau=1.0)


@pytest.fixture
def polarizer_matrix():
    """Horizontal polarizer (τ = 0.5, normalized)."""
    M = polarizer(theta=0.0, tau=0.5)
    return M / M[0, 0]  # Normalize


# =============================================================================
# TEST: Output Structure
# =============================================================================

class TestLuChipmanOutputStructure:
    """Tests for output structure and types."""

    def test_output_type(self, identity_matrix):
        """Should return LuChipmanResult."""
        result = lu_chipman_decomposition(identity_matrix)
        assert isinstance(result, LuChipmanResult)

    def test_output_fields_exist(self, identity_matrix):
        """Should have all expected fields."""
        result = lu_chipman_decomposition(identity_matrix)

        # Decomposed matrices
        assert hasattr(result, 'M_D')
        assert hasattr(result, 'M_R')
        assert hasattr(result, 'M_Delta')

        # Scalar parameters
        assert hasattr(result, 'D')
        assert hasattr(result, 'R_rad')
        assert hasattr(result, 'R_deg')
        assert hasattr(result, 'R_waves')
        assert hasattr(result, 'DI')
        assert hasattr(result, 'psi_deg')
        assert hasattr(result, 'chi_deg')

    def test_single_wavelength_shape(self, identity_matrix):
        """Single wavelength input should return 2D matrices."""
        result = lu_chipman_decomposition(identity_matrix)

        assert result.M_D.shape == (4, 4)
        assert result.M_R.shape == (4, 4)
        assert result.M_Delta.shape == (4, 4)

    def test_multi_wavelength_shape(self):
        """Multi-wavelength input should return 3D matrices."""
        n_wl = 10
        M = np.stack([np.eye(4) for _ in range(n_wl)], axis=2)

        result = lu_chipman_decomposition(M)

        assert result.M_D.shape == (4, 4, n_wl)
        assert result.M_R.shape == (4, 4, n_wl)
        assert result.M_Delta.shape == (4, 4, n_wl)
        assert len(result.D) == n_wl
        assert len(result.R_rad) == n_wl


# =============================================================================
# TEST: Identity Matrix Decomposition
# =============================================================================

class TestIdentityDecomposition:
    """Tests for identity matrix decomposition."""

    def test_identity_decomposition(self, identity_matrix):
        """Identity: M_D = M_R = M_Δ = I, D = R = 0, DI = 1."""
        result = lu_chipman_decomposition(identity_matrix)

        # M_D should be identity
        assert_allclose(result.M_D, np.eye(4), atol=1e-10)

        # M_R should be identity
        assert_allclose(result.M_R, np.eye(4), atol=1e-10)

        # M_Delta should be identity
        assert_allclose(result.M_Delta, np.eye(4), atol=1e-10)

        # D = 0 (no diattenuation)
        assert_allclose(result.D[0], 0.0, atol=1e-10)

        # R = 0 (no retardance)
        assert_allclose(result.R_rad[0], 0.0, atol=1e-10)
        assert_allclose(result.R_deg[0], 0.0, atol=1e-10)

        # DI = 1 (non-depolarizing)
        assert_allclose(result.DI[0], 1.0, atol=1e-10)

    def test_reconstruction_identity(self, identity_matrix):
        """M ≈ M_Δ @ M_R @ M_D for identity."""
        result = lu_chipman_decomposition(identity_matrix)

        M_reconstructed = result.M_Delta @ result.M_R @ result.M_D
        assert_allclose(M_reconstructed, identity_matrix, atol=1e-10)


# =============================================================================
# TEST: Pure Polarizer Decomposition
# =============================================================================

class TestPolarizerDecomposition:
    """Tests for polarizer decomposition."""

    def test_polarizer_diattenuation(self, polarizer_matrix):
        """Polarizer should have D > 0."""
        result = lu_chipman_decomposition(polarizer_matrix)

        # D should be positive (polarizer has diattenuation)
        assert result.D[0] > 0.5  # Significant diattenuation

    def test_polarizer_retardance(self, polarizer_matrix):
        """Ideal polarizer should have R ≈ 0."""
        result = lu_chipman_decomposition(polarizer_matrix)

        # Retardance should be small (no phase difference)
        assert result.R_rad[0] < 0.1

    def test_polarizer_di(self, polarizer_matrix):
        """Ideal polarizer should have DI = 1 (non-depolarizing)."""
        result = lu_chipman_decomposition(polarizer_matrix)

        # DI should be close to 1
        assert_allclose(result.DI[0], 1.0, rtol=0.1)

    def test_reconstruction_polarizer(self, polarizer_matrix):
        """M ≈ M_Δ @ M_R @ M_D for polarizer."""
        result = lu_chipman_decomposition(polarizer_matrix)

        M_reconstructed = result.M_Delta @ result.M_R @ result.M_D
        assert_allclose(M_reconstructed, polarizer_matrix, atol=0.1)


# =============================================================================
# TEST: Pure Retarder Decomposition
# =============================================================================

class TestRetarderDecomposition:
    """Tests for retarder decomposition."""

    def test_qwp_retardance(self, qwp_matrix):
        """QWP should have R ≈ 90°."""
        result = lu_chipman_decomposition(qwp_matrix)

        assert_allclose(result.R_deg[0], 90.0, rtol=0.05)
        assert_allclose(result.R_waves[0], 0.25, rtol=0.05)

    def test_hwp_retardance(self, hwp_matrix):
        """HWP should have R ≈ 180°."""
        result = lu_chipman_decomposition(hwp_matrix)

        assert_allclose(result.R_deg[0], 180.0, rtol=0.05)
        assert_allclose(result.R_waves[0], 0.5, rtol=0.05)

    def test_retarder_diattenuation(self, qwp_matrix):
        """Ideal retarder should have D ≈ 0."""
        result = lu_chipman_decomposition(qwp_matrix)

        assert_allclose(result.D[0], 0.0, atol=1e-10)

    def test_retarder_di(self, qwp_matrix):
        """Ideal retarder should have DI = 1 (non-depolarizing)."""
        result = lu_chipman_decomposition(qwp_matrix)

        assert_allclose(result.DI[0], 1.0, atol=1e-10)

    def test_linear_retarder_chi(self, qwp_matrix):
        """Linear retarder should have χ ≈ 0°."""
        result = lu_chipman_decomposition(qwp_matrix)

        # Chi should be near 0 for linear retarder
        assert_allclose(result.chi_deg[0], 0.0, atol=5.0)

    @pytest.mark.parametrize("delta_deg", [30, 45, 60, 90, 120, 150])
    def test_various_retardances(self, delta_deg):
        """Extracted R should match input δ for various values."""
        delta_rad = np.deg2rad(delta_deg)
        M = retarder(theta=0.0, delta=delta_rad, tau=1.0)

        result = lu_chipman_decomposition(M)

        assert_allclose(result.R_deg[0], delta_deg, rtol=0.1)

    def test_reconstruction_retarder(self, qwp_matrix):
        """M ≈ M_Δ @ M_R @ M_D for retarder."""
        result = lu_chipman_decomposition(qwp_matrix)

        M_reconstructed = result.M_Delta @ result.M_R @ result.M_D
        assert_allclose(M_reconstructed, qwp_matrix, atol=1e-10)


# =============================================================================
# TEST: Pure Depolarizer
# =============================================================================

class TestDepolarizer:
    """Tests for depolarizer decomposition."""

    def test_partial_depolarizer(self):
        """Partial depolarizer should have DI < 1."""
        # Construct a partial depolarizer
        # M_Δ has diagonal submatrix scaled by factor < 1
        M_delta = np.eye(4)
        M_delta[1:4, 1:4] *= 0.5  # 50% depolarization

        result = lu_chipman_decomposition(M_delta)

        # DI should be < 1
        assert result.DI[0] < 1.0
        assert result.DI[0] > 0.0

        # D and R should be small
        assert result.D[0] < 0.1
        assert result.R_rad[0] < 0.1


# =============================================================================
# TEST: Parameter Ranges
# =============================================================================

class TestParameterRanges:
    """Tests for physical parameter ranges."""

    def test_d_range(self, polarizer_matrix):
        """D should be in [0, 1]."""
        result = lu_chipman_decomposition(polarizer_matrix)
        assert 0.0 <= result.D[0] <= 1.0

    def test_di_range(self, identity_matrix):
        """DI should be in [0, 1]."""
        result = lu_chipman_decomposition(identity_matrix)
        assert 0.0 <= result.DI[0] <= 1.0

    def test_r_range(self, qwp_matrix):
        """R should be in [0, π]."""
        result = lu_chipman_decomposition(qwp_matrix)
        assert 0.0 <= result.R_rad[0] <= np.pi

    def test_psi_range(self):
        """ψ should be in [-90°, 90°]."""
        M = retarder(theta=np.pi/4, delta=np.pi/4, tau=1.0)
        result = lu_chipman_decomposition(M)

        # May be NaN for small retardance, but if defined, should be in range
        if not np.isnan(result.psi_deg[0]):
            assert -90.0 <= result.psi_deg[0] <= 90.0

    def test_chi_range(self):
        """χ should be in [-45°, 45°]."""
        M = retarder(theta=0.0, delta=np.pi/4, tau=1.0)
        result = lu_chipman_decomposition(M)

        if not np.isnan(result.chi_deg[0]):
            assert -45.0 <= result.chi_deg[0] <= 45.0


# =============================================================================
# TEST: Multi-Wavelength Processing
# =============================================================================

class TestMultiWavelength:
    """Tests for multi-wavelength input."""

    def test_wavelength_independent_processing(self):
        """Each wavelength should be processed independently."""
        n_wl = 5

        # Create different retarders for each wavelength
        M = np.zeros((4, 4, n_wl))
        deltas = [np.pi/6, np.pi/4, np.pi/3, np.pi/2, 2*np.pi/3]

        for i, delta in enumerate(deltas):
            M[:, :, i] = retarder(theta=0.0, delta=delta, tau=1.0)

        result = lu_chipman_decomposition(M)

        # Check each wavelength
        for i, delta in enumerate(deltas):
            expected_deg = np.rad2deg(delta)
            assert_allclose(result.R_deg[i], expected_deg, rtol=0.1)


# =============================================================================
# TEST: Input Validation
# =============================================================================

class TestInputValidation:
    """Tests for input validation."""

    def test_wrong_shape_raises(self):
        """Should raise error for wrong input shape."""
        M_wrong = np.eye(3)

        with pytest.raises(ValueError):
            lu_chipman_decomposition(M_wrong)

    def test_unnormalized_warning(self):
        """Should warn for unnormalized input."""
        M = np.eye(4) * 2.0  # M[0,0] = 2

        with pytest.warns(UserWarning, match="Expected 1.0"):
            result = lu_chipman_decomposition(M)

        # Should still produce valid result after renormalization
        assert_allclose(result.DI[0], 1.0, atol=1e-10)


# =============================================================================
# TEST: Retardance Conversion
# =============================================================================

class TestRetardanceConversion:
    """Tests for retardance unit conversions."""

    def test_rad_to_deg_conversion(self, qwp_matrix):
        """R_deg should equal rad2deg(R_rad)."""
        result = lu_chipman_decomposition(qwp_matrix)
        assert_allclose(result.R_deg[0], np.rad2deg(result.R_rad[0]), rtol=1e-10)

    def test_deg_to_waves_conversion(self, qwp_matrix):
        """R_waves should equal R_deg / 360."""
        result = lu_chipman_decomposition(qwp_matrix)
        assert_allclose(result.R_waves[0], result.R_deg[0] / 360.0, rtol=1e-10)

    def test_qwp_in_waves(self, qwp_matrix):
        """QWP should be 0.25 waves."""
        result = lu_chipman_decomposition(qwp_matrix)
        assert_allclose(result.R_waves[0], 0.25, rtol=0.05)

    def test_hwp_in_waves(self, hwp_matrix):
        """HWP should be 0.5 waves."""
        result = lu_chipman_decomposition(hwp_matrix)
        assert_allclose(result.R_waves[0], 0.5, rtol=0.05)
