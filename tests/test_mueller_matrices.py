"""
Tests for Mueller Matrix Generator Functions

This test module validates the Mueller matrix generators against known
analytical results and the physics conventions from Compain et al. (1999).

Test Categories
---------------
1. Rotation matrix properties (orthogonality, determinant, inverse)
2. Polarizer matrix properties (eigenvalues, idempotence, known forms)
3. Retarder matrix properties (QWP, HWP, zero retardation)
4. Optical element rotation (R(theta) M R(-theta) equivalence)
5. Physical Stokes vector transformations (sanity checks)

These tests are ported from the MATLAB test file:
    tests/test_mueller_generators.m

References
----------
[1] Compain et al., Appl. Opt. 38, 3490-3502 (1999)
"""

import pytest
import numpy as np
from numpy.testing import assert_allclose

from ecm.utils.mueller_matrices import rotation, polarizer, retarder, identity


# =============================================================================
# CONSTANTS
# =============================================================================

# Numerical tolerance for comparisons (matches MATLAB tests)
TOL = 1e-12


# =============================================================================
# TEST CLASS: ROTATION MATRIX
# =============================================================================

class TestRotationMatrix:
    """
    Tests for Mueller rotation matrix (Compain Eq. 4).

    Validates mathematical properties and physics conventions.
    """

    # -------------------------------------------------------------------------
    # Test: Orthogonality R @ R.T = I
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("theta", [0, np.pi/6, np.pi/4, np.pi/3, np.pi/2, np.pi])
    def test_orthogonality(self, theta: float) -> None:
        """
        Rotation matrices must be orthogonal: R @ R.T = I.

        This is a fundamental property of rotation matrices and ensures
        that rotations preserve the norm of Stokes vectors.
        """
        R = rotation(theta)

        # Compute R @ R.T and compare to identity
        product = R @ R.T
        expected = np.eye(4)

        assert_allclose(
            product, expected, atol=TOL,
            err_msg=f"R({theta:.4f}) is not orthogonal: R @ R.T != I"
        )

    # -------------------------------------------------------------------------
    # Test: Determinant = 1
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("theta", [0, np.pi/6, np.pi/4, np.pi/3, np.pi/2, np.pi])
    def test_determinant_is_one(self, theta: float) -> None:
        """
        Rotation matrices must have determinant = 1.

        This ensures the rotation is a proper rotation (not a reflection).
        """
        R = rotation(theta)
        det_R = np.linalg.det(R)

        assert_allclose(
            det_R, 1.0, atol=TOL,
            err_msg=f"det(R({theta:.4f})) = {det_R}, expected 1.0"
        )

    # -------------------------------------------------------------------------
    # Test: R(0) = Identity
    # -------------------------------------------------------------------------
    def test_zero_rotation_is_identity(self) -> None:
        """
        Rotation by zero angle must give the identity matrix.
        """
        R = rotation(0.0)
        expected = np.eye(4)

        assert_allclose(
            R, expected, atol=TOL,
            err_msg="R(0) should equal identity matrix"
        )

    # -------------------------------------------------------------------------
    # Test: Inverse property R(theta) @ R(-theta) = I
    # -------------------------------------------------------------------------
    def test_inverse_property(self) -> None:
        """
        R(theta) @ R(-theta) must equal identity.

        This verifies the inverse property of rotation matrices.
        """
        theta = np.pi / 4
        R_pos = rotation(theta)
        R_neg = rotation(-theta)

        product = R_pos @ R_neg
        expected = np.eye(4)

        assert_allclose(
            product, expected, atol=TOL,
            err_msg="R(theta) @ R(-theta) should equal identity"
        )

    # -------------------------------------------------------------------------
    # Test: R(-theta) = R(theta).T
    # -------------------------------------------------------------------------
    def test_transpose_equals_negative_rotation(self) -> None:
        """
        R(-theta) must equal R(theta).T for rotation matrices.

        This is a key property used in rotating optical elements.
        """
        theta = np.pi / 6
        R = rotation(theta)
        R_neg = rotation(-theta)

        assert_allclose(
            R_neg, R.T, atol=TOL,
            err_msg="R(-theta) should equal R(theta).T"
        )

    # -------------------------------------------------------------------------
    # Test: Composition R(a) @ R(b) = R(a+b)
    # -------------------------------------------------------------------------
    def test_composition_property(self) -> None:
        """
        Rotation matrices compose: R(alpha) @ R(beta) = R(alpha + beta).
        """
        alpha = np.pi / 6
        beta = np.pi / 4

        R_alpha = rotation(alpha)
        R_beta = rotation(beta)
        R_sum = rotation(alpha + beta)

        product = R_alpha @ R_beta

        assert_allclose(
            product, R_sum, atol=TOL,
            err_msg="R(alpha) @ R(beta) should equal R(alpha + beta)"
        )

    # -------------------------------------------------------------------------
    # Test: Input validation
    # -------------------------------------------------------------------------
    def test_invalid_input_type(self) -> None:
        """
        Rotation should raise TypeError for non-numeric input.
        """
        with pytest.raises(TypeError, match="must be a numeric scalar"):
            rotation("45 degrees")

        with pytest.raises(TypeError, match="must be a numeric scalar"):
            rotation([np.pi/4])


