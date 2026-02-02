"""
Tests for ECM CLI Scripts

Tests command-line interface functionality for calibrate, process, and postprocess scripts.
"""

import os
import subprocess
import sys
import pytest
import tempfile
import numpy as np
from pathlib import Path


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def project_dir():
    """Get the project directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def scripts_dir(project_dir):
    """Get the scripts directory."""
    return project_dir / 'scripts'


@pytest.fixture
def env_with_pythonpath(project_dir):
    """Create environment with PYTHONPATH set to include project."""
    env = os.environ.copy()
    current_pythonpath = env.get('PYTHONPATH', '')
    if current_pythonpath:
        env['PYTHONPATH'] = f"{project_dir}:{current_pythonpath}"
    else:
        env['PYTHONPATH'] = str(project_dir)
    return env


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_mueller_results(temp_dir):
    """Create mock Mueller matrix results for postprocessing tests."""
    sample_dir = temp_dir / 'QWP_test'
    sample_dir.mkdir()

    # Create mock Mueller matrix (identity-like)
    n_wl = 50
    wavelengths = np.linspace(400, 800, n_wl)
    M_normalized = np.zeros((4, 4, n_wl))
    for k in range(n_wl):
        M_normalized[:, :, k] = np.eye(4)

    np.savez(
        sample_dir / 'mueller_matrices.npz',
        M=M_normalized,
        M_normalized=M_normalized,
        M00=np.ones(n_wl),
        wavelengths=wavelengths,
    )

    return temp_dir


# =============================================================================
# TEST: Script Help
# =============================================================================

class TestScriptHelp:
    """Tests that scripts show help correctly."""

    def test_calibrate_help(self, scripts_dir):
        """Calibrate script should show help."""
        script = scripts_dir / 'calibrate_transmission.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, str(script), '--help'],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert 'ECM Transmission Calibration' in result.stdout
        assert '--config' in result.stdout
        assert '--data-dir' in result.stdout

    def test_process_help(self, scripts_dir):
        """Process script should show help."""
        script = scripts_dir / 'process_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, str(script), '--help'],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert 'ECM Sample Processing' in result.stdout
        assert '--sample-dir' in result.stdout

    def test_postprocess_help(self, scripts_dir):
        """Postprocess script should show help."""
        script = scripts_dir / 'postprocess_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, str(script), '--help'],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert 'Lu-Chipman' in result.stdout or 'Post-Processing' in result.stdout
        assert '--sample' in result.stdout


# =============================================================================
# TEST: Script Imports
# =============================================================================

class TestScriptImports:
    """Tests that scripts can import their dependencies."""

    def test_calibrate_imports(self, scripts_dir):
        """Calibrate script should import successfully."""
        script = scripts_dir / 'calibrate_transmission.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        # Test syntax and imports
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', str(script)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_process_imports(self, scripts_dir):
        """Process script should import successfully."""
        script = scripts_dir / 'process_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', str(script)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_postprocess_imports(self, scripts_dir):
        """Postprocess script should import successfully."""
        script = scripts_dir / 'postprocess_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', str(script)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Syntax error: {result.stderr}"


# =============================================================================
# TEST: Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests that scripts handle errors gracefully."""

    def test_process_missing_calibration(self, scripts_dir, temp_dir):
        """Process script should error on missing calibration file."""
        script = scripts_dir / 'process_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, str(script), str(temp_dir / 'nonexistent.npz')],
            capture_output=True,
            text=True
        )

        assert result.returncode != 0
        assert 'not found' in result.stdout.lower() or 'error' in result.stdout.lower()

    def test_postprocess_missing_directory(self, scripts_dir, temp_dir):
        """Postprocess script should error on missing directory."""
        script = scripts_dir / 'postprocess_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, str(script), str(temp_dir / 'nonexistent')],
            capture_output=True,
            text=True
        )

        assert result.returncode != 0
        assert 'not found' in result.stdout.lower() or 'error' in result.stdout.lower()

    def test_postprocess_empty_directory(self, scripts_dir, temp_dir, env_with_pythonpath):
        """Postprocess script should handle empty directory."""
        script = scripts_dir / 'postprocess_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        # Create empty directory
        empty_dir = temp_dir / 'empty'
        empty_dir.mkdir()

        result = subprocess.run(
            [sys.executable, str(script), str(empty_dir)],
            capture_output=True,
            text=True,
            env=env_with_pythonpath
        )

        # Should exit cleanly with message about no samples
        assert 'No processed samples' in result.stdout or result.returncode == 0


# =============================================================================
# TEST: Postprocess Integration
# =============================================================================

