"""
Tests for ECM Configuration Module

This test module validates the configuration dataclasses and their
serialization/deserialization functionality.

Test Categories
---------------
1. Default configuration creation
2. Nested dataclass access
3. Property calculations
4. Validation checks
5. JSON serialization/deserialization
6. YAML serialization/deserialization (if pyyaml installed)
"""

import pytest
import json
import tempfile
from pathlib import Path

from ecm.config import (
    ECMConfig,
    InstrumentConfig,
    AcquisitionConfig,
    SpectrometerConfig,
    WavelengthConfig,
    FileFormatConfig,
    CalibrationSampleConfig,
    ECMAlgorithmConfig,
    FourierConfig,
    FigureConfig,
)


# =============================================================================
# TEST CLASS: DEFAULT CONFIGURATION
# =============================================================================

class TestDefaultConfiguration:
    """
    Tests for default configuration creation.
    """

    def test_create_default_config(self) -> None:
        """
        Default ECMConfig should be created without errors.
        """
        cfg = ECMConfig()
        assert cfg is not None

    def test_default_mode(self) -> None:
        """
        Default mode should be 'transmission'.
        """
        cfg = ECMConfig()
        assert cfg.mode == 'transmission'

    def test_default_angular_positions(self) -> None:
        """
        Default n_angular_positions should be 96.
        """
        cfg = ECMConfig()
        assert cfg.acquisition.n_angular_positions == 96

    def test_default_wavelengths(self) -> None:
        """
        Default n_wavelengths should be 2048.
        """
        cfg = ECMConfig()
        assert cfg.spectrometer.n_wavelengths == 2048

    def test_default_wavelength_range(self) -> None:
        """
        Default wavelength range should be (400, 1000) nm.
        """
        cfg = ECMConfig()
        assert cfg.wavelength.range_nm == (400.0, 1000.0)

    def test_default_frequency_ratios(self) -> None:
        """
        Default frequency ratios should be 1:5.
        """
        cfg = ECMConfig()
        assert cfg.instrument.psg_freq_ratio == 1
        assert cfg.instrument.psa_freq_ratio == 5


# =============================================================================
# TEST CLASS: NESTED DATACLASS ACCESS
# =============================================================================

class TestNestedAccess:
    """
    Tests for accessing nested configuration values.
    """

    def test_access_instrument_config(self) -> None:
        """
        Should be able to access instrument configuration.
        """
        cfg = ECMConfig()
        assert isinstance(cfg.instrument, InstrumentConfig)
        assert cfg.instrument.psg_freq_ratio == 1

    def test_access_acquisition_config(self) -> None:
        """
        Should be able to access acquisition configuration.
        """
        cfg = ECMConfig()
        assert isinstance(cfg.acquisition, AcquisitionConfig)
        assert cfg.acquisition.n_rotation_cycles == 1

    def test_access_ecm_config(self) -> None:
        """
        Should be able to access ECM algorithm configuration.
        """
        cfg = ECMConfig()
        assert isinstance(cfg.ecm, ECMAlgorithmConfig)
        assert cfg.ecm.method == 'extended'

    def test_access_calibration_samples(self) -> None:
        """
        Should be able to access calibration sample configurations.
        """
        cfg = ECMConfig()
        assert 'pol_0' in cfg.calibration_samples
        assert 'pol_45' in cfg.calibration_samples
        assert 'ret_90' in cfg.calibration_samples
        assert 'ret_45' in cfg.calibration_samples

    def test_calibration_sample_properties(self) -> None:
        """
        Calibration samples should have correct properties.
        """
        cfg = ECMConfig()

        # Check polarizer at 0 degrees
        pol_0 = cfg.calibration_samples['pol_0']
        assert pol_0.type == 'polarizer'
        assert pol_0.orientation_deg == 0.0
        assert pol_0.transmittance == 0.5

        # Check retarder at 90 degrees
        ret_90 = cfg.calibration_samples['ret_90']
        assert ret_90.type == 'retarder'
        assert ret_90.orientation_deg == 90.0


# =============================================================================
# TEST CLASS: PROPERTY CALCULATIONS
# =============================================================================

