"""
Tests for Data I/O Functions

This test module validates the data loading functions for binary spectral
data and wavelength calibration files.

Test Categories
---------------
1. load_wavelengths: File loading, range selection, error handling
2. load_spectral_data: Binary loading, dimension handling, quality checks
3. SpectralDataInfo and WavelengthInfo: Dataclass integrity

These tests include both unit tests (with mock data) and integration tests
(with actual data files if available).
"""

import pytest
import tempfile
import numpy as np
from pathlib import Path

from ecm.config import ECMConfig
from ecm.utils.io import (
    load_spectral_data,
    load_wavelengths,
    SpectralDataInfo,
    WavelengthInfo,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_config() -> ECMConfig:
    """
    Create a sample configuration for testing.

    Returns
    -------
    ECMConfig
        Configuration with default settings.
    """
    cfg = ECMConfig()
    # Reduce verbosity for tests
    cfg.output.verbosity = 0
    return cfg


@pytest.fixture
def temp_wavelength_file() -> Path: # type: ignore
    """
    Create a temporary wavelength file for testing.

    Returns
    -------
    Path
        Path to the temporary wavelength file.
    """
    # Create wavelengths similar to BlackComet spectrometer
    # 2048 points from ~187 to ~1076 nm
    wavelengths = np.linspace(187.0, 1076.0, 2048)

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.txt', delete=False
    ) as f:
        for wl in wavelengths:
            f.write(f"{wl:.6f}\n")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink()


