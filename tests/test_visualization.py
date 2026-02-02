"""
Tests for ECM Visualization Module

Tests the plotting functions for Mueller matrices, polarimetric parameters,
and diagnostic visualizations.

Note: These tests verify that plots are generated without errors and have
correct structure. Visual correctness should be verified manually.
"""

import numpy as np
import pytest
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for testing
import matplotlib.pyplot as plt
from pathlib import Path
import tempfile

from ecm.utils.mueller_matrices import identity, polarizer, retarder
from ecm.postprocessing.lu_chipman import lu_chipman_decomposition

from ecm.visualization.figure_utils import (
    setup_figure,
    format_axes,
    get_publication_colors,
    get_color_cycle,
    save_figure,
    PUBLICATION_RCPARAMS,
)

from ecm.visualization.mueller_plots import (
    plot_mueller_matrix,
    plot_mueller_element,
)

from ecm.visualization.parameter_plots import (
    plot_polarimetric_parameters,
    plot_depolarization_index,
    plot_retardance,
    plot_diattenuation,
    plot_retarder_axis,
)

from ecm.visualization.decomposition_plots import (
    plot_decomposed_matrices,
    plot_decomposed_matrix,
)

from ecm.visualization.intensity_plots import (
    plot_intensity_data,
    plot_intensity_heatmap,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def wavelengths():
    """Create test wavelength array."""
    return np.linspace(400, 800, 50)


@pytest.fixture
def mueller_matrices(wavelengths):
    """Create wavelength-dependent Mueller matrices (QWP with dispersion)."""
    n_wl = len(wavelengths)
    M = np.zeros((4, 4, n_wl))

    for i, wl in enumerate(wavelengths):
        # Wavelength-dependent retardation (simulate dispersion)
        delta = np.pi / 2 * (600 / wl)
        M[:, :, i] = retarder(theta=0.0, delta=delta, tau=1.0)

    return M


@pytest.fixture
def intensity_data(wavelengths):
    """Create synthetic intensity data."""
    n_angles = 96
    n_wl = len(wavelengths)

    omega = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)
    intensity = np.zeros((n_angles, n_wl))

    for i, wl in enumerate(wavelengths):
        # Modulated signal with wavelength-dependent amplitude
        dc = 1000 * (wl / 600)
        ac = 300 * np.sin(wl / 100)
        intensity[:, i] = dc + ac * np.cos(2 * omega) + ac * 0.5 * np.cos(10 * omega)

    return intensity, omega


@pytest.fixture
def lu_result(mueller_matrices):
    """Create Lu-Chipman decomposition result."""
    return lu_chipman_decomposition(mueller_matrices)


@pytest.fixture
def temp_dir():
    """Create temporary directory for saving test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# TEST: Figure Utilities
# =============================================================================

class TestFigureUtils:
    """Tests for figure utility functions."""

    def test_setup_figure_creates_figure(self):
        """setup_figure should return a Figure object."""
        fig = setup_figure('Test Figure')
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_setup_figure_custom_size(self):
        """setup_figure should respect figsize parameter."""
        fig = setup_figure('Test', figsize=(12, 8))
        size = fig.get_size_inches()
        assert_allclose = np.testing.assert_allclose
        assert_allclose(size, [12, 8], rtol=0.1)
        plt.close(fig)

    def test_get_publication_colors_returns_dict(self):
        """get_publication_colors should return dictionary of colors."""
        colors = get_publication_colors()
        assert isinstance(colors, dict)
        assert 'blue' in colors
        assert 'orange' in colors
        assert 'green' in colors

    def test_publication_colors_are_rgb(self):
        """Colors should be RGB tuples with values in [0, 1]."""
        colors = get_publication_colors()
        for name, color in colors.items():
            assert len(color) == 3
            for val in color:
                assert 0.0 <= val <= 1.0

    def test_get_color_cycle_returns_list(self):
        """get_color_cycle should return list of colors."""
        cycle = get_color_cycle()
        assert isinstance(cycle, list)
        assert len(cycle) >= 5

    def test_format_axes(self):
        """format_axes should set labels and formatting."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])

        format_axes(ax, xlabel='X Label', ylabel='Y Label', title='Title')

        assert ax.get_xlabel() == 'X Label'
        assert ax.get_ylabel() == 'Y Label'
        assert ax.get_title() == 'Title'
        plt.close(fig)

    def test_publication_rcparams_dict(self):
        """PUBLICATION_RCPARAMS should contain expected keys."""
        assert 'font.size' in PUBLICATION_RCPARAMS
        assert 'lines.linewidth' in PUBLICATION_RCPARAMS
        assert PUBLICATION_RCPARAMS['font.size'] == 14
        assert PUBLICATION_RCPARAMS['lines.linewidth'] == 1.5


