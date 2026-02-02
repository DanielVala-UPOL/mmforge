"""
ECM Utilities Module

This module provides utility functions for Mueller matrix operations and data I/O.

Submodules
----------
mueller_matrices
    Mueller matrix generators (rotation, polarizer, retarder, identity)
io
    Data loading functions for binary spectral data and wavelength calibration

Mueller Matrix Functions
------------------------
rotation(theta)
    Mueller rotation matrix for coordinate transformation (Compain Eq. 4)
polarizer(theta, tau)
    Mueller matrix for linear polarizer (Compain Eq. 2-3)
retarder(theta, delta, tau)
    Mueller matrix for linear retarder (waveplate)
identity(tau)
    Mueller identity matrix for air/vacuum

I/O Functions
-------------
load_spectral_data(filepath, cfg)
    Load binary spectral measurement data from polarimeter
load_wavelengths(cfg)
    Load wavelength calibration data

Example
-------
>>> from ecm.utils.mueller_matrices import rotation, polarizer, retarder
>>> import numpy as np
>>>
>>> # Create Mueller matrices
>>> R45 = rotation(np.pi / 4)       # 45-degree rotation
>>> P_H = polarizer(0.0)            # Horizontal polarizer
>>> QWP = retarder(0.0, np.pi / 2)  # Quarter-wave plate, fast axis horizontal
>>>
>>> # Rotate a polarizer to 45 degrees
>>> P_45 = R45 @ P_H @ R45.T
"""

from ecm.utils.mueller_matrices import (
    rotation,
    polarizer,
    retarder,
    identity,
)

from ecm.utils.io import (
    load_spectral_data,
    load_wavelengths,
    SpectralDataInfo,
    WavelengthInfo,
)

__all__ = [
    # Mueller matrices
    "rotation",
    "polarizer",
    "retarder",
    "identity",
    # I/O
    "load_spectral_data",
    "load_wavelengths",
    "SpectralDataInfo",
    "WavelengthInfo",
]
