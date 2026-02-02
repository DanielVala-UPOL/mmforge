"""
Tests for ECM Diagnostics Module

Tests the calibration diagnostics functions including Fourier analysis
and diagnostic plotting.
"""

import numpy as np
import pytest
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for testing
import matplotlib.pyplot as plt
from pathlib import Path
import tempfile
from numpy.testing import assert_allclose

from ecm.diagnostics.calibration_diagnostics import (
    CalibrationDiagnosticsReport,
    FourierSpectrum,
    compute_fourier_spectrum,
    fit_and_reconstruct_fourier,
    plot_fourier_harmonics,
    plot_w_matrix_elements,
    plot_a_matrix_elements,
    plot_eigenvalue_analysis,
    plot_air_mueller_validation,
    run_calibration_diagnostics,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def wavelengths():
    """Create test wavelength array."""
    return np.linspace(400, 800, 50)


@pytest.fixture
def synthetic_intensity():
    """Create synthetic intensity with known Fourier content."""
    n_angles = 96
    theta = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)

    # Known harmonics: DC=100, 2nd=20, 10th=15, 12th=10
    intensity = (
        100.0  # DC
        + 20.0 * np.cos(2 * theta) + 10.0 * np.sin(2 * theta)  # 2nd harmonic
        + 15.0 * np.cos(10 * theta)  # 10th harmonic
        + 10.0 * np.cos(12 * theta)  # 12th harmonic
    )

    return intensity


@pytest.fixture
def calibration_matrices(wavelengths):
    """Create synthetic W and A matrices."""
    n_wl = len(wavelengths)

    W = np.zeros((4, 4, n_wl))
    A = np.zeros((4, 4, n_wl))

    for k in range(n_wl):
        # Wavelength-dependent variation
        scale = 1.0 + 0.1 * np.sin(2 * np.pi * k / n_wl)
        W[:, :, k] = np.eye(4) * scale
        A[:, :, k] = np.eye(4) * scale

    return W, A


@pytest.fixture
def eigenvalue_ratios(wavelengths):
    """Create synthetic eigenvalue ratios."""
    n_wl = len(wavelengths)
    return 1e-8 * np.ones(n_wl) * (1 + 0.1 * np.random.randn(n_wl))


@pytest.fixture
def condition_numbers(wavelengths):
    """Create synthetic condition numbers."""
    n_wl = len(wavelengths)
    cond_W = 2.0 + 0.1 * np.random.randn(n_wl)
    cond_A = 2.5 + 0.1 * np.random.randn(n_wl)
    return cond_W, cond_A


@pytest.fixture
def air_mueller(wavelengths):
    """Create near-identity air Mueller matrices."""
    n_wl = len(wavelengths)
    M_air = np.zeros((4, 4, n_wl))

    for k in range(n_wl):
        M_air[:, :, k] = np.eye(4) + 0.01 * np.random.randn(4, 4)
        M_air[0, 0, k] = 1.0  # Ensure normalized

    return M_air


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# TEST: Fourier Analysis
# =============================================================================

