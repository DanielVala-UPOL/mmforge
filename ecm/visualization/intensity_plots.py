"""
Intensity Data Visualization

Provides functions to visualize raw intensity measurements:
- Intensity vs wavelength at selected angles
- Intensity vs angle at reference wavelength
- 2D intensity heatmap (angle × wavelength)
- DC component (mean intensity) vs wavelength

These diagnostics help assess data quality before calibration.

References
----------
[1] Compain et al., Appl. Opt. 38, 3490-3502 (1999)
"""

import numpy as np
from numpy import ndarray
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import Optional, Tuple, List
from pathlib import Path

from ecm.visualization.figure_utils import (
    get_publication_colors,
    get_color_cycle,
    save_figure,
    PUBLICATION_RCPARAMS,
)


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def plot_intensity_data(
    intensity: ndarray,
    wavelengths: ndarray,
    omega: Optional[ndarray] = None,
    reference_wl: float = 633.0,
    title: str = 'Intensity Data',
    figsize: Tuple[float, float] = (12, 10),
    save_path: Optional[Path] = None,
    figure_name: str = 'Intensity Data',
) -> Figure:
    """
    Create multi-panel intensity diagnostic plot.

    Creates a 2×2 figure with:
    1. Intensity vs wavelength at selected angles (0°, 90°, 180°, 270°)
    2. Intensity vs angle at reference wavelength
    3. 2D heatmap (intensity map: angle vs wavelength)
    4. DC component (mean over angles) vs wavelength

    Parameters
    ----------
    intensity : ndarray, shape (n_angles, n_wavelengths)
        Raw intensity data.

    wavelengths : ndarray, shape (n_wavelengths,)
        Wavelength values in nm.

    omega : ndarray, shape (n_angles,), optional
        Angular positions in radians. If None, assumes uniform spacing [0, 2π).

    reference_wl : float, optional
        Reference wavelength for single-λ angle plot. Default 633.0 nm.

    title : str, optional
        Overall figure title.

    figsize : tuple, optional
        Figure size. Default (12, 10).

    save_path : Path, optional
        If provided, save figure.

    figure_name : str, optional
        Window title.

    Returns
    -------
    fig : Figure
        Matplotlib figure with 2×2 subplots.

    Examples
    --------
    >>> from ecm.visualization import plot_intensity_data
    >>> import numpy as np
    >>>
    >>> # Load intensity data
    >>> intensity = np.load('calibration_data.npy')
    >>> wavelengths = np.linspace(400, 800, intensity.shape[1])
    >>>
    >>> fig = plot_intensity_data(
    ...     intensity, wavelengths,
    ...     reference_wl=550.0,
    ...     title='Air Measurement'
    ... )
    >>> plt.show()
    """
    # -------------------------------------------------------------------------
    # Input processing
    # -------------------------------------------------------------------------
    intensity = np.asarray(intensity)
    wavelengths = np.asarray(wavelengths)

    n_angles, n_wl = intensity.shape

    # Generate angular positions if not provided
    if omega is None:
        omega = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)

    angles_deg = np.rad2deg(omega)

    # Find reference wavelength index
    ref_idx = np.argmin(np.abs(wavelengths - reference_wl))
    ref_wl_actual = wavelengths[ref_idx]

    # -------------------------------------------------------------------------
    # Create figure
    # -------------------------------------------------------------------------
    colors = get_publication_colors()
    color_cycle = get_color_cycle()

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, axes = plt.subplots(2, 2, figsize=figsize, facecolor='white')

        # ---------------------------------------------------------------------
        # Subplot 1: Intensity vs wavelength at selected angles
        # ---------------------------------------------------------------------
        ax1 = axes[0, 0]

        # Select 4-5 evenly spaced angles
        angle_indices = np.round(np.linspace(0, n_angles - 1, 5)).astype(int)

        for k, idx in enumerate(angle_indices):
            ax1.plot(wavelengths, intensity[idx, :],
                     color=color_cycle[k % len(color_cycle)],
                     linewidth=1.5,
                     label=f'{angles_deg[idx]:.0f}°')

        ax1.set_xlabel('Wavelength (nm)', fontsize=14)
        ax1.set_ylabel('Intensity (a.u.)', fontsize=14)
        ax1.set_title('Spectral Intensity at Selected Angles', fontsize=14)
        ax1.legend(loc='best', fontsize=12)
        ax1.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax1.tick_params(axis='both', labelsize=14)

        # ---------------------------------------------------------------------
        # Subplot 2: Intensity vs angle at reference wavelength
        # ---------------------------------------------------------------------
        ax2 = axes[0, 1]

        ax2.plot(angles_deg, intensity[:, ref_idx],
                 color=colors['blue'], linewidth=1.5)

        ax2.set_xlabel('Angle (degrees)', fontsize=14)
        ax2.set_ylabel('Intensity (a.u.)', fontsize=14)
        ax2.set_title(f'Angular Modulation at {ref_wl_actual:.0f} nm', fontsize=14)
        ax2.set_xlim(0, 360)
        ax2.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax2.tick_params(axis='both', labelsize=14)

        # ---------------------------------------------------------------------
        # Subplot 3: 2D heatmap (intensity map)
        # ---------------------------------------------------------------------
        ax3 = axes[1, 0]

        im = ax3.imshow(
            intensity,
            aspect='auto',
            origin='lower',
            extent=[wavelengths[0], wavelengths[-1], angles_deg[0], angles_deg[-1]],
            cmap='viridis',
        )

        ax3.set_xlabel('Wavelength (nm)', fontsize=14)
        ax3.set_ylabel('Angle (degrees)', fontsize=14)
        ax3.set_title('Intensity Map', fontsize=14)
        ax3.tick_params(axis='both', labelsize=14)

        cbar = fig.colorbar(im, ax=ax3)
        cbar.ax.tick_params(labelsize=12)
        cbar.set_label('Intensity (a.u.)', fontsize=12)

        # ---------------------------------------------------------------------
        # Subplot 4: DC component (mean intensity) vs wavelength
        # ---------------------------------------------------------------------
        ax4 = axes[1, 1]

        dc_component = np.mean(intensity, axis=0)

        ax4.plot(wavelengths, dc_component,
                 color=colors['black'], linewidth=1.5)

        ax4.set_xlabel('Wavelength (nm)', fontsize=14)
        ax4.set_ylabel('Mean Intensity (a.u.)', fontsize=14)
        ax4.set_title('DC Component (Mean over Angles)', fontsize=14)
        ax4.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax4.tick_params(axis='both', labelsize=14)

        # ---------------------------------------------------------------------
        # Overall title
        # ---------------------------------------------------------------------
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)

        fig.tight_layout()
        fig.subplots_adjust(top=0.93)

    # -------------------------------------------------------------------------
    # Save if requested
    # -------------------------------------------------------------------------
    if save_path is not None:
        save_figure(fig, save_path)

    return fig


