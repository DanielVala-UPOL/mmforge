"""
Mueller Matrix Generators for Polarimetry

This module provides pure functions for generating Mueller matrices of common
optical elements following the conventions of Compain et al. (1999).

Functions
---------
rotation(theta)
    Mueller rotation matrix for coordinate transformation (Compain Eq. 4)
polarizer(theta, tau)
    Mueller matrix for ideal linear polarizer (Compain Eq. 2-3)
retarder(theta, delta, tau)
    Mueller matrix for linear retarder (waveplate)
identity(tau)
    Mueller identity matrix for air/vacuum (no polarization change)

Coordinate System Convention
----------------------------
Looking into the beam (toward the detector, along +z axis):
    - z-axis: beam propagation direction (toward detector)
    - x-axis: horizontal, positive to the right
    - y-axis: vertical, positive upward
    - theta = 0: reference axis along x (horizontal)
    - theta = pi/2: axis along y (vertical)
    - Positive rotation: counterclockwise (right-hand rule around z)

Physics Conventions (CRITICAL)
------------------------------
These conventions MUST be preserved exactly to maintain compatibility with
the ECM calibration algorithm:

1. Rotation direction: Positive theta = counterclockwise when looking into beam
2. Retardation sign: delta = phase_fast - phase_slow
3. All angles are in RADIANS

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999)

[2] Collett, "Polarized Light", Marcel Dekker (1993)

[3] Goldstein, "Polarized Light", 3rd ed., CRC Press (2011)

Example
-------
>>> import numpy as np
>>> from ecm.utils.mueller_matrices import rotation, polarizer, retarder
>>>
>>> # Create a 45-degree rotation matrix
>>> R45 = rotation(np.pi / 4)
>>>
>>> # Create horizontal polarizer and rotate it to 45 degrees
>>> P_horizontal = polarizer(0.0)
>>> P_45 = R45 @ P_horizontal @ R45.T
>>>
>>> # Alternatively, create polarizer directly at 45 degrees
>>> P_45_direct = polarizer(np.pi / 4)
>>>
>>> # These should be identical
>>> np.allclose(P_45, P_45_direct)  # True
"""

import numpy as np
from numpy import ndarray


# =============================================================================
# ROTATION MATRIX
# =============================================================================