# =============================================================================
# TEST CLASS: POLARIZER MATRIX
# =============================================================================

class TestPolarizerMatrix:
    """
    Tests for Mueller polarizer matrix (Compain Eq. 2-3).

    Validates matrix form, eigenvalues, and idempotence property.
    """

    # -------------------------------------------------------------------------
    # Test: Horizontal polarizer form
    # -------------------------------------------------------------------------
    def test_horizontal_polarizer_form(
        self,
        horizontal_polarizer_expected: np.ndarray
    ) -> None:
        """
        Horizontal polarizer (theta=0) must match expected form.

        Compain Eq. 2: P(1,0) = 0.5 * [[1,1,0,0], [1,1,0,0], [0,0,0,0], [0,0,0,0]]
        """
        M_H = polarizer(0.0)

        assert_allclose(
            M_H, horizontal_polarizer_expected, atol=TOL,
            err_msg="Horizontal polarizer does not match expected form (Compain Eq. 2)"
        )

    # -------------------------------------------------------------------------
    # Test: Vertical polarizer form
    # -------------------------------------------------------------------------
    def test_vertical_polarizer_form(
        self,
        vertical_polarizer_expected: np.ndarray
    ) -> None:
        """
        Vertical polarizer (theta=pi/2) must match expected form.
        """
        M_V = polarizer(np.pi / 2)

        assert_allclose(
            M_V, vertical_polarizer_expected, atol=TOL,
            err_msg="Vertical polarizer does not match expected form"
        )

    # -------------------------------------------------------------------------
    # Test: +45 degree polarizer form
    # -------------------------------------------------------------------------
    def test_45_degree_polarizer_form(
        self,
        polarizer_45_expected: np.ndarray
    ) -> None:
        """
        +45 degree polarizer (theta=pi/4) must match expected form.
        """
        M_45 = polarizer(np.pi / 4)

        assert_allclose(
            M_45, polarizer_45_expected, atol=TOL,
            err_msg="+45 degree polarizer does not match expected form"
        )

    # -------------------------------------------------------------------------
    # Test: Eigenvalues
    # -------------------------------------------------------------------------
    def test_eigenvalues(self) -> None:
        """
        Polarizer eigenvalues must be tau (x1) and 0 (x3).

        For an ideal polarizer with tau=1, eigenvalues are [1, 0, 0, 0].
        """
        M_H = polarizer(0.0, tau=1.0)

        # Compute eigenvalues and sort in descending order
        eigenvalues = np.sort(np.linalg.eigvals(M_H).real)[::-1]
        expected = np.array([1.0, 0.0, 0.0, 0.0])

        assert_allclose(
            eigenvalues, expected, atol=TOL,
            err_msg=f"Polarizer eigenvalues incorrect: got {eigenvalues}, expected {expected}"
        )

    # -------------------------------------------------------------------------
    # Test: Idempotence P @ P = (tau/2) * P
    # -------------------------------------------------------------------------
    def test_idempotence(self) -> None:
        """
        Polarizers are idempotent: P @ P = P (for normalized polarizer).

        For our polarizer with built-in tau/2 normalization:
        P(tau) @ P(tau) = P(tau)

        This means two identical parallel polarizers act like one.
        The tau/2 factor is already included in the matrix definition.
        """
        tau = 1.0
        M_H = polarizer(0.0, tau=tau)

        # Compute P @ P
        M_squared = M_H @ M_H

        # For a polarizer with the (tau/2) normalization built in:
        # P @ P = P (the matrix is idempotent)
        M_expected = M_H

        assert_allclose(
            M_squared, M_expected, atol=TOL,
            err_msg="Polarizer not idempotent: P @ P != P"
        )

    # -------------------------------------------------------------------------
    # Test: Crossed polarizers transmit nothing
    # -------------------------------------------------------------------------
    def test_crossed_polarizers(self) -> None:
        """
        Crossed polarizers (H then V) should transmit no light.
        """
        M_H = polarizer(0.0)  # Horizontal
        M_V = polarizer(np.pi / 2)  # Vertical

        # Unpolarized input
        S_unpol = np.array([1.0, 0.0, 0.0, 0.0])

        # Pass through H then V
        S_out = M_V @ M_H @ S_unpol

        # Output intensity should be zero
        assert_allclose(
            S_out[0], 0.0, atol=TOL,
            err_msg="Crossed polarizers should transmit zero intensity"
        )

    # -------------------------------------------------------------------------
    # Test: Custom tau value
    # -------------------------------------------------------------------------
    def test_custom_tau(self) -> None:
        """
        Polarizer with custom tau should scale appropriately.
        """
        tau = 0.8
        M = polarizer(0.0, tau=tau)

        # M[0,0] should be tau/2
        expected_m00 = tau / 2.0

        assert_allclose(
            M[0, 0], expected_m00, atol=TOL,
            err_msg=f"M[0,0] should be tau/2 = {expected_m00}, got {M[0,0]}"
        )

    # -------------------------------------------------------------------------
    # Test: Input validation
    # -------------------------------------------------------------------------
    def test_invalid_theta_type(self) -> None:
        """
        Polarizer should raise TypeError for non-numeric theta.
        """
        with pytest.raises(TypeError, match="theta must be a numeric scalar"):
            polarizer("0 degrees")