class TestFourierAnalysis:
    """Tests for Fourier analysis functions."""

    def test_compute_fourier_spectrum_output_type(self, synthetic_intensity):
        """Should return FourierSpectrum object."""
        spectrum = compute_fourier_spectrum(synthetic_intensity)
        assert isinstance(spectrum, FourierSpectrum)

    def test_fourier_spectrum_dc_component(self, synthetic_intensity):
        """DC component should be mean of signal."""
        spectrum = compute_fourier_spectrum(synthetic_intensity)
        assert_allclose(spectrum.dc, np.mean(synthetic_intensity), rtol=1e-10)

    def test_fourier_spectrum_amplitude_shape(self, synthetic_intensity):
        """Amplitude array should have max_harmonic + 1 elements."""
        max_harm = 48
        spectrum = compute_fourier_spectrum(synthetic_intensity, max_harmonic=max_harm)
        assert len(spectrum.amplitude) == max_harm + 1

    def test_fourier_spectrum_known_harmonics(self, synthetic_intensity):
        """Should correctly identify known harmonics."""
        spectrum = compute_fourier_spectrum(synthetic_intensity, max_harmonic=24)

        # DC component = 100
        assert_allclose(spectrum.amplitude[0], 100.0, rtol=0.01)

        # 2nd harmonic amplitude = sqrt(20^2 + 10^2) ≈ 22.36
        expected_2 = np.sqrt(20**2 + 10**2)
        assert_allclose(spectrum.amplitude[2], expected_2, rtol=0.01)

        # 10th harmonic = 15
        assert_allclose(spectrum.amplitude[10], 15.0, rtol=0.01)

        # 12th harmonic = 10
        assert_allclose(spectrum.amplitude[12], 10.0, rtol=0.01)

    def test_fourier_spectrum_zero_harmonics(self, synthetic_intensity):
        """Harmonics not in signal should be near zero."""
        spectrum = compute_fourier_spectrum(synthetic_intensity, max_harmonic=24)

        # 5th harmonic should be near zero
        assert np.abs(spectrum.amplitude[5]) < 0.1

        # 15th harmonic should be near zero
        assert np.abs(spectrum.amplitude[15]) < 0.1

    def test_fit_and_reconstruct_residual_small(self, synthetic_intensity):
        """Residual should be small for Fourier fit of harmonic signal."""
        I_fit, residual = fit_and_reconstruct_fourier(synthetic_intensity, max_harmonic=24)

        # Residual RMS should be very small
        residual_rms = np.sqrt(np.mean(residual**2))
        assert residual_rms < 0.1

    def test_fit_preserves_signal_energy(self, synthetic_intensity):
        """Reconstructed signal should have similar energy to original."""
        I_fit, _ = fit_and_reconstruct_fourier(synthetic_intensity, max_harmonic=24)

        original_energy = np.sum(synthetic_intensity**2)
        fit_energy = np.sum(I_fit**2)

        assert_allclose(fit_energy, original_energy, rtol=0.01)


# =============================================================================
# TEST: Diagnostic Plots
# =============================================================================

class TestDiagnosticPlots:
    """Tests for diagnostic plotting functions."""

    def test_plot_w_matrix_elements(self, calibration_matrices, wavelengths):
        """Should create W matrix plot."""
        W, _ = calibration_matrices
        fig = plot_w_matrix_elements(W, wavelengths)

        assert isinstance(fig, plt.Figure)
        assert len(fig.get_axes()) == 16
        plt.close(fig)

    def test_plot_a_matrix_elements(self, calibration_matrices, wavelengths):
        """Should create A matrix plot."""
        _, A = calibration_matrices
        fig = plot_a_matrix_elements(A, wavelengths)

        assert isinstance(fig, plt.Figure)
        assert len(fig.get_axes()) == 16
        plt.close(fig)

    def test_plot_eigenvalue_analysis(self, eigenvalue_ratios, wavelengths):
        """Should create eigenvalue ratio plot."""
        fig = plot_eigenvalue_analysis(eigenvalue_ratios, wavelengths)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_air_mueller_validation(self, air_mueller, wavelengths):
        """Should create air validation plot with 2 panels."""
        fig = plot_air_mueller_validation(air_mueller, wavelengths)

        assert isinstance(fig, plt.Figure)
        assert len(fig.get_axes()) == 2
        plt.close(fig)

    def test_plot_fourier_harmonics(self, synthetic_intensity):
        """Should create Fourier harmonics plot."""
        spectrum = compute_fourier_spectrum(synthetic_intensity)
        spectra = {'test_sample': spectrum}

        fig = plot_fourier_harmonics(spectra, test_wavelength=550.0)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_save(self, calibration_matrices, wavelengths, temp_dir):
        """Plots should save to file."""
        W, _ = calibration_matrices
        save_path = temp_dir / 'W_test.png'

        fig = plot_w_matrix_elements(W, wavelengths, save_path=save_path)

        assert save_path.exists()
        plt.close(fig)


# =============================================================================
# TEST: Full Diagnostics Report
# =============================================================================

