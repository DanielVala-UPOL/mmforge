"""
Mueller Matrix Visualization

Provides functions to plot Mueller matrix elements as functions of wavelength
in publication-quality 4×4 subplot grids.

Functions
---------
plot_mueller_matrix(M, wavelengths, ...)
    Create 4×4 subplot grid of all 16 Mueller matrix elements

plot_mueller_element(M, wavelengths, i, j, ...)
    Plot a single Mueller matrix element

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
from typing import Optional, Tuple, Union
from pathlib import Path

from ecm.visualization.figure_utils import (
    setup_figure,
    format_axes,
    get_publication_colors,
    save_figure,
    PUBLICATION_RCPARAMS,
)


# =============================================================================
# ELEMENT LABELS
# =============================================================================

def _get_element_labels(normalized: bool = True) -> list:
    """
    Get Mueller matrix element labels using mathtext for proper rendering.

    Parameters
    ----------
    normalized : bool
        If True, use lowercase (m_ij).
        If False, use uppercase (M_ij).

    Returns
    -------
    labels : list of list
        4x4 nested list of label strings (mathtext format).
    """
    prefix = 'm' if normalized else 'M'

    labels = []
    for i in range(4):
        row = []
        for j in range(4):
            label = r'$%s_{%d%d}$' % (prefix, i+1, j+1)
            row.append(label)
        labels.append(row)

    return labels


# =============================================================================
# MAIN PLOTTING FUNCTIONS
# =============================================================================

def plot_mueller_matrix(
    M: ndarray,
    wavelengths: ndarray,
    title: str = '',
    normalized: bool = True,
    figsize: Tuple[float, float] = (12, 10),
    line_color: Optional[Tuple[float, float, float]] = None,
    show_grid: bool = True,
    y_limits: Optional[Union[Tuple[float, float], str]] = 'auto',
    save_path: Optional[Path] = None,
    figure_name: str = 'Mueller Matrix',
) -> Figure:
    """
    Plot all 16 Mueller matrix elements vs wavelength in 4×4 subplot grid.

    Parameters
    ----------
    M : ndarray, shape (4, 4, n_wavelengths)
        Mueller matrices to plot. Third axis is wavelength.

    wavelengths : ndarray, shape (n_wavelengths,)
        Wavelength values in nm.

    title : str, optional
        Figure title (super title above all subplots).

    normalized : bool, optional
        If True, use lowercase labels (mᵢⱼ) and set appropriate y-limits.
        If False, use uppercase labels (Mᵢⱼ). Default True.

    figsize : tuple, optional
        Figure size in inches (width, height). Default (12, 10).

    line_color : tuple, optional
        RGB color tuple for lines. If None, uses default blue.

    show_grid : bool, optional
        Whether to show grid on subplots. Default True.

    y_limits : tuple or 'auto', optional
        Y-axis limits (ymin, ymax) for all subplots.
        If 'auto', uses [-1.1, 1.1] for off-diagonal and appropriate
        limits for diagonal elements when normalized. Default 'auto'.

    save_path : Path, optional
        If provided, save figure to this path.

    figure_name : str, optional
        Window title for figure. Default 'Mueller Matrix'.

    Returns
    -------
    fig : Figure
        Matplotlib figure containing the 4×4 subplot grid.

    Examples
    --------
    >>> import numpy as np
    >>> from ecm.visualization import plot_mueller_matrix
    >>> from ecm.utils.mueller_matrices import retarder
    >>>
    >>> # Create wavelength-dependent Mueller matrix
    >>> wavelengths = np.linspace(400, 800, 100)
    >>> M = np.zeros((4, 4, len(wavelengths)))
    >>> for i, wl in enumerate(wavelengths):
    ...     delta = np.pi / 2 * (600 / wl)  # Dispersion
    ...     M[:, :, i] = retarder(0, delta, 1.0)
    >>>
    >>> fig = plot_mueller_matrix(M, wavelengths, title='QWP Mueller Matrix')
    >>> plt.show()
    """
    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    M = np.asarray(M)
    wavelengths = np.asarray(wavelengths)

    if M.ndim == 2:
        # Single wavelength
        M = M[:, :, np.newaxis]
        wavelengths = np.array([wavelengths]) if wavelengths.ndim == 0 else wavelengths

    if M.shape[:2] != (4, 4):
        raise ValueError(f"M must be 4×4×n_wavelengths, got shape {M.shape}")

    n_wl = M.shape[2]
    if len(wavelengths) != n_wl:
        raise ValueError(
            f"Wavelength vector length ({len(wavelengths)}) does not match "
            f"M dimension ({n_wl})"
        )

    # -------------------------------------------------------------------------
    # Setup colors and labels
    # -------------------------------------------------------------------------
    colors = get_publication_colors()
    if line_color is None:
        line_color = colors['blue']

    labels = _get_element_labels(normalized)

    # -------------------------------------------------------------------------
    # Create figure with publication styling
    # -------------------------------------------------------------------------
    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, axes = plt.subplots(
            4, 4,
            figsize=figsize,
            sharex=True,
            num=figure_name,
            facecolor='white',
        )

        # Plot each element
        for i in range(4):
            for j in range(4):
                ax = axes[i, j]

                # Extract element
                element = np.squeeze(M[i, j, :])

                # Plot
                ax.plot(wavelengths, element, color=line_color, linewidth=1.5)

                # Title (element label)
                ax.set_title(labels[i][j], fontsize=14, fontweight='normal')

                # Grid
                if show_grid:
                    ax.grid(True, linestyle='--', linewidth=0.5,
                            color='0.85', alpha=0.7)

                # Y-axis limits
                if y_limits == 'auto':
                    if normalized:
                        if i == 0 and j == 0:
                            ax.set_ylim(0.95, 1.05)  # m₁₁ should be 1
                        else:
                            ax.set_ylim(-1.1, 1.1)
                    # For unnormalized, let matplotlib auto-scale
                elif y_limits is not None:
                    ax.set_ylim(y_limits)

                # X-axis label only on bottom row
                if i == 3:
                    ax.set_xlabel('Wavelength (nm)', fontsize=12)

                # Font size for tick labels
                ax.tick_params(axis='both', labelsize=10)

        # Overall title
        if title:
            fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)

        # Adjust layout
        fig.tight_layout()
        if title:
            fig.subplots_adjust(top=0.93)

    # -------------------------------------------------------------------------
    # Save if requested
    # -------------------------------------------------------------------------
    if save_path is not None:
        save_figure(fig, save_path)

    return fig


def plot_mueller_element(
    M: ndarray,
    wavelengths: ndarray,
    i: int,
    j: int,
    ax: Optional[Axes] = None,
    normalized: bool = True,
    line_color: Optional[Tuple[float, float, float]] = None,
    linewidth: float = 1.5,
    label: Optional[str] = None,
    show_grid: bool = True,
    **kwargs
) -> Axes:
    """
    Plot a single Mueller matrix element vs wavelength.

    Parameters
    ----------
    M : ndarray, shape (4, 4, n_wavelengths)
        Mueller matrices.

    wavelengths : ndarray
        Wavelength values in nm.

    i, j : int
        Element indices (0-indexed). i is row, j is column.

    ax : Axes, optional
        If None, create new figure and axes.

    normalized : bool, optional
        Affects label styling. Default True.

    line_color : tuple, optional
        RGB color tuple. If None, uses default blue.

    linewidth : float, optional
        Line width. Default 1.5.

    label : str, optional
        Legend label. If None, uses element name.

    show_grid : bool, optional
        Whether to show grid. Default True.

    **kwargs : dict
        Additional keyword arguments passed to ax.plot().

    Returns
    -------
    ax : Axes
        The axes with the plot.

    Examples
    --------
    >>> fig, ax = plt.subplots()
    >>> plot_mueller_element(M, wavelengths, 1, 0, ax=ax, label='Sample A')
    >>> plot_mueller_element(M2, wavelengths, 1, 0, ax=ax, label='Sample B')
    >>> ax.legend()
    """
    M = np.asarray(M)
    wavelengths = np.asarray(wavelengths)

    if M.ndim == 2:
        M = M[:, :, np.newaxis]

    # Validate indices
    if not (0 <= i < 4 and 0 <= j < 4):
        raise ValueError(f"Indices must be in [0, 3], got i={i}, j={j}")

    # Create axes if needed
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    else:
        fig = ax.figure

    # Setup color
    colors = get_publication_colors()
    if line_color is None:
        line_color = colors['blue']

    # Element data
    element = np.squeeze(M[i, j, :])

    # Default label
    if label is None:
        labels = _get_element_labels(normalized)
        label = labels[i][j]

    # Plot
    ax.plot(wavelengths, element, color=line_color, linewidth=linewidth,
            label=label, **kwargs)

    # Formatting
    ax.set_xlabel('Wavelength (nm)', fontsize=14)
    ax.set_ylabel(label, fontsize=14)
    ax.tick_params(axis='both', labelsize=14)

    if show_grid:
        ax.grid(True, linestyle='--', linewidth=0.5, color='0.85', alpha=0.7)

    return ax


def plot_mueller_matrix_comparison(
    M_list: list,
    wavelengths: ndarray,
    labels: list,
    title: str = '',
    figsize: Tuple[float, float] = (14, 12),
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Plot multiple Mueller matrices overlaid for comparison.

    Parameters
    ----------
    M_list : list of ndarray
        List of Mueller matrices, each shape (4, 4, n_wavelengths).

    wavelengths : ndarray
        Wavelength values in nm (same for all matrices).

    labels : list of str
        Legend labels for each matrix.

    title : str, optional
        Figure title.

    figsize : tuple, optional
        Figure size in inches.

    save_path : Path, optional
        If provided, save figure to this path.

    Returns
    -------
    fig : Figure
        Matplotlib figure.

    Examples
    --------
    >>> fig = plot_mueller_matrix_comparison(
    ...     [M_measured, M_theory],
    ...     wavelengths,
    ...     ['Measured', 'Theory'],
    ...     title='QWP Comparison'
    ... )
    """
    colors = get_publication_colors()
    color_list = [
        colors['blue'],
        colors['orange'],
        colors['green'],
        colors['purple'],
        colors['cyan'],
    ]

    element_labels = _get_element_labels(normalized=True)

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, axes = plt.subplots(4, 4, figsize=figsize, sharex=True,
                                 facecolor='white')

        for i in range(4):
            for j in range(4):
                ax = axes[i, j]

                for k, M in enumerate(M_list):
                    element = np.squeeze(M[i, j, :])
                    color = color_list[k % len(color_list)]
                    ax.plot(wavelengths, element, color=color, linewidth=1.5,
                            label=labels[k] if (i == 0 and j == 0) else None)

                ax.set_title(element_labels[i][j], fontsize=12)
                ax.grid(True, linestyle='--', linewidth=0.5, color='0.85')

                if i == 3:
                    ax.set_xlabel('Wavelength (nm)', fontsize=10)

                ax.tick_params(axis='both', labelsize=9)

                # Y-limits for normalized
                if i == 0 and j == 0:
                    ax.set_ylim(0.9, 1.1)
                else:
                    ax.set_ylim(-1.1, 1.1)

        # Legend in first subplot
        axes[0, 0].legend(loc='upper right', fontsize=10)

        if title:
            fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)

        fig.tight_layout()
        if title:
            fig.subplots_adjust(top=0.93)

    if save_path is not None:
        save_figure(fig, save_path)

    return fig