@pytest.fixture
def temp_binary_file() -> Path: # type: ignore
    """
    Create a temporary binary data file for testing.

    Returns
    -------
    Path
        Path to the temporary binary file.
    """
    # Create test data: 2048 wavelengths x 96 angles
    n_wavelengths = 2048
    n_angles = 96

    # Generate intensity data with some structure
    # Simulate modulated intensity vs angle
    angles = np.linspace(0, 2 * np.pi, n_angles)
    wavelengths = np.linspace(400, 1000, n_wavelengths)

    # Create data with wavelength-dependent baseline and angular modulation
    data = np.zeros((n_wavelengths, n_angles), dtype=np.float32)
    for i, wl in enumerate(wavelengths):
        baseline = 10000 + 5000 * np.sin((wl - 400) / 200)
        modulation = 1000 * np.cos(4 * angles)
        data[i, :] = baseline + modulation

    # Write as little-endian float32
    with tempfile.NamedTemporaryFile(
        mode='wb', suffix='.bin', delete=False
    ) as f:
        data.astype('<f4').tofile(f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink()


# =============================================================================
# TEST CLASS: WAVELENGTH LOADING
# =============================================================================

class TestLoadWavelengths:
    """
    Tests for load_wavelengths function.
    """

    def test_load_wavelengths_returns_correct_types(
        self,
        sample_config: ECMConfig,
        temp_wavelength_file: Path
    ) -> None:
        """
        load_wavelengths should return correct types.
        """
        sample_config.spectrometer.wavelength_file = temp_wavelength_file

        wavelengths, idx_range, info = load_wavelengths(sample_config)

        assert isinstance(wavelengths, np.ndarray)
        assert isinstance(idx_range, np.ndarray)
        assert isinstance(info, WavelengthInfo)

    def test_load_wavelengths_selects_range(
        self,
        sample_config: ECMConfig,
        temp_wavelength_file: Path
    ) -> None:
        """
        load_wavelengths should select wavelengths within configured range.
        """
        sample_config.spectrometer.wavelength_file = temp_wavelength_file
        sample_config.wavelength.range_nm = (400.0, 800.0)

        wavelengths, idx_range, info = load_wavelengths(sample_config)

        # All selected wavelengths should be within range
        assert wavelengths.min() >= 400.0
        assert wavelengths.max() <= 800.0

    def test_load_wavelengths_info_correct(
        self,
        sample_config: ECMConfig,
        temp_wavelength_file: Path
    ) -> None:
        """
        WavelengthInfo should contain correct metadata.
        """
        sample_config.spectrometer.wavelength_file = temp_wavelength_file
        sample_config.wavelength.range_nm = (400.0, 1000.0)

        wavelengths, idx_range, info = load_wavelengths(sample_config)

        assert info.n_total == 2048
        assert info.n_selected == len(wavelengths)
        assert len(wavelengths) == len(idx_range)
        assert info.range_nm[0] >= 400.0
        assert info.range_nm[1] <= 1000.0

    def test_load_wavelengths_idx_range_correct(
        self,
        sample_config: ECMConfig,
        temp_wavelength_file: Path
    ) -> None:
        """
        idx_range should correctly index into full wavelength array.
        """
        sample_config.spectrometer.wavelength_file = temp_wavelength_file
        sample_config.wavelength.range_nm = (400.0, 1000.0)

        wavelengths, idx_range, info = load_wavelengths(sample_config)

        # Check that using idx_range gives the same wavelengths
        reconstructed = info.all_wavelengths[idx_range]
        np.testing.assert_array_equal(wavelengths, reconstructed)

    def test_load_wavelengths_empty_range_raises(
        self,
        sample_config: ECMConfig,
        temp_wavelength_file: Path
    ) -> None:
        """
        Empty wavelength range should raise ValueError.
        """
        sample_config.spectrometer.wavelength_file = temp_wavelength_file
        sample_config.wavelength.range_nm = (1500.0, 2000.0)  # Outside data range

        with pytest.raises(ValueError, match="No wavelengths found"):
            load_wavelengths(sample_config)

    def test_load_wavelengths_file_not_found_raises(
        self,
        sample_config: ECMConfig
    ) -> None:
        """
        Missing wavelength file should raise FileNotFoundError.
        """
        sample_config.spectrometer.wavelength_file = Path("/nonexistent/file.txt")
        sample_config.paths.assets_dir = Path("/nonexistent/")
        sample_config.paths.data_dir = Path("/nonexistent/")

        with pytest.raises(FileNotFoundError):
            load_wavelengths(sample_config)


# =============================================================================
# TEST CLASS: SPECTRAL DATA LOADING
# =============================================================================

class TestLoadSpectralData:
    """
    Tests for load_spectral_data function.
    """

    def test_load_spectral_data_returns_correct_types(
        self,
        sample_config: ECMConfig,
        temp_binary_file: Path
    ) -> None:
        """
        load_spectral_data should return correct types.
        """
        data, info = load_spectral_data(temp_binary_file, sample_config)

        assert isinstance(data, np.ndarray)
        assert isinstance(info, SpectralDataInfo)

    def test_load_spectral_data_correct_shape(
        self,
        sample_config: ECMConfig,
        temp_binary_file: Path
    ) -> None:
        """
        Loaded data should have shape (n_angles, n_wavelengths).
        """
        data, info = load_spectral_data(temp_binary_file, sample_config)

        # Data should be transposed from file layout
        assert data.shape == (96, 2048)
        assert info.n_angles == 96
        assert info.n_wavelengths == 2048

    def test_load_spectral_data_is_float64(
        self,
        sample_config: ECMConfig,
        temp_binary_file: Path
    ) -> None:
        """
        Loaded data should be converted to float64.
        """
        data, info = load_spectral_data(temp_binary_file, sample_config)
        assert data.dtype == np.float64

    def test_load_spectral_data_info_correct(
        self,
        sample_config: ECMConfig,
        temp_binary_file: Path
    ) -> None:
        """
        SpectralDataInfo should contain correct metadata.
        """
        data, info = load_spectral_data(temp_binary_file, sample_config)

        assert info.filepath == temp_binary_file.resolve()
        assert info.n_wavelengths == 2048
        assert info.n_angles == 96
        assert info.file_size == 2048 * 96 * 4  # float32 = 4 bytes
        assert info.load_time > 0

    def test_load_spectral_data_file_not_found_raises(
        self,
        sample_config: ECMConfig
    ) -> None:
        """
        Missing data file should raise FileNotFoundError.
        """
        sample_config.paths.calibration_transmission_dir = Path("/nonexistent/")
        sample_config.paths.data_dir = Path("/nonexistent/")

        with pytest.raises(FileNotFoundError):
            load_spectral_data("/nonexistent/file.bin", sample_config)

    def test_load_spectral_data_values_preserved(
        self,
        sample_config: ECMConfig
    ) -> None:
        """
        Loaded values should match written values.

        Note: The binary file format is MATLAB-compatible (column-major order).
        Data is stored as [n_wavelengths × n_angles] in column-major order,
        meaning all wavelengths for angle 0 come first, then all wavelengths
        for angle 1, etc.
        """
        # Create specific test data in the expected [n_angles x n_wavelengths] layout
        # This is what we expect after loading and transposing
        n_wavelengths = 2048
        n_angles = 96
        expected_data = np.arange(n_wavelengths * n_angles, dtype=np.float64).reshape(
            (n_angles, n_wavelengths)
        )

        # To write this in MATLAB-compatible format, we need to:
        # 1. Transpose to [n_wavelengths, n_angles]
        # 2. Write in column-major (Fortran) order
        # The file stores: all wavelengths for angle 0, then all for angle 1, etc.
        write_data = expected_data.T.astype('<f4')  # [n_wavelengths, n_angles]

        with tempfile.NamedTemporaryFile(
            mode='wb', suffix='.bin', delete=False
        ) as f:
            # Write in Fortran order to match MATLAB binary format
            write_data.flatten(order='F').tofile(f)
            temp_path = Path(f.name)

        try:
            loaded_data, _ = load_spectral_data(temp_path, sample_config)

            # Loaded data should match our expected layout
            np.testing.assert_array_almost_equal(loaded_data, expected_data)
        finally:
            temp_path.unlink()


# =============================================================================
# TEST CLASS: DATA QUALITY CHECKS
# =============================================================================

class TestDataQualityChecks:
    """
    Tests for data quality warning functionality.
    """

    def test_warn_on_negative_values(
        self,
        sample_config: ECMConfig
    ) -> None:
        """
        Negative values should trigger a warning.
        """
        # Create data with negative values
        n_wavelengths = 2048
        n_angles = 96
        test_data = np.ones((n_wavelengths, n_angles), dtype=np.float32) * 1000
        test_data[0, 0] = -100  # Add negative value

        with tempfile.NamedTemporaryFile(
            mode='wb', suffix='.bin', delete=False
        ) as f:
            test_data.astype('<f4').tofile(f)
            temp_path = Path(f.name)

        try:
            with pytest.warns(UserWarning, match="negative values"):
                load_spectral_data(temp_path, sample_config)
        finally:
            temp_path.unlink()

    def test_warn_on_saturation(
        self,
        sample_config: ECMConfig
    ) -> None:
        """
        Saturated values should trigger a warning.
        """
        # Create data with saturated values
        n_wavelengths = 2048
        n_angles = 96
        test_data = np.ones((n_wavelengths, n_angles), dtype=np.float32) * 1000
        test_data[0, 0] = 70000  # Above 16-bit saturation

        with tempfile.NamedTemporaryFile(
            mode='wb', suffix='.bin', delete=False
        ) as f:
            test_data.astype('<f4').tofile(f)
            temp_path = Path(f.name)

        try:
            with pytest.warns(UserWarning, match="saturated"):
                load_spectral_data(temp_path, sample_config)
        finally:
            temp_path.unlink()

    def test_warn_on_nan_values(
        self,
        sample_config: ECMConfig
    ) -> None:
        """
        NaN values should trigger a warning.
        """
        # Create data with NaN values
        n_wavelengths = 2048
        n_angles = 96
        test_data = np.ones((n_wavelengths, n_angles), dtype=np.float32) * 1000
        test_data[0, 0] = np.nan

        with tempfile.NamedTemporaryFile(
            mode='wb', suffix='.bin', delete=False
        ) as f:
            test_data.astype('<f4').tofile(f)
            temp_path = Path(f.name)

        try:
            with pytest.warns(UserWarning, match="NaN or Inf"):
                load_spectral_data(temp_path, sample_config)
        finally:
            temp_path.unlink()


# =============================================================================
# TEST CLASS: FILE SIZE HANDLING
# =============================================================================

class TestFileSizeHandling:
    """
    Tests for file size mismatch handling.
    """

    def test_warn_on_size_mismatch_with_inference(
        self,
        sample_config: ECMConfig
    ) -> None:
        """
        Size mismatch with inferrable dimensions should warn but succeed.
        """
        # Create data with different number of angles
        n_wavelengths = 2048
        n_angles = 48  # Different from expected 96
        test_data = np.ones((n_wavelengths, n_angles), dtype=np.float32)

        with tempfile.NamedTemporaryFile(
            mode='wb', suffix='.bin', delete=False
        ) as f:
            test_data.astype('<f4').tofile(f)
            temp_path = Path(f.name)

        try:
            with pytest.warns(UserWarning, match="File size mismatch"):
                data, info = load_spectral_data(temp_path, sample_config)

            # Should infer correct dimensions
            assert data.shape == (48, 2048)
            assert info.n_angles == 48
        finally:
            temp_path.unlink()

    def test_error_on_invalid_file_size(
        self,
        sample_config: ECMConfig
    ) -> None:
        """
        Invalid file size (not divisible by 4) should raise ValueError.
        """
        # Create file with odd number of bytes
        with tempfile.NamedTemporaryFile(
            mode='wb', suffix='.bin', delete=False
        ) as f:
            f.write(b'12345')  # 5 bytes, not divisible by 4
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="not divisible"):
                load_spectral_data(temp_path, sample_config)
        finally:
            temp_path.unlink()


