"""
Shared input validation for postprocessing modules.

Validates and normalizes Mueller matrix input shapes for Lu-Chipman,
Cloude, differential, and purity space analysis.
"""

import numpy as np
from numpy import ndarray
from typing import Tuple


def validate_mueller_input(M_norm: ndarray) -> Tuple[ndarray, bool]:
    """
    Validate and normalize Mueller matrix input shape.

    Accepts (4, 4) or (4, 4, n_wavelengths) and always returns 3D.

    Parameters
    ----------
    M_norm : array_like
        Mueller matrix(ces), shape (4, 4) or (4, 4, n_wavelengths).

    Returns
    -------
    M_3d : ndarray, shape (4, 4, n_wavelengths)
        3D Mueller matrix array.
    single_wavelength : bool
        True if input was 2D (single wavelength).

    Raises
    ------
    ValueError
        If input shape is not (4, 4) or (4, 4, n_wavelengths).
    """
    M_norm = np.asarray(M_norm, dtype=np.float64)

    if M_norm.ndim == 2:
        if M_norm.shape != (4, 4):
            raise ValueError(
                f"M_norm must be 4×4 or 4×4×n_wavelengths, got shape {M_norm.shape}"
            )
        M_norm = M_norm[:, :, np.newaxis]
        single_wavelength = True
    elif M_norm.ndim == 3:
        if M_norm.shape[:2] != (4, 4):
            raise ValueError(
                f"M_norm must be 4×4 or 4×4×n_wavelengths, got shape {M_norm.shape}"
            )
        single_wavelength = False
    else:
        raise ValueError(
            f"M_norm must be 4×4 or 4×4×n_wavelengths, got {M_norm.ndim}D array"
        )

    return M_norm, single_wavelength
