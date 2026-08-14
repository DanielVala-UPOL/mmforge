"""
Plotly Plot Components - Interactive visualization functions.

Provides interactive Plotly plots for:
- Mueller matrix 4x4 grid
- Eigenvalue ratio analysis
- Lu-Chipman parameters
- Decomposed matrices

All plots feature:
- ~1.5x larger fonts for readability
- Grid lines (except Quality Breakdown)
- Subscript labels for matrix elements

Author: Daniel Vala
"""

# ============================================================================
# PLOT STYLING STANDARDS (for Phase 5 implementation)
# ============================================================================
# - Font sizes: FONT_SIZE_* constants defined below
# - Grid: Always show grid (except Quality Breakdown)
# - No box frames around plots
# - trace_colors()[0] for single traces, trace_colors() for multi-sample overlays
# - Wavelength on x-axis with label "Wavelength (nm)"
# - Y-axis labels specific to parameter (e.g., "DI", "R (deg)", "ν (deg)")
# - Use subscript HTML format for matrix elements (M<sub>11</sub>)
# - Angle parameter ψ from ECM should be displayed as ν in the GUI

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from numpy import ndarray
from typing import Optional, List, Tuple, Dict

from utils.theme import palette, is_dark, rgba, HEATMAP_COLORSCALE


# ============================================================================
# COMMON STYLING CONSTANTS
# ============================================================================

# ----------------------------------------------------------------------------
# Global typography
# ----------------------------------------------------------------------------
FONT_SIZE_BASE = 20
FONT_SIZE_TITLE = 22
FONT_SIZE_AXIS_TITLE = 20
FONT_SIZE_TICK = 20            # ~25% larger than the historical 16
FONT_SIZE_SUBPLOT_TITLE = 22   # M_ij / m_ij labels on Mueller grids — bumped
FONT_SIZE_LEGEND = 22          # bumped ~44% from 18 per user request

# How far (px) to lift `make_subplots` subplot titles above the top edge
# of each subplot's box. Without this, Plotly anchors them at y=top of
# the subplot domain (yanchor='bottom'), so the text sits *on* the box
# edge and overlaps the top y-tick.
SUBPLOT_TITLE_YSHIFT = 12

# ----------------------------------------------------------------------------
# Global axis-frame styling (applied by ``apply_common_styling``)
# ----------------------------------------------------------------------------
# Every "data plot" (i.e. anything except the QualityBreakdown bar chart)
# gets a thin rectangular box around its plot area — Plotly's
# ``showline=True, mirror=True`` combination. For ``make_subplots``
# figures, each subplot gets its own box. The box is black in light mode
# and a muted grey in dark: the *width* is fixed here, the *colour* comes
# from the active palette (see ``chart_axis`` below).
AXIS_BOX_WIDTH = 1.2

# Grid styling
GRID_WIDTH = 1

# Layout margins / legend (sized so the legend below the plot doesn't
# overlap the x-axis title even on small Streamlit windows).
MARGIN_DEFAULT = dict(l=70, r=40, t=80, b=140)
LEGEND_Y_OFFSET = -0.24

# ============================================================================
# MMFORGE COLOR PALETTE
# ============================================================================
# Colours are deliberately *not* module constants any more. They are looked
# up per call from the theme that is active in the current script run
# (streamlit_app/utils/theme.py). A constant evaluated at import time would
# freeze whichever theme happened to be active the first time the module was
# imported, and Streamlit imports a module once per process, not once per
# session — so every later session, and every theme switch, would get the
# wrong palette.
#
# The light values these functions return are exactly the literals that used
# to sit here; the light theme does not move.


def primary_color() -> str:
    """The brand accent, for figures that need the house colour."""
    return palette()['primary']


def quality_colors() -> Dict[str, str]:
    """Calibration-quality tier colours, keyed 'excellent' … 'poor'."""
    return palette()['quality']


def trace_colors() -> List[str]:
    """The 16-entry multi-sample trace sequence for the active theme."""
    return palette()['traces']


def _trace(idx: int) -> str:
    """Trace colour for series ``idx``, cycling through the sequence."""
    seq = trace_colors()
    return seq[idx % len(seq)]


def _ink() -> str:
    """Colour for the curves that are drawn in plain black in light mode.

    The eigenvalue-ratio trace and the purity-space boundary curves (with
    their matching bold zerolines) are black on white today. Black is
    *data* ink there, not chrome, so on a near-black panel it becomes the
    bright chart text colour rather than the dim axis colour — the axis
    grey would leave the main curve barely readable. In light mode this
    returns the same '#000000' those curves have always used.
    """
    p = palette()
    return p['chart_text'] if is_dark() else p['chart_axis']


def apply_common_styling(fig, show_grid=True, show_box=True):
    """Apply MMForge's global plot styling.

    Single source of truth for typography, axis frame, gridlines, margins,
    legend, and hover styling. **Every plot helper in this module must
    call this once at the end** so the GUI stays visually consistent.

    Two styling modes
    -----------------
    *Data-plot mode* (``show_box=True``, the default) — for everything
    in the app *except* the Quality Breakdown bar chart. Draws a thin
    rectangular box around every axis (a real box, not just a
    single line: ``showline=True, mirror=True`` on both axes). For a
    ``make_subplots`` figure this puts a box around *each* subplot
    individually, not the whole figure. Ticks sit outside the plot
    area for a publication-quality look.

    *Chart mode* (``show_box=False``) — used by the Quality Breakdown
    horizontal bar chart. Single, lightweight bottom + left lines in
    the border colour (a soft gray in light mode), no mirror, inside
    ticks, smaller tick font. Visually matches the original
    (pre-v2.0-styling) chart appearance.

    Every colour here comes from the active theme's palette; the
    geometry — sizes, margins, tick lengths — does not change with it.

    Subplot titles
    --------------
    After applying axes, any annotations already present on the figure
    (the ``M_ij`` / ``m_ij`` labels created by ``make_subplots`` via
    ``subplot_titles=...``) are bumped to ``FONT_SIZE_SUBPLOT_TITLE``.
    Custom annotations added *after* this call (e.g. the centered
    "Wavelength (nm)" label below a Mueller grid) keep their own font
    settings.

    Parameters
    ----------
    fig : go.Figure
        Plotly figure to style.
    show_grid : bool
        Whether to show grid lines (default True; False for bar charts).
    show_box : bool
        True (default): draw a black rectangular box around the plot
        area. False: lightweight bottom + left axis lines only.

    Returns
    -------
    fig : go.Figure
        The styled figure (also mutated in place).
    """
    p = palette()

    # Layout: typography, backgrounds, margins, legend, hover.
    fig.update_layout(
        font=dict(
            family='Arial, sans-serif',
            size=FONT_SIZE_BASE,
            color=p['chart_text'],
        ),
        title_font=dict(size=FONT_SIZE_TITLE),
        paper_bgcolor=p['chart_bg'],
        plot_bgcolor=p['chart_bg'],
        margin=MARGIN_DEFAULT,
        legend=dict(
            orientation='h',
            yanchor='top',
            y=LEGEND_Y_OFFSET,
            xanchor='center',
            x=0.5,
            bgcolor=rgba(p['chart_panel'], 0.9),
            bordercolor=p['border'],
            borderwidth=1,
            font=dict(size=FONT_SIZE_LEGEND),
        ),
        hoverlabel=dict(
            bgcolor=p['chart_panel'],
            bordercolor=p['structural'],
            font=dict(size=12, color=p['chart_text']),
        ),
    )

    if show_box:
        # Data-plot mode: rectangular box, outside ticks, large tick
        # labels for readability.
        #
        # Note the tick labels take ``chart_text`` and not ``chart_tick``:
        # in light mode these ticks are #333333, which is the *text*
        # colour, while ``chart_tick`` (#666666) is what the chart-mode
        # branch below uses. Keeping that split is what stops the light
        # theme from shifting; it does mean the data plots' dark ticks are
        # the brighter of the two dark tick colours.
        axis_style = dict(
            showgrid=show_grid,
            gridwidth=GRID_WIDTH,
            gridcolor=p['chart_grid'] if show_grid else None,
            showline=True,
            linewidth=AXIS_BOX_WIDTH,
            linecolor=p['chart_axis'],
            mirror=True,
            ticks='outside',
            ticklen=4,
            tickwidth=1,
            tickcolor=p['chart_axis'],
            tickfont=dict(size=FONT_SIZE_TICK, color=p['chart_text']),
            title_font=dict(size=FONT_SIZE_AXIS_TITLE, color=p['chart_text']),
        )
    else:
        # Chart mode: lightweight axes for the Quality Breakdown bar
        # chart (and any future "chart style" figure).
        axis_style = dict(
            showgrid=show_grid,
            gridwidth=GRID_WIDTH,
            gridcolor=p['chart_grid'] if show_grid else None,
            showline=True,
            linewidth=1,
            linecolor=p['border'],
            mirror=False,
            ticks='inside',
            tickfont=dict(size=16, color=p['chart_tick']),
            title_font=dict(size=FONT_SIZE_AXIS_TITLE, color=p['chart_text']),
        )

    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)

    # Bump subplot-title annotations created by ``make_subplots`` and
    # lift them clear of the subplot's top box edge.
    #
    # Plotly anchors subplot titles at the *top* of each subplot's domain
    # with ``yanchor='bottom'``; without a shift the text sits flush on
    # the box line and overlaps the top y-tick. Subplot titles have
    # ``yref='paper'`` with ``y`` strictly inside ``(0, 1]`` (the y-coord
    # of each subplot's top edge in paper space). Custom annotations we
    # add elsewhere — a shared "Wavelength (nm)" label below the grid
    # (y ≈ -0.10), or ``add_vrect`` region markers — fall outside that
    # range, so the filter below leaves them alone.
    if fig.layout.annotations:
        for ann in fig.layout.annotations:
            y_val = getattr(ann, 'y', None)
            if y_val is None or not (0.0 < y_val <= 1.0):
                continue
            # Looks like a subplot title — bump font and nudge above
            # the box edge. Preserve any explicit yshift already set.
            if ann.font is None:
                ann.font = dict(size=FONT_SIZE_SUBPLOT_TITLE)
            else:
                ann.font.size = FONT_SIZE_SUBPLOT_TITLE
            if not getattr(ann, 'yshift', None):
                ann.yshift = SUBPLOT_TITLE_YSHIFT

    return fig