# =============================================================================
# TEST CLASS: RETARDER MATRIX
# =============================================================================

class TestRetarderMatrix:
    """
    Tests for Mueller retarder matrix (waveplate).

    Validates QWP, HWP, and zero retardation cases.
    """

    # -------------------------------------------------------------------------
    # Test: Quarter-wave plate (QWP) form
    # -------------------------------------------------------------------------
    def test_qwp_form(self, qwp_horizontal_expected: np.ndarray) -> None:
        """
        QWP with fast axis horizontal (delta=pi/2, theta=0) must match expected form.
        """
        M_QWP = retarder(0.0, np.pi / 2)

        assert_allclose(
            M_QWP, qwp_horizontal_expected, atol=TOL,
            err_msg="QWP matrix does not match expected form"
        )

    # -------------------------------------------------------------------------
    # Test: Half-wave plate (HWP) form
    # -------------------------------------------------------------------------
    def test_hwp_form(self, hwp_horizontal_expected: np.ndarray) -> None:
        """
        HWP with fast axis horizontal (delta=pi, theta=0) must match expected form.
        """
        M_HWP = retarder(0.0, np.pi)

        assert_allclose(
            M_HWP, hwp_horizontal_expected, atol=TOL,
            err_msg="HWP matrix does not match expected form"
        )

    # -------------------------------------------------------------------------
    # Test: Zero retardation gives identity
    # -------------------------------------------------------------------------
    def test_zero_retardation_is_identity(self) -> None:
        """
        Retarder with delta=0 must equal identity matrix.
        """
        M = retarder(0.0, 0.0)
        expected = np.eye(4)

        assert_allclose(
            M, expected, atol=TOL,
            err_msg="Retarder with zero retardation should equal identity"
        )

    # -------------------------------------------------------------------------
    # Test: Determinant = 1
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("delta", [0, np.pi/4, np.pi/2, np.pi])
    def test_determinant_is_one(self, delta: float) -> None:
        """
        Retarder determinant must equal 1 (for tau=1).

        This ensures the retarder preserves orthogonality.
        """
        M = retarder(0.0, delta, tau=1.0)
        det_M = np.linalg.det(M)

        assert_allclose(
            det_M, 1.0, atol=TOL,
            err_msg=f"det(retarder(delta={delta:.4f})) = {det_M}, expected 1.0"
        )

    # -------------------------------------------------------------------------
    # Test: QWP eigenvalues
    # -------------------------------------------------------------------------
    def test_qwp_eigenvalues(self) -> None:
        """
        QWP eigenvalues must be 1, 1, i, -i (for tau=1).
        """
        M_QWP = retarder(0.0, np.pi / 2)

        eigenvalues = np.linalg.eigvals(M_QWP)
        eigenvalues_sorted = np.sort(eigenvalues)

        expected = np.sort(np.array([1.0, 1.0, 1j, -1j]))

        assert_allclose(
            eigenvalues_sorted, expected, atol=TOL,
            err_msg="QWP eigenvalues should be [1, 1, i, -i]"
        )

    # -------------------------------------------------------------------------
    # Test: Full-wave plate equals identity
    # -------------------------------------------------------------------------
    def test_full_wave_plate(self) -> None:
        """
        Full-wave plate (delta=2*pi) must equal identity.
        """
        M = retarder(0.0, 2.0 * np.pi)
        expected = np.eye(4)

        assert_allclose(
            M, expected, atol=TOL,
            err_msg="Full-wave plate should equal identity"
        )

    # -------------------------------------------------------------------------
    # Test: Custom tau value
    # -------------------------------------------------------------------------
    def test_custom_tau(self) -> None:
        """
        Retarder with custom tau should scale M[0,0].
        """
        tau = 0.95
        M = retarder(0.0, np.pi / 2, tau=tau)

        assert_allclose(
            M[0, 0], tau, atol=TOL,
            err_msg=f"M[0,0] should be tau = {tau}, got {M[0,0]}"
        )

    # -------------------------------------------------------------------------
    # Test: Input validation
    # -------------------------------------------------------------------------
    def test_invalid_tau_range(self) -> None:
        """
        Retarder should raise ValueError for negative tau.
        Note: tau > 1 is now allowed due to measurement noise at spectral edges.
        """
        # tau > 1 should NOT raise (allowed for noise tolerance)
        M = retarder(0.0, np.pi / 2, tau=1.5)
        assert M[0, 0] == pytest.approx(1.5, rel=1e-10)

        # Negative tau should still raise
        with pytest.raises(ValueError, match="tau must be non-negative"):
            retarder(0.0, np.pi / 2, tau=-0.1)


