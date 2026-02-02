"""
ECM Configuration Module

This module provides dataclass-based configuration for the ECM calibration pipeline.
All parameters are centralized here as the single source of truth.

Classes
-------
ECMConfig
    Main configuration container with all calibration parameters
InstrumentConfig
    PSG/PSA instrument geometry settings
AcquisitionConfig
    Data acquisition parameters
SpectrometerConfig
    Spectrometer hardware settings
WavelengthConfig
    Wavelength range and reference settings
FileFormatConfig
    Binary file format specifications
PathsConfig
    Directory and file path configuration
CalibrationSampleConfig
    Properties of calibration samples (polarizers, retarders)
ECMAlgorithmConfig
    ECM algorithm parameters and optimization settings
FourierConfig
    Fourier analysis parameters
FigureConfig
    Plotting and visualization settings
OutputConfig
    Output and diagnostic settings
MuellerConfig
    Mueller matrix conventions
ProcessingConfig
    Data processing options

Example
-------
>>> from ecm.config import ECMConfig
>>>
>>> # Create default configuration
>>> cfg = ECMConfig()
>>>
>>> # Access nested settings
>>> print(cfg.acquisition.n_angular_positions)  # 96
>>> print(cfg.wavelength.range_nm)              # (400.0, 1000.0)
>>>
>>> # Modify and save
>>> cfg.wavelength.range_nm = (450.0, 900.0)
>>> cfg.to_yaml(Path("my_config.yaml"))
"""

from ecm.config.ecm_config import (
    ECMConfig,
    InstrumentConfig,
    AcquisitionConfig,
    SpectrometerConfig,
    WavelengthConfig,
    FileFormatConfig,
    PathsConfig,
    CalibrationSampleConfig,
    ECMAlgorithmConfig,
    FourierConfig,
    FigureConfig,
    OutputConfig,
    MuellerConfig,
    ProcessingConfig,
    RetarderCharConfig,
    BoundsConfig,
)

__all__ = [
    "ECMConfig",
    "InstrumentConfig",
    "AcquisitionConfig",
    "SpectrometerConfig",
    "WavelengthConfig",
    "FileFormatConfig",
    "PathsConfig",
    "CalibrationSampleConfig",
    "ECMAlgorithmConfig",
    "FourierConfig",
    "FigureConfig",
    "OutputConfig",
    "MuellerConfig",
    "ProcessingConfig",
    "RetarderCharConfig",
    "BoundsConfig",
]