# ============================================================================
# MUELLER MATRIX PLOTS
# ============================================================================

def create_mueller_matrix_plot(
    M_normalized: ndarray,
    wavelengths: ndarray,
    title: str = "Mueller Matrix",
    m00: Optional[ndarray] = None
) -> go.Figure:
    """
    Create interactive 4x4 Mueller matrix plot.

    Parameters
    ----------
    M_normalized : ndarray, shape (4, 4, n_wavelengths)
        Normalized Mueller matrices.
    wavelengths : ndarray
        Wavelength values in nm.
    title : str
        Plot title.
    m00 : ndarray, optional, shape (n_wavelengths,)
        Unnormalized M00 (transmission) to plot in top-left subplot.
        If provided, this replaces the normalized m11 (which is always 1).

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    # Subplot titles with subscript format
    # M_11 for top-left (intensity), m_ij for others (lowercase, normalized)
    subplot_titles = []
    for i in range(4):
        for j in range(4):
            if i == 0 and j == 0:
                subplot_titles.append(f'M<sub>{i+1}{j+1}</sub>')  # Capital M for intensity
            else:
                subplot_titles.append(f'm<sub>{i+1}{j+1}</sub>')  # lowercase m for normalized

    # Create 4x4 subplot grid. Generous spacing so each subplot's
    # 20-pt tick labels don't bleed into its neighbour's box.
    fig = make_subplots(
        rows=4, cols=4,
        subplot_titles=subplot_titles,
        shared_xaxes=True,
        vertical_spacing=0.10,
        horizontal_spacing=0.08,
    )

    for i in range(4):
        for j in range(4):
            # Use m00 for top-left subplot if provided
            if i == 0 and j == 0 and m00 is not None:
                y_data = m00
                hover_label = f'M<sub>11</sub>'
            else:
                y_data = M_normalized[i, j, :]
                hover_label = f'M<sub>{i+1}{j+1}</sub>' if (i == 0 and j == 0) else f'm<sub>{i+1}{j+1}</sub>'

            fig.add_trace(
                go.Scatter(
                    x=wavelengths,
                    y=y_data,
                    mode='lines',
                    name=f'm{i+1}{j+1}',
                    line=dict(color=trace_colors()[0]),  # Explicit blue for all traces
                    hovertemplate=f'{hover_label}<br>λ=%{{x:.1f}} nm<br>Value=%{{y:.4f}}<extra></extra>',
                    showlegend=False
                ),
                row=i+1, col=j+1
            )

    fig.update_layout(
        title=title,
        height=900,
        hovermode='x unified',
    )

    # Apply styling — handles margin (MARGIN_DEFAULT), legend
    # (FONT_SIZE_LEGEND at LEGEND_Y_OFFSET), axis frames, and bumps
    # subplot-title annotations to FONT_SIZE_SUBPLOT_TITLE with the
    # SUBPLOT_TITLE_YSHIFT lift above each subplot's top edge.
    apply_common_styling(fig, show_grid=True)

    # Set y-limits for matrix elements
    for i in range(4):
        for j in range(4):
            if i == 0 and j == 0:
                # M00 (transmission) - fixed range [0, 1.05]
                fig.update_yaxes(range=[0, 1.05], row=i+1, col=j+1)
            else:
                fig.update_yaxes(range=[-1.1, 1.1], row=i+1, col=j+1)

    # Common x-axis label, far enough below the bottom row's 20-pt
    # tick labels that they don't visually overlap.
    fig.add_annotation(
        text="Wavelength (nm)",
        xref="paper", yref="paper",
        x=0.5, y=-0.11,
        showarrow=False,
        font=dict(size=FONT_SIZE_AXIS_TITLE)
    )

    return fig


def create_selected_elements_plot(
    M_normalized: ndarray,
    wavelengths: ndarray,
    selected_elements: List[Tuple[int, int]],
    title: str = "Selected Mueller Elements"
) -> go.Figure:
    """
    Create plot with selected Mueller elements overlaid.

    Parameters
    ----------
    M_normalized : ndarray, shape (4, 4, n_wavelengths)
        Normalized Mueller matrices.
    wavelengths : ndarray
        Wavelength values in nm.
    selected_elements : list of (i, j) tuples
        Selected element indices (0-indexed).
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    fig = go.Figure()

    colors = trace_colors()

    for idx, (i, j) in enumerate(selected_elements):
        # Use subscript format in legend
        label = f'M<sub>{i+1}{j+1}</sub>' if (i == 0 and j == 0) else f'm<sub>{i+1}{j+1}</sub>'
        fig.add_trace(
            go.Scatter(
                x=wavelengths,
                y=M_normalized[i, j, :],
                mode='lines',
                name=label,
                line=dict(color=colors[idx % len(colors)]),
                hovertemplate=f'{label}<br>λ=%{{x:.1f}} nm<br>Value=%{{y:.4f}}<extra></extra>',
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Wavelength (nm)",
        yaxis_title="Normalized Value",
        height=550,
        hovermode='x unified',
    )

    # Single source of truth — apply_common_styling handles margin
    # (MARGIN_DEFAULT) and legend (FONT_SIZE_LEGEND at LEGEND_Y_OFFSET).
    apply_common_styling(fig, show_grid=True)
    return fig


# ============================================================================
# EIGENVALUE RATIO PLOT
# ============================================================================

def create_eigenvalue_plot(
    eigenvalue_ratios: ndarray,
    wavelengths: ndarray,
    title: str = "Eigenvalue Ratio (Calibration Quality)"
) -> go.Figure:
    """
    Create interactive eigenvalue ratio plot with shaded quality regions.

    Parameters
    ----------
    eigenvalue_ratios : ndarray
        Eigenvalue ratios at each wavelength.
    wavelengths : ndarray
        Wavelength values in nm.
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    fig = go.Figure()

    # Quality tier background regions (shaded)
    tier = quality_colors()
    quality_regions = [
        (1e-6, 1e-4, tier['excellent'], 'Excellent'),
        (1e-4, 1e-3, tier['good'], 'Good'),
        (1e-3, 1e-2, tier['acceptable'], 'Acceptable'),
        (1e-2, 0.1, tier['marginal'], 'Marginal'),
        (0.1, 10, tier['poor'], 'Poor'),
    ]

    for y0, y1, color, label in quality_regions:
        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor=color,
            opacity=0.15,
            line_width=0,
        )

    # Main data trace (drawn on top of the shaded regions: black on
    # white, bright grey on the dark panel — see ``_ink``)
    fig.add_trace(
        go.Scatter(
            x=wavelengths,
            y=eigenvalue_ratios,
            mode='lines',
            name='Eigenvalue Ratio',
            line=dict(color=_ink(), width=2),
            hovertemplate='λ=%{x:.1f} nm<br>Ratio=%{y:.2e}<extra></extra>',
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Wavelength (nm)",
        yaxis_title="Eigenvalue Ratio",
        yaxis_type="log",
        height=500,
        hovermode='x unified'
    )

    # Apply styling with grid
    apply_common_styling(fig, show_grid=True)

    # Fix y-axis tick format - use scientific notation instead of "100μ"
    fig.update_yaxes(
        tickformat=".0e",
        tickvals=[1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1],
        ticktext=['1e-5', '1e-4', '1e-3', '1e-2', '1e-1', '1']
    )

    return fig


# ============================================================================
# QUALITY BREAKDOWN BAR CHART
# ============================================================================

def create_quality_breakdown_chart(
    quality_counts: dict,
    total: int
) -> go.Figure:
    """
    Create horizontal bar chart showing the calibration quality breakdown.

    Styling is intentionally **separate from every other figure in the
    module** — this is a chart, not a data plot, so it does not call
    ``apply_common_styling``. The visual language is meant to feel like
    a dashboard tile: lightweight axes, no box, all five quality tiers
    always visible on the y-axis (even zero-count ones), thick bars, and
    a compact x-axis title that doesn't compete with the bar labels.

    Parameters
    ----------
    quality_counts : dict
        Dictionary with keys 'excellent', 'good', 'acceptable',
        'marginal', 'poor'.
    total : int
        Total number of wavelengths.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    # Order: Poor at the bottom, Excellent at the top of the horizontal
    # bar chart. We force the y-axis to show all 5 categories via
    # `categoryorder='array'` so empty tiers still get a tick label.
    categories = ['Poor', 'Marginal', 'Acceptable', 'Good', 'Excellent']
    keys = ['poor', 'marginal', 'acceptable', 'good', 'excellent']
    tier = quality_colors()
    colors = [
        tier['poor'],
        tier['marginal'],
        tier['acceptable'],
        tier['good'],
        tier['excellent'],
    ]

    counts = [quality_counts.get(k, 0) for k in keys]
    percentages = [100 * c / total if total > 0 else 0 for c in counts]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=categories,
            x=percentages,
            orientation='h',
            marker_color=colors,
            marker_line_width=0,
            width=0.7,                           # Thicker bars
            text=[f"{c} ({p:.0f}%)" for c, p in zip(counts, percentages)],
            textposition='auto',
            textfont=dict(size=15),
            hovertemplate='%{y}: %{x:.1f}%<extra></extra>',
        )
    )

    # Dedicated chart styling — does NOT go through apply_common_styling,
    # so it reads the palette itself. The colour roles mirror that
    # function's chart mode exactly.
    p = palette()
    fig.update_layout(
        title=dict(text="Quality Breakdown", font=dict(size=FONT_SIZE_TITLE)),
        font=dict(family='Arial, sans-serif', size=FONT_SIZE_BASE,
                  color=p['chart_text']),
        paper_bgcolor=p['chart_bg'],
        plot_bgcolor=p['chart_bg'],
        height=320,
        showlegend=False,
        margin=dict(l=110, r=40, t=70, b=70),
        bargap=0.25,
        hoverlabel=dict(bgcolor=p['chart_panel'], bordercolor=p['structural'],
                        font=dict(size=12, color=p['chart_text'])),
    )

    fig.update_xaxes(
        title=dict(text="Percentage (%)",
                   font=dict(size=18, color=p['chart_tick'])),
        range=[0, 100],
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor=p['border'],
        mirror=False,
        ticks='inside',
        tickfont=dict(size=18, color=p['chart_tick']),
        zeroline=False,
    )
    fig.update_yaxes(
        # Force all five tiers to always show, even those with 0 wavelengths.
        categoryorder='array',
        categoryarray=categories,
        showgrid=False,
        showline=False,
        ticks='',
        tickfont=dict(size=18, color=p['chart_text']),
        zeroline=False,
    )

    return fig