# =============================================================================
# TEST CLASS: IDENTITY MATRIX
# =============================================================================

class TestIdentityMatrix:
    """
    Tests for Mueller identity matrix (air/vacuum).
    """

    # -------------------------------------------------------------------------
    # Test: Default is 4x4 identity
    # -------------------------------------------------------------------------
    def test_default_is_identity(self) -> None:
        """
        Identity with default tau=1 must equal 4x4 identity matrix.
        """
        M = identity()
        expected = np.eye(4)

        assert_allclose(
            M, expected, atol=TOL,
            err_msg="identity() should equal 4x4 identity matrix"
        )

    # -------------------------------------------------------------------------
    # Test: Custom tau scales the matrix
    # -------------------------------------------------------------------------
    def test_custom_tau(self) -> None:
        """
        Identity with custom tau should equal tau * I.
        """
        tau = 0.92
        M = identity(tau)
        expected = tau * np.eye(4)

        assert_allclose(
            M, expected, atol=TOL,
            err_msg=f"identity({tau}) should equal {tau} * I"
        )

    # -------------------------------------------------------------------------
    # Test: Input validation
    # -------------------------------------------------------------------------
    def test_invalid_tau_negative(self) -> None:
        """
        Identity should raise ValueError for negative tau.
        """
        with pytest.raises(ValueError, match="tau must be non-negative"):
            identity(-0.1)


