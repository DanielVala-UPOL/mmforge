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
# - Blue (TRACE_COLORS[0]) for single traces, TRACE_COLORS for multi-sample overlays
# - Wavelength on x-axis with label "Wavelength (nm)"
# - Y-axis labels specific to parameter (e.g., "DI", "R (deg)", "ν (deg)")
# - Use subscript HTML format for matrix elements (M<sub>11</sub>)
# - Angle parameter ψ from ECM should be displayed as ν in the GUI

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from numpy import ndarray
from typing import Optional, List, Tuple


# ============================================================================
# COMMON STYLING CONSTANTS
# ============================================================================

# Font sizes (~1.5x default, increased for readability)
FONT_SIZE_BASE = 20
FONT_SIZE_TITLE = 22
FONT_SIZE_AXIS_TITLE = 20
FONT_SIZE_TICK = 16
FONT_SIZE_SUBPLOT_TITLE = 16
FONT_SIZE_LEGEND = 16

# Grid styling
GRID_COLOR = 'lightgray'
GRID_WIDTH = 1

# ============================================================================
# MMFORGE COLOR PALETTE
# ============================================================================

# Primary brand color
PRIMARY_COLOR = '#FF1F5B'

# Quality tier colors (muted versions for charts)
QUALITY_COLORS = {
    'excellent': '#0C8AB3',  # Blue
    'good': '#56D39A',       # Green
    'acceptable': '#E8C34A', # Gold
    'marginal': '#FF1F5B',   # Magenta (primary)
    'poor': '#C22026',       # Dark red
}

# Multi-trace color sequence for comparison plots
TRACE_COLORS = [
    '#0C8AB3',  # Blue (1st)
    '#FF1F5B',  # Magenta/primary (2nd)
    '#56D39A',  # Green (3rd)
    '#E8C34A',  # Gold (4th)
    '#C22026',  # Dark red (5th)
    '#9467bd',  # Purple (6th)
    '#8c564b',  # Brown (7th)
    '#7f7f7f',  # Gray (8th)
]