# ============================================================================
# INSTRUMENT MATRIX PLOTS (W and A matrices)
# ============================================================================

def create_matrix_elements_plot(
    matrix: ndarray,
    wavelengths: ndarray,
    matrix_name: str = "W"
) -> go.Figure:
    """
    Create 4x4 subplot grid for instrument matrix elements.

    Parameters
    ----------
    matrix : ndarray, shape (4, 4, n_wavelengths)
        W or A matrices.
    wavelengths : ndarray
        Wavelength values in nm.
    matrix_name : str
        'W' or 'A' for labeling.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    # Subplot titles with subscript format
    subplot_titles = [f'{matrix_name}<sub>{i+1}{j+1}</sub>' for i in range(4) for j in range(4)]

    fig = make_subplots(
        rows=4, cols=4,
        subplot_titles=subplot_titles,
        shared_xaxes=True,
        vertical_spacing=0.10,
        horizontal_spacing=0.08,
    )

    for i in range(4):
        for j in range(4):
            fig.add_trace(
                go.Scatter(
                    x=wavelengths,
                    y=matrix[i, j, :],
                    mode='lines',
                    name=f'{matrix_name}[{i+1},{j+1}]',
                    hovertemplate=(
                        f'{matrix_name}<sub>{i+1}{j+1}</sub><br>'
                        'λ=%{x:.1f} nm<br>'
                        'Value=%{y:.4f}<extra></extra>'
                    ),
                    showlegend=False
                ),
                row=i+1, col=j+1
            )

    fig.update_layout(
        title=f"{matrix_name} Matrix Elements vs Wavelength",
        height=900,
        hovermode='x unified',
    )

    # Apply styling with grid
    apply_common_styling(fig, show_grid=True)

    # Common x-axis label at bottom
    fig.add_annotation(
        text="Wavelength (nm)",
        xref="paper", yref="paper",
        x=0.5, y=-0.10,
        showarrow=False,
        font=dict(size=FONT_SIZE_AXIS_TITLE)
    )

    return fig


def create_air_validation_plot(
    W: ndarray,
    A: ndarray,
    wavelengths: ndarray
) -> go.Figure:
    """
    Create air validation plot comparing A @ W to identity matrix.

    For a properly calibrated system, A @ W should equal the identity
    matrix (for air sample with M_air = I).

    Parameters
    ----------
    W : ndarray, shape (4, 4, n_wavelengths)
        PSG matrices.
    A : ndarray, shape (4, 4, n_wavelengths)
        PSA matrices.
    wavelengths : ndarray
        Wavelength values in nm.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    # Compute A @ W for each wavelength
    n_wl = W.shape[2]
    M_reconstructed = np.zeros((4, 4, n_wl))
    for i_wl in range(n_wl):
        M_reconstructed[:, :, i_wl] = A[:, :, i_wl] @ W[:, :, i_wl]

    # Normalize by M[0,0] to get normalized Mueller matrix
    for i_wl in range(n_wl):
        if M_reconstructed[0, 0, i_wl] != 0:
            M_reconstructed[:, :, i_wl] /= M_reconstructed[0, 0, i_wl]

    # Subplot titles with subscript format
    subplot_titles = [f'm<sub>{i+1}{j+1}</sub>' for i in range(4) for j in range(4)]

    fig = make_subplots(
        rows=4, cols=4,
        subplot_titles=subplot_titles,
        shared_xaxes=True,
        vertical_spacing=0.10,
        horizontal_spacing=0.08,
    )

    # Expected values for identity matrix (normalized)
    for i in range(4):
        for j in range(4):
            expected = 1.0 if i == j else 0.0

            # Add measured trace
            fig.add_trace(
                go.Scatter(
                    x=wavelengths,
                    y=M_reconstructed[i, j, :],
                    mode='lines',
                    name='Measured',
                    line=dict(color='blue'),
                    showlegend=(i == 0 and j == 0),
                    hovertemplate='λ=%{x:.1f} nm<br>Value=%{y:.4f}<extra></extra>',
                ),
                row=i+1, col=j+1
            )

            # Add expected reference line
            fig.add_hline(
                y=expected,
                line_dash="dash",
                line_color="red",
                row=i+1, col=j+1
            )

    fig.update_layout(
        title="Air Validation: A @ W (should equal Identity Matrix)",
        height=900,
        hovermode='x unified',
    )

    # Apply styling with grid
    apply_common_styling(fig, show_grid=True)

    # Common x-axis label at bottom
    fig.add_annotation(
        text="Wavelength (nm)",
        xref="paper", yref="paper",
        x=0.5, y=-0.10,
        showarrow=False,
        font=dict(size=FONT_SIZE_AXIS_TITLE)
    )

    return fig


