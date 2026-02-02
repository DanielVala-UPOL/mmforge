"""
Tests for ECM Calibration I/O Module

Tests calibration save/load and sample file discovery functions.
"""

import json
import numpy as np
import pytest
import tempfile
from pathlib import Path
from numpy.testing import assert_allclose, assert_array_equal

from ecm.config import ECMConfig
from ecm.io.calibration_io import (
    save_calibration,
    load_calibration,
    get_calibration_info,
    CalibrationMetadata,
    CALIBRATION_FILE_VERSION,
    LIBRARY_VERSION,
)
from ecm.io.sample_discovery import (
    discover_sample_files,
    list_all_files,
    SampleFiles,
    _extract_sample_name,
    CALIBRATION_KEYWORDS,
)
from ecm.core.transmission_calibration import (
    CalibrationResult,
    CalibrationDiagnostics,
    RetarderCalibrationParams,
)
from ecm.core.file_discovery import CalibrationFiles


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def wavelengths():
    """Create test wavelength array."""
    return np.linspace(400, 800, 50)


@pytest.fixture
def mock_calibration_result(wavelengths):
    """Create mock CalibrationResult for testing."""
    n_wl = len(wavelengths)
    n_angles = 96

    # Create mock W and A matrices (identity-like)
    W = np.zeros((4, 4, n_wl))
    A = np.zeros((4, 4, n_wl))
    for k in range(n_wl):
        W[:, :, k] = np.eye(4) * (1 + 0.01 * np.sin(2 * np.pi * k / n_wl))
        A[:, :, k] = np.eye(4) * (1 + 0.01 * np.cos(2 * np.pi * k / n_wl))

    # Polarizer angles
    pol_theta = np.zeros((2, n_wl))
    pol_theta[0, :] = 0.0
    pol_theta[1, :] = np.pi / 4

    # Retarder parameters
    ret_params = RetarderCalibrationParams(
        tau=np.ones(n_wl) * 0.95,
        delta=np.ones(n_wl) * np.pi / 2,  # QWP
        theta=np.ones(n_wl) * np.pi / 2,
        psi=np.ones(n_wl) * np.pi / 4,
    )

    # Mock calibration files
    cal_files = CalibrationFiles(
        dark=Path('/data/dark.bin'),
        air=Path('/data/air.bin'),
        pol_0=Path('/data/pol0.bin'),
        pol_45=Path('/data/pol45.bin'),
        ret_90=Path('/data/ret90.bin'),
        ret_45=None,
        has_second_retarder=False,
    )

    # Mock inv_W_mod
    inv_W_mod = np.random.randn(16, n_angles)

    return CalibrationResult(
        W=W,
        A=A,
        wavelengths=wavelengths,
        pol_theta=pol_theta,
        ret_params=ret_params,
        ret45_params=None,
        inv_W_mod=inv_W_mod,
        wl_indices=np.arange(n_wl),
        cal_files=cal_files,
        use_ret45=False,
    )


@pytest.fixture
def mock_calibration_diagnostics(wavelengths):
    """Create mock CalibrationDiagnostics for testing."""
    n_wl = len(wavelengths)
    n_angles = 96

    # Create mock B matrices
    B_air = np.random.randn(4, 4, n_wl) * 0.1 + np.eye(4)[:, :, np.newaxis]
    B_pol0 = np.random.randn(4, 4, n_wl) * 0.1
    B_pol45 = np.random.randn(4, 4, n_wl) * 0.1
    B_ret = np.random.randn(4, 4, n_wl) * 0.1

    return CalibrationDiagnostics(
        eigenvalue_ratio=1e-6 * np.ones(n_wl),
        cond_W=2.0 + 0.1 * np.random.randn(n_wl),
        cond_A=2.5 + 0.1 * np.random.randn(n_wl),
        B_air=B_air,
        B_pol0=B_pol0,
        B_pol45=B_pol45,
        B_ret=B_ret,
        B_ret45=None,
        I_dark=np.random.randn(n_angles, n_wl) * 10 + 100,
        pol0_params={'tau': np.ones(n_wl) * 0.48},
        pol45_params={'tau': np.ones(n_wl) * 0.49},
    )