def rotation(theta: float) -> ndarray:
    """
    Mueller rotation matrix for coordinate transformation.

    Generates the 4x4 Mueller rotation matrix that transforms between
    coordinate systems rotated by angle theta. This is used to rotate
    optical elements to arbitrary orientations.

    Implements Compain et al., Appl. Opt. 38, 3490 (1999), Eq. 4:

        R(theta) = [ 1      0            0           0 ]
                   [ 0   cos(2*theta)  -sin(2*theta)  0 ]
                   [ 0   sin(2*theta)   cos(2*theta)  0 ]
                   [ 0      0            0           1 ]

    Parameters
    ----------
    theta : float
        Rotation angle in radians.
        Positive = counterclockwise when looking into the beam
        (toward the detector, along +z axis).

    Returns
    -------
    R : ndarray, shape (4, 4)
        Mueller rotation matrix.

    Notes
    -----
    **Physical Meaning:**
    The rotation matrix transforms between coordinate systems.
    To rotate an optical element M by angle theta:

        M_rotated = R(theta) @ M_original @ R(-theta)

    Since rotation matrices are orthogonal, R(-theta) = R(theta).T, so:

        M_rotated = R(theta) @ M_original @ R(theta).T

    **Important Properties:**
    - R(theta) is orthogonal: R @ R.T = I (identity)
    - Determinant: det(R) = 1
    - Inverse: R(theta)^(-1) = R(-theta) = R(theta).T
    - Composition: R(alpha) @ R(beta) = R(alpha + beta)

    **Coordinate System:**
    - theta = 0: reference axis along x (horizontal)
    - theta = pi/2: axis along y (vertical)

    **Why 2*theta in the formula:**
    The factor of 2 arises from the Stokes parameter transformation.
    Linear polarization at angle theta corresponds to Stokes parameters
    with cos(2*theta) and sin(2*theta) terms, because the electric field
    oscillates, making the intensity pattern have twice the angular frequency.

    References
    ----------
    [1] Compain et al., Appl. Opt. 38, 3490-3502 (1999), Eq. (4)
    [2] Collett, "Polarized Light", Marcel Dekker (1993)

    Examples
    --------
    >>> import numpy as np
    >>> R = rotation(np.pi / 4)  # 45-degree rotation
    >>> np.allclose(R @ R.T, np.eye(4))  # Orthogonality check
    True
    >>> np.isclose(np.linalg.det(R), 1.0)  # Determinant check
    True
    >>> np.allclose(rotation(0), np.eye(4))  # Zero rotation is identity
    True
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    if not isinstance(theta, (int, float, np.floating, np.integer)):
        raise TypeError(
            f"theta must be a numeric scalar (int or float), got {type(theta).__name__}. "
            f"Angle should be in radians."
        )

    # -------------------------------------------------------------------------
    # Compute trigonometric terms
    # The 2*theta factor comes from Stokes parameter transformation
    # (see docstring for physical explanation)
    # -------------------------------------------------------------------------
    two_theta = 2.0 * theta
    cos_2theta = np.cos(two_theta)
    sin_2theta = np.sin(two_theta)

    # -------------------------------------------------------------------------
    # Build rotation matrix (Compain Eq. 4)
    # Structure:
    #   - S0 (total intensity) unchanged: R[0,0] = 1
    #   - S3 (circular polarization) unchanged: R[3,3] = 1
    #   - S1, S2 (linear polarization) rotate in 2D subspace
    # -------------------------------------------------------------------------
    R = np.array([
        [1.0,        0.0,         0.0,        0.0],
        [0.0,  cos_2theta, -sin_2theta,        0.0],
        [0.0,  sin_2theta,  cos_2theta,        0.0],
        [0.0,        0.0,         0.0,        1.0]
    ], dtype=np.float64)

    return R


# =============================================================================
# LINEAR POLARIZER
# =============================================================================

def polarizer(theta: float, tau: float = 1.0) -> ndarray:
    """
    Mueller matrix for an ideal linear polarizer.

    Generates the 4x4 Mueller matrix for a linear polarizer with its
    transmission axis at angle theta from the horizontal (x-axis).

    Implements Compain et al., Appl. Opt. 38, 3490 (1999), Eq. 2-3:

    For horizontal polarizer (theta = 0):

        P(tau, 0) = (tau/2) * [ 1  1  0  0 ]
                              [ 1  1  0  0 ]
                              [ 0  0  0  0 ]
                              [ 0  0  0  0 ]

    For polarizer at angle theta:

        P(tau, theta) = R(theta) @ P(tau, 0) @ R(-theta)

    Parameters
    ----------
    theta : float
        Orientation of transmission axis in radians.
        - theta = 0: horizontal (x-axis, passes horizontal polarization)
        - theta = pi/4: +45 degrees (passes +45 degree polarization)
        - theta = pi/2: vertical (y-axis, passes vertical polarization)
        Positive = counterclockwise looking into beam.

    tau : float, optional
        Transmission coefficient, default = 1.0.
        For an ideal polarizer with unpolarized input, transmitted
        intensity is tau/2 (since half the light is absorbed).
        Must be in range [0, 1].

    Returns
    -------
    M : ndarray, shape (4, 4)
        Mueller matrix for the polarizer.

    Notes
    -----
    **Physical Properties:**
    - An ideal polarizer completely blocks the orthogonal polarization
    - Output is 100% linearly polarized along the transmission axis
    - Transmits tau/2 of unpolarized input intensity
    - Eigenvalues: tau (multiplicity 1), 0 (multiplicity 3)

    **Idempotence Property:**
    For an ideal polarizer: P @ P = (tau/2) * P
    This means passing light through two identical parallel polarizers
    is equivalent to passing through one (with additional attenuation).

    **Common Configurations:**
    - Horizontal (H): theta = 0, passes S1 = +1
    - Vertical (V): theta = pi/2, passes S1 = -1
    - +45 degree (P): theta = pi/4, passes S2 = +1
    - -45 degree (M): theta = -pi/4, passes S2 = -1

    References
    ----------
    [1] Compain et al., Appl. Opt. 38, 3490-3502 (1999), Eqs. (2-3)
    [2] Collett, "Polarized Light", Marcel Dekker (1993)

    Examples
    --------
    >>> import numpy as np
    >>> P_H = polarizer(0)  # Horizontal polarizer
    >>> P_V = polarizer(np.pi / 2)  # Vertical polarizer
    >>> P_45 = polarizer(np.pi / 4)  # +45 degree polarizer
    >>>
    >>> # Crossed polarizers transmit nothing
    >>> S_unpol = np.array([1, 0, 0, 0])  # Unpolarized light
    >>> S_out = P_V @ P_H @ S_unpol  # H then V
    >>> np.isclose(S_out[0], 0)  # Zero transmission
    True
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    if not isinstance(theta, (int, float, np.floating, np.integer)):
        raise TypeError(
            f"theta must be a numeric scalar (int or float), got {type(theta).__name__}. "
            f"Angle should be in radians."
        )

    if not isinstance(tau, (int, float, np.floating, np.integer)):
        raise TypeError(
            f"tau must be a numeric scalar (int or float), got {type(tau).__name__}."
        )

    # Clamp tau to valid range [0, 1]
    # This can happen during optimization when parameters drift out of bounds
    if tau < 0.0 or tau > 1.0:
        # Silently clamp to valid range (matches MATLAB behavior)
        tau = np.clip(tau, 0.0, 1.0)

    # -------------------------------------------------------------------------
    # Build horizontal polarizer matrix (theta = 0)
    # Compain Eq. 2: P(tau, 0) = (tau/2) * [1 1 0 0; 1 1 0 0; 0 0 0 0; 0 0 0 0]
    # -------------------------------------------------------------------------
    half_tau = tau / 2.0

    M0 = half_tau * np.array([
        [1.0, 1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0]
    ], dtype=np.float64)

    # -------------------------------------------------------------------------
    # Optimization: if theta is zero (or very close), return directly
    # This avoids unnecessary matrix multiplications
    # -------------------------------------------------------------------------
    if np.abs(theta) < 1e-12:
        return M0

    # -------------------------------------------------------------------------
    # Rotate to desired orientation
    # Compain Eq. 3: P(tau, theta) = R(theta) @ P(tau, 0) @ R(-theta)
    # Since R(-theta) = R(theta).T for rotation matrices:
    #   P(tau, theta) = R(theta) @ P(tau, 0) @ R(theta).T
    # -------------------------------------------------------------------------
    R = rotation(theta)
    M = R @ M0 @ R.T

    return M