# ============================================================================
# TRANSMISSION / M00 PLOT
# ============================================================================

def create_m00_plot(
    m00: ndarray,
    wavelengths: ndarray,
    sample_name: str = "Sample",
    title: str = "Transmission (M₀₀)"
) -> go.Figure:
    """
    Create transmission plot showing m00 (intensity) vs wavelength.

    Parameters
    ----------
    m00 : ndarray, shape (n_wavelengths,)
        Transmission/intensity values (unnormalized M[0,0]).
    wavelengths : ndarray
        Wavelength values in nm.
    sample_name : str
        Sample name for legend.
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=wavelengths,
            y=m00,
            mode='lines',
            name=sample_name,
            line=dict(color=trace_colors()[0], width=2),
            hovertemplate='λ=%{x:.1f} nm<br>M₀₀=%{y:.4f}<extra></extra>',
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Wavelength (nm)",
        yaxis_title="Transmission (a.u.)",
        height=400,
        hovermode='x unified'
    )

    # Apply styling with grid
    apply_common_styling(fig, show_grid=True)

    return fig


def create_m00_comparison_plot(
    m00_dict: dict,
    wavelengths: ndarray,
    title: str = "Transmission Comparison (M₀₀)"
) -> go.Figure:
    """
    Create transmission plot comparing multiple samples.

    Parameters
    ----------
    m00_dict : dict
        Dictionary mapping sample names to m00 arrays.
    wavelengths : ndarray
        Wavelength values in nm.
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    fig = go.Figure()

    colors = trace_colors()

    for idx, (name, m00) in enumerate(m00_dict.items()):
        fig.add_trace(
            go.Scatter(
                x=wavelengths,
                y=m00,
                mode='lines',
                name=name,
                line=dict(color=colors[idx % len(colors)], width=2),
                hovertemplate=f'{name}<br>λ=%{{x:.1f}} nm<br>M₀₀=%{{y:.4f}}<extra></extra>',
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Wavelength (nm)",
        yaxis_title="Transmission (a.u.)",
        height=520,
        hovermode='x unified',
    )

    apply_common_styling(fig, show_grid=True)
    return fig


def create_mueller_comparison_plot(
    samples_dict: dict,
    wavelengths: ndarray,
    title: str = "Mueller Matrix Comparison"
) -> go.Figure:
    """
    Create 4x4 Mueller matrix comparison plot for multiple samples.

    Parameters
    ----------
    samples_dict : dict
        Dictionary mapping sample names to (M_normalized, m00) tuples.
        M_normalized shape: (4, 4, n_wavelengths)
        m00 shape: (n_wavelengths,)
    wavelengths : ndarray
        Wavelength values in nm.
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    # Subplot titles with subscript format
    subplot_titles = []
    for i in range(4):
        for j in range(4):
            if i == 0 and j == 0:
                subplot_titles.append(f'M<sub>{i+1}{j+1}</sub>')
            else:
                subplot_titles.append(f'm<sub>{i+1}{j+1}</sub>')

    # Create 4x4 subplot grid
    fig = make_subplots(
        rows=4, cols=4,
        subplot_titles=subplot_titles,
        shared_xaxes=True,
        vertical_spacing=0.10,
        horizontal_spacing=0.08,
    )

    colors = trace_colors()

    sample_names = list(samples_dict.keys())

    for sample_idx, (name, (M_norm, m00)) in enumerate(samples_dict.items()):
        color = colors[sample_idx % len(colors)]
        show_legend = True  # Show legend for first element only

        for i in range(4):
            for j in range(4):
                # Use m00 for top-left subplot
                if i == 0 and j == 0 and m00 is not None:
                    y_data = m00
                else:
                    y_data = M_norm[i, j, :]

                fig.add_trace(
                    go.Scatter(
                        x=wavelengths,
                        y=y_data,
                        mode='lines',
                        name=name,
                        line=dict(color=color),
                        showlegend=show_legend,
                        legendgroup=name,
                        hovertemplate=f'{name}<br>λ=%{{x:.1f}} nm<br>Value=%{{y:.4f}}<extra></extra>',
                    ),
                    row=i+1, col=j+1
                )
                show_legend = False  # Only show legend once per sample

    fig.update_layout(
        title=title,
        height=900,
        hovermode='x unified',
    )

    # Apply styling — handles margin (MARGIN_DEFAULT b=140), subplot-title
    # yshift, legend (font 26, y=-0.24), and axis frames.
    apply_common_styling(fig, show_grid=True)

    # Set y-limits for matrix elements
    for i in range(4):
        for j in range(4):
            if i == 0 and j == 0:
                fig.update_yaxes(range=[0, 1.05], row=i+1, col=j+1)
            else:
                fig.update_yaxes(range=[-1.1, 1.1], row=i+1, col=j+1)

    # Shared "Wavelength (nm)" label below the grid, added AFTER
    # apply_common_styling so the subplot-title yshift doesn't touch it.
    fig.add_annotation(
        text="Wavelength (nm)",
        xref="paper", yref="paper",
        x=0.5, y=-0.10,
        showarrow=False,
        font=dict(size=FONT_SIZE_AXIS_TITLE),
    )

    return fig


# ============================
# LU-CHIPMAN PARAMETER PLOTS
# ============================

def create_depolarization_plot(
    DI: ndarray,
    wavelengths: ndarray
) -> go.Figure:
    """Create depolarization index plot. Placeholder for Phase 5."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=wavelengths, y=DI, mode='lines', name='DI')
    )
    fig.update_layout(
        title="Depolarization Index",
        xaxis_title="Wavelength (nm)",
        yaxis_title="DI",
        height=400
    )
    apply_common_styling(fig, show_grid=True)
    return fig