# =============================================================================
# TEST CLASS: OPTICAL ELEMENT ROTATION
# =============================================================================

class TestOpticalElementRotation:
    """
    Tests for rotating optical elements using R(theta) @ M @ R(-theta).
    """

    # -------------------------------------------------------------------------
    # Test: Rotating H polarizer by 90 degrees gives V polarizer
    # -------------------------------------------------------------------------
    def test_rotate_h_to_v_polarizer(
        self,
        horizontal_polarizer_expected: np.ndarray,
        vertical_polarizer_expected: np.ndarray
    ) -> None:
        """
        Rotating horizontal polarizer by 90 degrees must give vertical polarizer.
        """
        M_H = polarizer(0.0)
        R90 = rotation(np.pi / 2)

        # Rotate: M_rotated = R @ M @ R.T
        M_H_rotated = R90 @ M_H @ R90.T

        assert_allclose(
            M_H_rotated, vertical_polarizer_expected, atol=TOL,
            err_msg="Rotating H polarizer by 90 deg should give V polarizer"
        )

    # -------------------------------------------------------------------------
    # Test: 360 degree rotation returns original
    # -------------------------------------------------------------------------
    def test_360_degree_rotation(self) -> None:
        """
        Rotating any element by 360 degrees must return the original.
        """
        # Create an arbitrary polarizer
        M_original = polarizer(np.pi / 6, tau=0.8)
        R360 = rotation(2.0 * np.pi)

        M_rotated = R360 @ M_original @ R360.T

        assert_allclose(
            M_rotated, M_original, atol=TOL,
            err_msg="360 degree rotation should return original element"
        )

    # -------------------------------------------------------------------------
    # Test: Direct construction equals rotation method
    # -------------------------------------------------------------------------
    def test_direct_vs_rotation_method(self) -> None:
        """
        Polarizer constructed directly at theta must equal rotated version.

        polarizer(theta) == R(theta) @ polarizer(0) @ R(-theta)
        """
        theta = np.pi / 6

        # Method 1: Direct construction
        M_direct = polarizer(theta)

        # Method 2: Construct at 0 and rotate
        M_0 = polarizer(0.0)
        R = rotation(theta)
        M_rotated = R @ M_0 @ R.T

        assert_allclose(
            M_direct, M_rotated, atol=TOL,
            err_msg="polarizer(theta) should equal R(theta) @ polarizer(0) @ R(-theta)"
        )

    # -------------------------------------------------------------------------
    # Test: Retarder rotation equivalence
    # -------------------------------------------------------------------------
    def test_retarder_rotation_equivalence(self) -> None:
        """
        Retarder constructed directly at theta must equal rotated version.
        """
        theta = np.pi / 4
        delta = np.pi / 3

        # Method 1: Direct construction
        M_direct = retarder(theta, delta)

        # Method 2: Construct at 0 and rotate
        M_0 = retarder(0.0, delta)
        R = rotation(theta)
        M_rotated = R @ M_0 @ R.T

        assert_allclose(
            M_direct, M_rotated, atol=TOL,
            err_msg="retarder(theta, delta) should equal R(theta) @ retarder(0, delta) @ R(-theta)"
        )


