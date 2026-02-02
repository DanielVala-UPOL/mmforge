"""
ECM Diagnostics Module

Provides comprehensive calibration quality analysis including:
- Fourier harmonic analysis
- Eigenvalue ratio statistics
- Condition number analysis
- Air Mueller matrix validation
- Retardation systematic error analysis
- Residual analysis

Functions
---------
run_calibration_diagnostics(result, diagnostics, cfg, ...)
    Generate comprehensive calibration diagnostics and figures

compute_fourier_spectrum(intensity, max_harmonic)
    Compute Fourier spectrum of intensity signal

References
----------
[1] Compain et al., Appl. Opt. 38, 3490-3502 (1999)
"""

from ecm.diagnostics.calibration_diagnostics import (
    CalibrationDiagnosticsReport,
    FourierSpectrum,
    run_calibration_diagnostics,
    compute_fourier_spectrum,
    fit_and_reconstruct_fourier,
    plot_fourier_harmonics,
    plot_w_matrix_elements,
    plot_a_matrix_elements,
    plot_eigenvalue_analysis,
    plot_air_mueller_validation,
)

__all__ = [
    'CalibrationDiagnosticsReport',
    'FourierSpectrum',
    'run_calibration_diagnostics',
    'compute_fourier_spectrum',
    'fit_and_reconstruct_fourier',
    'plot_fourier_harmonics',
    'plot_w_matrix_elements',
    'plot_a_matrix_elements',
    'plot_eigenvalue_analysis',
    'plot_air_mueller_validation',
]