# =============================================================================
# ADDITIONAL INTENSITY PLOTS
# =============================================================================

def plot_intensity_heatmap(
    intensity: ndarray,
    wavelengths: ndarray,
    omega: Optional[ndarray] = None,
    title: str = 'Intensity Map',
    figsize: Tuple[float, float] = (10, 6),
    cmap: str = 'viridis',
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot 2D intensity heatmap (angle × wavelength).

    Parameters
    ----------
    intensity : ndarray, shape (n_angles, n_wavelengths)
        Intensity data.

    wavelengths : ndarray
        Wavelength values in nm.

    omega : ndarray, optional
        Angular positions in radians.

    title : str, optional
        Plot title.

    figsize : tuple, optional
        Figure size. Default (10, 6).

    cmap : str, optional
        Colormap name. Default 'viridis'.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure.
    """
    intensity = np.asarray(intensity)
    wavelengths = np.asarray(wavelengths)

    n_angles = intensity.shape[0]

    if omega is None:
        omega = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)

    angles_deg = np.rad2deg(omega)

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, ax = plt.subplots(figsize=figsize, facecolor='white')

        im = ax.imshow(
            intensity,
            aspect='auto',
            origin='lower',
            extent=[wavelengths[0], wavelengths[-1], angles_deg[0], angles_deg[-1]],
            cmap=cmap,
        )

        ax.set_xlabel('Wavelength (nm)', fontsize=14)
        ax.set_ylabel('Angle (degrees)', fontsize=14)
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.tick_params(axis='both', labelsize=14)

        cbar = fig.colorbar(im, ax=ax)
        cbar.ax.tick_params(labelsize=12)
        cbar.set_label('Intensity (a.u.)', fontsize=12)

        fig.tight_layout()

    if save_path is not None:
        save_figure(fig, save_path)

    return fig


def plot_intensity_spectrum(
    intensity: ndarray,
    wavelengths: ndarray,
    omega: Optional[ndarray] = None,
    angles_to_plot: Optional[List[float]] = None,
    title: str = 'Spectral Intensity',
    figsize: Tuple[float, float] = (10, 6),
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot intensity vs wavelength at selected angles.

    Parameters
    ----------
    intensity : ndarray, shape (n_angles, n_wavelengths)
        Intensity data.

    wavelengths : ndarray
        Wavelength values in nm.

    omega : ndarray, optional
        Angular positions in radians.

    angles_to_plot : list of float, optional
        Angles in degrees to plot. Default [0, 45, 90, 135, 180].

    title : str, optional
        Plot title.

    figsize : tuple, optional
        Figure size.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure.
    """
    intensity = np.asarray(intensity)
    wavelengths = np.asarray(wavelengths)

    n_angles = intensity.shape[0]

    if omega is None:
        omega = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)

    angles_deg = np.rad2deg(omega)

    if angles_to_plot is None:
        angles_to_plot = [0, 45, 90, 135, 180]

    color_cycle = get_color_cycle()

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, ax = plt.subplots(figsize=figsize, facecolor='white')

        for k, target_angle in enumerate(angles_to_plot):
            # Find closest angle
            idx = np.argmin(np.abs(angles_deg - target_angle))
            actual_angle = angles_deg[idx]

            ax.plot(wavelengths, intensity[idx, :],
                    color=color_cycle[k % len(color_cycle)],
                    linewidth=1.5,
                    label=f'{actual_angle:.0f}°')

        ax.set_xlabel('Wavelength (nm)', fontsize=14)
        ax.set_ylabel('Intensity (a.u.)', fontsize=14)
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.legend(loc='best', fontsize=12)
        ax.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax.tick_params(axis='both', labelsize=14)

        fig.tight_layout()

    if save_path is not None:
        save_figure(fig, save_path)

    return fig


