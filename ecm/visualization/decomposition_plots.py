"""
Decomposed Mueller Matrix Visualization

Provides functions to plot the Lu-Chipman decomposed matrices:
- M_D (Diattenuator)
- M_R (Retarder)
- M_Δ (Depolarizer)

Each decomposed matrix is plotted as a 4×4 grid of elements vs wavelength,
similar to plot_mueller_matrix but with color coding by matrix type.

References
----------
[1] Lu & Chipman, J. Opt. Soc. Am. A 13, 1106-1113 (1996)
"""

import numpy as np
from numpy import ndarray
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.figure import Figure
from typing import Optional, Tuple, Dict, Literal
from pathlib import Path

from ecm.postprocessing.lu_chipman import LuChipmanResult
from ecm.visualization.figure_utils import (
    get_publication_colors,
    save_figure,
    PUBLICATION_RCPARAMS,
)


# =============================================================================
# MATRIX TYPE CONFIGURATION
# =============================================================================

MATRIX_CONFIG = {
    'D': {
        'symbol': 'M_D',
        'symbol_tex': r'$M_D$',
        'title': 'Diattenuation',
        'color_key': 'orange',
    },
    'R': {
        'symbol': 'M_R',
        'symbol_tex': r'$M_R$',
        'title': 'Retardation',
        'color_key': 'green',
    },
    'Delta': {
        'symbol': 'M_Δ',
        'symbol_tex': r'$M_\Delta$',
        'title': 'Depolarization',
        'color_key': 'purple',
    },
}


# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

def plot_decomposed_matrices(
    lu_result: LuChipmanResult,
    wavelengths: ndarray,
    sample_name: str = '',
    save_dir: Optional[Path] = None,
    figsize: Tuple[float, float] = (12, 10),
) -> Dict[str, Figure]:
    """
    Plot all three decomposed Mueller matrices (M_D, M_R, M_Δ).

    Parameters
    ----------
    lu_result : LuChipmanResult
        Output from lu_chipman_decomposition().

    wavelengths : ndarray
        Wavelength values in nm.

    sample_name : str, optional
        Sample name for figure titles.

    save_dir : Path, optional
        If provided, save figures to this directory.
        Filenames: M_D.png, M_R.png, M_Delta.png

    figsize : tuple, optional
        Figure size for each matrix plot. Default (12, 10).

    Returns
    -------
    figures : dict
        Dictionary with keys 'M_D', 'M_R', 'M_Delta' mapping to figures.

    Examples
    --------
    >>> from ecm.postprocessing import lu_chipman_decomposition
    >>> from ecm.visualization import plot_decomposed_matrices
    >>>
    >>> result = lu_chipman_decomposition(M_normalized)
    >>> figures = plot_decomposed_matrices(
    ...     result, wavelengths, sample_name='QWP',
    ...     save_dir=Path('output')
    ... )
    """
    figures = {}

    # Create save directory if needed
    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

    # Plot each decomposed matrix
    matrices = {
        'M_D': ('D', lu_result.M_D),
        'M_R': ('R', lu_result.M_R),
        'M_Delta': ('Delta', lu_result.M_Delta),
    }

    for key, (matrix_type, M) in matrices.items():
        fig = plot_decomposed_matrix(
            M=M,
            wavelengths=wavelengths,
            matrix_type=matrix_type,
            sample_name=sample_name,
            figsize=figsize,
            save_path=save_dir / f'{key}.png' if save_dir else None,
        )
        figures[key] = fig

    return figures