# =============================================================================
# TEST CLASS: PHYSICAL STOKES TRANSFORMATIONS
# =============================================================================

class TestStokesTransformations:
    """
    Tests for physical Stokes vector transformations.

    These tests verify that the Mueller matrices produce physically
    correct polarization transformations.
    """

    # -------------------------------------------------------------------------
    # Test: Unpolarized through horizontal polarizer
    # -------------------------------------------------------------------------
    def test_unpolarized_through_h_polarizer(self) -> None:
        """
        Unpolarized light through horizontal polarizer gives horizontal polarization.

        Input: S = [1, 0, 0, 0] (unpolarized)
        Output: S = [0.5, 0.5, 0, 0] (horizontal, half intensity)
        """
        M_H = polarizer(0.0)
        S_unpol = np.array([1.0, 0.0, 0.0, 0.0])

        S_out = M_H @ S_unpol
        S_expected = np.array([0.5, 0.5, 0.0, 0.0])

        assert_allclose(
            S_out, S_expected, atol=TOL,
            err_msg="Unpolarized through H polarizer should give [0.5, 0.5, 0, 0]"
        )

    # -------------------------------------------------------------------------
    # Test: +45 linear through QWP gives circular
    # -------------------------------------------------------------------------
    def test_linear_45_through_qwp(self) -> None:
        """
        +45 degree linear through QWP (fast axis H) gives right-hand circular.

        Input: S = [1, 0, 1, 0] (+45 degree linear)
        Output: S = [1, 0, 0, -1] (right-hand circular in our convention)

        Note: The sign of S3 (V parameter) depends on the convention for
        right-hand vs left-hand circular. In our convention (Compain),
        right-hand circular has V = -1.
        """
        M_QWP = retarder(0.0, np.pi / 2)  # QWP, fast axis horizontal
        S_45 = np.array([1.0, 0.0, 1.0, 0.0])  # +45 degree linear

        S_out = M_QWP @ S_45
        S_expected = np.array([1.0, 0.0, 0.0, -1.0])  # Right-hand circular

        assert_allclose(
            S_out, S_expected, atol=TOL,
            err_msg="+45 linear through QWP should give right-hand circular [1, 0, 0, -1]"
        )

    # -------------------------------------------------------------------------
    # Test: HWP at 45 degrees rotates H to V
    # -------------------------------------------------------------------------
    def test_hwp_rotates_polarization(self) -> None:
        """
        HWP at 45 degrees rotates horizontal to vertical polarization.

        A half-wave plate at 45 degrees rotates linear polarization by 90 degrees.
        Input: S = [1, 1, 0, 0] (horizontal)
        Output: S = [1, -1, 0, 0] (vertical)
        """
        M_HWP_45 = retarder(np.pi / 4, np.pi)  # HWP at 45 degrees
        S_H = np.array([1.0, 1.0, 0.0, 0.0])  # Horizontal

        S_out = M_HWP_45 @ S_H
        S_expected = np.array([1.0, -1.0, 0.0, 0.0])  # Vertical

        assert_allclose(
            S_out, S_expected, atol=TOL,
            err_msg="HWP at 45 deg should rotate H to V: [1,1,0,0] -> [1,-1,0,0]"
        )

    # -------------------------------------------------------------------------
    # Test: Polarizer output is fully polarized
    # -------------------------------------------------------------------------
    def test_polarizer_output_fully_polarized(self) -> None:
        """
        Light through a polarizer must be 100% polarized.

        Degree of polarization: DOP = sqrt(S1^2 + S2^2 + S3^2) / S0
        For fully polarized light: DOP = 1
        """
        M_H = polarizer(0.0)
        S_unpol = np.array([1.0, 0.0, 0.0, 0.0])

        S_out = M_H @ S_unpol

        # Compute degree of polarization
        S0 = S_out[0]
        if S0 > 0:
            dop = np.sqrt(S_out[1]**2 + S_out[2]**2 + S_out[3]**2) / S0
        else:
            dop = 0.0

        assert_allclose(
            dop, 1.0, atol=TOL,
            err_msg="Polarizer output should be 100% polarized (DOP=1)"
        )

    # -------------------------------------------------------------------------
    # Test: Retarder preserves degree of polarization
    # -------------------------------------------------------------------------
    def test_retarder_preserves_dop(self) -> None:
        """
        Retarders must preserve the degree of polarization.

        A retarder changes the polarization state but not the degree.
        """
        M_QWP = retarder(0.0, np.pi / 2)

        # Start with +45 linear (DOP = 1)
        S_in = np.array([1.0, 0.0, 1.0, 0.0])
        dop_in = np.sqrt(S_in[1]**2 + S_in[2]**2 + S_in[3]**2) / S_in[0]

        S_out = M_QWP @ S_in
        dop_out = np.sqrt(S_out[1]**2 + S_out[2]**2 + S_out[3]**2) / S_out[0]

        assert_allclose(
            dop_out, dop_in, atol=TOL,
            err_msg="Retarder should preserve degree of polarization"
        )