def create_diattenuation_plot(
    D: ndarray,
    wavelengths: ndarray,
    sample_name: str = "Sample",
    title: str = "Diattenuation"
) -> go.Figure:
    """
    Create single-sample diattenuation plot.

    Parameters
    ----------
    D : ndarray, shape (n_wavelengths,)
        Diattenuation values.
    wavelengths : ndarray
        Wavelength values in nm.
    sample_name : str
        Sample name for legend.
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=wavelengths,
            y=D,
            mode='lines',
            name=sample_name,
            line=dict(color=trace_colors()[0], width=2),
            hovertemplate='λ=%{x:.1f} nm<br>D=%{y:.4f}<extra></extra>',
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Wavelength (nm)",
        yaxis_title="Diattenuation (D)",
        yaxis=dict(range=[0, 1]),
        height=400,
        hovermode='x unified'
    )

    apply_common_styling(fig, show_grid=True)
    return fig


def create_diattenuation_comparison_plot(
    samples_dict: dict,
    wavelengths: ndarray,
    title: str = "Diattenuation Comparison"
) -> go.Figure:
    """
    Create multi-sample diattenuation overlay plot.

    Parameters
    ----------
    samples_dict : dict
        Dictionary mapping sample names to D arrays.
    wavelengths : ndarray
        Wavelength values in nm.
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    fig = go.Figure()

    colors = trace_colors()

    for idx, (name, D) in enumerate(samples_dict.items()):
        fig.add_trace(
            go.Scatter(
                x=wavelengths,
                y=D,
                mode='lines',
                name=name,
                line=dict(color=colors[idx % len(colors)], width=2),
                hovertemplate=f'{name}<br>λ=%{{x:.1f}} nm<br>D=%{{y:.4f}}<extra></extra>',
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Wavelength (nm)",
        yaxis_title="Diattenuation (D)",
        yaxis=dict(range=[0, 1]),
        height=520,
        hovermode='x unified',
    )

    apply_common_styling(fig, show_grid=True)
    return fig


def create_di_plot(
    DI: ndarray,
    wavelengths: ndarray,
    sample_name: str = "Sample",
    title: str = "Depolarization Index"
) -> go.Figure:
    """
    Create single-sample depolarization index plot.

    Parameters
    ----------
    DI : ndarray, shape (n_wavelengths,)
        Depolarization index values.
    wavelengths : ndarray
        Wavelength values in nm.
    sample_name : str
        Sample name for legend.
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=wavelengths,
            y=DI,
            mode='lines',
            name=sample_name,
            line=dict(color=trace_colors()[0], width=2),
            hovertemplate='λ=%{x:.1f} nm<br>DI=%{y:.4f}<extra></extra>',
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Wavelength (nm)",
        yaxis_title="Depolarization Index (DI)",
        yaxis=dict(range=[0, 1.05]),
        height=400,
        hovermode='x unified'
    )

    apply_common_styling(fig, show_grid=True)
    return fig


def create_di_comparison_plot(
    samples_dict: dict,
    wavelengths: ndarray,
    title: str = "Depolarization Index Comparison"
) -> go.Figure:
    """
    Create multi-sample depolarization index overlay plot.

    Parameters
    ----------
    samples_dict : dict
        Dictionary mapping sample names to DI arrays.
    wavelengths : ndarray
        Wavelength values in nm.
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    fig = go.Figure()

    colors = trace_colors()

    for idx, (name, DI) in enumerate(samples_dict.items()):
        fig.add_trace(
            go.Scatter(
                x=wavelengths,
                y=DI,
                mode='lines',
                name=name,
                line=dict(color=colors[idx % len(colors)], width=2),
                hovertemplate=f'{name}<br>λ=%{{x:.1f}} nm<br>DI=%{{y:.4f}}<extra></extra>',
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Wavelength (nm)",
        yaxis_title="Depolarization Index (DI)",
        yaxis=dict(range=[0, 1.05]),
        height=520,
        hovermode='x unified',
    )

    apply_common_styling(fig, show_grid=True)
    return fig


def create_retardance_plot(
    R_deg: ndarray,
    wavelengths: ndarray,
    R_rad: ndarray = None,
    R_waves: ndarray = None,
    unit: str = "degrees",
    sample_name: str = "Sample",
    title: str = "Retardance"
) -> go.Figure:
    """
    Create retardance plot with selectable unit.

    Parameters
    ----------
    R_deg : ndarray, shape (n_wavelengths,)
        Retardance in degrees.
    wavelengths : ndarray
        Wavelength values in nm.
    R_rad : ndarray, optional
        Retardance in radians.
    R_waves : ndarray, optional
        Retardance in waves.
    unit : str
        Unit to display: "degrees", "radians", or "waves".
    sample_name : str
        Sample name for legend.
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    import numpy as np

    # Select data and label based on unit
    if unit == "radians":
        if R_rad is not None:
            y_data = R_rad
        else:
            y_data = np.deg2rad(R_deg)
        y_label = "Retardance (rad)"
        qwp_val = np.pi / 2
        hwp_val = np.pi
        qwp_text = "QWP (π/2)"
        hwp_text = "HWP (π)"
    elif unit == "waves":
        if R_waves is not None:
            y_data = R_waves
        else:
            y_data = R_deg / 360.0
        y_label = "Retardance (waves)"
        qwp_val = 0.25
        hwp_val = 0.5
        qwp_text = "QWP (0.25)"
        hwp_text = "HWP (0.5)"
    else:  # degrees (default)
        y_data = R_deg
        y_label = "Retardance (°)"
        qwp_val = 90
        hwp_val = 180
        qwp_text = "QWP (90°)"
        hwp_text = "HWP (180°)"

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=wavelengths,
            y=y_data,
            mode='lines',
            name=sample_name,
            line=dict(color=trace_colors()[0], width=2),
            hovertemplate=f'λ=%{{x:.1f}} nm<br>R=%{{y:.4f}}<extra></extra>',
        )
    )

    # QWP and HWP reference lines
    fig.add_hline(
        y=qwp_val,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"  {qwp_text}",
        annotation_position="right",
        annotation_font=dict(size=FONT_SIZE_TICK)
    )
    fig.add_hline(
        y=hwp_val,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"  {hwp_text}",
        annotation_position="right",
        annotation_font=dict(size=FONT_SIZE_TICK)
    )

    fig.update_layout(
        title=title,
        xaxis_title="Wavelength (nm)",
        yaxis_title=y_label,
        height=400,
        hovermode='x unified'
    )

    apply_common_styling(fig, show_grid=True)
    return fig


def create_retardance_comparison_plot(
    samples_dict: dict,
    wavelengths: ndarray,
    unit: str = "degrees",
    title: str = "Retardance Comparison"
) -> go.Figure:
    """
    Create multi-sample retardance overlay plot with selectable unit.

    Parameters
    ----------
    samples_dict : dict
        Dictionary mapping sample names to LuChipmanResult objects or
        (R_deg, R_rad, R_waves) tuples.
    wavelengths : ndarray
        Wavelength values in nm.
    unit : str
        Unit to display: "degrees", "radians", or "waves".
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    import numpy as np

    # Set up labels and reference values
    if unit == "radians":
        y_label = "Retardance (rad)"
        qwp_val = np.pi / 2
        hwp_val = np.pi
        qwp_text = "QWP (π/2)"
        hwp_text = "HWP (π)"
    elif unit == "waves":
        y_label = "Retardance (waves)"
        qwp_val = 0.25
        hwp_val = 0.5
        qwp_text = "QWP (0.25)"
        hwp_text = "HWP (0.5)"
    else:  # degrees
        y_label = "Retardance (°)"
        qwp_val = 90
        hwp_val = 180
        qwp_text = "QWP (90°)"
        hwp_text = "HWP (180°)"

    fig = go.Figure()

    colors = trace_colors()

    for idx, (name, result) in enumerate(samples_dict.items()):
        # Handle both LuChipmanResult objects and tuples
        if hasattr(result, 'R_deg'):
            if unit == "radians":
                y_data = result.R_rad
            elif unit == "waves":
                y_data = result.R_waves
            else:
                y_data = result.R_deg
        elif isinstance(result, tuple):
            R_deg, R_rad, R_waves = result
            if unit == "radians":
                y_data = R_rad
            elif unit == "waves":
                y_data = R_waves
            else:
                y_data = R_deg
        else:
            # Assume it's R_deg array
            if unit == "radians":
                y_data = np.deg2rad(result)
            elif unit == "waves":
                y_data = result / 360.0
            else:
                y_data = result

        fig.add_trace(
            go.Scatter(
                x=wavelengths,
                y=y_data,
                mode='lines',
                name=name,
                line=dict(color=colors[idx % len(colors)], width=2),
                hovertemplate=f'{name}<br>λ=%{{x:.1f}} nm<br>R=%{{y:.4f}}<extra></extra>',
            )
        )

    # QWP and HWP reference lines
    fig.add_hline(
        y=qwp_val,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"  {qwp_text}",
        annotation_position="right",
        annotation_font=dict(size=FONT_SIZE_TICK)
    )
    fig.add_hline(
        y=hwp_val,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"  {hwp_text}",
        annotation_position="right",
        annotation_font=dict(size=FONT_SIZE_TICK)
    )

    fig.update_layout(
        title=title,
        xaxis_title="Wavelength (nm)",
        yaxis_title=y_label,
        height=520,
        hovermode='x unified',
    )

    apply_common_styling(fig, show_grid=True)
    return fig


# ============================================================================
# FAST AXIS (ν) AND ELLIPTICITY (χ) PLOTS
# ============================================================================

def create_fast_axis_plot(
    psi_deg: ndarray,
    chi_deg: ndarray,
    wavelengths: ndarray,
    unit: str = "degrees",
    sample_name: str = "Sample",
    title: str = "Eigenmodes"
) -> go.Figure:
    """
    Create 2-subplot vertical figure for fast axis (ν) and ellipticity (χ).

    Parameters
    ----------
    psi_deg : ndarray
        Fast-axis azimuth in degrees (ECM psi_deg, displayed as ν).
    chi_deg : ndarray
        Ellipticity angle in degrees.
    wavelengths : ndarray
        Wavelength values in nm.
    unit : str
        "degrees" or "radians" (no waves for angles).
    sample_name : str
        Sample name for legend.
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure with 2 vertically stacked subplots.
    """
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=["Fast Axis (ν)", "Ellipticity (χ)"],
        shared_xaxes=True,
        vertical_spacing=0.12
    )

    # Unit conversion
    if unit == "radians":
        psi_data = np.deg2rad(psi_deg)
        chi_data = np.deg2rad(chi_deg)
        psi_label, chi_label = "ν (rad)", "χ (rad)"
        psi_range, chi_range = [-np.pi/2, np.pi/2], [-np.pi/4, np.pi/4]
    else:
        psi_data, chi_data = psi_deg, chi_deg
        psi_label, chi_label = "ν (°)", "χ (°)"
        psi_range, chi_range = [-90, 90], [-45, 45]

    # Top: Fast axis ν
    fig.add_trace(
        go.Scatter(
            x=wavelengths,
            y=psi_data,
            mode='lines',
            name=sample_name,
            line=dict(color=trace_colors()[0], width=2),
            hovertemplate='λ=%{x:.1f} nm<br>ν=%{y:.2f}<extra></extra>',
        ),
        row=1, col=1
    )

    # Bottom: Ellipticity χ
    fig.add_trace(
        go.Scatter(
            x=wavelengths,
            y=chi_data,
            mode='lines',
            name=sample_name,
            line=dict(color=trace_colors()[0], width=2),
            showlegend=False,
            hovertemplate='λ=%{x:.1f} nm<br>χ=%{y:.2f}<extra></extra>',
        ),
        row=2, col=1
    )

    # Reference lines (0 line for both)
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)
    fig.add_hline(
        y=0, line_dash="dash", line_color="gray", row=2, col=1,
        annotation_text="  Linear", annotation_position="right",
        annotation_font=dict(size=FONT_SIZE_TICK)
    )

    fig.update_layout(
        title=title,
        height=600,
        hovermode='x unified'
    )

    # Set y-axis labels and ranges
    fig.update_yaxes(title_text=psi_label, range=psi_range, row=1, col=1)
    fig.update_yaxes(title_text=chi_label, range=chi_range, row=2, col=1)
    fig.update_xaxes(title_text="Wavelength (nm)", row=2, col=1)

    apply_common_styling(fig, show_grid=True)
    return fig


