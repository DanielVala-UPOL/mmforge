"""
Calibration Diagnostics

Comprehensive analysis of ECM calibration quality including:
- Fourier harmonic analysis (Mueller content vs residuals)
- W and A matrix element visualization
- Eigenvalue ratio analysis
- Air Mueller matrix validation (cross-talk check)
- Residual analysis (Fourier fit quality)

These diagnostics help identify:
- Measurement noise level
- Systematic errors
- Angular jitter or drift
- Retarder characterization accuracy

References
----------
[1] Compain et al., Appl. Opt. 38, 3490-3502 (1999)
"""

import numpy as np
from numpy import ndarray
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.figure import Figure
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, List
from pathlib import Path

from ecm.visualization.figure_utils import (
    get_publication_colors,
    get_color_cycle,
    save_figure,
    PUBLICATION_RCPARAMS,
)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FourierSpectrum:
    """
    Fourier spectrum of intensity signal.

    Attributes
    ----------
    dc : float
        DC component (mean intensity).

    amplitude : ndarray
        Amplitude spectrum (0 to max_harmonic).

    a : ndarray
        Cosine coefficients.

    b : ndarray
        Sine coefficients.

    max_harmonic : int
        Maximum harmonic order computed.
    """
    dc: float
    amplitude: ndarray
    a: ndarray
    b: ndarray
    max_harmonic: int


@dataclass
class CalibrationDiagnosticsReport:
    """
    Comprehensive calibration diagnostics report.

    Attributes
    ----------
    eigenvalue_ratio_stats : dict
        Statistics of λ₁₆/λ₁₅ ratio: 'mean', 'median', 'max', 'min'.

    condition_number_stats : dict
        Statistics for W and A condition numbers.

    air_mueller_deviation : dict
        Deviation of air Mueller from identity:
        'diagonal_mean', 'diagonal_max', 'off_diagonal_mean', 'off_diagonal_max'.

    fourier_residual_energy : dict
        Residual harmonic energy (>24) as fraction of total,
        keyed by sample name.

    snr_stats : dict
        Signal-to-noise ratio statistics (if computed).

    figures : dict
        Dictionary of generated diagnostic figures.

    summary_text : str
        Printable text summary of diagnostics.
    """
    eigenvalue_ratio_stats: Dict[str, float]
    condition_number_stats: Dict[str, Dict[str, float]]
    air_mueller_deviation: Dict[str, float]
    fourier_residual_energy: Dict[str, float]
    snr_stats: Optional[Dict[str, float]]
    figures: Dict[str, Figure]
    summary_text: str


# =============================================================================
# FOURIER ANALYSIS FUNCTIONS
# =============================================================================

def compute_fourier_spectrum(
    intensity: ndarray,
    max_harmonic: int = 48
) -> FourierSpectrum:
    """
    Compute Fourier spectrum of intensity signal.

    For a dual rotating compensator with frequency ratio 1:5, the Mueller
    matrix information is contained in harmonics 0-24. Higher harmonics
    (25+) should be near zero for a well-aligned system.

    Parameters
    ----------
    intensity : ndarray, shape (n_angles,)
        Intensity signal sampled at uniform angular intervals [0, 2π).

    max_harmonic : int, optional
        Maximum harmonic order to compute. Default 48.

    Returns
    -------
    spectrum : FourierSpectrum
        Fourier spectrum with DC, amplitude, and coefficients.

    Notes
    -----
    The Fourier coefficients are computed as:
        a₀ = (1/N) Σ I(θᵢ)                    (DC component)
        aₖ = (2/N) Σ I(θᵢ) cos(k θᵢ)          (cosine coefficient)
        bₖ = (2/N) Σ I(θᵢ) sin(k θᵢ)          (sine coefficient)

    Amplitude: Aₖ = √(aₖ² + bₖ²)

    Examples
    --------
    >>> spectrum = compute_fourier_spectrum(intensity_data, max_harmonic=48)
    >>> print(f"DC component: {spectrum.dc:.2f}")
    >>> print(f"Harmonic 12 amplitude: {spectrum.amplitude[12]:.2f}")
    """
    intensity = np.asarray(intensity).flatten()
    n = len(intensity)

    # Angular positions
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)

    # Pre-allocate
    amplitude = np.zeros(max_harmonic + 1)
    a = np.zeros(max_harmonic + 1)
    b = np.zeros(max_harmonic + 1)

    # DC component
    dc = np.mean(intensity)
    amplitude[0] = dc
    a[0] = dc

    # Higher harmonics
    for k in range(1, max_harmonic + 1):
        ak = (2.0 / n) * np.sum(intensity * np.cos(k * theta))
        bk = (2.0 / n) * np.sum(intensity * np.sin(k * theta))

        a[k] = ak
        b[k] = bk
        amplitude[k] = np.sqrt(ak**2 + bk**2)

    return FourierSpectrum(
        dc=dc,
        amplitude=amplitude,
        a=a,
        b=b,
        max_harmonic=max_harmonic
    )