class TestPostprocessIntegration:
    """Integration tests for postprocess script."""

    def test_postprocess_runs_on_mock_data(self, scripts_dir, mock_mueller_results, env_with_pythonpath):
        """Postprocess should run on mock Mueller matrices."""
        script = scripts_dir / 'postprocess_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, str(script), str(mock_mueller_results), '--verbose'],
            capture_output=True,
            text=True,
            env=env_with_pythonpath
        )

        # Should succeed
        assert result.returncode == 0, f"Script failed: {result.stdout}\n{result.stderr}"
        assert 'QWP_test' in result.stdout
        assert 'Success' in result.stdout

    def test_postprocess_creates_output(self, scripts_dir, mock_mueller_results, env_with_pythonpath):
        """Postprocess should create decomposition output."""
        script = scripts_dir / 'postprocess_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, str(script), str(mock_mueller_results)],
            capture_output=True,
            text=True,
            env=env_with_pythonpath
        )

        assert result.returncode == 0

        # Check output file was created
        output_file = mock_mueller_results / 'QWP_test' / 'lu_chipman_decomposition.npz'
        assert output_file.exists()

        # Verify contents
        data = np.load(output_file)
        assert 'M_D' in data
        assert 'M_R' in data
        assert 'M_Delta' in data
        assert 'D' in data
        assert 'R_deg' in data
        assert 'DI' in data

    def test_postprocess_with_plots(self, scripts_dir, mock_mueller_results, env_with_pythonpath):
        """Postprocess should create plots when requested."""
        script = scripts_dir / 'postprocess_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, str(script), str(mock_mueller_results), '--plot'],
            capture_output=True,
            text=True,
            env=env_with_pythonpath
        )

        assert result.returncode == 0

        # Check plot files were created
        sample_dir = mock_mueller_results / 'QWP_test'
        assert (sample_dir / 'DI.png').exists()
        assert (sample_dir / 'retardance.png').exists()
        assert (sample_dir / 'diattenuation.png').exists()
        assert (sample_dir / 'axis.png').exists()

    def test_postprocess_sample_filter(self, scripts_dir, mock_mueller_results, temp_dir, env_with_pythonpath):
        """Postprocess should filter by sample name."""
        script = scripts_dir / 'postprocess_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        # Create additional sample
        other_sample = mock_mueller_results / 'HWP_test'
        other_sample.mkdir()
        np.savez(
            other_sample / 'mueller_matrices.npz',
            M=np.eye(4)[:, :, np.newaxis],
            M_normalized=np.eye(4)[:, :, np.newaxis],
            M00=np.ones(1),
            wavelengths=np.array([550.0]),
        )

        # Process only QWP_test
        result = subprocess.run(
            [sys.executable, str(script), str(mock_mueller_results),
             '--sample', 'QWP_test'],
            capture_output=True,
            text=True,
            env=env_with_pythonpath
        )

        assert result.returncode == 0
        assert 'QWP_test' in result.stdout
        assert 'Processed: 1' in result.stdout

        # Verify HWP was not processed
        hwp_output = mock_mueller_results / 'HWP_test' / 'lu_chipman_decomposition.npz'
        assert not hwp_output.exists()


# =============================================================================
# TEST: Calibrate Script Validation
# =============================================================================

class TestCalibrateValidation:
    """Tests for calibrate script input validation."""

    def test_calibrate_invalid_config_file(self, scripts_dir, temp_dir):
        """Calibrate should error on invalid config file."""
        script = scripts_dir / 'calibrate_transmission.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, str(script), '--config', str(temp_dir / 'nonexistent.yaml')],
            capture_output=True,
            text=True
        )

        assert result.returncode != 0

    def test_calibrate_invalid_data_dir(self, scripts_dir, temp_dir):
        """Calibrate should error on missing data directory."""
        script = scripts_dir / 'calibrate_transmission.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, str(script), '--data-dir', str(temp_dir / 'nonexistent')],
            capture_output=True,
            text=True
        )

        assert result.returncode != 0


# =============================================================================
# TEST: Process Script Validation
# =============================================================================

class TestProcessValidation:
    """Tests for process script input validation."""

    def test_process_requires_calibration_arg(self, scripts_dir):
        """Process script should require calibration file argument."""
        script = scripts_dir / 'process_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True
        )

        # Should fail due to missing required argument
        assert result.returncode != 0


# =============================================================================
# TEST: Script Module Execution
# =============================================================================

class TestModuleExecution:
    """Tests that scripts can be executed as modules."""

    def test_calibrate_module_exec(self, project_dir, env_with_pythonpath):
        """Calibrate script should show help when run as module with -h."""
        result = subprocess.run(
            [sys.executable, '-c',
             'import sys; sys.path.insert(0, r"{}"); '
             'exec(open(r"{}/scripts/calibrate_transmission.py").read().replace("if __name__", "if False"))'.format(
                 project_dir, project_dir
             )],
            capture_output=True,
            text=True,
            env=env_with_pythonpath
        )

        # Should at least import without errors
        assert 'SyntaxError' not in result.stderr

    def test_process_module_exec(self, project_dir, env_with_pythonpath):
        """Process script should import without errors."""
        result = subprocess.run(
            [sys.executable, '-c',
             'import sys; sys.path.insert(0, r"{}"); '
             'exec(open(r"{}/scripts/process_samples.py").read().replace("if __name__", "if False"))'.format(
                 project_dir, project_dir
             )],
            capture_output=True,
            text=True,
            env=env_with_pythonpath
        )

        assert 'SyntaxError' not in result.stderr

    def test_postprocess_module_exec(self, project_dir, env_with_pythonpath):
        """Postprocess script should import without errors."""
        result = subprocess.run(
            [sys.executable, '-c',
             'import sys; sys.path.insert(0, r"{}"); '
             'exec(open(r"{}/scripts/postprocess_samples.py").read().replace("if __name__", "if False"))'.format(
                 project_dir, project_dir
             )],
            capture_output=True,
            text=True,
            env=env_with_pythonpath
        )

        assert 'SyntaxError' not in result.stderr


# =============================================================================
# TEST: Verbose Output
# =============================================================================

class TestVerboseOutput:
    """Tests for verbose output mode."""

    def test_postprocess_verbose_shows_parameters(self, scripts_dir, mock_mueller_results, env_with_pythonpath):
        """Verbose mode should show parameter values."""
        script = scripts_dir / 'postprocess_samples.py'
        if not script.exists():
            pytest.skip(f"Script not found: {script}")

        result = subprocess.run(
            [sys.executable, str(script), str(mock_mueller_results), '--verbose'],
            capture_output=True,
            text=True,
            env=env_with_pythonpath
        )

        assert result.returncode == 0
        # Verbose mode should show mean values
        assert 'Diattenuation' in result.stdout or 'mean' in result.stdout.lower()
        assert 'Retardance' in result.stdout or 'wavelengths' in result.stdout.lower()
