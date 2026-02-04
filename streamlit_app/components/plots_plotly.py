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
# - Blue (#1f77b4) for single traces, color palette for multi-sample overlays
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
                    line=dict(color='#1f77b4'),  # Explicit blue for all traces
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

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
              '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
              '#bcbd22', '#17becf', '#1f77b4', '#ff7f0e',
              '#2ca02c', '#d62728', '#9467bd', '#8c564b']

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
    Create interactive eigenvalue ratio plot with threshold lines.

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

    # Main data trace
    fig.add_trace(
        go.Scatter(
            x=wavelengths,
            y=eigenvalue_ratios,
            mode='lines',
            name='Eigenvalue Ratio',
            line=dict(color='#9467bd', width=2),
            hovertemplate='λ=%{x:.1f} nm<br>Ratio=%{y:.2e}<extra></extra>',
        )
    )

    # Threshold lines (colors match Quality Breakdown bars)
    thresholds = [
        (1e-4, 'Excellent', '#17a2b8'),  # cyan/blue
        (1e-3, 'Good', '#28a745'),       # green
        (1e-2, 'Acceptable', '#ffc107'), # yellow
    ]

    for threshold, label, color in thresholds:
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color=color,
            annotation_text=f"  {label} ({threshold:.0e})",
            annotation_position="right",
            annotation_font=dict(size=FONT_SIZE_TICK)
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
    colors = ['#17a2b8', '#28a745', '#ffc107', '#fd7e14', '#dc3545']

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
            line=dict(color='#1f77b4', width=2),
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

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
              '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
              '#bcbd22', '#17becf']

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

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
              '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
              '#bcbd22', '#17becf']

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


def create_retardance_plot(
    R_deg: ndarray,
    wavelengths: ndarray
) -> go.Figure:
    """Create retardance plot. Placeholder for Phase 5."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=wavelengths, y=R_deg, mode='lines', name='Retardance')
    )
    # QWP and HWP reference lines
    fig.add_hline(y=90, line_dash="dash", annotation_text="QWP (90°)")
    fig.add_hline(y=180, line_dash="dash", annotation_text="HWP (180°)")
    fig.update_layout(
        title="Retardance",
        xaxis_title="Wavelength (nm)",
        yaxis_title="Retardance (degrees)",
        height=400
    )
    apply_common_styling(fig, show_grid=True)
    return fig