class TestPropertyCalculations:
    """
    Tests for computed properties in configuration.
    """

    def test_angular_step_calculation(self) -> None:
        """
        angular_step_deg should be computed from angular_range / n_positions.
        """
        cfg = ECMConfig()

        expected_step = 360.0 / 96  # 3.75 degrees
        assert abs(cfg.acquisition.angular_step_deg - expected_step) < 1e-10

    def test_angular_step_custom_values(self) -> None:
        """
        angular_step_deg should update with custom values.
        """
        cfg = ECMConfig()
        cfg.acquisition.n_angular_positions = 72
        cfg.acquisition.angular_range_deg = 360.0

        expected_step = 360.0 / 72  # 5 degrees
        assert abs(cfg.acquisition.angular_step_deg - expected_step) < 1e-10


# =============================================================================
# TEST CLASS: VALIDATION
# =============================================================================

class TestValidation:
    """
    Tests for configuration validation.
    """

    def test_invalid_wavelength_range_raises(self) -> None:
        """
        Invalid wavelength range (min >= max) should raise ValueError.
        """
        cfg = ECMConfig()
        cfg.wavelength.range_nm = (800.0, 400.0)  # Invalid: min > max

        # Re-validate (normally happens in __post_init__)
        with pytest.raises(ValueError, match="Invalid wavelength range"):
            cfg._validate()

    def test_invalid_mode_raises(self) -> None:
        """
        Invalid mode should raise ValueError.
        """
        cfg = ECMConfig()
        cfg.mode = 'invalid_mode'

        with pytest.raises(ValueError, match="Invalid mode"):
            cfg._validate()

    def test_invalid_ecm_method_raises(self) -> None:
        """
        Invalid ECM method should raise ValueError.
        """
        cfg = ECMConfig()
        cfg.ecm.method = 'invalid_method'

        with pytest.raises(ValueError, match="Invalid ECM method"):
            cfg._validate()

    def test_warning_for_insufficient_angular_positions(self) -> None:
        """
        Insufficient angular positions should trigger a warning.
        """
        cfg = ECMConfig()
        cfg.acquisition.n_angular_positions = 20  # Less than 2 * max_harmonic

        with pytest.warns(UserWarning, match="Angular positions.*may be insufficient"):
            cfg._validate()


# =============================================================================
# TEST CLASS: MODIFICATION
# =============================================================================

class TestModification:
    """
    Tests for modifying configuration values.
    """

    def test_modify_wavelength_range(self) -> None:
        """
        Should be able to modify wavelength range.
        """
        cfg = ECMConfig()
        cfg.wavelength.range_nm = (450.0, 900.0)
        assert cfg.wavelength.range_nm == (450.0, 900.0)

    def test_modify_angular_positions(self) -> None:
        """
        Should be able to modify angular positions.
        """
        cfg = ECMConfig()
        cfg.acquisition.n_angular_positions = 72
        assert cfg.acquisition.n_angular_positions == 72

    def test_modify_ecm_parameters(self) -> None:
        """
        Should be able to modify ECM algorithm parameters.
        """
        cfg = ECMConfig()
        cfg.ecm.optimize_polarizer_angles = False
        cfg.ecm.method = 'standard'

        assert cfg.ecm.optimize_polarizer_angles is False
        assert cfg.ecm.method == 'standard'


# =============================================================================
# TEST CLASS: JSON SERIALIZATION
# =============================================================================

