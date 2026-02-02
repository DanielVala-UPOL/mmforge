"""
Fourier Coefficient Extraction for Polarimetric Analysis

This module provides an alternative analysis path for extracting harmonic
content from the intensity modulation in a dual rotating compensator
polarimeter using FFT.

Functions
---------
extract_fourier_coefficients(intensity, cfg)
    Extract Fourier coefficients (a0, an, bn) from intensity modulation

Theory
------
The measured intensity modulation in a dual rotating compensator system
can be written as a Fourier series:

    I(θ) = a₀ + Σₙ [aₙ·cos(nθ) + bₙ·sin(nθ)]

For a 1:5 frequency ratio system (PSG at frequency 1, PSA at frequency 5),
the Mueller matrix information is encoded in the even harmonics:
    n = {2, 4, 6, 8, 10, 12}

This module extracts these Fourier coefficients using FFT, which can be
used as an alternative to the modulation basis approach.

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999)

[2] Azzam, "Photopolarimetric measurement of the Mueller matrix by Fourier
    analysis of a single detected signal", Opt. Lett. 2, 148-150 (1978)
"""

import numpy as np
from numpy import ndarray
from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from ecm.config.ecm_config import ECMConfig


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FourierCoefficients:
    """
    Fourier decomposition of intensity modulation.

    Contains the DC component and harmonic coefficients extracted from
    the angular intensity measurements.

    Attributes
    ----------
    a0 : ndarray, shape (n_wavelengths,)
        DC (mean) component of the intensity modulation.

    an : ndarray, shape (n_harmonics, n_wavelengths)
        Cosine coefficients for each harmonic and wavelength.
        an[i, k] = cosine coefficient for harmonic harmonics[i] at wavelength k.

    bn : ndarray, shape (n_harmonics, n_wavelengths)
        Sine coefficients for each harmonic and wavelength.
        bn[i, k] = sine coefficient for harmonic harmonics[i] at wavelength k.

    harmonics : ndarray, shape (n_harmonics,)
        Array of harmonic indices that were extracted (e.g., [2, 4, 6, 8, 10, 12]).

    Notes
    -----
    The Fourier decomposition is:

        I(θ) = a₀ + Σₙ [aₙ·cos(nθ) + bₙ·sin(nθ)]

    For a 1:5 dual rotating compensator, the Mueller matrix elements are
    encoded in harmonics n = {2, 4, 6, 8, 10, 12}.
    """
    a0: ndarray
    an: ndarray
    bn: ndarray
    harmonics: ndarray


# =============================================================================
# FOURIER COEFFICIENT EXTRACTION
# =============================================================================