def apply_common_styling(fig, show_grid=True):
    """Apply common styling to all plots."""
    fig.update_layout(
        font=dict(size=FONT_SIZE_BASE),
        title_font=dict(size=FONT_SIZE_TITLE),
        legend=dict(font=dict(size=FONT_SIZE_LEGEND)),
    )

    if show_grid:
        fig.update_xaxes(
            showgrid=True,
            gridwidth=GRID_WIDTH,
            gridcolor=GRID_COLOR,
            title_font=dict(size=FONT_SIZE_AXIS_TITLE),
            tickfont=dict(size=FONT_SIZE_TICK)
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=GRID_WIDTH,
            gridcolor=GRID_COLOR,
            title_font=dict(size=FONT_SIZE_AXIS_TITLE),
            tickfont=dict(size=FONT_SIZE_TICK)
        )
    else:
        fig.update_xaxes(
            title_font=dict(size=FONT_SIZE_AXIS_TITLE),
            tickfont=dict(size=FONT_SIZE_TICK)
        )
        fig.update_yaxes(
            title_font=dict(size=FONT_SIZE_AXIS_TITLE),
            tickfont=dict(size=FONT_SIZE_TICK)
        )

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

    # Create 4x4 subplot grid
    fig = make_subplots(
        rows=4, cols=4,
        subplot_titles=subplot_titles,
        shared_xaxes=True,
        vertical_spacing=0.08,
        horizontal_spacing=0.05
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
                    line=dict(color=TRACE_COLORS[0]),  # Explicit blue for all traces
                    hovertemplate=f'{hover_label}<br>λ=%{{x:.1f}} nm<br>Value=%{{y:.4f}}<extra></extra>',
                    showlegend=False
                ),
                row=i+1, col=j+1
            )

    fig.update_layout(
        title=title,
        height=800,
        hovermode='x unified'
    )

    # Apply styling with grid
    apply_common_styling(fig, show_grid=True)

    # Set y-limits for matrix elements
    for i in range(4):
        for j in range(4):
            if i == 0 and j == 0:
                # M00 (transmission) - fixed range [0, 1.05]
                fig.update_yaxes(range=[0, 1.05], row=i+1, col=j+1)
            else:
                fig.update_yaxes(range=[-1.1, 1.1], row=i+1, col=j+1)

    # Common x-axis label at bottom
    fig.add_annotation(
        text="Wavelength (nm)",
        xref="paper", yref="paper",
        x=0.5, y=-0.06,
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

    colors = TRACE_COLORS

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
        height=500,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Apply styling with grid - legend toggle is enabled by default in Plotly
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
    quality_regions = [
        (1e-6, 1e-4, QUALITY_COLORS['excellent'], 'Excellent'),
        (1e-4, 1e-3, QUALITY_COLORS['good'], 'Good'),
        (1e-3, 1e-2, QUALITY_COLORS['acceptable'], 'Acceptable'),
        (1e-2, 0.1, QUALITY_COLORS['marginal'], 'Marginal'),
        (0.1, 10, QUALITY_COLORS['poor'], 'Poor'),
    ]

    for y0, y1, color, label in quality_regions:
        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor=color,
            opacity=0.15,
            line_width=0,
        )

    # Main data trace (black curve on top of shaded regions)
    fig.add_trace(
        go.Scatter(
            x=wavelengths,
            y=eigenvalue_ratios,
            mode='lines',
            name='Eigenvalue Ratio',
            line=dict(color='black', width=2),
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
    Create horizontal bar chart showing quality breakdown.

    Parameters
    ----------
    quality_counts : dict
        Dictionary with keys 'excellent', 'good', 'acceptable', 'marginal', 'poor'.
    total : int
        Total number of wavelengths.

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    categories = ['Excellent', 'Good', 'Acceptable', 'Marginal', 'Poor']
    keys = ['excellent', 'good', 'acceptable', 'marginal', 'poor']
    colors = [
        QUALITY_COLORS['excellent'],
        QUALITY_COLORS['good'],
        QUALITY_COLORS['acceptable'],
        QUALITY_COLORS['marginal'],
        QUALITY_COLORS['poor'],
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
            text=[f"{c} ({p:.0f}%)" for c, p in zip(counts, percentages)],
            textposition='auto',
            textfont=dict(size=FONT_SIZE_TICK),
            hovertemplate='%{y}: %{x:.1f}%<extra></extra>',
        )
    )

    fig.update_layout(
        title="Quality Breakdown",
        xaxis_title="Percentage (%)",  # Updated label
        yaxis_title="",
        height=300,
        showlegend=False,
        xaxis=dict(range=[0, 100])
    )

    # Apply styling WITHOUT grid and WITHOUT box for this chart
    apply_common_styling(fig, show_grid=False)

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
        vertical_spacing=0.08,
        horizontal_spacing=0.05
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
        height=800,
        hovermode='x unified'
    )

    # Apply styling with grid
    apply_common_styling(fig, show_grid=True)

    # Common x-axis label at bottom
    fig.add_annotation(
        text="Wavelength (nm)",
        xref="paper", yref="paper",
        x=0.5, y=-0.06,
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
        vertical_spacing=0.08,
        horizontal_spacing=0.05
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
        height=800,
        hovermode='x unified'
    )

    # Apply styling with grid
    apply_common_styling(fig, show_grid=True)

    # Common x-axis label at bottom
    fig.add_annotation(
        text="Wavelength (nm)",
        xref="paper", yref="paper",
        x=0.5, y=-0.06,
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
            line=dict(color=TRACE_COLORS[0], width=2),
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

    colors = TRACE_COLORS

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
        height=400,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Apply styling with grid
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
        vertical_spacing=0.08,
        horizontal_spacing=0.05
    )

    colors = TRACE_COLORS

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
        height=800,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Apply styling with grid
    apply_common_styling(fig, show_grid=True)

    # Set y-limits for matrix elements
    for i in range(4):
        for j in range(4):
            if i == 0 and j == 0:
                # M00 (transmission) - fixed range [0, 1.05]
                fig.update_yaxes(range=[0, 1.05], row=i+1, col=j+1)
            else:
                fig.update_yaxes(range=[-1.1, 1.1], row=i+1, col=j+1)

    # Common x-axis label at bottom
    fig.add_annotation(
        text="Wavelength (nm)",
        xref="paper", yref="paper",
        x=0.5, y=-0.06,
        showarrow=False,
        font=dict(size=FONT_SIZE_AXIS_TITLE)
    )

    return fig


# ============================================================================
# LU-CHIPMAN PARAMETER PLOTS (placeholders for Phase 5)
# ============================================================================

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
            line=dict(color=TRACE_COLORS[0], width=2),
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

    colors = TRACE_COLORS

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
        height=400,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
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
            line=dict(color=TRACE_COLORS[0], width=2),
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

    colors = TRACE_COLORS

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
        height=400,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
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
            line=dict(color=TRACE_COLORS[0], width=2),
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

    colors = TRACE_COLORS

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
        height=400,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
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
    title: str = "Fast Axis & Ellipticity"
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
            line=dict(color=TRACE_COLORS[0], width=2),
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
            line=dict(color=TRACE_COLORS[0], width=2),
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
    title: str = "Fast Axis Comparison"
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

    colors = TRACE_COLORS

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
        height=600,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_yaxes(title_text=psi_label, range=psi_range, row=1, col=1)
    fig.update_yaxes(title_text=chi_label, range=chi_range, row=2, col=1)
    fig.update_xaxes(title_text="Wavelength (nm)", row=2, col=1)

    apply_common_styling(fig, show_grid=True)
    return fig
