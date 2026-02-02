"""
Polarimetric Parameter Visualization

Provides functions to plot Lu-Chipman decomposition parameters:
- Depolarization Index (DI)
- Retardance (degrees and waves) - 2×1 subplot
- Diattenuation (D)
- Retarder axis angles (ψ, χ) - 2×1 subplot

These mirror the MATLAB plot_polarimetric_parameters.m functionality.

References
----------
[1] Lu & Chipman, J. Opt. Soc. Am. A 13, 1106-1113 (1996)
"""

import numpy as np
from numpy import ndarray
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import Optional, Tuple, Dict
from pathlib import Path

from ecm.postprocessing.lu_chipman import LuChipmanResult
from ecm.visualization.figure_utils import (
    setup_figure,
    format_axes,
    get_publication_colors,
    add_reference_line,
    save_figure,
    PUBLICATION_RCPARAMS,
)


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def plot_polarimetric_parameters(
    lu_result: LuChipmanResult,
    wavelengths: ndarray,
    sample_name: str = '',
    save_dir: Optional[Path] = None,
    figsize_single: Tuple[float, float] = (8, 6),
    figsize_double: Tuple[float, float] = (8, 8),
) -> Dict[str, Figure]:
    """
    Generate publication-quality plots of Lu-Chipman parameters.

    Creates four figures:
    1. Depolarization Index (DI) vs wavelength
    2. Retardance in degrees and waves vs wavelength (2×1 subplot)
    3. Diattenuation (D) vs wavelength
    4. Retarder axis angles (ψ, χ) vs wavelength (2×1 subplot)

    Parameters
    ----------
    lu_result : LuChipmanResult
        Output from lu_chipman_decomposition().

    wavelengths : ndarray
        Wavelength values in nm.

    sample_name : str, optional
        Sample name for figure titles.

    save_dir : Path, optional
        If provided, save all figures to this directory.
        Filenames: DI.png, retardance.png, diattenuation.png, axis.png

    figsize_single : tuple, optional
        Figure size for single-panel figures. Default (8, 6).

    figsize_double : tuple, optional
        Figure size for two-panel figures. Default (8, 8).

    Returns
    -------
    figures : dict
        Dictionary mapping parameter names to Figure objects.
        Keys: 'DI', 'retardance', 'diattenuation', 'axis'

    Examples
    --------
    >>> from ecm.postprocessing import lu_chipman_decomposition
    >>> from ecm.visualization import plot_polarimetric_parameters
    >>>
    >>> result = lu_chipman_decomposition(M_normalized)
    >>> figures = plot_polarimetric_parameters(
    ...     result, wavelengths, sample_name='QWP at 0°',
    ...     save_dir=Path('output/qwp')
    ... )
    >>> plt.show()
    """
    figures = {}

    # Format sample name for display
    if sample_name:
        display_name = sample_name.replace('_', ' ')
    else:
        display_name = 'Sample'

    # Create save directory if needed
    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Figure 1: Depolarization Index (DI)
    # -------------------------------------------------------------------------
    figures['DI'] = plot_depolarization_index(
        lu_result.DI,
        wavelengths,
        title=f'{display_name} - Depolarization Index (DI)',
        figsize=figsize_single,
        save_path=save_dir / 'DI.png' if save_dir else None,
    )

    # -------------------------------------------------------------------------
    # Figure 2: Retardance (2×1 subplot: degrees and waves)
    # -------------------------------------------------------------------------
    figures['retardance'] = plot_retardance(
        lu_result.R_deg,
        lu_result.R_waves,
        wavelengths,
        title=f'{display_name} - Retardance',
        figsize=figsize_double,
        save_path=save_dir / 'retardance.png' if save_dir else None,
    )

    # -------------------------------------------------------------------------
    # Figure 3: Diattenuation (D)
    # -------------------------------------------------------------------------
    figures['diattenuation'] = plot_diattenuation(
        lu_result.D,
        wavelengths,
        title=f'{display_name} - Net Diattenuation (D)',
        figsize=figsize_single,
        save_path=save_dir / 'diattenuation.png' if save_dir else None,
    )

    # -------------------------------------------------------------------------
    # Figure 4: Retarder Axis Parameters (ψ and χ)
    # -------------------------------------------------------------------------
    figures['axis'] = plot_retarder_axis(
        lu_result.psi_deg,
        lu_result.chi_deg,
        wavelengths,
        title=f'{display_name} - Retarder Axis',
        figsize=figsize_double,
        save_path=save_dir / 'axis.png' if save_dir else None,
    )

    return figures