@pytest.fixture
def mock_config():
    """Create mock ECMConfig for testing."""
    cfg = ECMConfig()
    cfg.mode = 'transmission'
    return cfg


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_directory(temp_dir):
    """Create mock sample directory with test files."""
    samples_dir = temp_dir / 'samples'
    samples_dir.mkdir()

    # Create sample files (extensionless binary format)
    sample_files = [
        '260109_QWP_0deg',
        '260109_QWP_45deg',
        '260109_HWP_0deg',
        '260109_AIR_SAMPLE',
    ]
    for name in sample_files:
        (samples_dir / name).touch()

    # Create calibration files (should be excluded)
    calibration_files = [
        '260109_DARK_ECM_1',
        '260109_ST_ECM_1',
        '260109_P0_ECM_1',
        '260109_P45_ECM_1',
        '260109_RET90_FP1_ECM_1',
    ]
    for name in calibration_files:
        (samples_dir / name).touch()

    # Create other files (should be excluded by extension)
    other_files = [
        'readme.txt',
        'notes.md',
        'data.csv',
    ]
    for name in other_files:
        (samples_dir / name).touch()

    return samples_dir


# =============================================================================
# TEST: CalibrationMetadata
# =============================================================================

class TestCalibrationMetadata:
    """Tests for CalibrationMetadata dataclass."""

    def test_metadata_fields(self):
        """Should have all required fields."""
        metadata = CalibrationMetadata(
            timestamp='2024-01-15T10:30:00',
            file_version='1.0.0',
            library_version='6.5.5',
            mode='transmission',
            n_wavelengths=100,
            wavelength_range=(400.0, 800.0),
            use_ret45=False,
            mean_eigenvalue_ratio=1e-6,
            calibration_files={},
        )

        assert metadata.timestamp == '2024-01-15T10:30:00'
        assert metadata.file_version == '1.0.0'
        assert metadata.mode == 'transmission'
        assert metadata.n_wavelengths == 100


# =============================================================================
# TEST: Save Calibration
# =============================================================================