# =============================================================================
# TEST CLASS: EDGE CASES AND NUMERICAL STABILITY
# =============================================================================

class TestEdgeCases:
    """
    Tests for edge cases and numerical stability.
    """

    # -------------------------------------------------------------------------
    # Test: Very small angles
    # -------------------------------------------------------------------------
    def test_very_small_angle(self) -> None:
        """
        Very small angles should still give correct results.
        """
        theta = 1e-15

        R = rotation(theta)

        # Should be very close to identity
        assert_allclose(
            R, np.eye(4), atol=1e-10,
            err_msg="Rotation by very small angle should be near identity"
        )

    # -------------------------------------------------------------------------
    # Test: Large angles (multiple rotations)
    # -------------------------------------------------------------------------
    def test_large_angle(self) -> None:
        """
        Large angles (multiple full rotations) should work correctly.
        """
        # 10 full rotations + pi/4
        theta = 10 * 2 * np.pi + np.pi / 4

        R_large = rotation(theta)
        R_small = rotation(np.pi / 4)

        assert_allclose(
            R_large, R_small, atol=TOL,
            err_msg="Large angle rotation should equal equivalent small angle"
        )

    # -------------------------------------------------------------------------
    # Test: Negative angles
    # -------------------------------------------------------------------------
    def test_negative_angles(self) -> None:
        """
        Negative angles should work correctly (clockwise rotation).
        """
        theta = -np.pi / 4

        R_neg = rotation(theta)
        R_pos = rotation(np.pi / 4)

        # R(-theta) should equal R(theta).T
        assert_allclose(
            R_neg, R_pos.T, atol=TOL,
            err_msg="R(-theta) should equal R(theta).T"
        )

    # -------------------------------------------------------------------------
    # Test: tau = 0 for polarizer
    # -------------------------------------------------------------------------
    def test_polarizer_tau_zero(self) -> None:
        """
        Polarizer with tau=0 should be all zeros (complete absorption).
        """
        M = polarizer(0.0, tau=0.0)
        expected = np.zeros((4, 4))

        assert_allclose(
            M, expected, atol=TOL,
            err_msg="Polarizer with tau=0 should be all zeros"
        )

    # -------------------------------------------------------------------------
    # Test: tau = 0 for retarder
    # -------------------------------------------------------------------------
    def test_retarder_tau_zero(self) -> None:
        """
        Retarder with tau=0 should be all zeros (complete absorption).
        """
        M = retarder(0.0, np.pi / 2, tau=0.0)
        expected = np.zeros((4, 4))

        assert_allclose(
            M, expected, atol=TOL,
            err_msg="Retarder with tau=0 should be all zeros"
        )