class TestJsonSerialization:
    """
    Tests for JSON serialization and deserialization.
    """

    def test_to_dict(self) -> None:
        """
        to_dict() should return a dictionary.
        """
        cfg = ECMConfig()
        d = cfg.to_dict()

        assert isinstance(d, dict)
        assert 'mode' in d
        assert 'instrument' in d
        assert 'acquisition' in d

    def test_to_dict_contains_all_sections(self) -> None:
        """
        to_dict() should contain all configuration sections.
        """
        cfg = ECMConfig()
        d = cfg.to_dict()

        expected_keys = [
            'mode', 'instrument', 'acquisition', 'spectrometer',
            'wavelength', 'file_format', 'paths', 'calibration_samples',
            'ecm', 'fourier', 'mueller', 'processing', 'output', 'figure'
        ]

        for key in expected_keys:
            assert key in d, f"Missing key: {key}"

    def test_to_json_creates_file(self) -> None:
        """
        to_json() should create a JSON file.
        """
        cfg = ECMConfig()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_path = Path(f.name)

        try:
            cfg.to_json(json_path)
            assert json_path.exists()

            # Verify it's valid JSON
            with open(json_path, 'r') as f:
                data = json.load(f)
            assert isinstance(data, dict)
        finally:
            json_path.unlink()

    def test_from_json_loads_correctly(self) -> None:
        """
        from_json() should load configuration from JSON file.
        """
        # Create and save config
        cfg_original = ECMConfig()
        cfg_original.wavelength.range_nm = (450.0, 850.0)
        cfg_original.acquisition.n_angular_positions = 72

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_path = Path(f.name)

        try:
            cfg_original.to_json(json_path)

            # Load config
            cfg_loaded = ECMConfig.from_json(json_path)

            # Verify values match
            assert cfg_loaded.wavelength.range_nm == (450.0, 850.0)
            assert cfg_loaded.acquisition.n_angular_positions == 72
        finally:
            json_path.unlink()

    def test_json_round_trip(self) -> None:
        """
        Save to JSON and load back should preserve all values.
        """
        cfg_original = ECMConfig()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_path = Path(f.name)

        try:
            cfg_original.to_json(json_path)
            cfg_loaded = ECMConfig.from_json(json_path)

            # Check key values are preserved
            assert cfg_loaded.mode == cfg_original.mode
            assert cfg_loaded.acquisition.n_angular_positions == cfg_original.acquisition.n_angular_positions
            assert cfg_loaded.spectrometer.n_wavelengths == cfg_original.spectrometer.n_wavelengths
            assert cfg_loaded.ecm.method == cfg_original.ecm.method
        finally:
            json_path.unlink()


# =============================================================================
# TEST CLASS: YAML SERIALIZATION (Optional)
# =============================================================================

class TestYamlSerialization:
    """
    Tests for YAML serialization and deserialization.

    These tests are skipped if PyYAML is not installed.
    """

    @pytest.fixture
    def yaml_available(self) -> bool:
        """Check if PyYAML is available."""
        try:
            import yaml
            return True
        except ImportError:
            return False

    def test_to_yaml_creates_file(self, yaml_available: bool) -> None:
        """
        to_yaml() should create a YAML file.
        """
        if not yaml_available:
            pytest.skip("PyYAML not installed")

        cfg = ECMConfig()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_path = Path(f.name)

        try:
            cfg.to_yaml(yaml_path)
            assert yaml_path.exists()
        finally:
            yaml_path.unlink()

    def test_yaml_round_trip(self, yaml_available: bool) -> None:
        """
        Save to YAML and load back should preserve all values.
        """
        if not yaml_available:
            pytest.skip("PyYAML not installed")

        cfg_original = ECMConfig()
        cfg_original.wavelength.range_nm = (500.0, 800.0)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_path = Path(f.name)

        try:
            cfg_original.to_yaml(yaml_path)
            cfg_loaded = ECMConfig.from_yaml(yaml_path)

            assert cfg_loaded.wavelength.range_nm == (500.0, 800.0)
        finally:
            yaml_path.unlink()


# =============================================================================
# TEST CLASS: PATHS CONFIGURATION
# =============================================================================

class TestPathsConfiguration:
    """
    Tests for path configuration and resolution.
    """

    def test_paths_are_set(self) -> None:
        """
        Default paths should be set after initialization.
        """
        cfg = ECMConfig()

        assert cfg.paths.data_dir is not None
        assert cfg.paths.assets_dir is not None
        assert cfg.paths.calibration_dir is not None

    def test_paths_are_path_objects(self) -> None:
        """
        Paths should be Path objects.
        """
        cfg = ECMConfig()

        assert isinstance(cfg.paths.data_dir, Path)
        assert isinstance(cfg.paths.assets_dir, Path)

    def test_wavelength_file_path_set(self) -> None:
        """
        Wavelength file path should be set.
        """
        cfg = ECMConfig()
        assert cfg.spectrometer.wavelength_file is not None
        assert isinstance(cfg.spectrometer.wavelength_file, Path)


# =============================================================================
# TEST CLASS: REPR
# =============================================================================

class TestRepr:
    """
    Tests for string representation.
    """

    def test_repr_returns_string(self) -> None:
        """
        __repr__ should return a string.
        """
        cfg = ECMConfig()
        r = repr(cfg)
        assert isinstance(r, str)

    def test_repr_contains_key_info(self) -> None:
        """
        __repr__ should contain key configuration info.
        """
        cfg = ECMConfig()
        r = repr(cfg)

        assert 'ECMConfig' in r
        assert 'transmission' in r
        assert '96' in r  # n_angular_positions
