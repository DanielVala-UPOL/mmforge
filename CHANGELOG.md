# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [6.5.5] - 2024

### Added

#### Core Features
- Complete ECM calibration pipeline for transmission mode
- Eigenvalue-based W and A matrix solution
- Fourier coefficient extraction from intensity modulation
- H and K matrix construction for overdetermined systems
- Parameter extraction for polarizers and retarders

#### Post-processing
- Lu-Chipman polar decomposition (M = M_Delta @ M_R @ M_D)
- Diattenuation, retardance, and depolarization index extraction
- Fast-axis orientation angle calculation

#### Visualization
- 4x4 Mueller matrix element plots vs wavelength
- Intensity diagnostic plots (angular modulation, heatmaps)
- Lu-Chipman parameter plots (DI, R, D, axis angles)
- Decomposed Mueller matrix visualization

#### Diagnostics
- Eigenvalue ratio analysis
- Condition number monitoring
- Air Mueller matrix validation
- Fourier harmonic analysis

#### I/O & CLI
- Binary spectral data loading (MATLAB-compatible format)
- Calibration save/load with metadata
- Sample file auto-discovery
- Command-line interface (ecm-calibrate, ecm-process, ecm-postprocess)

#### Configuration
- Hierarchical dataclass-based configuration
- JSON/YAML serialization
- Validation with meaningful error messages

### Technical Details
- 383 passing tests
- 100% feature parity with MATLAB v6.5.5
- Python 3.9+ support
- Type hints throughout
- NumPy/SciPy-based numerical operations

### Migration Notes
This version is a complete Python translation of the MATLAB ECM calibration
toolbox v6.5.5. All algorithms have been verified to produce numerically
equivalent results.

Key differences from MATLAB version:
- Uses dataclasses instead of structs
- Uses pickle/NPZ instead of .mat files for saving
- Uses pytest instead of MATLAB unit tests
- Modular package structure for better maintainability

## [Unreleased]

### Planned
- Reflection mode support
- Parallel sample processing
- GPU acceleration (optional)
- Interactive Jupyter widgets
