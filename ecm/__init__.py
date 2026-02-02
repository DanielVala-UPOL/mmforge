"""
ECM Polarimetry - Ellipsometric Calibration Method for Mueller Matrix Polarimetry

A Python implementation of the ECM algorithm for calibrating and analyzing
spectroscopic Mueller matrix polarimeters with dual rotating compensators.

Features
--------
- Complete ECM calibration pipeline for transmission mode
- Lu-Chipman polar decomposition of Mueller matrices
- Publication-quality visualization tools
- Command-line interface for batch processing
- Comprehensive test suite (383 tests)

References
----------
    [1] Compain et al., "General and self-consistent method for the calibration
        of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
        Appl. Opt. 38, 3490-3502 (1999)

    [2] Rosales et al., "Extended eigenvalue calibration method for overdetermined
        Mueller matrix polarimeters", Opt. Lett. 49, 1165-1168 (2024)

    [3] Lu & Chipman, "Interpretation of Mueller matrices based on polar
        decomposition", J. Opt. Soc. Am. A 13, 1106-1113 (1996)

Modules
-------
config
    Configuration dataclasses for ECM calibration parameters
core
    Core ECM algorithms (calibration, solvers, matrix operations)
utils
    Utility functions including Mueller matrix generators
io
    File I/O for calibration data and results
visualization
    Publication-quality plotting functions
postprocessing
    Lu-Chipman polar decomposition
diagnostics
    Calibration quality analysis tools

Quick Start
-----------
>>> from ecm.config import ECMConfig
>>> from ecm.core import calibrate_transmission
>>> from ecm.postprocessing import lu_chipman_decomposition
>>>
>>> # Create configuration
>>> cfg = ECMConfig()
>>> cfg.paths.data_dir = Path("./calibration_data")
>>>
>>> # Run calibration
>>> result, diagnostics = calibrate_transmission(cfg)
>>>
>>> # Process a sample and decompose
>>> from ecm.core import process_sample
>>> M, M_norm = process_sample(sample_data, result, cfg)
>>> lu_result = lu_chipman_decomposition(M_norm)

CLI Commands
------------
    ecm-calibrate   Run ECM calibration
    ecm-process     Process samples using saved calibration
    ecm-postprocess Lu-Chipman decomposition on processed samples

Version History
---------------
6.5.5 - Complete Python translation of MATLAB ECM calibration v6.5.5
      - 383 tests, 100% MATLAB feature parity
"""

__version__ = "6.5.5"
__author__ = "Daniel Vala"

# Import main classes and functions for convenient access
from ecm.config.ecm_config import ECMConfig

# Lazy imports for commonly used functions
def __getattr__(name):
    """Lazy import for commonly used submodules."""
    if name == "calibrate_transmission":
        from ecm.core.transmission_calibration import calibrate_transmission
        return calibrate_transmission
    elif name == "lu_chipman_decomposition":
        from ecm.postprocessing.lu_chipman import lu_chipman_decomposition
        return lu_chipman_decomposition
    elif name == "process_sample":
        from ecm.core.sample_processing import process_sample
        return process_sample
    elif name == "plot_mueller_matrix":
        from ecm.visualization.mueller_plots import plot_mueller_matrix
        return plot_mueller_matrix
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Configuration
    "ECMConfig",
    # Core functions (lazy imported)
    "calibrate_transmission",
    "process_sample",
    "lu_chipman_decomposition",
    "plot_mueller_matrix",
]