def fit_and_reconstruct_fourier(
    intensity: ndarray,
    max_harmonic: int = 24
) -> Tuple[ndarray, ndarray]:
    """
    Fit Fourier series to intensity and compute residuals.

    This provides the true noise estimate by subtracting the signal model.

    Parameters
    ----------
    intensity : ndarray, shape (n_angles,)
        Intensity signal.

    max_harmonic : int, optional
        Maximum harmonic for the fit. Default 24 (Mueller content limit).

    Returns
    -------
    I_reconstructed : ndarray
        Fourier fit of intensity.

    residual : ndarray
        Residual (measured - fit).

    Examples
    --------
    >>> I_fit, residual = fit_and_reconstruct_fourier(intensity, max_harmonic=24)
    >>> noise_std = np.std(residual)
    >>> snr = np.mean(intensity) / noise_std
    """
    intensity = np.asarray(intensity).flatten()
    n = len(intensity)

    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)

    # DC component
    a0 = np.mean(intensity)
    I_reconstructed = np.full(n, a0)

    # Add harmonics
    for k in range(1, max_harmonic + 1):
        ak = (2.0 / n) * np.sum(intensity * np.cos(k * theta))
        bk = (2.0 / n) * np.sum(intensity * np.sin(k * theta))
        I_reconstructed += ak * np.cos(k * theta) + bk * np.sin(k * theta)

    residual = intensity - I_reconstructed

    return I_reconstructed, residual


# =============================================================================
# DIAGNOSTIC PLOTTING FUNCTIONS
# =============================================================================

