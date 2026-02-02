# ECM Polarimetry

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-383%20passing-green.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Ellipsometric Calibration Method for Mueller Matrix Polarimetry**

A Python implementation of the ECM algorithm for calibrating and analyzing
spectroscopic Mueller matrix polarimeters with dual rotating compensators.

## Features

- Complete ECM calibration pipeline for transmission mode
- Lu-Chipman polar decomposition of Mueller matrices
- Publication-quality visualization tools
- Command-line interface for batch processing
- Comprehensive test suite (383 tests)
- 100% feature parity with MATLAB implementation

## Installation

### From source (recommended for development)

```bash
git clone https://github.com/yourusername/ecm-polarimetry.git
cd ecm-polarimetry
pip install -e .
```

### With development dependencies

```bash
pip install -e ".[dev]"
```

### With documentation dependencies

```bash
pip install -e ".[docs]"
```

## Quick Start

### Python API

```python
from pathlib import Path
from ecm.config import ECMConfig
from ecm.core import calibrate_transmission
from ecm.postprocessing import lu_chipman_decomposition

# Create configuration
cfg = ECMConfig()
cfg.paths.data_dir = Path("./calibration_data")

# Run calibration
result, diagnostics = calibrate_transmission(cfg)

# Process a sample
from ecm.core import process_sample
from ecm.utils.io import load_spectral_data

sample_data, _ = load_spectral_data("sample.bin", cfg)
M, M_norm = process_sample(sample_data, result, cfg)

# Lu-Chipman decomposition
lu_result = lu_chipman_decomposition(M_norm)
print(f"Retardance: {lu_result.R_deg.mean():.1f} degrees")
print(f"Diattenuation: {lu_result.D.mean():.4f}")
print(f"Depolarization Index: {lu_result.DI.mean():.4f}")
```

### Command Line Interface

After installation, three CLI commands are available:

```bash
# Run calibration
ecm-calibrate --data-dir ./calibration_data --output-dir ./results

# Process samples using saved calibration
ecm-process calibration.npz --sample-dir ./samples --output-dir ./results

# Post-process with Lu-Chipman decomposition
ecm-postprocess ./results --plot --verbose
```

#### CLI Help

```bash
ecm-calibrate --help
ecm-process --help
ecm-postprocess --help
```

## Package Structure

```
ecm/
├── config/           # Configuration dataclasses
│   └── ecm_config.py
├── core/             # Core ECM algorithms
│   ├── modulation.py
│   ├── fourier.py
│   ├── ecm_matrices.py
│   ├── ecm_solver.py
│   ├── parameter_extraction.py
│   ├── sample_processing.py
│   ├── file_discovery.py
│   └── transmission_calibration.py
├── utils/            # Utility functions
│   ├── mueller_matrices.py
│   └── io.py
├── io/               # File I/O
│   ├── calibration_io.py
│   └── sample_discovery.py
├── visualization/    # Plotting functions
│   ├── mueller_plots.py
│   ├── intensity_plots.py
│   ├── parameter_plots.py
│   ├── decomposition_plots.py
│   └── figure_utils.py
├── postprocessing/   # Post-processing algorithms
│   └── lu_chipman.py
├── diagnostics/      # Calibration diagnostics
│   └── calibration_diagnostics.py
└── cli.py            # CLI entry points
```

## ECM Algorithm Overview

The Eigenvalue Calibration Method (ECM) calibrates Mueller matrix polarimeters
by solving an eigenvalue problem that determines the instrument matrices W and A.

### Measurement Model

```
B = A @ M @ W
```

Where:
- **B**: Measured intensity matrix (from Fourier coefficients)
- **A**: Analyzer arm instrument matrix (4x4)
- **M**: Sample Mueller matrix (4x4)
- **W**: Polarization state generator matrix (4x4)

### Calibration Workflow

1. **Data Acquisition**: Measure calibration samples (air, polarizers, retarders)
2. **Fourier Analysis**: Extract Fourier coefficients from intensity modulation
3. **Build System**: Construct H and K matrices from calibration measurements
4. **Eigenvalue Solution**: Solve for W (smallest eigenvalue eigenvector)
5. **Calculate A**: Compute A = B_air @ W^(-1)
6. **Parameter Extraction**: Extract and validate retarder/polarizer parameters

### Lu-Chipman Decomposition

After obtaining Mueller matrices, the Lu-Chipman polar decomposition extracts
physical parameters:

```
M = M_Delta @ M_R @ M_D
```

Where:
- **M_D**: Diattenuator (dichroism)
- **M_R**: Retarder (birefringence)
- **M_Delta**: Depolarizer

Extracted parameters:
- **D**: Diattenuation magnitude [0, 1]
- **R**: Retardance in degrees
- **DI**: Depolarization Index [0, 1]
- **psi, chi**: Fast-axis orientation angles

## Configuration

ECM uses a hierarchical configuration system with sensible defaults:

```python
from ecm.config import ECMConfig

cfg = ECMConfig()

# Modify paths
cfg.paths.data_dir = Path("./my_data")
cfg.paths.calibration_output_dir = Path("./output")

# Modify acquisition parameters
cfg.acquisition.n_angular_positions = 192
cfg.acquisition.wavelength_range = (400, 800)

# Save/load configuration
cfg.to_yaml("my_config.yaml")
cfg = ECMConfig.from_yaml("my_config.yaml")
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ecm --cov-report=html

# Run specific test file
pytest tests/test_lu_chipman.py -v
```

## References

1. Compain, E., Poirier, S., & Drevillon, B. (1999). General and self-consistent
   method for the calibration of polarization modulators, polarimeters, and
   Mueller-matrix ellipsometers. *Applied Optics*, 38(16), 3490-3502.

2. Rosales, A. G., et al. (2024). Extended eigenvalue calibration method for
   overdetermined Mueller matrix polarimeters. *Optics Letters*, 49(5), 1165-1168.

3. Lu, S. Y., & Chipman, R. A. (1996). Interpretation of Mueller matrices based
   on polar decomposition. *Journal of the Optical Society of America A*, 13(5),
   1106-1113.

## Citation

If you use this software in your research, please cite:

```bibtex
@software{ecm_polarimetry,
  title = {ECM Polarimetry: Python Implementation},
  author = {Vala, Daniel},
  year = {2024},
  version = {6.5.5},
  url = {https://github.com/yourusername/ecm-polarimetry}
}
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request