# =============================================================================
# INDIVIDUAL PARAMETER PLOTS
# =============================================================================

def plot_depolarization_index(
    DI: ndarray,
    wavelengths: ndarray,
    title: str = 'Depolarization Index (DI)',
    figsize: Tuple[float, float] = (8, 6),
    ax: Optional[Axes] = None,
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot Depolarization Index vs wavelength.

    Parameters
    ----------
    DI : ndarray
        Depolarization Index values, range [0, 1].

    wavelengths : ndarray
        Wavelength values in nm.

    title : str, optional
        Plot title.

    figsize : tuple, optional
        Figure size if creating new figure.

    ax : Axes, optional
        If provided, plot on this axes.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure.
    """
    colors = get_publication_colors()

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize, facecolor='white')
        else:
            fig = ax.figure

        # Main plot
        ax.plot(wavelengths, DI, color=colors['purple'], linewidth=1.5)

        # Reference lines
        ax.axhline(y=1.0, color='k', linestyle='--', linewidth=1.0)
        ax.axhline(y=0.0, color='k', linestyle=':', linewidth=1.0)

        # Labels for reference lines
        xlim = ax.get_xlim()
        ax.text(xlim[1], 1.0, '  Non-depolarizing', fontsize=12, va='center')
        ax.text(xlim[1], 0.0, '  Ideal depolarizer', fontsize=12, va='center')

        # Formatting
        ax.set_xlabel('Wavelength (nm)', fontsize=14)
        ax.set_ylabel('Depolarization Index', fontsize=14)
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_ylim(0, 1.05)
        ax.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax.tick_params(axis='both', labelsize=14)

        fig.tight_layout()

    if save_path is not None:
        save_figure(fig, save_path)

    return fig


def plot_retardance(
    R_deg: ndarray,
    R_waves: ndarray,
    wavelengths: ndarray,
    title: str = 'Retardance',
    figsize: Tuple[float, float] = (8, 8),
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot retardance in degrees and waves (2×1 subplot).

    Parameters
    ----------
    R_deg : ndarray
        Retardance in degrees.

    R_waves : ndarray
        Retardance in waves (degrees/360).

    wavelengths : ndarray
        Wavelength values in nm.

    title : str, optional
        Overall figure title.

    figsize : tuple, optional
        Figure size.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure with 2×1 subplots.
    """
    colors = get_publication_colors()

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, facecolor='white')

        # ---------------------------------------------------------------------
        # Subplot 1: Retardance in degrees
        # ---------------------------------------------------------------------
        ax1.plot(wavelengths, R_deg, color=colors['green'], linewidth=1.5)

        # Reference lines for QWP and HWP
        ax1.axhline(y=90, color='b', linestyle='--', linewidth=1.0)
        ax1.axhline(y=180, color='r', linestyle='--', linewidth=1.0)

        # Labels
        xlim = ax1.get_xlim()
        ax1.text(xlim[1], 90, '  QWP (90°)', fontsize=12, va='center', color='b')
        ax1.text(xlim[1], 180, '  HWP (180°)', fontsize=12, va='center', color='r')

        ax1.set_xlabel('Wavelength (nm)', fontsize=14)
        ax1.set_ylabel('Retardance (degrees)', fontsize=14)
        ax1.set_title(title, fontsize=16, fontweight='bold')
        ax1.set_ylim(0, 200)
        ax1.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax1.tick_params(axis='both', labelsize=14)

        # ---------------------------------------------------------------------
        # Subplot 2: Retardance in waves
        # ---------------------------------------------------------------------
        ax2.plot(wavelengths, R_waves, color=colors['green'], linewidth=1.5)

        # Reference lines
        ax2.axhline(y=0.25, color='b', linestyle='--', linewidth=1.0)
        ax2.axhline(y=0.5, color='r', linestyle='--', linewidth=1.0)

        # Labels
        xlim = ax2.get_xlim()
        ax2.text(xlim[1], 0.25, '  QWP (0.25)', fontsize=12, va='center', color='b')
        ax2.text(xlim[1], 0.5, '  HWP (0.5)', fontsize=12, va='center', color='r')

        ax2.set_xlabel('Wavelength (nm)', fontsize=14)
        ax2.set_ylabel('Retardance (waves)', fontsize=14)
        ax2.set_ylim(0, 0.6)
        ax2.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax2.tick_params(axis='both', labelsize=14)

        fig.tight_layout()

    if save_path is not None:
        save_figure(fig, save_path)

    return fig