class TestSaveCalibration:
    """Tests for save_calibration function."""

    def test_save_creates_file(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Should create .npz file."""
        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            verbose=False,
        )

        assert filepath.exists()
        assert filepath.suffix == '.npz'

    def test_save_with_custom_filename(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Should use custom filename when provided."""
        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            filename='my_calibration.npz',
            verbose=False,
        )

        assert filepath.name == 'my_calibration.npz'

    def test_save_with_full_path(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Should accept full file path."""
        full_path = temp_dir / 'subdir' / 'calibration.npz'

        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=full_path,
            verbose=False,
        )

        assert filepath == full_path
        assert filepath.exists()

    def test_save_contains_required_arrays(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Saved file should contain all required arrays."""
        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            verbose=False,
        )

        with np.load(filepath, allow_pickle=True) as data:
            # Core matrices
            assert 'W' in data
            assert 'A' in data
            assert 'wavelengths' in data

            # Parameters
            assert 'ret_delta' in data
            assert 'ret_tau' in data

            # Diagnostics
            assert 'eigenvalue_ratio' in data
            assert 'cond_W' in data
            assert 'cond_A' in data

            # Metadata
            assert 'metadata_json' in data
            assert 'config_json' in data

    def test_save_array_shapes_correct(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Saved arrays should have correct shapes."""
        n_wl = len(mock_calibration_result.wavelengths)

        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            verbose=False,
        )

        with np.load(filepath) as data:
            assert data['W'].shape == (4, 4, n_wl)
            assert data['A'].shape == (4, 4, n_wl)
            assert data['wavelengths'].shape == (n_wl,)
            assert data['eigenvalue_ratio'].shape == (n_wl,)


# =============================================================================
# TEST: Load Calibration
# =============================================================================

class TestLoadCalibration:
    """Tests for load_calibration function."""

    def test_load_returns_correct_types(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Should return correct object types."""
        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            verbose=False,
        )

        result, diagnostics, cfg, metadata = load_calibration(filepath, verbose=False)

        assert isinstance(result, CalibrationResult)
        assert isinstance(diagnostics, CalibrationDiagnostics)
        assert isinstance(cfg, ECMConfig)
        assert isinstance(metadata, CalibrationMetadata)

    def test_load_roundtrip_W_matrix(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """W matrix should survive save/load roundtrip."""
        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            verbose=False,
        )

        result, _, _, _ = load_calibration(filepath, verbose=False)

        assert_allclose(result.W, mock_calibration_result.W)

    def test_load_roundtrip_A_matrix(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """A matrix should survive save/load roundtrip."""
        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            verbose=False,
        )

        result, _, _, _ = load_calibration(filepath, verbose=False)

        assert_allclose(result.A, mock_calibration_result.A)

    def test_load_roundtrip_wavelengths(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Wavelengths should survive save/load roundtrip."""
        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            verbose=False,
        )

        result, _, _, _ = load_calibration(filepath, verbose=False)

        assert_allclose(result.wavelengths, mock_calibration_result.wavelengths)

    def test_load_roundtrip_retarder_params(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Retarder parameters should survive save/load roundtrip."""
        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            verbose=False,
        )

        result, _, _, _ = load_calibration(filepath, verbose=False)

        assert_allclose(result.ret_params.delta, mock_calibration_result.ret_params.delta)
        assert_allclose(result.ret_params.tau, mock_calibration_result.ret_params.tau)

    def test_load_roundtrip_diagnostics(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Diagnostics should survive save/load roundtrip."""
        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            verbose=False,
        )

        _, diagnostics, _, _ = load_calibration(filepath, verbose=False)

        assert_allclose(
            diagnostics.eigenvalue_ratio,
            mock_calibration_diagnostics.eigenvalue_ratio
        )
        assert_allclose(diagnostics.cond_W, mock_calibration_diagnostics.cond_W)

    def test_load_metadata_correct(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Metadata should be correct after load."""
        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            verbose=False,
        )

        _, _, _, metadata = load_calibration(filepath, verbose=False)

        assert metadata.file_version == CALIBRATION_FILE_VERSION
        assert metadata.library_version == LIBRARY_VERSION
        assert metadata.mode == 'transmission'
        assert metadata.n_wavelengths == len(mock_calibration_result.wavelengths)

    def test_load_nonexistent_file_raises(self, temp_dir):
        """Should raise FileNotFoundError for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            load_calibration(temp_dir / 'nonexistent.npz', verbose=False)

    def test_load_config_roundtrip(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Configuration should survive save/load roundtrip."""
        mock_config.wavelength.range_nm = (450.0, 850.0)

        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            verbose=False,
        )

        _, _, cfg, _ = load_calibration(filepath, verbose=False)

        assert cfg.wavelength.range_nm == (450.0, 850.0)
        assert cfg.mode == 'transmission'


# =============================================================================
# TEST: Get Calibration Info
# =============================================================================