def plot_decomposed_matrix(
    M: ndarray,
    wavelengths: ndarray,
    matrix_type: Literal['D', 'R', 'Delta'],
    sample_name: str = '',
    figsize: Tuple[float, float] = (12, 10),
    save_path: Optional[Path] = None,
    figure_name: Optional[str] = None,
) -> Figure:
    """
    Plot a single decomposed Mueller matrix as 4×4 subplot grid.

    Parameters
    ----------
    M : ndarray, shape (4, 4) or (4, 4, n_wavelengths)
        Decomposed Mueller matrix (M_D, M_R, or M_Δ).

    wavelengths : ndarray
        Wavelength values in nm.

    matrix_type : {'D', 'R', 'Delta'}
        Type of decomposed matrix:
        - 'D': Diattenuator (M_D) - orange color
        - 'R': Retarder (M_R) - green color
        - 'Delta': Depolarizer (M_Δ) - purple color

    sample_name : str, optional
        Sample name for title.

    figsize : tuple, optional
        Figure size. Default (12, 10).

    save_path : Path, optional
        If provided, save figure.

    figure_name : str, optional
        Window title for figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure.

    Examples
    --------
    >>> fig = plot_decomposed_matrix(
    ...     result.M_R, wavelengths, 'R',
    ...     sample_name='QWP', save_path=Path('M_R.png')
    ... )
    """
    # Validate matrix type
    if matrix_type not in MATRIX_CONFIG:
        raise ValueError(
            f"matrix_type must be 'D', 'R', or 'Delta', got '{matrix_type}'"
        )

    config = MATRIX_CONFIG[matrix_type]
    colors = get_publication_colors()
    line_color = colors[config['color_key']]

    # -------------------------------------------------------------------------
    # Input validation
    # -------------------------------------------------------------------------
    M = np.asarray(M)

    if M.ndim == 2:
        M = M[:, :, np.newaxis]

    if M.shape[:2] != (4, 4):
        raise ValueError(f"M must be 4×4 or 4×4×n_wavelengths, got shape {M.shape}")

    n_wl = M.shape[2]
    wavelengths = np.asarray(wavelengths)

    if len(wavelengths) != n_wl:
        raise ValueError(
            f"Wavelength length ({len(wavelengths)}) doesn't match M ({n_wl})"
        )

    # -------------------------------------------------------------------------
    # Build title
    # -------------------------------------------------------------------------
    if sample_name:
        display_name = sample_name.replace('_', ' ')
        fig_title = f'{display_name} - {config["title"]} ({config["symbol"]})'
    else:
        fig_title = f'{config["title"]} ({config["symbol"]})'

    if figure_name is None:
        figure_name = f'{sample_name} {config["symbol"]}' if sample_name else config["symbol"]

    # -------------------------------------------------------------------------
    # Create figure
    # -------------------------------------------------------------------------
    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, axes = plt.subplots(
            4, 4,
            figsize=figsize,
            sharex=True,
            num=figure_name,
            facecolor='white',
        )

        # Build element labels using mathtext
        # Use symbol_tex base and add indices (e.g., $M_D$ becomes $(M_D)_{11}$)
        symbol_tex = config['symbol_tex']  # e.g., r'$M_D$'
        # Remove outer $ signs to get inner tex, then build proper label
        symbol_inner = symbol_tex.strip('$')  # e.g., 'M_D'

        for i in range(4):
            for j in range(4):
                ax = axes[i, j]

                # Extract element
                element = np.squeeze(M[i, j, :])

                # Plot
                ax.plot(wavelengths, element, color=line_color, linewidth=1.5)

                # Element label as title (mathtext format with grouped symbol)
                label = r'$({%s})_{%d%d}$' % (symbol_inner, i+1, j+1)
                ax.set_title(label, fontsize=14)

                # Grid
                ax.grid(True, linestyle='--', linewidth=0.5, color='0.85')

                # Y-axis limits based on expected values
                if i == 0 and j == 0:
                    ax.set_ylim(0.9, 1.1)  # Diagonal should be ~1
                else:
                    ax.set_ylim(-1.1, 1.1)

                # X-axis label only on bottom row
                if i == 3:
                    ax.set_xlabel('Wavelength (nm)', fontsize=12)

                ax.tick_params(axis='both', labelsize=10)

        # Overall title
        fig.suptitle(fig_title, fontsize=16, fontweight='bold', y=0.98)

        fig.tight_layout()
        fig.subplots_adjust(top=0.93)

    # -------------------------------------------------------------------------
    # Save if requested
    # -------------------------------------------------------------------------
    if save_path is not None:
        save_figure(fig, save_path)

    return fig


def plot_decomposition_summary(
    lu_result: LuChipmanResult,
    wavelengths: ndarray,
    sample_name: str = '',
    figsize: Tuple[float, float] = (14, 10),
    save_path: Optional[Path] = None,
) -> Figure:
    """
    Create summary plot showing key elements from all decomposed matrices.

    Plots a 3×4 grid showing diagonal elements (m₁₁, m₂₂, m₃₃, m₄₄) from
    M_D, M_R, and M_Δ for quick validation of the decomposition.

    Parameters
    ----------
    lu_result : LuChipmanResult
        Output from lu_chipman_decomposition().

    wavelengths : ndarray
        Wavelength values in nm.

    sample_name : str, optional
        Sample name for title.

    figsize : tuple, optional
        Figure size. Default (14, 10).

    save_path : Path, optional
        If provided, save figure.

    Returns
    -------
    fig : Figure
        Matplotlib figure.
    """
    colors = get_publication_colors()

    matrices = [
        ('D', lu_result.M_D, colors['orange']),
        ('R', lu_result.M_R, colors['green']),
        ('Delta', lu_result.M_Delta, colors['purple']),
    ]

    with mpl.rc_context(PUBLICATION_RCPARAMS):
        fig, axes = plt.subplots(3, 4, figsize=figsize, sharex=True, facecolor='white')

        for row, (mtype, M, color) in enumerate(matrices):
            config = MATRIX_CONFIG[mtype]
            # Get the inner tex symbol (e.g., 'M_D' from '$M_D$')
            symbol_inner = config['symbol_tex'].strip('$')

            # Ensure 3D
            if M.ndim == 2:
                M = M[:, :, np.newaxis]

            for col in range(4):
                ax = axes[row, col]

                # Plot diagonal element
                element = np.squeeze(M[col, col, :])
                ax.plot(wavelengths, element, color=color, linewidth=1.5)

                # Title with matrix and element (mathtext format with grouped symbol)
                label = r'$({%s})_{%d%d}$' % (symbol_inner, col+1, col+1)
                ax.set_title(label, fontsize=12)

                # Grid
                ax.grid(True, linestyle='--', linewidth=0.5, color='0.85')

                # Expected range for diagonal
                ax.set_ylim(0.5, 1.1)

                if row == 2:
                    ax.set_xlabel('Wavelength (nm)', fontsize=11)

                if col == 0:
                    ax.set_ylabel(config['title'], fontsize=11)

                ax.tick_params(axis='both', labelsize=10)

        # Overall title
        if sample_name:
            display_name = sample_name.replace('_', ' ')
            fig.suptitle(f'{display_name} - Decomposition Diagonal Elements',
                         fontsize=16, fontweight='bold', y=0.98)
        else:
            fig.suptitle('Lu-Chipman Decomposition - Diagonal Elements',
                         fontsize=16, fontweight='bold', y=0.98)

        fig.tight_layout()
        fig.subplots_adjust(top=0.92)

    if save_path is not None:
        save_figure(fig, save_path)

    return fig