def plot_angular_modulation(
    intensity: ndarray,
    wavelengths: ndarray,
    wavelengths_to_plot: Optional[List[float]] = None,
    omega: Optional[ndarray] = None,
    title: str = 'Angular Modulation',
    figsize: Tuple[float, float] = (10, 6),
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot intensity vs angle at selected wavelengths.

    Parameters
    ----------
    intensity : ndarray, shape (n_angles, n_wavelengths)
        Intensity data.

    wavelengths : ndarray
        Wavelength values in nm.

    wavelengths_to_plot : list of float, optional
        Wavelengths in nm to plot. Default selects 5 evenly spaced.

    omega : ndarray, optional
        Angular positions in radians.

    title : str, optional
        Plot title.

    figsize : tuple, optional
        Figure size.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure.
    """
    intensity = np.asarray(intensity)
    wavelengths = np.asarray(wavelengths)

    n_angles, n_wl = intensity.shape

    if omega is None:
        omega = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)

    angles_deg = np.rad2deg(omega)

    if wavelengths_to_plot is None:
        # Select 5 evenly spaced wavelengths
        wl_indices = np.round(np.linspace(0, n_wl - 1, 5)).astype(int)
        wavelengths_to_plot = wavelengths[wl_indices]

    color_cycle = get_color_cycle()

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, ax = plt.subplots(figsize=figsize, facecolor='white')

        for k, target_wl in enumerate(wavelengths_to_plot):
            # Find closest wavelength
            idx = np.argmin(np.abs(wavelengths - target_wl))
            actual_wl = wavelengths[idx]

            ax.plot(angles_deg, intensity[:, idx],
                    color=color_cycle[k % len(color_cycle)],
                    linewidth=1.5,
                    label=f'{actual_wl:.0f} nm')

        ax.set_xlabel('Angle (degrees)', fontsize=14)
        ax.set_ylabel('Intensity (a.u.)', fontsize=14)
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlim(0, 360)
        ax.legend(loc='best', fontsize=12)
        ax.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax.tick_params(axis='both', labelsize=14)

        fig.tight_layout()

    if save_path is not None:
        save_figure(fig, save_path)

    return fig


def plot_dc_component(
    intensity: ndarray,
    wavelengths: ndarray,
    title: str = 'DC Component',
    figsize: Tuple[float, float] = (10, 6),
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot mean intensity (DC component) vs wavelength.

    Parameters
    ----------
    intensity : ndarray, shape (n_angles, n_wavelengths)
        Intensity data.

    wavelengths : ndarray
        Wavelength values in nm.

    title : str, optional
        Plot title.

    figsize : tuple, optional
        Figure size.

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure.
    """
    intensity = np.asarray(intensity)
    wavelengths = np.asarray(wavelengths)

    dc_component = np.mean(intensity, axis=0)

    colors = get_publication_colors()

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, ax = plt.subplots(figsize=figsize, facecolor='white')

        ax.plot(wavelengths, dc_component,
                color=colors['black'], linewidth=1.5)

        ax.set_xlabel('Wavelength (nm)', fontsize=14)
        ax.set_ylabel('Mean Intensity (a.u.)', fontsize=14)
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.grid(True, linestyle='--', linewidth=0.5, color='0.85')
        ax.tick_params(axis='both', labelsize=14)

        fig.tight_layout()

    if save_path is not None:
        save_figure(fig, save_path)

    return fig
