"""
Plotly Plot Components - Interactive visualization functions.

Provides interactive Plotly plots for:
- Mueller matrix 4x4 grid
- Eigenvalue ratio analysis
- Lu-Chipman parameters
- Decomposed matrices

Author: Daniel Vala
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from numpy import ndarray
from typing import Optional, List, Tuple


# ============================================================================
# MUELLER MATRIX PLOTS
# ============================================================================

def create_mueller_matrix_plot(
    M_normalized: ndarray,
    wavelengths: ndarray,
    title: str = "Mueller Matrix"
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

    Returns
    -------
    fig : go.Figure
        Plotly figure.
    """
    # Create 4x4 subplot grid
    fig = make_subplots(
        rows=4, cols=4,
        subplot_titles=[f'm{i+1}{j+1}' for i in range(4) for j in range(4)],
        shared_xaxes=True,
        vertical_spacing=0.05,
        horizontal_spacing=0.05
    )

    for i in range(4):
        for j in range(4):
            fig.add_trace(
                go.Scatter(
                    x=wavelengths,
                    y=M_normalized[i, j, :],
                    mode='lines',
                    name=f'm{i+1}{j+1}',
                    hovertemplate=f'm{i+1}{j+1}<br>λ=%{{x:.1f}} nm<br>Value=%{{y:.4f}}<extra></extra>',
                    showlegend=False
                ),
                row=i+1, col=j+1
            )

    fig.update_layout(
        title=title,
        height=800,
        hovermode='x unified'
    )

    # Set y-limits for normalized matrix
    for i in range(4):
        for j in range(4):
            if i == 0 and j == 0:
                fig.update_yaxes(range=[0.95, 1.05], row=i+1, col=j+1)
            else:
                fig.update_yaxes(range=[-1.1, 1.1], row=i+1, col=j+1)

    # Add x-axis label to bottom row
    for j in range(4):
        fig.update_xaxes(title_text="Wavelength (nm)", row=4, col=j+1)

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
        fig.add_trace(
            go.Scatter(
                x=wavelengths,
                y=M_normalized[i, j, :],
                mode='lines',
                name=f'm{i+1}{j+1}',
                line=dict(color=colors[idx % len(colors)]),
                hovertemplate=f'm{i+1}{j+1}<br>λ=%{{x:.1f}} nm<br>Value=%{{y:.4f}}<extra></extra>',
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

    # Threshold lines
    thresholds = [
        (1e-4, 'Excellent', 'blue'),
        (1e-3, 'Good', 'green'),
        (1e-2, 'Acceptable', 'orange'),
    ]

    for threshold, label, color in thresholds:
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color=color,
            annotation_text=f"  {label} ({threshold:.0e})",
            annotation_position="right"
        )

    fig.update_layout(
        title=title,
        xaxis_title="Wavelength (nm)",
        yaxis_title="Eigenvalue Ratio",
        yaxis_type="log",
        height=500,
        hovermode='x unified'
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
    colors = ['#28a745', '#17a2b8', '#ffc107', '#fd7e14', '#dc3545']

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
            hovertemplate='%{y}: %{x:.1f}%<extra></extra>',
        )
    )

    fig.update_layout(
        title="Quality Breakdown",
        xaxis_title="Percentage",
        yaxis_title="",
        height=300,
        showlegend=False,
        xaxis=dict(range=[0, 100])
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
    return fig