def create_fast_axis_comparison_plot(
    samples_dict: dict,
    wavelengths: ndarray,
    unit: str = "degrees",
    title: str = "Eigenmodes Comparison"
) -> go.Figure:
    """
    Create multi-sample comparison plot for fast axis and ellipticity.

    Parameters
    ----------
    samples_dict : dict
        Dictionary mapping sample names to LuChipmanResult objects.
    wavelengths : ndarray
        Wavelength values in nm.
    unit : str
        Unit to display: "degrees" or "radians".
    title : str
        Plot title.

    Returns
    -------
    fig : go.Figure
        Plotly figure with 2 vertically stacked subplots.
    """
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=["Fast Axis (ν)", "Ellipticity (χ)"],
        shared_xaxes=True,
        vertical_spacing=0.12
    )

    colors = trace_colors()

    # Unit settings
    if unit == "radians":
        psi_label, chi_label = "ν (rad)", "χ (rad)"
        psi_range, chi_range = [-np.pi/2, np.pi/2], [-np.pi/4, np.pi/4]
    else:
        psi_label, chi_label = "ν (°)", "χ (°)"
        psi_range, chi_range = [-90, 90], [-45, 45]

    for idx, (name, result) in enumerate(samples_dict.items()):
        color = colors[idx % len(colors)]

        # Get data with unit conversion
        if unit == "radians":
            psi_data = np.deg2rad(result.psi_deg)
            chi_data = np.deg2rad(result.chi_deg)
        else:
            psi_data = result.psi_deg
            chi_data = result.chi_deg

        # Top subplot: psi/nu
        fig.add_trace(
            go.Scatter(
                x=wavelengths,
                y=psi_data,
                mode='lines',
                name=name,
                line=dict(color=color, width=2),
                legendgroup=name,
                hovertemplate=f'{name}<br>λ=%{{x:.1f}} nm<br>ν=%{{y:.2f}}<extra></extra>',
            ),
            row=1, col=1
        )

        # Bottom subplot: chi
        fig.add_trace(
            go.Scatter(
                x=wavelengths,
                y=chi_data,
                mode='lines',
                name=name,
                line=dict(color=color, width=2),
                legendgroup=name,
                showlegend=False,
                hovertemplate=f'{name}<br>λ=%{{x:.1f}} nm<br>χ=%{{y:.2f}}<extra></extra>',
            ),
            row=2, col=1
        )

    # Reference lines
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)

    fig.update_layout(
        title=title,
        height=720,
        hovermode='x unified',
    )

    fig.update_yaxes(title_text=psi_label, range=psi_range, row=1, col=1)
    fig.update_yaxes(title_text=chi_label, range=chi_range, row=2, col=1)
    fig.update_xaxes(title_text="Wavelength (nm)", row=2, col=1)

    apply_common_styling(fig, show_grid=True)
    return fig


# ============================================================================
# ELLIPSOMETRY PLOTS (Reflection Mode)
# ============================================================================

_ELLIPS_PARAMS = ('psi_delta', 'ncs', 'pseudo_epsilon', 'pseudo_nk')


def _extract_ellips_traces(ellips, parameter: str):
    """Return a list of (label, y_values, unit) tuples for a given parameter."""
    if parameter == 'psi_delta':
        return [
            ('Ψ', ellips.psi_deg, 'deg'),
            ('Δ', ellips.delta_deg, 'deg'),
        ]
    if parameter == 'ncs':
        return [
            ('N', ellips.N, ''),
            ('C', ellips.C, ''),
            ('S', ellips.S, ''),
        ]
    if parameter == 'pseudo_epsilon':
        return [
            ('Re⟨ε⟩', ellips.pseudo_epsilon.real, ''),
            ('Im⟨ε⟩', ellips.pseudo_epsilon.imag, ''),
        ]
    if parameter == 'pseudo_nk':
        return [
            ('⟨n⟩', ellips.pseudo_n, ''),
            ('⟨k⟩', ellips.pseudo_k, ''),
        ]
    raise ValueError(
        f"Unknown ellipsometry parameter '{parameter}'. "
        f"Must be one of {_ELLIPS_PARAMS}."
    )


def _ellips_y_title(parameter: str) -> str:
    """Single-axis y-axis title for a given parameter (not used for psi_delta)."""
    return {
        'ncs': 'N, C, S',
        'pseudo_epsilon': '⟨ε⟩',
        'pseudo_nk': '⟨n⟩, ⟨k⟩',
    }.get(parameter, '')


def create_ellipsometry_plot(
    wavelengths: ndarray,
    ellips_result,
    parameter: str = 'psi_delta',
) -> go.Figure:
    """
    Plot ellipsometric parameters for a single sample.

    Parameters
    ----------
    wavelengths : ndarray
        Wavelength axis (nm).
    ellips_result : EllipsometricResult
        Object with attributes psi_deg, delta_deg, N, C, S,
        pseudo_epsilon (complex), pseudo_n, pseudo_k.
    parameter : str
        One of 'psi_delta', 'ncs', 'pseudo_epsilon', 'pseudo_nk'.
        'psi_delta' uses a secondary y-axis (Ψ left, Δ right).

    Returns
    -------
    fig : go.Figure
    """
    if parameter == 'psi_delta':
        fig = make_subplots(specs=[[{'secondary_y': True}]])
        fig.add_trace(
            go.Scatter(
                x=wavelengths, y=ellips_result.psi_deg, name='Ψ',
                line=dict(color=primary_color(), width=2),
                mode='lines',
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=wavelengths, y=ellips_result.delta_deg, name='Δ',
                line=dict(color=trace_colors()[0], width=2),
                mode='lines',
            ),
            secondary_y=True,
        )
        fig.update_xaxes(title_text='Wavelength (nm)')
        fig.update_yaxes(title_text='Ψ (deg)', secondary_y=False)
        fig.update_yaxes(title_text='Δ (deg)', secondary_y=True)
        fig.update_layout(title='Ψ and Δ')
        return apply_common_styling(fig)

    # Single-axis plots: NCS, pseudo-epsilon, pseudo-nk
    fig = go.Figure()
    traces = _extract_ellips_traces(ellips_result, parameter)
    for i, (label, y, _unit) in enumerate(traces):
        fig.add_trace(
            go.Scatter(
                x=wavelengths, y=y, name=label,
                line=dict(color=_trace(i), width=2),
                mode='lines',
            )
        )
    title_map = {
        'ncs': 'NCS Parameters',
        'pseudo_epsilon': 'Pseudo-dielectric function ⟨ε⟩',
        'pseudo_nk': 'Pseudo n and k',
    }
    fig.update_layout(
        title=title_map.get(parameter, parameter),
        xaxis_title='Wavelength (nm)',
        yaxis_title=_ellips_y_title(parameter),
    )
    return apply_common_styling(fig)