class TestDiagnosticsReport:
    """Tests for run_calibration_diagnostics function."""

    def test_report_output_type(
        self, calibration_matrices, wavelengths,
        eigenvalue_ratios, condition_numbers
    ):
        """Should return CalibrationDiagnosticsReport."""
        W, A = calibration_matrices
        cond_W, cond_A = condition_numbers

        report = run_calibration_diagnostics(
            W, A, wavelengths, eigenvalue_ratios, cond_W, cond_A,
            verbose=False
        )

        assert isinstance(report, CalibrationDiagnosticsReport)

        # Close all generated figures
        for fig in report.figures.values():
            plt.close(fig)

    def test_report_eigenvalue_stats(
        self, calibration_matrices, wavelengths,
        eigenvalue_ratios, condition_numbers
    ):
        """Report should contain eigenvalue ratio statistics."""
        W, A = calibration_matrices
        cond_W, cond_A = condition_numbers

        report = run_calibration_diagnostics(
            W, A, wavelengths, eigenvalue_ratios, cond_W, cond_A,
            verbose=False
        )

        stats = report.eigenvalue_ratio_stats
        assert 'mean' in stats
        assert 'median' in stats
        assert 'max' in stats
        assert 'min' in stats

        # Verify statistics match input
        assert_allclose(stats['mean'], np.mean(eigenvalue_ratios), rtol=1e-10)

        for fig in report.figures.values():
            plt.close(fig)

    def test_report_condition_number_stats(
        self, calibration_matrices, wavelengths,
        eigenvalue_ratios, condition_numbers
    ):
        """Report should contain condition number statistics."""
        W, A = calibration_matrices
        cond_W, cond_A = condition_numbers

        report = run_calibration_diagnostics(
            W, A, wavelengths, eigenvalue_ratios, cond_W, cond_A,
            verbose=False
        )

        stats = report.condition_number_stats
        assert 'W' in stats
        assert 'A' in stats
        assert 'mean' in stats['W']

        for fig in report.figures.values():
            plt.close(fig)

    def test_report_with_air_mueller(
        self, calibration_matrices, wavelengths,
        eigenvalue_ratios, condition_numbers, air_mueller
    ):
        """Report should include air Mueller validation when provided."""
        W, A = calibration_matrices
        cond_W, cond_A = condition_numbers

        report = run_calibration_diagnostics(
            W, A, wavelengths, eigenvalue_ratios, cond_W, cond_A,
            M_air=air_mueller,
            verbose=False
        )

        assert 'air_validation' in report.figures
        assert 'diagonal_mean' in report.air_mueller_deviation

        for fig in report.figures.values():
            plt.close(fig)

    def test_report_summary_text(
        self, calibration_matrices, wavelengths,
        eigenvalue_ratios, condition_numbers
    ):
        """Report should include summary text."""
        W, A = calibration_matrices
        cond_W, cond_A = condition_numbers

        report = run_calibration_diagnostics(
            W, A, wavelengths, eigenvalue_ratios, cond_W, cond_A,
            verbose=False
        )

        assert isinstance(report.summary_text, str)
        assert 'Eigenvalue' in report.summary_text
        assert 'Condition' in report.summary_text

        for fig in report.figures.values():
            plt.close(fig)

    def test_report_save_figures(
        self, calibration_matrices, wavelengths,
        eigenvalue_ratios, condition_numbers, temp_dir
    ):
        """Should save all figures when save_dir provided."""
        W, A = calibration_matrices
        cond_W, cond_A = condition_numbers

        report = run_calibration_diagnostics(
            W, A, wavelengths, eigenvalue_ratios, cond_W, cond_A,
            save_dir=temp_dir,
            verbose=False
        )

        assert (temp_dir / 'W_matrix_elements.png').exists()
        assert (temp_dir / 'A_matrix_elements.png').exists()
        assert (temp_dir / 'eigenvalue_ratio.png').exists()

        for fig in report.figures.values():
            plt.close(fig)


# =============================================================================
# TEST: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_fourier_single_sample(self):
        """Should handle very short signals."""
        intensity = np.array([100, 50, 100, 50])
        spectrum = compute_fourier_spectrum(intensity, max_harmonic=2)

        assert len(spectrum.amplitude) == 3
        assert spectrum.dc == 75.0  # Mean

    def test_constant_signal(self):
        """Constant signal should have only DC component."""
        n = 96
        intensity = np.full(n, 500.0)

        spectrum = compute_fourier_spectrum(intensity, max_harmonic=24)

        assert_allclose(spectrum.dc, 500.0, rtol=1e-10)
        assert_allclose(spectrum.amplitude[1:], 0.0, atol=1e-10)

    def test_single_harmonic_signal(self):
        """Single harmonic signal should be detected correctly."""
        n = 96
        theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
        intensity = 100 + 50 * np.cos(5 * theta)  # DC + 5th harmonic

        spectrum = compute_fourier_spectrum(intensity, max_harmonic=24)

        assert_allclose(spectrum.dc, 100.0, rtol=0.01)
        assert_allclose(spectrum.amplitude[5], 50.0, rtol=0.01)

        # Other harmonics should be near zero
        for k in [1, 2, 3, 4, 6, 7, 8]:
            assert np.abs(spectrum.amplitude[k]) < 0.1