# =============================================================================
# LINEAR RETARDER (WAVEPLATE)
# =============================================================================

def retarder(theta: float, delta: float, tau: float = 1.0) -> ndarray:
    """
    Mueller matrix for a linear retarder (waveplate).

    Generates the 4x4 Mueller matrix for a linear retarder with its
    fast axis at angle theta from the horizontal and retardation delta.

    For a retarder with fast axis horizontal (theta = 0):

        M_ret(delta, 0) = tau * [ 1    0        0         0    ]
                                [ 0    1        0         0    ]
                                [ 0    0     cos(delta)  sin(delta) ]
                                [ 0    0    -sin(delta)  cos(delta) ]

    For retarder at angle theta:

        M_ret(delta, theta) = R(theta) @ M_ret(delta, 0) @ R(-theta)

    Parameters
    ----------
    theta : float
        Orientation of fast axis in radians.
        - theta = 0: fast axis horizontal (x-axis)
        - theta = pi/4: fast axis at +45 degrees
        - theta = pi/2: fast axis vertical (y-axis)
        Positive = counterclockwise looking into beam.

    delta : float
        Retardation (phase delay) in radians.
        - delta = phase_fast - phase_slow (CRITICAL SIGN CONVENTION)
        - delta > 0: fast axis is "fast" (lower refractive index)
        - delta = pi/2: quarter-wave plate (QWP)
        - delta = pi: half-wave plate (HWP)

    tau : float, optional
        Transmission coefficient, default = 1.0.
        Must be in range [0, 1].

    Returns
    -------
    M : ndarray, shape (4, 4)
        Mueller matrix for the retarder.

    Notes
    -----
    **Retardation Sign Convention (CRITICAL):**
    The input delta is defined as (phase_fast - phase_slow).
    If your retarder characterization gives (phase_slow - phase_fast),
    you MUST negate the value before passing it to this function.

    **Physical Properties:**
    - No absorption for ideal retarder (M[0,0] = tau)
    - Does not change the degree of polarization
    - Preserves orthogonality: det(M) = 1 for tau = 1
    - Eigenvalues: tau, tau, tau*exp(i*delta), tau*exp(-i*delta)

    **Polarization Transformation:**
    - Positive delta with fast axis horizontal:
      +45 degree linear -> right-hand elliptical/circular
    - delta = +pi/2 (QWP): +45 degree linear -> right-hand circular
    - delta = +pi (HWP): rotates linear polarization by 2*theta

    **Common Waveplates:**
    - Quarter-wave plate (QWP): delta = pi/2, converts linear to circular
    - Half-wave plate (HWP): delta = pi, rotates polarization plane
    - Full-wave plate: delta = 2*pi, equivalent to identity

    References
    ----------
    [1] Collett, "Polarized Light", Marcel Dekker (1993)
    [2] Goldstein, "Polarized Light", 3rd ed., CRC Press (2011)

    Examples
    --------
    >>> import numpy as np
    >>> QWP = retarder(0, np.pi / 2)  # QWP, fast axis horizontal
    >>> HWP = retarder(np.pi / 4, np.pi)  # HWP at 45 degrees
    >>>
    >>> # QWP converts +45 linear to circular
    >>> S_45 = np.array([1, 0, 1, 0])  # +45 degree linear
    >>> S_out = QWP @ S_45
    >>> np.allclose(S_out, [1, 0, 0, -1])  # Right-hand circular
    True
    >>>
    >>> # Zero retardation gives identity
    >>> np.allclose(retarder(0, 0), np.eye(4))
    True
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    if not isinstance(theta, (int, float, np.floating, np.integer)):
        raise TypeError(
            f"theta must be a numeric scalar (int or float), got {type(theta).__name__}. "
            f"Angle should be in radians."
        )

    if not isinstance(delta, (int, float, np.floating, np.integer)):
        raise TypeError(
            f"delta must be a numeric scalar (int or float), got {type(delta).__name__}. "
            f"Retardation should be in radians."
        )

    if not isinstance(tau, (int, float, np.floating, np.integer)):
        raise TypeError(
            f"tau must be a numeric scalar (int or float), got {type(tau).__name__}."
        )

    # Note: tau may slightly exceed 1 due to measurement noise at spectral edges
    # We allow this but ensure it's positive
    if tau < 0.0:
        raise ValueError(
            f"tau must be non-negative, got {tau}. "
            f"Transmission coefficient cannot be negative."
        )

    # -------------------------------------------------------------------------
    # Compute trigonometric terms for retardation
    # -------------------------------------------------------------------------
    cos_delta = np.cos(delta)
    sin_delta = np.sin(delta)

    # -------------------------------------------------------------------------
    # Build retarder matrix with fast axis horizontal (theta = 0)
    # This matrix rotates the S2-S3 subspace (U-V Stokes parameters)
    # while leaving S0 (intensity) and S1 (H/V linear) unchanged
    # -------------------------------------------------------------------------
    M0 = tau * np.array([
        [1.0, 0.0,        0.0,         0.0],
        [0.0, 1.0,        0.0,         0.0],
        [0.0, 0.0,  cos_delta,   sin_delta],
        [0.0, 0.0, -sin_delta,   cos_delta]
    ], dtype=np.float64)

    # -------------------------------------------------------------------------
    # Optimization: if theta is zero (or very close), return directly
    # -------------------------------------------------------------------------
    if np.abs(theta) < 1e-12:
        return M0

    # -------------------------------------------------------------------------
    # Rotate to desired orientation
    # M_ret(delta, theta) = R(theta) @ M_ret(delta, 0) @ R(-theta)
    # Since R(-theta) = R(theta).T:
    #   M_ret(delta, theta) = R(theta) @ M_ret(delta, 0) @ R(theta).T
    # -------------------------------------------------------------------------
    R = rotation(theta)
    M = R @ M0 @ R.T

    return M


# =============================================================================
# IDENTITY MATRIX (AIR/VACUUM)
# =============================================================================

def identity(tau: float = 1.0) -> ndarray:
    """
    Mueller identity matrix for air/vacuum (no polarization change).

    Generates a 4x4 identity Mueller matrix, representing a medium that
    does not change the polarization state. Used for "straight-through"
    (air or vacuum) calibration measurements.

    Parameters
    ----------
    tau : float, optional
        Transmission coefficient, default = 1.0.
        Accounts for intensity loss (e.g., Fresnel reflections at surfaces).
        Must be non-negative.

    Returns
    -------
    M : ndarray, shape (4, 4)
        Mueller identity matrix: M = tau * I_4 (4x4 identity scaled by tau)

    Notes
    -----
    **Physical Meaning:**
    - Represents a non-polarizing, non-depolarizing medium
    - Used for "straight-through" (ST) calibration measurement
    - Output Stokes vector equals input (scaled by tau):
      S_out = tau * S_in

    **Use Cases:**
    - Perfect air: identity() returns 4x4 identity matrix
    - Air with Fresnel losses: identity(0.96) accounts for 4% loss
    - Calibration: The "air" measurement should recover M = I

    Examples
    --------
    >>> import numpy as np
    >>> M_air = identity()
    >>> np.allclose(M_air, np.eye(4))  # Perfect transmission
    True
    >>> M_lossy = identity(0.92)  # 8% loss
    >>> np.isclose(M_lossy[0, 0], 0.92)
    True
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    if not isinstance(tau, (int, float, np.floating, np.integer)):
        raise TypeError(
            f"tau must be a numeric scalar (int or float), got {type(tau).__name__}."
        )

    if tau < 0.0:
        raise ValueError(
            f"tau must be non-negative, got {tau}. "
            f"Transmission coefficient cannot be negative."
        )

    # -------------------------------------------------------------------------
    # Create scaled identity matrix
    # -------------------------------------------------------------------------
    M = tau * np.eye(4, dtype=np.float64)

    return M