# =============================================================================
# TEST: Mueller Matrix Plots
# =============================================================================

class TestMuellerPlots:
    """Tests for Mueller matrix plotting functions."""

    def test_plot_mueller_matrix_creates_figure(self, mueller_matrices, wavelengths):
        """plot_mueller_matrix should create figure."""
        fig = plot_mueller_matrix(mueller_matrices, wavelengths)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_mueller_matrix_has_16_subplots(self, mueller_matrices, wavelengths):
        """Should create 4×4 = 16 subplots."""
        fig = plot_mueller_matrix(mueller_matrices, wavelengths)

        axes = fig.get_axes()
        assert len(axes) == 16
        plt.close(fig)

    def test_plot_mueller_matrix_with_title(self, mueller_matrices, wavelengths):
        """Should include title when provided."""
        fig = plot_mueller_matrix(mueller_matrices, wavelengths, title='Test Title')

        # Check suptitle
        assert fig._suptitle is not None
        assert 'Test' in fig._suptitle.get_text()
        plt.close(fig)

    def test_plot_mueller_matrix_save(self, mueller_matrices, wavelengths, temp_dir):
        """Should save figure when save_path provided."""
        save_path = temp_dir / 'mueller_test.png'
        fig = plot_mueller_matrix(mueller_matrices, wavelengths, save_path=save_path)

        assert save_path.exists()
        plt.close(fig)

    def test_plot_mueller_element_creates_axes(self, mueller_matrices, wavelengths):
        """plot_mueller_element should create axes."""
        ax = plot_mueller_element(mueller_matrices, wavelengths, 0, 0)

        assert isinstance(ax, plt.Axes)
        plt.close(ax.figure)

    def test_plot_mueller_element_on_existing_axes(self, mueller_matrices, wavelengths):
        """Should plot on provided axes."""
        fig, ax = plt.subplots()
        result_ax = plot_mueller_element(mueller_matrices, wavelengths, 1, 0, ax=ax)

        assert result_ax is ax
        plt.close(fig)


# =============================================================================
# TEST: Parameter Plots
# =============================================================================

class TestParameterPlots:
    """Tests for polarimetric parameter plotting functions."""

    def test_plot_polarimetric_parameters_returns_dict(self, lu_result, wavelengths):
        """Should return dictionary with 4 figures."""
        figures = plot_polarimetric_parameters(lu_result, wavelengths)

        assert isinstance(figures, dict)
        assert 'DI' in figures
        assert 'retardance' in figures
        assert 'diattenuation' in figures
        assert 'axis' in figures

        for fig in figures.values():
            plt.close(fig)

    def test_plot_depolarization_index(self, lu_result, wavelengths):
        """Should create DI plot."""
        fig = plot_depolarization_index(lu_result.DI, wavelengths)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_retardance_has_two_subplots(self, lu_result, wavelengths):
        """Retardance plot should have 2 subplots (degrees and waves)."""
        fig = plot_retardance(lu_result.R_deg, lu_result.R_waves, wavelengths)

        axes = fig.get_axes()
        assert len(axes) == 2
        plt.close(fig)

    def test_plot_diattenuation(self, lu_result, wavelengths):
        """Should create diattenuation plot."""
        fig = plot_diattenuation(lu_result.D, wavelengths)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_retarder_axis_has_two_subplots(self, lu_result, wavelengths):
        """Axis plot should have 2 subplots (ψ and χ)."""
        fig = plot_retarder_axis(lu_result.psi_deg, lu_result.chi_deg, wavelengths)

        axes = fig.get_axes()
        assert len(axes) == 2
        plt.close(fig)

    def test_save_all_parameter_plots(self, lu_result, wavelengths, temp_dir):
        """Should save all figures to directory."""
        figures = plot_polarimetric_parameters(
            lu_result, wavelengths, sample_name='test', save_dir=temp_dir
        )

        assert (temp_dir / 'DI.png').exists()
        assert (temp_dir / 'retardance.png').exists()
        assert (temp_dir / 'diattenuation.png').exists()
        assert (temp_dir / 'axis.png').exists()

        for fig in figures.values():
            plt.close(fig)


# =============================================================================
# TEST: Decomposition Plots
# =============================================================================