def extract_fourier_coefficients(
    intensity: ndarray,
    cfg: 'ECMConfig'
) -> FourierCoefficients:
    """
    Extract Fourier coefficients from intensity modulation using FFT.

    Decomposes the angular intensity variation into harmonic components.
    For a 1:5 dual rotating compensator, the Mueller matrix information
    is encoded in even harmonics n = {2, 4, 6, 8, 10, 12}.

    Reference: Compain et al., Appl. Opt. 38, 3490-3502 (1999)
               Azzam, Opt. Lett. 2, 148-150 (1978)

    Parameters
    ----------
    intensity : ndarray, shape (n_angles, n_wavelengths) or (n_angles,)
        Angular intensity measurements. Rows are angular positions,
        columns are wavelengths.

    cfg : ECMConfig
        ECM configuration containing:
        - cfg.fourier.mueller_harmonics : Tuple[int, ...]
            Harmonic indices to extract (default: (2, 4, 6, 8, 10, 12))
        - cfg.fourier.max_harmonic : int
            Maximum harmonic allowed (for Nyquist check)

    Returns
    -------
    FourierCoefficients
        Dataclass containing:
        - a0: DC component [n_wavelengths]
        - an: Cosine coefficients [n_harmonics × n_wavelengths]
        - bn: Sine coefficients [n_harmonics × n_wavelengths]
        - harmonics: Array of harmonic indices extracted

    Raises
    ------
    ValueError
        If requested harmonics exceed Nyquist limit (n_angles // 2).

    Examples
    --------
    >>> from ecm.config import ECMConfig
    >>> cfg = ECMConfig()
    >>> n_angles = 96
    >>> n_wl = 10
    >>>
    >>> # Create synthetic signal: I = 1000 + 100*cos(2θ) + 50*sin(4θ)
    >>> theta = np.linspace(0, 2*np.pi, n_angles, endpoint=False)
    >>> intensity = 1000 + 100*np.cos(2*theta) + 50*np.sin(4*theta)
    >>> intensity = np.tile(intensity.reshape(-1, 1), (1, n_wl))
    >>>
    >>> coeffs = extract_fourier_coefficients(intensity, cfg)
    >>> print(f"DC: {coeffs.a0[0]:.1f}")  # Should be ~1000
    >>> print(f"a2: {coeffs.an[0, 0]:.1f}")  # Should be ~100
    >>> print(f"b4: {coeffs.bn[1, 0]:.1f}")  # Should be ~50

    Notes
    -----
    **FFT Sign Convention (CRITICAL):**

    NumPy's FFT uses the convention:

        H[k] = Σₙ x[n] exp(-2πi·k·n/N)

    The real Fourier series is:

        I(θ) = a₀ + Σₙ [aₙ·cos(nθ) + bₙ·sin(nθ)]

    The relationship between FFT output H and Fourier coefficients is:

        a₀ = (1/N) · Re(H[0])           DC component
        aₙ = (2/N) · Re(H[n])           Cosine coefficients
        bₙ = -(2/N) · Im(H[n])          Sine coefficients (NEGATIVE!)

    The negative sign on the sine term comes from the FFT sign convention
    and must be preserved for correct results.

    **Nyquist Limit:**

    The maximum extractable harmonic is n_angles // 2. Requesting higher
    harmonics will raise a ValueError. For 96 angular positions, the
    Nyquist limit is 48.
    """
    # -------------------------------------------------------------------------
    # Handle 1D input (single wavelength)
    # -------------------------------------------------------------------------
    squeeze_output = False
    if intensity.ndim == 1:
        intensity = intensity.reshape(-1, 1)
        squeeze_output = True

    # -------------------------------------------------------------------------
    # Get dimensions
    # -------------------------------------------------------------------------
    n_angles, n_wavelengths = intensity.shape

    # -------------------------------------------------------------------------
    # Get harmonic configuration
    # -------------------------------------------------------------------------
    # Mueller harmonics to extract (typically [2, 4, 6, 8, 10, 12] for 1:5 system)
    harmonics = np.array(cfg.fourier.mueller_harmonics, dtype=np.int32)
    n_harmonics = len(harmonics)

    # -------------------------------------------------------------------------
    # Nyquist limit check
    # Maximum resolvable harmonic is floor(n_angles / 2)
    # -------------------------------------------------------------------------
    nyquist_limit = n_angles // 2

    max_requested = np.max(harmonics)
    if max_requested > nyquist_limit:
        raise ValueError(
            f"Requested harmonic n={max_requested} exceeds Nyquist limit "
            f"({nyquist_limit}) for {n_angles} angular positions. "
            f"Either increase angular sampling or reduce max harmonic."
        )

    # -------------------------------------------------------------------------
    # Compute FFT along angular axis (axis 0)
    #
    # FFT convention: H[k] = Σₙ x[n] exp(-2πi·k·n/N)
    # -------------------------------------------------------------------------
    H = np.fft.fft(intensity, axis=0)

    # -------------------------------------------------------------------------
    # Extract DC component
    #
    # a₀ = (1/N) · Re(H[0])
    # -------------------------------------------------------------------------
    a0 = np.real(H[0, :]) / n_angles

    # -------------------------------------------------------------------------
    # Extract harmonic coefficients
    #
    # For harmonic n:
    #   aₙ = (2/N) · Re(H[n])
    #   bₙ = -(2/N) · Im(H[n])   (NEGATIVE sign!)
    #
    # The negative sign on bₙ comes from the FFT sign convention:
    #   exp(-i·n·θ) = cos(nθ) - i·sin(nθ)
    # So Im(H[n]) corresponds to -bₙ, not +bₙ.
    # -------------------------------------------------------------------------
    an = np.zeros((n_harmonics, n_wavelengths), dtype=np.float64)
    bn = np.zeros((n_harmonics, n_wavelengths), dtype=np.float64)

    scale_factor = 2.0 / n_angles

    for i_harm, n in enumerate(harmonics):
        # FFT index for harmonic n
        # In Python/NumPy, FFT output is indexed from 0 to N-1
        # H[n] contains the n-th harmonic (for n < N/2)
        fft_idx = n

        # Extract real and imaginary parts
        H_n = H[fft_idx, :]

        # Compute Fourier coefficients
        # aₙ = (2/N) · Re(H[n])
        an[i_harm, :] = scale_factor * np.real(H_n)

        # bₙ = -(2/N) · Im(H[n])  -- NEGATIVE SIGN IS CRITICAL!
        bn[i_harm, :] = -scale_factor * np.imag(H_n)

    # -------------------------------------------------------------------------
    # Handle single wavelength output
    # -------------------------------------------------------------------------
    if squeeze_output:
        a0 = a0[0] if a0.size == 1 else a0.squeeze()
        an = an[:, 0] if an.shape[1] == 1 else an.squeeze()
        bn = bn[:, 0] if bn.shape[1] == 1 else bn.squeeze()

    # -------------------------------------------------------------------------
    # Return result
    # -------------------------------------------------------------------------
    return FourierCoefficients(
        a0=a0,
        an=an,
        bn=bn,
        harmonics=harmonics
    )