def create_ellipsometry_comparison_plot(
    wavelengths: ndarray,
    results: Dict[str, object],
    parameter: str = 'psi_delta',
) -> go.Figure:
    """
    Multi-sample ellipsometric comparison plot.

    Parameters
    ----------
    wavelengths : ndarray
        Wavelength axis (nm).
    results : dict[str, EllipsometricResult]
        Sample name → result.
    parameter : str
        One of 'psi_delta', 'ncs', 'pseudo_epsilon', 'pseudo_nk'.
        For multi-sample, components are stacked vertically (one row per
        component) rather than dual-axis to keep traces readable.
    """
    # Components stacked vertically: psi_delta → 2 rows; ncs → 3 rows;
    # pseudo_epsilon/pseudo_nk → 2 rows.
    traces_template = _extract_ellips_traces(next(iter(results.values())), parameter)
    n_components = len(traces_template)
    component_labels = [t[0] for t in traces_template]
    component_units = [t[2] for t in traces_template]

    fig = make_subplots(
        rows=n_components, cols=1, shared_xaxes=True,
        subplot_titles=component_labels, vertical_spacing=0.10,
    )

    for i, (name, ellips) in enumerate(results.items()):
        color = _trace(i)
        traces = _extract_ellips_traces(ellips, parameter)
        for row_idx, (label, y, _unit) in enumerate(traces, start=1):
            fig.add_trace(
                go.Scatter(
                    x=wavelengths, y=y, name=name,
                    legendgroup=name,
                    showlegend=(row_idx == 1),  # only legend entry on first row
                    line=dict(color=color, width=2),
                    mode='lines',
                ),
                row=row_idx, col=1,
            )

    # Y-axis titles per row (include units)
    for row_idx in range(1, n_components + 1):
        label = component_labels[row_idx - 1]
        unit = component_units[row_idx - 1]
        title = f"{label} ({unit})" if unit else label
        fig.update_yaxes(title_text=title, row=row_idx, col=1)

    fig.update_xaxes(title_text='Wavelength (nm)', row=n_components, col=1)
    title_map = {
        'psi_delta': 'Ψ and Δ — Comparison',
        'ncs': 'NCS Parameters — Comparison',
        'pseudo_epsilon': 'Pseudo-dielectric function — Comparison',
        'pseudo_nk': 'Pseudo n and k — Comparison',
    }
    fig.update_layout(title=title_map.get(parameter, parameter))
    return apply_common_styling(fig)


# ============================================================================
# DECOMPOSITION PLOTS — Differential / Cloude / Purity
# ============================================================================

# Differential decomposition: L_m, L_u, M_m, M_u are all 4x4 spectral matrices.
# The 4x4 grid display reuses `create_mueller_matrix_plot()` directly.
# Single-element overlays reuse `create_selected_elements_plot()`.

def create_eigenvalue_spectrum_plot(
    wavelengths: ndarray,
    eigenvalues: ndarray,
    title: str = 'Cloude Eigenvalues',
) -> go.Figure:
    """Plot the four Cloude coherency eigenvalues vs wavelength.

    Parameters
    ----------
    wavelengths : ndarray, shape (n_wl,)
    eigenvalues : ndarray, shape (4, n_wl)
        Each row is one eigenvalue across wavelength.
    """
    fig = go.Figure()
    labels = ['λ₀ (dominant)', 'λ₁', 'λ₂', 'λ₃']
    for i in range(4):
        fig.add_trace(
            go.Scatter(
                x=wavelengths, y=eigenvalues[i, :], name=labels[i],
                line=dict(color=_trace(i), width=2),
                mode='lines',
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title='Wavelength (nm)',
        yaxis_title='Eigenvalue',
    )
    return apply_common_styling(fig)


def create_eigenvalue_spectrum_comparison_plot(
    wavelengths: ndarray,
    results: Dict[str, object],
) -> go.Figure:
    """Multi-sample Cloude eigenvalue comparison (one row per eigenvalue)."""
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=('λ<sub>0</sub> (dominant)', 'λ<sub>1</sub>',
                        'λ<sub>2</sub>', 'λ<sub>3</sub>'),
    )
    for i, (name, res) in enumerate(results.items()):
        color = _trace(i)
        for row in range(4):
            fig.add_trace(
                go.Scatter(
                    x=wavelengths, y=res.eigenvalues[row, :], name=name,
                    legendgroup=name, showlegend=(row == 0),
                    line=dict(color=color, width=2),
                    mode='lines',
                ),
                row=row + 1, col=1,
            )
    fig.update_xaxes(title_text='Wavelength (nm)', row=4, col=1)
    # Only the middle row carries the y-axis title — same trick as the
    # purity-indices comparison, prevents 4 stacked "Eigenvalue" labels.
    fig.update_yaxes(title_text='Eigenvalue', row=2, col=1)
    fig.update_layout(title='Cloude Eigenvalues — Comparison', height=900)
    return apply_common_styling(fig)


def create_coherency_matrix_plot(
    wavelengths: ndarray,
    H: ndarray,
    elements: Optional[List[Tuple[int, int]]] = None,
    title: str = 'Coherency Matrix |H<sub>ij</sub>|',
) -> go.Figure:
    """Plot the magnitude of selected elements of the 4×4 coherency matrix.

    Parameters
    ----------
    wavelengths : ndarray, shape (n_wl,)
    H : ndarray, shape (4, 4, n_wl), complex
    elements : list of (i, j), optional
        Defaults to the four diagonal elements (0,0), (1,1), (2,2), (3,3).
    """
    if elements is None:
        elements = [(0, 0), (1, 1), (2, 2), (3, 3)]

    fig = go.Figure()
    for k, (i, j) in enumerate(elements):
        y = np.abs(H[i, j, :])
        fig.add_trace(
            go.Scatter(
                x=wavelengths, y=y,
                name=f'|H<sub>{i}{j}</sub>|',
                line=dict(color=_trace(k), width=2),
                mode='lines',
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title='Wavelength (nm)',
        yaxis_title='|H<sub>ij</sub>|',
    )
    return apply_common_styling(fig)


def create_purity_indices_plot(
    wavelengths: ndarray,
    P_P: ndarray,
    P_S: ndarray,
    P_Delta: ndarray,
    sample_name: Optional[str] = None,
) -> go.Figure:
    """Plot the three purity indices vs wavelength on a single axis."""
    fig = go.Figure()
    triples = (
        ('P<sub>P</sub> (polarimetric)', P_P),
        ('P<sub>S</sub> (spherical)', P_S),
        ('P<sub>Δ</sub> (overall)', P_Delta),
    )
    for i, (label, y) in enumerate(triples):
        fig.add_trace(
            go.Scatter(
                x=wavelengths, y=y, name=label,
                line=dict(color=_trace(i), width=2),
                mode='lines',
            )
        )
    title = 'Purity Indices'
    if sample_name:
        title = f'{title} — {sample_name}'
    fig.update_layout(
        title=title,
        xaxis_title='Wavelength (nm)',
        yaxis_title='Purity index',
        yaxis=dict(range=[0, 1.05]),
    )
    return apply_common_styling(fig)


def create_purity_indices_comparison_plot(
    wavelengths: ndarray,
    results: Dict[str, object],
) -> go.Figure:
    """Multi-sample purity indices comparison (one row per index).

    The three rows (P_P / P_S / P_Δ) all share the same [0, 1] y-range,
    so we put the y-axis title only on the **middle** row rather than
    repeating "Purity index" three times. ``vertical_spacing=0.16``
    leaves room for each subplot's title to sit cleanly above its box
    (after the global ``SUBPLOT_TITLE_YSHIFT`` lift). Titles use proper
    ``<sub>...</sub>`` HTML so subscripts render — the previous
    ``P_P`` / ``P_S`` literals showed as raw text with underscores.
    """
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.16,
        subplot_titles=(
            'P<sub>P</sub> (polarimetric)',
            'P<sub>S</sub> (spherical)',
            'P<sub>Δ</sub> (overall)',
        ),
    )
    for i, (name, res) in enumerate(results.items()):
        color = _trace(i)
        for row_idx, attr in enumerate(('P_P', 'P_S', 'P_Delta'), start=1):
            fig.add_trace(
                go.Scatter(
                    x=wavelengths, y=getattr(res, attr), name=name,
                    legendgroup=name, showlegend=(row_idx == 1),
                    line=dict(color=color, width=2),
                    mode='lines',
                ),
                row=row_idx, col=1,
            )
    fig.update_xaxes(title_text='Wavelength (nm)', row=3, col=1)
    # Y-axis title only on the middle row (avoids three overlapping
    # vertical "Purity index" labels stacking on top of each other).
    fig.update_yaxes(range=[0, 1.05], row=1, col=1)
    fig.update_yaxes(title_text='Purity index', range=[0, 1.05], row=2, col=1)
    fig.update_yaxes(range=[0, 1.05], row=3, col=1)
    fig.update_layout(title='Purity Indices — Comparison', height=780)
    return apply_common_styling(fig)