class TestDecompositionPlots:
    """Tests for decomposed matrix plotting functions."""

    def test_plot_decomposed_matrices_returns_dict(self, lu_result, wavelengths):
        """Should return dictionary with 3 figures."""
        figures = plot_decomposed_matrices(lu_result, wavelengths)

        assert isinstance(figures, dict)
        assert 'M_D' in figures
        assert 'M_R' in figures
        assert 'M_Delta' in figures

        for fig in figures.values():
            plt.close(fig)

    def test_plot_decomposed_matrix_d(self, lu_result, wavelengths):
        """Should create M_D plot."""
        fig = plot_decomposed_matrix(lu_result.M_D, wavelengths, 'D')

        assert isinstance(fig, plt.Figure)
        axes = fig.get_axes()
        assert len(axes) == 16
        plt.close(fig)

    def test_plot_decomposed_matrix_r(self, lu_result, wavelengths):
        """Should create M_R plot."""
        fig = plot_decomposed_matrix(lu_result.M_R, wavelengths, 'R')

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_decomposed_matrix_delta(self, lu_result, wavelengths):
        """Should create M_Δ plot."""
        fig = plot_decomposed_matrix(lu_result.M_Delta, wavelengths, 'Delta')

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_invalid_matrix_type_raises(self, wavelengths):
        """Should raise error for invalid matrix type."""
        M = np.eye(4)

        with pytest.raises(ValueError, match="matrix_type"):
            plot_decomposed_matrix(M, wavelengths, 'invalid')


# =============================================================================
# TEST: Intensity Plots
# =============================================================================

class TestIntensityPlots:
    """Tests for intensity data plotting functions."""

    def test_plot_intensity_data_has_four_panels(self, intensity_data, wavelengths):
        """Should create 2×2 = 4 subplot figure."""
        intensity, omega = intensity_data
        fig = plot_intensity_data(intensity, wavelengths, omega)

        axes = fig.get_axes()
        # 4 panels + 1 colorbar
        assert len(axes) >= 4
        plt.close(fig)

    def test_plot_intensity_data_without_omega(self, intensity_data, wavelengths):
        """Should work without explicit omega array."""
        intensity, _ = intensity_data
        fig = plot_intensity_data(intensity, wavelengths)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_intensity_heatmap(self, intensity_data, wavelengths):
        """Should create heatmap."""
        intensity, omega = intensity_data
        fig = plot_intensity_heatmap(intensity, wavelengths, omega)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_intensity_plot_save(self, intensity_data, wavelengths, temp_dir):
        """Should save figure."""
        intensity, omega = intensity_data
        save_path = temp_dir / 'intensity.png'

        fig = plot_intensity_data(intensity, wavelengths, omega, save_path=save_path)

        assert save_path.exists()
        plt.close(fig)


# =============================================================================
# TEST: Save Utilities
# =============================================================================

class TestSaveUtilities:
    """Tests for figure saving utilities."""

    def test_save_figure_png(self, temp_dir):
        """Should save PNG file."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])

        saved = save_figure(fig, temp_dir / 'test.png')

        assert len(saved) == 1
        assert saved[0].suffix == '.png'
        assert saved[0].exists()
        plt.close(fig)

    def test_save_figure_multiple_formats(self, temp_dir):
        """Should save multiple formats."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])

        saved = save_figure(fig, temp_dir / 'test', formats=['png', 'pdf'])

        assert len(saved) == 2
        assert (temp_dir / 'test.png').exists()
        assert (temp_dir / 'test.pdf').exists()
        plt.close(fig)

    def test_save_figure_creates_directory(self, temp_dir):
        """Should create parent directories."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])

        subdir = temp_dir / 'subdir' / 'nested'
        saved = save_figure(fig, subdir / 'test.png')

        assert saved[0].exists()
        plt.close(fig)


# =============================================================================
# TEST: Plot Content Validation
# =============================================================================

class TestPlotContent:
    """Tests that verify plot content is correct."""

    def test_mueller_plot_element_order(self, mueller_matrices, wavelengths):
        """Elements should be in correct order (row-major)."""
        fig = plot_mueller_matrix(mueller_matrices, wavelengths, normalized=True)

        axes = fig.get_axes()

        # First row should have m_11, m_12, m_13, m_14 (mathtext format)
        expected_titles = [r'$m_{11}$', r'$m_{12}$', r'$m_{13}$', r'$m_{14}$']
        for i, title in enumerate(expected_titles):
            assert title == axes[i].get_title()

        plt.close(fig)

    def test_parameter_plot_reference_lines(self, lu_result, wavelengths):
        """Retardance plot should have QWP and HWP reference lines."""
        fig = plot_retardance(lu_result.R_deg, lu_result.R_waves, wavelengths)

        ax = fig.get_axes()[0]  # First subplot (degrees)
        lines = ax.get_lines()

        # Should have data line plus at least 2 reference lines
        assert len(lines) >= 1

        plt.close(fig)
