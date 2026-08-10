"""
ECM Polarimetry — Eigenvalue Calibration Method for Mueller Matrix Polarimetry

A Python implementation of the ECM algorithm for calibrating and analyzing
spectroscopic Mueller matrix polarimeters with dual rotating compensators.
Powers MMForge v2.0.

Features
--------
- Complete ECM calibration for both **transmission** and **reflection**
  (oblique-incidence) modes
- Per-wavelength wafer-characterization optimization with physically
  motivated bounds
- Physics-informed reflection calibration via Transfer Matrix Method (TMM)
  with thickness and AOI refinement
- **Ellipsometric parameter extraction** (Ψ, Δ, pseudo-dielectric function,
  pseudo-n/k) for reflection samples
- **Four Mueller-matrix decompositions:**
  - Lu-Chipman polar (M = M_Δ · M_R · M_D)
  - Differential (Minkowski metric) — L_m, L_u, M_m, M_u
  - Cloude spectral (coherency-matrix eigendecomposition)
  - Purity space — P_P, P_S, P_Δ indices
- Auto-detection of angular positions from binary file dimensions
- Mode-aware save/load — single ``.npz`` format covers both modes
- WAFER25NM / WAFER10NM reference-wafer terminology throughout

References
----------
    [1] Compain et al., "General and self-consistent method for the calibration
        of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
        Appl. Opt. 38, 3490-3502 (1999)

    [2] Rosales et al., "Extended eigenvalue calibration method for overdetermined
        Mueller matrix polarimeters", Opt. Lett. 49, 1165-1168 (2024)

    [3] Lu & Chipman, "Interpretation of Mueller matrices based on polar
        decomposition", J. Opt. Soc. Am. A 13, 1106-1113 (1996)

    [4] Gil & Ossikovski, *Polarized Light and the Mueller Matrix Approach*,
        2nd ed., CRC Press (2022).

Modules
-------
config
    Configuration dataclasses for ECM calibration parameters
    (``ECMConfig`` plus ``ReflectionOptConfig`` / ``ThicknessFitConfig``
    / ``ReflectionCalConfig`` sub-dataclasses for reflection settings).
core
    Core ECM algorithms (calibration, solvers, matrix operations,
    ellipsometry, TMM).
utils
    Utility functions including Mueller matrix generators (with the
    ``reflector(ψ, Δ)`` helper used by reflection mode) and terminal
    color helpers.
io
    File I/O for calibration data, results, and sample discovery.
visualization
    Publication-quality plotting functions (Plotly is used by the GUI
    via streamlit_app/components/plots_plotly.py; this matplotlib-based
    module remains for notebook workflows).
postprocessing
    Four Mueller-matrix decompositions: Lu-Chipman, differential, Cloude,
    purity space.
diagnostics
    Calibration quality analysis tools.

Quick Start — Transmission
--------------------------
>>> from ecm.config import ECMConfig
>>> from ecm.core import calibrate_transmission
>>> from ecm.postprocessing import lu_chipman_decomposition
>>>
>>> cfg = ECMConfig()
>>> cfg.paths.data_dir = Path("./calibration_data")
>>> result, diagnostics = calibrate_transmission(cfg)
>>>
>>> from ecm.core import process_sample
>>> M, M_norm = process_sample(sample_data, result, cfg)
>>> lu_result = lu_chipman_decomposition(M_norm)

Quick Start — Reflection
------------------------
>>> from ecm.core.reflection_calibration import calibrate_reflection
>>> from ecm.core.ellipsometry import extract_ellipsometric_parameters
>>>
>>> cfg = ECMConfig()
>>> cfg.mode = 'reflection'
>>> cfg.paths.calibration_reflection_dir = Path("./reflection_data")
>>> cfg.reflection_cal.angle_of_incidence_deg = 70.0
>>> result, diagnostics = calibrate_reflection(cfg)
>>>
>>> M, M_norm = process_sample(sample_data, result, cfg)
>>> ellips = extract_ellipsometric_parameters(M_norm, aoi_deg=70.0)

Version History
---------------
8.0.0 - Reflection mode + 4 decompositions (Lu-Chipman, differential,
      Cloude, purity space) + ellipsometric parameter extraction +
      mode-aware save/load + WAFER terminology
6.5.5 - Complete Python translation of MATLAB ECM calibration v6.5.5
      - 383 tests, 100% MATLAB feature parity
"""

__version__ = "8.0.0"
__author__ = "Daniel Vala"

# Import main classes and functions for convenient access
from ecm.config.ecm_config import ECMConfig

# Lazy imports for commonly used functions
def __getattr__(name):
    """Lazy import for commonly used submodules."""
    if name == "calibrate_transmission":
        from ecm.core.transmission_calibration import calibrate_transmission
        return calibrate_transmission
    elif name == "calibrate_reflection":
        from ecm.core.reflection_calibration import calibrate_reflection
        return calibrate_reflection
    elif name == "lu_chipman_decomposition":
        from ecm.postprocessing.lu_chipman import lu_chipman_decomposition
        return lu_chipman_decomposition
    elif name == "process_sample":
        from ecm.core.sample_processing import process_sample
        return process_sample
    elif name == "extract_ellipsometric_parameters":
        from ecm.core.ellipsometry import extract_ellipsometric_parameters
        return extract_ellipsometric_parameters
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
    "calibrate_reflection",
    "process_sample",
    "extract_ellipsometric_parameters",
    # Postprocessing (lazy imported)
    "lu_chipman_decomposition",
    # Visualization (lazy imported)
    "plot_mueller_matrix",
]
