"""
Figure Utilities for Publication-Quality Plots

Provides consistent styling and formatting for all ECM visualizations,
suitable for publication in high-impact journals (Nature Photonics,
Science Advances, etc.).

Style Guidelines
----------------
- Font size: 14 pt for normal text (labels, ticks, legend)
- Title font size: 16 pt (slightly larger than body text)
- Line width: 1.5 pt
- Figure background: white
- Axes: box style with tick marks
- Grid: light gray, dashed when enabled
- DPI: 300 for saved figures

Color Palette
-------------
The default color palette is designed for:
- Colorblind accessibility
- Clear distinction in grayscale
- Print and screen readability
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import Optional, Tuple, Dict, List, Any
from pathlib import Path
import numpy as np


# =============================================================================
# PUBLICATION STYLE PARAMETERS
# =============================================================================

PUBLICATION_RCPARAMS: Dict[str, Any] = {
    # Font settings
    'font.size': 14,
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],

    # Axes settings
    'axes.labelsize': 14,
    'axes.titlesize': 16,
    'axes.titleweight': 'bold',
    'axes.linewidth': 1.0,
    'axes.spines.top': True,
    'axes.spines.right': True,
    'axes.spines.left': True,
    'axes.spines.bottom': True,

    # Tick settings
    'xtick.labelsize': 14,
    'ytick.labelsize': 14,
    'xtick.major.size': 5,
    'ytick.major.size': 5,
    'xtick.minor.size': 3,
    'ytick.minor.size': 3,
    'xtick.major.width': 1.0,
    'ytick.major.width': 1.0,
    'xtick.direction': 'in',
    'ytick.direction': 'in',

    # Legend settings
    'legend.fontsize': 12,
    'legend.frameon': True,
    'legend.framealpha': 0.9,
    'legend.edgecolor': '0.8',

    # Line settings
    'lines.linewidth': 1.5,
    'lines.markersize': 6,

    # Figure settings
    'figure.facecolor': 'white',
    'figure.edgecolor': 'white',
    'figure.dpi': 100,
    'figure.titlesize': 16,
    'figure.titleweight': 'bold',

    # Saving settings
    'savefig.dpi': 300,
    'savefig.facecolor': 'white',
    'savefig.edgecolor': 'white',
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,

    # Grid settings (when enabled)
    'grid.color': '0.85',
    'grid.linestyle': '--',
    'grid.linewidth': 0.5,
}


# =============================================================================
# COLOR PALETTE
# =============================================================================

def get_publication_colors() -> Dict[str, Tuple[float, float, float]]:
    """
    Return publication-quality color palette.

    Colors are chosen for:
    - Colorblind accessibility (distinguishable by those with color vision deficiency)
    - Clear distinction when printed in grayscale
    - Professional appearance suitable for journals

    Returns
    -------
    colors : dict
        Dictionary mapping color names to RGB tuples (0-1 scale).

    Colors Available
    ----------------
    - 'blue': Primary data color
    - 'orange': Secondary/contrast color
    - 'green': Retardance-related plots
    - 'purple': Depolarization-related plots
    - 'red': Diattenuation-related plots
    - 'cyan': Axis angle ψ
    - 'magenta': Axis angle χ
    - 'gray': Reference lines, secondary data
    - 'black': Text, axes

    Examples
    --------
    >>> colors = get_publication_colors()
    >>> plt.plot(x, y, color=colors['blue'])
    """
    return {
        # Primary colors (MATLAB-like, colorblind-friendly)
        'blue': (0.0000, 0.4470, 0.7410),      # Primary data
        'orange': (0.8500, 0.3250, 0.0980),    # Diattenuation
        'green': (0.4660, 0.6740, 0.1880),     # Retardance
        'purple': (0.4940, 0.1840, 0.5560),    # Depolarization
        'cyan': (0.3010, 0.7450, 0.9330),      # Axis angle ψ
        'magenta': (0.6350, 0.0780, 0.1840),   # Axis angle χ

        # Neutral colors
        'gray': (0.5, 0.5, 0.5),
        'lightgray': (0.75, 0.75, 0.75),
        'black': (0.0, 0.0, 0.0),

        # Additional colors for multi-line plots
        'teal': (0.2, 0.6, 0.8),
        'lime': (0.2, 0.7, 0.4),
        'aqua': (0.15, 0.93, 0.73),
        'violet': (0.58, 0.47, 0.92),
    }


def get_color_cycle() -> List[Tuple[float, float, float]]:
    """
    Return ordered color cycle for multi-line plots.

    Returns
    -------
    colors : list
        List of RGB tuples in recommended order for distinguishability.
    """
    c = get_publication_colors()
    return [
        c['blue'],
        c['orange'],
        c['green'],
        c['purple'],
        c['cyan'],
        c['magenta'],
        c['teal'],
        c['lime'],
    ]


# =============================================================================
# FIGURE SETUP
# =============================================================================

def setup_figure(
    name: str = '',
    figsize: Tuple[float, float] = (8, 6),
    dpi: int = 100,
    apply_style: bool = True,
    **kwargs
) -> Figure:
    """
    Create a figure with publication-quality defaults.

    Parameters
    ----------
    name : str, optional
        Figure window title (not the plot title).

    figsize : tuple, optional
        Figure size in inches (width, height). Default (8, 6).

    dpi : int, optional
        Resolution in dots per inch. Default 100 for screen,
        use 300+ for publication.

    apply_style : bool, optional
        If True, apply PUBLICATION_RCPARAMS. Default True.

    **kwargs : dict
        Additional keyword arguments passed to plt.figure().

    Returns
    -------
    fig : Figure
        Matplotlib figure with publication styling.

    Examples
    --------
    >>> fig = setup_figure('Mueller Matrix', figsize=(12, 10))
    >>> ax = fig.add_subplot(111)
    >>> ax.plot(wavelengths, data)
    >>> fig.savefig('output.png')
    """
    if apply_style:
        # Temporarily apply publication style
        with mpl.rc_context(PUBLICATION_RCPARAMS):
            fig = plt.figure(
                num=name if name else None,
                figsize=figsize,
                dpi=dpi,
                facecolor='white',
                edgecolor='white',
                **kwargs
            )
    else:
        fig = plt.figure(
            num=name if name else None,
            figsize=figsize,
            dpi=dpi,
            facecolor='white',
            edgecolor='white',
            **kwargs
        )

    return fig


def apply_publication_style():
    """
    Apply publication style globally to all subsequent plots.

    Call this at the beginning of a script to set consistent styling
    for all figures. Can be reverted with plt.rcdefaults().

    Examples
    --------
    >>> apply_publication_style()
    >>> # All subsequent plots will use publication styling
    >>> fig, ax = plt.subplots()
    >>> ax.plot(x, y)
    """
    plt.rcParams.update(PUBLICATION_RCPARAMS)


# =============================================================================
# AXES FORMATTING
# =============================================================================

def format_axes(
    ax: Axes,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    title: Optional[str] = None,
    xlim: Optional[Tuple[float, float]] = None,
    ylim: Optional[Tuple[float, float]] = None,
    grid: bool = True,
    legend: bool = False,
    legend_loc: str = 'best',
    fontsize: int = 14,
    title_fontsize: int = 16,
) -> Axes:
    """
    Apply consistent formatting to axes.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes to format.

    xlabel : str, optional
        X-axis label.

    ylabel : str, optional
        Y-axis label.

    title : str, optional
        Axes title.

    xlim : tuple, optional
        X-axis limits (min, max).

    ylim : tuple, optional
        Y-axis limits (min, max).

    grid : bool, optional
        Whether to show grid. Default True.

    legend : bool, optional
        Whether to show legend. Default False.

    legend_loc : str, optional
        Legend location. Default 'best'.

    fontsize : int, optional
        Font size for labels and ticks. Default 14.

    title_fontsize : int, optional
        Font size for title. Default 16.

    Returns
    -------
    ax : Axes
        The formatted axes (same object, modified in place).

    Examples
    --------
    >>> fig, ax = plt.subplots()
    >>> ax.plot(wavelengths, M[0, 0, :])
    >>> format_axes(ax, xlabel='Wavelength (nm)', ylabel='m₁₁', grid=True)
    """
    if xlabel is not None:
        ax.set_xlabel(xlabel, fontsize=fontsize)

    if ylabel is not None:
        ax.set_ylabel(ylabel, fontsize=fontsize)

    if title is not None:
        ax.set_title(title, fontsize=title_fontsize, fontweight='bold')

    if xlim is not None:
        ax.set_xlim(xlim)

    if ylim is not None:
        ax.set_ylim(ylim)

    # Tick formatting
    ax.tick_params(axis='both', which='major', labelsize=fontsize)
    ax.tick_params(axis='both', which='minor', labelsize=fontsize - 2)

    # Grid
    if grid:
        ax.grid(True, linestyle='--', linewidth=0.5, color='0.85', alpha=0.7)

    # Legend
    if legend:
        ax.legend(loc=legend_loc, fontsize=fontsize - 2)

    return ax


def add_reference_line(
    ax: Axes,
    value: float,
    orientation: str = 'horizontal',
    label: Optional[str] = None,
    color: str = 'k',
    linestyle: str = '--',
    linewidth: float = 1.0,
    fontsize: int = 12,
    label_position: str = 'right',
) -> None:
    """
    Add a reference line to axes.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes.

    value : float
        Position of the reference line.

    orientation : str, optional
        'horizontal' or 'vertical'. Default 'horizontal'.

    label : str, optional
        Text label for the reference line.

    color : str, optional
        Line color. Default 'k' (black).

    linestyle : str, optional
        Line style. Default '--' (dashed).

    linewidth : float, optional
        Line width. Default 1.0.

    fontsize : int, optional
        Label font size. Default 12.

    label_position : str, optional
        Position for label: 'left', 'right', 'top', 'bottom'. Default 'right'.

    Examples
    --------
    >>> add_reference_line(ax, 90, label='QWP (90°)', color='blue')
    >>> add_reference_line(ax, 180, label='HWP (180°)', color='red')
    """
    if orientation == 'horizontal':
        line = ax.axhline(y=value, color=color, linestyle=linestyle,
                          linewidth=linewidth, zorder=1)
        if label is not None:
            xlim = ax.get_xlim()
            if label_position == 'right':
                x_pos = xlim[1] - 0.02 * (xlim[1] - xlim[0])
                ha = 'right'
            else:
                x_pos = xlim[0] + 0.02 * (xlim[1] - xlim[0])
                ha = 'left'
            ax.text(x_pos, value, f'  {label}', fontsize=fontsize,
                    va='center', ha=ha, color=color)
    else:
        line = ax.axvline(x=value, color=color, linestyle=linestyle,
                          linewidth=linewidth, zorder=1)
        if label is not None:
            ylim = ax.get_ylim()
            if label_position == 'top':
                y_pos = ylim[1] - 0.02 * (ylim[1] - ylim[0])
                va = 'top'
            else:
                y_pos = ylim[0] + 0.02 * (ylim[1] - ylim[0])
                va = 'bottom'
            ax.text(value, y_pos, f' {label}', fontsize=fontsize,
                    va=va, ha='left', color=color, rotation=90)


# =============================================================================
# SAVE UTILITIES
# =============================================================================

def save_figure(
    fig: Figure,
    path: Path,
    dpi: int = 300,
    formats: Optional[List[str]] = None,
    tight: bool = True,
) -> List[Path]:
    """
    Save figure to file(s) with publication settings.

    Parameters
    ----------
    fig : Figure
        Matplotlib figure to save.

    path : Path
        Output path. Extension determines format unless `formats` specified.

    dpi : int, optional
        Resolution in dots per inch. Default 300.

    formats : list, optional
        List of formats to save (e.g., ['png', 'pdf', 'svg']).
        If None, uses extension from path.

    tight : bool, optional
        Use tight bounding box. Default True.

    Returns
    -------
    saved_paths : list
        List of paths where files were saved.

    Examples
    --------
    >>> save_figure(fig, Path('output/mueller_matrix.png'))
    >>> save_figure(fig, Path('output/fig1'), formats=['png', 'pdf', 'svg'])
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    saved_paths = []

    if formats is None:
        # Use extension from path
        formats = [path.suffix.lstrip('.') or 'png']
        base_path = path.with_suffix('')
    else:
        base_path = path

    bbox_inches = 'tight' if tight else None

    for fmt in formats:
        out_path = base_path.with_suffix(f'.{fmt}')
        fig.savefig(
            out_path,
            dpi=dpi,
            facecolor='white',
            edgecolor='white',
            bbox_inches=bbox_inches,
            pad_inches=0.1,
        )
        saved_paths.append(out_path)

    return saved_paths