# =============================================================================
# ELLIPTIC RETARDER (NON-IDEAL, WITH DICHROISM)
# =============================================================================

def elliptic_retarder(
    theta: float,
    delta: float,
    psi: float,
    tau: float = 1.0
) -> ndarray:
    """
    Mueller matrix for a general elliptic retarder (non-ideal, with dichroism).

    Generates the 4x4 Mueller matrix for an elliptic retarder with
    transmission tau, ellipsometric angle psi, retardation delta, and
    fast-axis orientation theta.

    Implements Compain et al., Appl. Opt. 38, 3490 (1999), Appendix A:

    For fast axis horizontal (theta = 0):

        M₀(τ, Ψ, δ) = τ × [  1      -c₂Ψ      0         0    ]
                          [ -c₂Ψ     1        0         0    ]
                          [  0       0     s₂Ψ·cδ    s₂Ψ·sδ ]
                          [  0       0    -s₂Ψ·sδ    s₂Ψ·cδ ]

    where c₂Ψ = cos(2Ψ), s₂Ψ = sin(2Ψ), cδ = cos(δ), sδ = sin(δ)

    For rotated orientation:

        M(θ) = R(θ) @ M₀ @ R(-θ)

    Parameters
    ----------
    theta : float
        Fast axis orientation in radians.
        - theta = 0: fast axis horizontal (x-axis)
        - theta = pi/4: fast axis at +45 degrees
        - theta = pi/2: fast axis vertical (y-axis)
        Positive = counterclockwise looking into beam.

    delta : float
        Retardation (phase delay) in radians.
        - delta = phase_fast - phase_slow (CRITICAL SIGN CONVENTION)
        - delta = pi/2: quarter-wave retardation
        - delta = pi: half-wave retardation

    psi : float
        Ellipsometric angle in radians, characterizing dichroism.
        - psi = pi/4 (45°): ideal LINEAR retarder (no dichroism)
        - psi < pi/4: preferentially transmits polarization along slow axis
        - psi > pi/4: preferentially transmits polarization along fast axis

        For ideal linear retarders (waveplates), psi = 45° exactly.
        Use the simpler `retarder()` function for ideal linear retarders.

    tau : float, optional
        Transmission coefficient, default = 1.0.
        Must be in range [0, 1].

    Returns
    -------
    M : ndarray, shape (4, 4)
        Mueller matrix for the elliptic retarder.

    Notes
    -----
    **When to Use This Function:**

    This function is only needed when:
    1. The retarder exhibits dichroism (different absorption for orthogonal
       polarization states along fast/slow axes).
    2. You want to optimize the ellipsometric angle Ψ during calibration.

    For ideal linear retarders (standard waveplates), use the simpler
    `retarder()` function which assumes Ψ = 45° (no dichroism).

    **Physical Interpretation:**

    - The ellipsometric angle Ψ relates to the amplitude reflection/transmission
      coefficients for polarization along the fast and slow axes.
    - For Ψ = 45°, both polarizations are transmitted equally (no dichroism),
      and this function reduces to the standard linear retarder formula.
    - Dichroism (Ψ ≠ 45°) introduces off-diagonal coupling between S₀ and S₁.

    **Eigenvalue Structure (Compain Appendix B):**

    The eigenvalues of an elliptic retarder are:
        λ₁ = 2τ sin²(Ψ)           (real)
        λ₂ = 2τ cos²(Ψ)           (real)
        λ₃ = τ sin(2Ψ) exp(+iδ)   (complex)
        λ₄ = τ sin(2Ψ) exp(-iδ)   (complex conjugate)

    For ideal linear retarder (Ψ = 45°):
        λ₁ = λ₂ = τ
        λ₃,₄ = τ exp(±iδ)

    References
    ----------
    [1] Compain et al., Appl. Opt. 38, 3490-3502 (1999), Appendix A

    Examples
    --------
    >>> import numpy as np

    # Ideal linear retarder (psi = 45°) should match retarder() function
    >>> M_elliptic = elliptic_retarder(theta=0, delta=np.pi/2, psi=np.pi/4)
    >>> M_linear = retarder(theta=0, delta=np.pi/2)
    >>> np.allclose(M_elliptic, M_linear)
    True

    # Dichroic retarder with preferential transmission along slow axis
    >>> M_dichroic = elliptic_retarder(theta=0, delta=np.pi/2, psi=np.pi/6)
    >>> # Note the coupling between S0 and S1 (M[0,1] and M[1,0] non-zero)
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    if not isinstance(theta, (int, float, np.floating, np.integer)):
        raise TypeError(
            f"theta must be a numeric scalar (int or float), got {type(theta).__name__}. "
            f"Angle should be in radians."
        )

    if not isinstance(delta, (int, float, np.floating, np.integer)):
        raise TypeError(
            f"delta must be a numeric scalar (int or float), got {type(delta).__name__}. "
            f"Retardation should be in radians."
        )

    if not isinstance(psi, (int, float, np.floating, np.integer)):
        raise TypeError(
            f"psi must be a numeric scalar (int or float), got {type(psi).__name__}. "
            f"Ellipsometric angle should be in radians."
        )

    if not isinstance(tau, (int, float, np.floating, np.integer)):
        raise TypeError(
            f"tau must be a numeric scalar (int or float), got {type(tau).__name__}."
        )

    # Note: tau may slightly exceed 1 due to measurement noise at spectral edges
    # We allow this but ensure it's positive
    if tau < 0.0:
        raise ValueError(
            f"tau must be non-negative, got {tau}. "
            f"Transmission coefficient cannot be negative."
        )

    # -------------------------------------------------------------------------
    # Compute trigonometric terms
    # -------------------------------------------------------------------------
    # Ellipsometric angle terms
    cos_2psi = np.cos(2.0 * psi)
    sin_2psi = np.sin(2.0 * psi)

    # Retardation terms
    cos_delta = np.cos(delta)
    sin_delta = np.sin(delta)

    # -------------------------------------------------------------------------
    # Build elliptic retarder matrix with fast axis horizontal (theta = 0)
    # Compain Eq. A3 (Appendix A)
    #
    # Structure:
    #   - [0,0] and [1,1]: unity (before tau scaling)
    #   - [0,1] and [1,0]: -cos(2Ψ) coupling (dichroism)
    #   - [2,2] and [3,3]: sin(2Ψ)·cos(δ) rotation in S2-S3 plane
    #   - [2,3] and [3,2]: sin(2Ψ)·sin(δ) rotation in S2-S3 plane
    # -------------------------------------------------------------------------
    M0 = tau * np.array([
        [1.0,      -cos_2psi,          0.0,               0.0],
        [-cos_2psi,     1.0,           0.0,               0.0],
        [0.0,           0.0,   sin_2psi * cos_delta,  sin_2psi * sin_delta],
        [0.0,           0.0,  -sin_2psi * sin_delta,  sin_2psi * cos_delta]
    ], dtype=np.float64)

    # -------------------------------------------------------------------------
    # Optimization: if theta is zero (or very close), return directly
    # -------------------------------------------------------------------------
    if np.abs(theta) < 1e-12:
        return M0

    # -------------------------------------------------------------------------
    # Rotate to desired orientation
    # M(θ) = R(θ) @ M₀ @ R(-θ) = R(θ) @ M₀ @ R(θ).T
    # -------------------------------------------------------------------------
    R = rotation(theta)
    M = R @ M0 @ R.T

    return M