def plot_diattenuation(
    D: ndarray,
    wavelengths: ndarray,
    title: str = 'Net Diattenuation (D)',
    figsize: Tuple[float, float] = (8, 6),
    ax: Optional[Axes] = None,
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot Diattenuation vs wavelength.

    Parameters
    ----------
    D : ndarray
        Diattenuation values, range [0, 1].

    wavelengths : ndarray
        Wavelength values in nm.

    title : str, optional
        Plot title.

    figsize : tuple, optional
        Figure size if creating new figure.

    ax : Axes, optional
        If provided, plot on this axes.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure.
    """
    colors = get_publication_colors()

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize, facecolor='white')
        else:
            fig = ax.figure

        # Main plot
        ax.plot(wavelengths, D, color=colors['orange'], linewidth=1.5)

        # Reference lines
        ax.axhline(y=1.0, color='k', linestyle='--', linewidth=1.0)
        ax.axhline(y=0.0, color='k', linestyle=':', linewidth=1.0)

        # Labels for reference lines
        xlim = ax.get_xlim()
        ax.text(xlim[1], 1.0, '  Ideal polarizer', fontsize=12, va='center')
        ax.text(xlim[1], 0.0, '  No diattenuation', fontsize=12, va='center')

        # Formatting
        ax.set_xlabel('Wavelength (nm)', fontsize=14)
        ax.set_ylabel('Diattenuation', fontsize=14)
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_ylim(0, 1.05)
        ax.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax.tick_params(axis='both', labelsize=14)

        fig.tight_layout()

    if save_path is not None:
        save_figure(fig, save_path)

    return fig


def plot_retarder_axis(
    psi_deg: ndarray,
    chi_deg: ndarray,
    wavelengths: ndarray,
    title: str = 'Retarder Axis',
    figsize: Tuple[float, float] = (8, 8),
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot retarder axis angles ψ and χ (2×1 subplot).

    Parameters
    ----------
    psi_deg : ndarray
        Fast-axis azimuth in degrees.

    chi_deg : ndarray
        Ellipticity angle in degrees.

    wavelengths : ndarray
        Wavelength values in nm.

    title : str, optional
        Overall figure title.

    figsize : tuple, optional
        Figure size.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure with 2×1 subplots.
    """
    colors = get_publication_colors()

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, facecolor='white')

        # ---------------------------------------------------------------------
        # Subplot 1: Fast-axis azimuth ψ (degrees)
        # ---------------------------------------------------------------------
        ax1.plot(wavelengths, psi_deg, color=colors['cyan'], linewidth=1.5)

        # Reference lines
        ax1.axhline(y=0, color='k', linestyle='--', linewidth=1.0)
        ax1.axhline(y=45, color='b', linestyle='--', linewidth=1.0)
        ax1.axhline(y=-45, color='b', linestyle='--', linewidth=1.0)

        # Labels
        xlim = ax1.get_xlim()
        ax1.text(xlim[1], 0, '  0°', fontsize=12, va='center', color='k')
        ax1.text(xlim[1], 45, '  45°', fontsize=12, va='center', color='b')
        ax1.text(xlim[1], -45, '  -45°', fontsize=12, va='center', color='b')

        ax1.set_xlabel('Wavelength (nm)', fontsize=14)
        ax1.set_ylabel(r'$\psi$ (degrees)', fontsize=14)
        ax1.set_title(f'{title} - Fast-Axis Azimuth (ψ)', fontsize=16, fontweight='bold')
        ax1.set_ylim(-90, 90)
        ax1.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax1.tick_params(axis='both', labelsize=14)

        # ---------------------------------------------------------------------
        # Subplot 2: Ellipticity χ (degrees)
        # ---------------------------------------------------------------------
        ax2.plot(wavelengths, chi_deg, color=colors['magenta'], linewidth=1.5)

        # Reference line for linear retarder
        ax2.axhline(y=0, color='k', linestyle='--', linewidth=1.0)

        # Labels
        xlim = ax2.get_xlim()
        ax2.text(xlim[1], 0, '  Linear (0°)', fontsize=12, va='center', color='k')

        ax2.set_xlabel('Wavelength (nm)', fontsize=14)
        ax2.set_ylabel(r'$\chi$ (degrees)', fontsize=14)
        ax2.set_title(f'{title} - Ellipticity (χ)', fontsize=16, fontweight='bold')
        ax2.set_ylim(-45, 45)
        ax2.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax2.tick_params(axis='both', labelsize=14)

        fig.tight_layout()

    if save_path is not None:
        save_figure(fig, save_path)

    return fig
