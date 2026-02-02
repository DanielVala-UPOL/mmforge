"""
ECM Core Algorithm Module

This module implements the core Eigenvalue Calibration Method (ECM) algorithm
for Mueller matrix polarimetry calibration.

Modules
-------
modulation
    Build modulation basis matrix and intensity matrices
fourier
    Extract Fourier coefficients from intensity modulation
ecm_matrices
    Build H and K constraint matrices
ecm_solver
    Solve for PSG (W) and PSA (A) matrices
parameter_extraction
    Extract sample parameters from eigenvalue analysis
sample_processing
    Extract Mueller matrices from calibrated measurements
file_discovery
    Auto-discover calibration files
transmission_calibration
    Main calibration orchestrator

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999)

[2] Rosales et al., "Extended eigenvalue calibration method for Mueller-matrix
    polarimetry", Opt. Lett. 49, 1165-1168 (2024)
"""

from ecm.core.modulation import (
    ModulationBasis,
    build_modulation_basis,
    build_intensity_matrix,
)
from ecm.core.fourier import (
    FourierCoefficients,
    extract_fourier_coefficients,
)
from ecm.core.ecm_matrices import (
    build_H_matrix,
    build_K_matrix,
)
from ecm.core.ecm_solver import (
    WDiagnostics,
    ADiagnostics,
    solve_W,
    solve_A,
)
from ecm.core.parameter_extraction import (
    PolarizerParams,
    RetarderParams,
    extract_sample_params,
)
from ecm.core.sample_processing import (
    MuellerMatrixResult,
    extract_mueller_matrix,
    process_sample,
    normalize_mueller_matrix,
    validate_mueller_matrix,
)
from ecm.core.file_discovery import (
    CalibrationFiles,
    discover_calibration_files,
)
from ecm.core.transmission_calibration import (
    CalibrationResult,
    CalibrationDiagnostics,
    RetarderCalibrationParams,
    calibrate_transmission,
)

__all__ = [
    # modulation
    'ModulationBasis',
    'build_modulation_basis',
    'build_intensity_matrix',
    # fourier
    'FourierCoefficients',
    'extract_fourier_coefficients',
    # ecm_matrices
    'build_H_matrix',
    'build_K_matrix',
    # ecm_solver
    'WDiagnostics',
    'ADiagnostics',
    'solve_W',
    'solve_A',
    # parameter_extraction
    'PolarizerParams',
    'RetarderParams',
    'extract_sample_params',
    # sample_processing
    'MuellerMatrixResult',
    'extract_mueller_matrix',
    'process_sample',
    'normalize_mueller_matrix',
    'validate_mueller_matrix',
    # file_discovery
    'CalibrationFiles',
    'discover_calibration_files',
    # transmission_calibration
    'CalibrationResult',
    'CalibrationDiagnostics',
    'RetarderCalibrationParams',
    'calibrate_transmission',
]