class TestGetCalibrationInfo:
    """Tests for get_calibration_info function."""

    def test_get_info_returns_metadata(
        self, mock_calibration_result, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Should return CalibrationMetadata."""
        filepath = save_calibration(
            mock_calibration_result,
            mock_calibration_diagnostics,
            mock_config,
            output_path=temp_dir,
            verbose=False,
        )

        info = get_calibration_info(filepath)

        assert isinstance(info, CalibrationMetadata)
        assert info.n_wavelengths == len(mock_calibration_result.wavelengths)

    def test_get_info_nonexistent_file_raises(self, temp_dir):
        """Should raise FileNotFoundError for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            get_calibration_info(temp_dir / 'nonexistent.npz')


# =============================================================================
# TEST: Sample Discovery
# =============================================================================

class TestSampleDiscovery:
    """Tests for discover_sample_files function."""

    def test_discover_finds_samples(self, sample_directory, mock_config):
        """Should find sample files."""
        samples = discover_sample_files(sample_directory, mock_config, verbose=False)

        assert isinstance(samples, SampleFiles)
        assert samples.n_samples == 4  # 4 sample files

    def test_discover_excludes_calibration(self, sample_directory, mock_config):
        """Should exclude calibration files."""
        samples = discover_sample_files(sample_directory, mock_config, verbose=False)

        # Check that calibration keywords are not in sample names
        for name in samples.names:
            name_lower = name.lower()
            for keyword in CALIBRATION_KEYWORDS:
                assert keyword.lower() not in name_lower

    def test_discover_excludes_other_extensions(self, sample_directory, mock_config):
        """Should exclude files with non-binary extensions."""
        samples = discover_sample_files(sample_directory, mock_config, verbose=False)

        for path in samples.paths:
            # Should not have .txt, .md, .csv extensions
            assert path.suffix.lower() not in ['.txt', '.md', '.csv']

    def test_discover_returns_correct_mode(self, sample_directory, mock_config):
        """Should return correct mode from config."""
        samples = discover_sample_files(sample_directory, mock_config, verbose=False)

        assert samples.mode == mock_config.mode

    def test_discover_empty_directory(self, temp_dir, mock_config):
        """Should return empty result for empty directory."""
        empty_dir = temp_dir / 'empty'
        empty_dir.mkdir()

        samples = discover_sample_files(empty_dir, mock_config, verbose=False)

        assert samples.n_samples == 0
        assert len(samples.names) == 0
        assert len(samples.paths) == 0

    def test_discover_nonexistent_directory_raises(self, temp_dir, mock_config):
        """Should raise FileNotFoundError for nonexistent directory."""
        with pytest.raises(FileNotFoundError):
            discover_sample_files(temp_dir / 'nonexistent', mock_config, verbose=False)

    def test_discover_custom_exclude_patterns(self, sample_directory, mock_config):
        """Should exclude additional patterns."""
        samples = discover_sample_files(
            sample_directory, mock_config,
            exclude_patterns=['_AIR_'],
            verbose=False,
        )

        # AIR_SAMPLE should be excluded
        for name in samples.names:
            assert '_AIR_' not in name.upper()

    def test_sample_files_iteration(self, sample_directory, mock_config):
        """Should support iteration over (name, path) pairs."""
        samples = discover_sample_files(sample_directory, mock_config, verbose=False)

        for name, path in samples:
            assert isinstance(name, str)
            assert isinstance(path, Path)

    def test_sample_files_len(self, sample_directory, mock_config):
        """Should support len()."""
        samples = discover_sample_files(sample_directory, mock_config, verbose=False)

        assert len(samples) == samples.n_samples


# =============================================================================
# TEST: Extract Sample Name
# =============================================================================

class TestExtractSampleName:
    """Tests for _extract_sample_name helper."""

    def test_remove_extension(self):
        """Should remove file extension."""
        assert _extract_sample_name('sample.bin') == 'sample'

    def test_remove_sample_suffix(self):
        """Should remove _SAMPLE suffix."""
        assert _extract_sample_name('QWP_45deg_SAMPLE') == 'QWP_45deg'

    def test_remove_measurement_suffix(self):
        """Should remove _MEASUREMENT suffix."""
        assert _extract_sample_name('HWP_0deg_MEASUREMENT') == 'HWP_0deg'

    def test_preserve_clean_name(self):
        """Should preserve names without suffixes."""
        assert _extract_sample_name('260109_QWP_45deg') == '260109_QWP_45deg'

    def test_clean_trailing_underscores(self):
        """Should remove trailing underscores."""
        assert _extract_sample_name('sample_') == 'sample'


# =============================================================================
# TEST: List All Files
# =============================================================================

class TestListAllFiles:
    """Tests for list_all_files utility."""

    def test_categorizes_files(self, sample_directory):
        """Should categorize files correctly."""
        result = list_all_files(sample_directory, verbose=False)

        assert 'calibration' in result
        assert 'samples' in result
        assert 'other' in result

        # Should have found calibration files
        assert len(result['calibration']) == 5

        # Should have found sample files
        assert len(result['samples']) == 4

        # Should have found other files
        assert len(result['other']) == 3

    def test_nonexistent_directory_raises(self, temp_dir):
        """Should raise FileNotFoundError for nonexistent directory."""
        with pytest.raises(FileNotFoundError):
            list_all_files(temp_dir / 'nonexistent', verbose=False)


# =============================================================================
# TEST: Second Retarder Support
# =============================================================================

class TestSecondRetarderSupport:
    """Tests for second retarder save/load."""

    def test_save_load_with_second_retarder(
        self, wavelengths, mock_calibration_diagnostics,
        mock_config, temp_dir
    ):
        """Should save and load second retarder parameters."""
        n_wl = len(wavelengths)
        n_angles = 96

        # Create result with second retarder
        ret45_params = RetarderCalibrationParams(
            tau=np.ones(n_wl) * 0.93,
            delta=np.ones(n_wl) * np.pi,  # HWP
            theta=np.ones(n_wl) * np.pi / 4,
            psi=np.ones(n_wl) * np.pi / 4,
        )

        ret_params = RetarderCalibrationParams(
            tau=np.ones(n_wl) * 0.95,
            delta=np.ones(n_wl) * np.pi / 2,
            theta=np.ones(n_wl) * np.pi / 2,
            psi=np.ones(n_wl) * np.pi / 4,
        )

        result = CalibrationResult(
            W=np.eye(4)[:, :, np.newaxis] * np.ones(n_wl),
            A=np.eye(4)[:, :, np.newaxis] * np.ones(n_wl),
            wavelengths=wavelengths,
            pol_theta=np.zeros((2, n_wl)),
            ret_params=ret_params,
            ret45_params=ret45_params,
            inv_W_mod=np.random.randn(16, n_angles),
            wl_indices=np.arange(n_wl),
            cal_files=CalibrationFiles(
                dark=Path('.'), air=Path('.'), pol_0=Path('.'),
                pol_45=Path('.'), ret_90=Path('.'), ret_45=Path('.'),
                has_second_retarder=True,
            ),
            use_ret45=True,
        )

        # Add B_ret45 to diagnostics
        diagnostics = CalibrationDiagnostics(
            eigenvalue_ratio=mock_calibration_diagnostics.eigenvalue_ratio,
            cond_W=mock_calibration_diagnostics.cond_W,
            cond_A=mock_calibration_diagnostics.cond_A,
            B_air=mock_calibration_diagnostics.B_air,
            B_pol0=mock_calibration_diagnostics.B_pol0,
            B_pol45=mock_calibration_diagnostics.B_pol45,
            B_ret=mock_calibration_diagnostics.B_ret,
            B_ret45=np.random.randn(4, 4, n_wl),
            I_dark=mock_calibration_diagnostics.I_dark,
            pol0_params=mock_calibration_diagnostics.pol0_params,
            pol45_params=mock_calibration_diagnostics.pol45_params,
        )

        # Save and load
        filepath = save_calibration(result, diagnostics, mock_config,
                                    output_path=temp_dir, verbose=False)
        loaded_result, loaded_diag, _, metadata = load_calibration(filepath, verbose=False)

        # Verify
        assert loaded_result.use_ret45 is True
        assert loaded_result.ret45_params is not None
        assert_allclose(loaded_result.ret45_params.delta, ret45_params.delta)
        assert metadata.use_ret45 is True