# =============================================================================
# TEST CLASS: INTEGRATION TESTS (with actual data if available)
# =============================================================================

class TestIntegration:
    """
    Integration tests using actual data files.

    These tests are skipped if the data files are not available.
    """

    @pytest.fixture
    def matlab_data_dir(self) -> Path:
        """Get the MATLAB data directory."""
        matlab_project = Path(
            "/Users/danielvala/Documents/PYTHON/VS/ECM/"
            "ecm_calibration 6.5.5 MATLAB/data"
        )
        return matlab_project

    def test_load_actual_wavelength_file(
        self,
        sample_config: ECMConfig,
        matlab_data_dir: Path
    ) -> None:
        """
        Test loading actual wavelength calibration file.
        """
        wavelength_file = matlab_data_dir / "assets" / "BlackCommet_wavelengths.txt"

        if not wavelength_file.exists():
            pytest.skip(f"Wavelength file not found: {wavelength_file}")

        sample_config.spectrometer.wavelength_file = wavelength_file

        wavelengths, idx_range, info = load_wavelengths(sample_config)

        # BlackComet has 2048 channels
        assert info.n_total == 2048
        assert len(wavelengths) > 0

        # Check wavelength range is reasonable
        assert info.all_wavelengths.min() > 100  # nm
        assert info.all_wavelengths.max() < 1200  # nm

    def test_load_actual_calibration_file(
        self,
        sample_config: ECMConfig,
        matlab_data_dir: Path
    ) -> None:
        """
        Test loading actual calibration data file.
        """
        # Look for any calibration file
        cal_dir = matlab_data_dir / "calibration" / "transmission"

        if not cal_dir.exists():
            pytest.skip(f"Calibration directory not found: {cal_dir}")

        # Find any binary calibration file in the directory
        # Exclude hidden files (like .DS_Store) and files with extensions
        cal_files = list(cal_dir.glob("*"))
        binary_files = [
            f for f in cal_files
            if f.is_file() and not f.suffix and not f.name.startswith('.')
        ]

        if not binary_files:
            pytest.skip("No calibration files found")

        cal_file = binary_files[0]

        data, info = load_spectral_data(cal_file, sample_config)

        # Check basic properties
        assert data.shape[0] == 96  # n_angles
        assert data.shape[1] == 2048  # n_wavelengths
        assert data.dtype == np.float64
        assert np.all(np.isfinite(data))  # No NaN/Inf