def plot_fourier_harmonics(
    spectra: Dict[str, FourierSpectrum],
    test_wavelength: float = 550.0,
    figsize: Tuple[float, float] = (16, 8),
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot Fourier harmonics for multiple samples (Mueller content and residuals).

    Creates two rows:
    - Top: Harmonics 0-24 (Mueller matrix content)
    - Bottom: Harmonics 25+ (residuals, should be near zero)

    Parameters
    ----------
    spectra : dict
        Dictionary mapping sample names to FourierSpectrum objects.

    test_wavelength : float, optional
        Wavelength for title annotation.

    figsize : tuple, optional
        Figure size.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure.
    """
    n_samples = len(spectra)

    # Sample-specific colors
    sample_colors = {
        'air': (0.2, 0.6, 0.8),
        'pol_0': (0.2, 0.7, 0.4),
        'pol_45': (0.15, 0.93, 0.73),
        'ret_90': (0.6, 0.3, 0.7),
        'ret_45': (0.58, 0.47, 0.92),
    }

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, axes = plt.subplots(2, n_samples, figsize=figsize, facecolor='white')

        if n_samples == 1:
            axes = axes.reshape(2, 1)

        for col, (name, spectrum) in enumerate(spectra.items()):
            # Determine color
            color = sample_colors.get(name.lower(), (0.5, 0.5, 0.5))

            # Format display name
            display_name = name.replace('_', ' ').title()

            # -------------------------------------------------------------
            # Top row: Mueller content (0-24)
            # -------------------------------------------------------------
            ax_top = axes[0, col]
            ax_top.bar(range(25), spectrum.amplitude[:25], color=color, width=0.8)
            ax_top.set_xlabel('Harmonic Order', fontsize=12)
            ax_top.set_ylabel('Amplitude', fontsize=12)
            ax_top.set_title(f'{display_name}\nλ = {test_wavelength:.0f} nm', fontsize=12)
            ax_top.tick_params(axis='both', labelsize=10)
            ax_top.grid(True, linestyle='--', linewidth=0.5, color='0.85', axis='y')

            # -------------------------------------------------------------
            # Bottom row: Residuals (25+)
            # -------------------------------------------------------------
            ax_bot = axes[1, col]
            n_residual = len(spectrum.amplitude) - 25
            if n_residual > 0:
                ax_bot.bar(range(25, 25 + n_residual),
                           spectrum.amplitude[25:],
                           color=color, width=0.8)
            ax_bot.set_xlabel('Harmonic Order', fontsize=12)
            ax_bot.set_ylabel('Amplitude', fontsize=12)
            ax_bot.tick_params(axis='both', labelsize=10)
            ax_bot.grid(True, linestyle='--', linewidth=0.5, color='0.85', axis='y')

        # Row titles
        fig.text(0.02, 0.75, 'Mueller\nContent\n(0-24)', fontsize=12,
                 ha='center', va='center', fontweight='bold')
        fig.text(0.02, 0.28, 'Residuals\n(25+)', fontsize=12,
                 ha='center', va='center', fontweight='bold')

        fig.suptitle('Fourier Harmonic Analysis', fontsize=16, fontweight='bold', y=0.98)

        fig.tight_layout()
        fig.subplots_adjust(left=0.08, top=0.92)

    if save_path is not None:
        save_figure(fig, save_path)

    return fig


def plot_w_matrix_elements(
    W: ndarray,
    wavelengths: ndarray,
    figsize: Tuple[float, float] = (12, 10),
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot W (PSG modulation) matrix elements vs wavelength.

    Parameters
    ----------
    W : ndarray, shape (4, 4, n_wavelengths)
        PSG modulation matrices.

    wavelengths : ndarray
        Wavelength values in nm.

    figsize : tuple, optional
        Figure size.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure with 4×4 subplot grid.
    """
    colors = get_publication_colors()

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, axes = plt.subplots(4, 4, figsize=figsize, sharex=True, facecolor='white')

        for i in range(4):
            for j in range(4):
                ax = axes[i, j]

                element = np.squeeze(W[i, j, :])
                ax.plot(wavelengths, element, color=colors['blue'], linewidth=1.5)

                ax.set_title(r'$W_{%d%d}$' % (i+1, j+1), fontsize=12)
                ax.grid(True, linestyle='--', linewidth=0.5, color='0.85')
                ax.tick_params(axis='both', labelsize=9)

                if i == 3:
                    ax.set_xlabel('λ (nm)', fontsize=10)

        fig.suptitle('PSG Modulation Matrix W', fontsize=16, fontweight='bold', y=0.98)

        fig.tight_layout()
        fig.subplots_adjust(top=0.93)

    if save_path is not None:
        save_figure(fig, save_path)

    return fig


def plot_a_matrix_elements(
    A: ndarray,
    wavelengths: ndarray,
    figsize: Tuple[float, float] = (12, 10),
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot A (PSA analysis) matrix elements vs wavelength.

    Parameters
    ----------
    A : ndarray, shape (4, 4, n_wavelengths)
        PSA analysis matrices.

    wavelengths : ndarray
        Wavelength values in nm.

    figsize : tuple, optional
        Figure size.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure with 4×4 subplot grid.
    """
    colors = get_publication_colors()

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, axes = plt.subplots(4, 4, figsize=figsize, sharex=True, facecolor='white')

        for i in range(4):
            for j in range(4):
                ax = axes[i, j]

                element = np.squeeze(A[i, j, :])
                ax.plot(wavelengths, element, color=colors['orange'], linewidth=1.5)

                ax.set_title(r'$A_{%d%d}$' % (i+1, j+1), fontsize=12)
                ax.grid(True, linestyle='--', linewidth=0.5, color='0.85')
                ax.tick_params(axis='both', labelsize=9)

                if i == 3:
                    ax.set_xlabel('λ (nm)', fontsize=10)

        fig.suptitle('PSA Analysis Matrix A', fontsize=16, fontweight='bold', y=0.98)

        fig.tight_layout()
        fig.subplots_adjust(top=0.93)

    if save_path is not None:
        save_figure(fig, save_path)

    return fig


def plot_eigenvalue_analysis(
    eigenvalue_ratios: ndarray,
    wavelengths: ndarray,
    figsize: Tuple[float, float] = (10, 6),
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot eigenvalue ratio λ₁₆/λ₁₅ vs wavelength.

    A small ratio (< 10⁻³) indicates consistent calibration data.
    Large ratios may indicate measurement errors or inconsistent samples.

    Parameters
    ----------
    eigenvalue_ratios : ndarray
        Ratio λ₁₆/λ₁₅ for each wavelength.

    wavelengths : ndarray
        Wavelength values in nm.

    figsize : tuple, optional
        Figure size.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure.
    """
    colors = get_publication_colors()

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, ax = plt.subplots(figsize=figsize, facecolor='white')

        ax.semilogy(wavelengths, eigenvalue_ratios, color=colors['purple'], linewidth=1.5)

        # Threshold lines (updated per spec: Excellent < 1e-4, Good < 1e-3, Acceptable < 1e-2)
        ax.axhline(y=1e-4, color='b', linestyle='--', linewidth=1.0)   # Excellent
        ax.axhline(y=1e-3, color='g', linestyle='--', linewidth=1.0)   # Good
        ax.axhline(y=1e-2, color='y', linestyle='--', linewidth=1.0)   # Acceptable

        # Labels
        xlim = ax.get_xlim()
        ax.text(xlim[1], 1e-4, r'  Excellent ($10^{-4}$)', fontsize=12, va='center', color='b')
        ax.text(xlim[1], 1e-3, r'  Good ($10^{-3}$)', fontsize=12, va='center', color='g')
        ax.text(xlim[1], 1e-2, r'  Acceptable ($10^{-2}$)', fontsize=12, va='center', color='y')

        ax.set_xlabel('Wavelength (nm)', fontsize=14)
        ax.set_ylabel(r'Eigenvalue Ratio $\lambda_{16}/\lambda_{15}$', fontsize=14)
        ax.set_title('ECM Eigenvalue Ratio (Calibration Quality)', fontsize=16, fontweight='bold')
        ax.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax.tick_params(axis='both', labelsize=14)

        fig.tight_layout()

    if save_path is not None:
        save_figure(fig, save_path)

    return fig


def plot_air_mueller_validation(
    M_air: ndarray,
    wavelengths: ndarray,
    figsize: Tuple[float, float] = (12, 5),
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot air Mueller matrix validation (should be identity).

    Creates two panels:
    1. Diagonal elements (should be 1)
    2. Maximum off-diagonal element (cross-talk, should be ~0)

    Parameters
    ----------
    M_air : ndarray, shape (4, 4, n_wavelengths)
        Normalized air Mueller matrices.

    wavelengths : ndarray
        Wavelength values in nm.

    figsize : tuple, optional
        Figure size.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure.
    """
    colors = get_publication_colors()
    color_cycle = get_color_cycle()

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize, facecolor='white')

        # ---------------------------------------------------------------------
        # Panel 1: Diagonal elements (should be 1)
        # ---------------------------------------------------------------------
        for k in range(4):
            element = np.squeeze(M_air[k, k, :])
            ax1.plot(wavelengths, element, color=color_cycle[k], linewidth=1.5,
                     label=r'$m_{%d%d}$' % (k+1, k+1))

        ax1.axhline(y=1.0, color='k', linestyle='--', linewidth=1.0)

        ax1.set_xlabel('Wavelength (nm)', fontsize=14)
        ax1.set_ylabel('Normalized Value', fontsize=14)
        ax1.set_title('Air Mueller - Diagonal (Should = 1)', fontsize=14, fontweight='bold')
        ax1.legend(loc='best', fontsize=12)
        ax1.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax1.tick_params(axis='both', labelsize=14)

        # ---------------------------------------------------------------------
        # Panel 2: Max off-diagonal (cross-talk)
        # ---------------------------------------------------------------------
        n_wl = M_air.shape[2]
        off_diag_max = np.zeros(n_wl)

        for k in range(n_wl):
            M_k = M_air[:, :, k].copy()
            np.fill_diagonal(M_k, 0)  # Zero diagonal
            off_diag_max[k] = np.max(np.abs(M_k))

        ax2.plot(wavelengths, off_diag_max, color=colors['orange'], linewidth=1.5)
        ax2.axhline(y=0.1, color='k', linestyle='--', linewidth=1.0)

        xlim = ax2.get_xlim()
        ax2.text(xlim[1], 0.1, '  10% threshold', fontsize=12, va='center')

        ax2.set_xlabel('Wavelength (nm)', fontsize=14)
        ax2.set_ylabel(r'Max $|m_{ij}|$ $(i \neq j)$', fontsize=14)
        ax2.set_title('Air Mueller - Cross-talk', fontsize=14, fontweight='bold')
        ax2.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax2.tick_params(axis='both', labelsize=14)

        fig.suptitle('Air Validation - Should Be Identity Matrix',
                     fontsize=16, fontweight='bold', y=1.02)

        fig.tight_layout()

    if save_path is not None:
        save_figure(fig, save_path)

    return fig


# =============================================================================
# MAIN DIAGNOSTIC FUNCTION
# =============================================================================

def run_calibration_diagnostics(
    W: ndarray,
    A: ndarray,
    wavelengths: ndarray,
    eigenvalue_ratios: ndarray,
    cond_W: ndarray,
    cond_A: ndarray,
    M_air: Optional[ndarray] = None,
    save_dir: Optional[Path] = None,
    verbose: bool = True,
) -> CalibrationDiagnosticsReport:
    """
    Generate comprehensive calibration diagnostics.

    Performs:
    1. Eigenvalue ratio distribution analysis
    2. W/A matrix element spectral plots
    3. Condition number analysis
    4. Air Mueller matrix validation (if provided)

    Parameters
    ----------
    W : ndarray, shape (4, 4, n_wavelengths)
        PSG modulation matrices from calibration.

    A : ndarray, shape (4, 4, n_wavelengths)
        PSA analysis matrices from calibration.

    wavelengths : ndarray
        Wavelength values in nm.

    eigenvalue_ratios : ndarray
        λ₁₆/λ₁₅ ratio for each wavelength.

    cond_W : ndarray
        Condition number of W for each wavelength.

    cond_A : ndarray
        Condition number of A for each wavelength.

    M_air : ndarray, optional
        Normalized air Mueller matrices for validation.

    save_dir : Path, optional
        Directory to save diagnostic figures.

    verbose : bool, optional
        Print summary to console. Default True.

    Returns
    -------
    report : CalibrationDiagnosticsReport
        Complete diagnostics with figures and statistics.

    Examples
    --------
    >>> from ecm.diagnostics import run_calibration_diagnostics
    >>>
    >>> report = run_calibration_diagnostics(
    ...     result.W, result.A, result.wavelengths,
    ...     diagnostics.eigenvalue_ratio,
    ...     diagnostics.cond_W, diagnostics.cond_A,
    ...     M_air=M_air_normalized,
    ...     save_dir=Path('output/diagnostics'),
    ...     verbose=True
    ... )
    """
    figures = {}

    # Create save directory if needed
    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Eigenvalue ratio statistics
    # -------------------------------------------------------------------------
    eigenvalue_ratio_stats = {
        'mean': float(np.mean(eigenvalue_ratios)),
        'median': float(np.median(eigenvalue_ratios)),
        'max': float(np.max(eigenvalue_ratios)),
        'min': float(np.min(eigenvalue_ratios)),
    }

    # -------------------------------------------------------------------------
    # Condition number statistics
    # -------------------------------------------------------------------------
    condition_number_stats = {
        'W': {
            'mean': float(np.mean(cond_W)),
            'max': float(np.max(cond_W)),
            'min': float(np.min(cond_W)),
        },
        'A': {
            'mean': float(np.mean(cond_A)),
            'max': float(np.max(cond_A)),
            'min': float(np.min(cond_A)),
        },
    }

    # -------------------------------------------------------------------------
    # Air Mueller deviation (if provided)
    # -------------------------------------------------------------------------
    if M_air is not None:
        n_wl = M_air.shape[2]

        # Diagonal deviation from 1
        diag_devs = []
        for k in range(4):
            diag_devs.extend(np.abs(M_air[k, k, :] - 1.0))

        # Off-diagonal magnitudes
        off_diag_vals = []
        for wl_idx in range(n_wl):
            M_k = M_air[:, :, wl_idx].copy()
            np.fill_diagonal(M_k, 0)
            off_diag_vals.extend(np.abs(M_k).flatten())

        air_mueller_deviation = {
            'diagonal_mean': float(np.mean(diag_devs)),
            'diagonal_max': float(np.max(diag_devs)),
            'off_diagonal_mean': float(np.mean(off_diag_vals)),
            'off_diagonal_max': float(np.max(off_diag_vals)),
        }
    else:
        air_mueller_deviation = {}

    # -------------------------------------------------------------------------
    # Generate plots
    # -------------------------------------------------------------------------
    # W matrix elements
    figures['W_elements'] = plot_w_matrix_elements(
        W, wavelengths,
        save_path=save_dir / 'W_matrix_elements.png' if save_dir else None
    )

    # A matrix elements
    figures['A_elements'] = plot_a_matrix_elements(
        A, wavelengths,
        save_path=save_dir / 'A_matrix_elements.png' if save_dir else None
    )

    # Eigenvalue analysis
    figures['eigenvalue_ratio'] = plot_eigenvalue_analysis(
        eigenvalue_ratios, wavelengths,
        save_path=save_dir / 'eigenvalue_ratio.png' if save_dir else None
    )

    # Air validation (if provided)
    if M_air is not None:
        figures['air_validation'] = plot_air_mueller_validation(
            M_air, wavelengths,
            save_path=save_dir / 'air_mueller_validation.png' if save_dir else None
        )

    # -------------------------------------------------------------------------
    # Build summary text
    # -------------------------------------------------------------------------
    summary_lines = [
        "=" * 50,
        "CALIBRATION DIAGNOSTICS SUMMARY",
        "=" * 50,
        "",
        "Eigenvalue Ratio λ₁₆/λ₁₅:",
        f"  Mean:   {eigenvalue_ratio_stats['mean']:.2e}",
        f"  Median: {eigenvalue_ratio_stats['median']:.2e}",
        f"  Max:    {eigenvalue_ratio_stats['max']:.2e}",
        "",
        "Condition Numbers:",
        f"  cond(W) - Mean: {condition_number_stats['W']['mean']:.2f}",
        f"  cond(W) - Max:  {condition_number_stats['W']['max']:.2f}",
        f"  cond(A) - Mean: {condition_number_stats['A']['mean']:.2f}",
        f"  cond(A) - Max:  {condition_number_stats['A']['max']:.2f}",
    ]

    if air_mueller_deviation:
        summary_lines.extend([
            "",
            "Air Mueller Matrix Validation:",
            f"  Diagonal deviation from 1 (mean): {air_mueller_deviation['diagonal_mean']:.4f}",
            f"  Diagonal deviation from 1 (max):  {air_mueller_deviation['diagonal_max']:.4f}",
            f"  Off-diagonal (mean): {air_mueller_deviation['off_diagonal_mean']:.4f}",
            f"  Off-diagonal (max):  {air_mueller_deviation['off_diagonal_max']:.4f}",
        ])

    summary_lines.extend([
        "",
        "=" * 50,
    ])

    summary_text = "\n".join(summary_lines)

    # -------------------------------------------------------------------------
    # Print if verbose
    # -------------------------------------------------------------------------
    if verbose:
        print(summary_text)

    # -------------------------------------------------------------------------
    # Build report
    # -------------------------------------------------------------------------
    report = CalibrationDiagnosticsReport(
        eigenvalue_ratio_stats=eigenvalue_ratio_stats,
        condition_number_stats=condition_number_stats,
        air_mueller_deviation=air_mueller_deviation,
        fourier_residual_energy={},  # Computed separately if raw data available
        snr_stats=None,
        figures=figures,
        summary_text=summary_text,
    )

    return report