def _purity_space_boundary_traces():
    """Return three boundary-curve traces for the (P_S, P_P) diagram.

    Curves match ECM-PURE's `purity_plots.plot_purity_space` (Gil & Ossikovski):
      - Solid ellipse for P_S ∈ [√3/3, 1]:  P_P = √(3·(1 − P_S²)/2)
      - Dashed ellipse for P_S ∈ [0, √3/3]
      - Solid hyperbola for P_S ∈ [0, √3/3]: P_P = √((1 + 3·P_S²)/2)
    """
    sqrt3_3 = np.sqrt(3) / 3
    # Solid ellipse
    ps1 = np.linspace(sqrt3_3, 1.0, 200)
    pp1 = np.sqrt(np.maximum(3.0 * (1.0 - ps1**2) / 2.0, 0.0))
    # Dashed ellipse
    ps2 = np.linspace(0.0, sqrt3_3, 200)
    pp2 = np.sqrt(np.maximum(3.0 * (1.0 - ps2**2) / 2.0, 0.0))
    # Hyperbola
    ps3 = np.linspace(0.0, sqrt3_3, 200)
    pp3 = np.sqrt((1.0 + 3.0 * ps3**2) / 2.0)

    ink = _ink()
    return [
        go.Scatter(x=ps1, y=pp1, mode='lines',
                   line=dict(color=ink, width=2),
                   name='Ellipse (solid)', showlegend=False, hoverinfo='skip'),
        go.Scatter(x=ps2, y=pp2, mode='lines',
                   line=dict(color=ink, width=2, dash='dash'),
                   name='Ellipse (dashed)', showlegend=False, hoverinfo='skip'),
        go.Scatter(x=ps3, y=pp3, mode='lines',
                   line=dict(color=ink, width=2),
                   name='Hyperbola', showlegend=False, hoverinfo='skip'),
    ]


# Theoretical purity-space axes, per Gil & Ossikovski (2022):
#   x = P_S ∈ [0, 1]      (degree of spherical purity)
#   y = P_P ∈ [0, √6/2]   (degree of polarimetric purity)
# We pad the displayed range a hair so the bold-black axis box doesn't
# clip data points that sit right on the boundary curves.
_PURITY_X_RANGE = (-0.02, 1.02)
_PURITY_Y_RANGE = (-0.02, float(np.sqrt(6) / 2) + 0.02)


def _apply_purity_space_axes(fig: go.Figure, title: str) -> go.Figure:
    """Purity-space–specific axis overrides (run *after* common styling).

    Sets the explicit ``[0, 1] × [0, √6/2]`` domain and turns on the
    reference zerolines at ``P_S = 0`` and ``P_P = 0`` as bold black
    lines matching the analytical boundary curves' thickness (2 px).

    The common-styling box (``AXIS_BOX_WIDTH``) is inherited from
    ``apply_common_styling`` — don't redefine it here.

    Notes
    -----
    ``scaleanchor='x'`` (forced equal pixel scale) silently widens the
    displayed x-range past the configured ``range=`` whenever the plot
    container is wider than tall — which is how the GUI draws every figure
    (``width="stretch"``). We don't use it; a slightly stretched
    (P_S, P_P) plot is preferable to losing the requested limits.
    """
    ink = _ink()
    fig.update_layout(title=title)
    fig.update_xaxes(
        title_text='Degree of Spherical Purity P<sub>S</sub>',
        range=list(_PURITY_X_RANGE),
        zeroline=True,
        zerolinecolor=ink,
        zerolinewidth=2,
    )
    fig.update_yaxes(
        title_text='Degree of Polarimetric Purity P<sub>P</sub>',
        range=list(_PURITY_Y_RANGE),
        zeroline=True,
        zerolinecolor=ink,
        zerolinewidth=2,
    )
    return fig


def create_purity_space_scatter(
    P_S: ndarray,
    P_P: ndarray,
    wavelengths: Optional[ndarray] = None,
    sample_name: Optional[str] = None,
) -> go.Figure:
    """2-D (P_S, P_P) purity space scatter with theoretical boundary curves.

    The boundary curves are taken from Gil & Ossikovski (2022) via
    ECM-PURE's `purity_plots.py`. Axes match the original convention:
    x = P_S ∈ [0, 1], y = P_P ∈ [0, √6/2], with a bold black rectangular
    border drawn at those limits.
    """
    fig = go.Figure()
    for tr in _purity_space_boundary_traces():
        fig.add_trace(tr)

    if wavelengths is not None:
        fig.add_trace(
            go.Scatter(
                x=P_S, y=P_P, mode='markers',
                marker=dict(
                    size=8,
                    color=wavelengths,
                    # Plasma is perceptually uniform and reads correctly on
                    # both backgrounds, so it is shared by the two themes.
                    colorscale=HEATMAP_COLORSCALE,
                    showscale=True,
                    colorbar=dict(title='Wavelength (nm)'),
                    line=dict(width=0.3, color=_ink()),
                ),
                name=sample_name or 'Sample',
                showlegend=False,
            )
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=P_S, y=P_P, mode='markers',
                marker=dict(size=8, color=primary_color(),
                            line=dict(width=0.3, color=_ink())),
                name=sample_name or 'Sample',
                showlegend=False,
            )
        )

    title = 'Purity Space'
    if sample_name:
        title = f'{title}: {sample_name}'
    # IMPORTANT: apply common styling FIRST, then the purity-specific axes
    # overrides — apply_common_styling resets linewidth/linecolor on every
    # axis, which would wipe out our bold black box.
    apply_common_styling(fig)
    return _apply_purity_space_axes(fig, title)


def create_purity_space_comparison_scatter(
    results: Dict[str, object],
    wavelengths: Optional[ndarray] = None,
) -> go.Figure:
    """Multi-sample (P_S, P_P) scatter with the same boundary curves.

    Wavelength colorbar is suppressed; each sample gets one trace color.
    The bold rectangular axis box highlights the natural [0, 1]×[0, √6/2]
    domain.
    """
    fig = go.Figure()
    for tr in _purity_space_boundary_traces():
        fig.add_trace(tr)

    for i, (name, res) in enumerate(results.items()):
        color = _trace(i)
        fig.add_trace(
            go.Scatter(
                x=res.P_S, y=res.P_P, mode='markers',
                marker=dict(size=7, color=color,
                            line=dict(width=0.3, color=_ink())),
                name=name,
            )
        )

    # IMPORTANT: apply common styling FIRST so the purity-specific
    # overrides (bold black box, explicit range) win on top.
    apply_common_styling(fig)
    return _apply_purity_space_axes(fig, 'Purity Space — Comparison')
