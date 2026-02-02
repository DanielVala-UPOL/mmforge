Quick Start Guide
=================

This guide will walk you through the basic usage of ECM Polarimetry.

Configuration
-------------

ECM uses a hierarchical configuration system:

.. code-block:: python

   from pathlib import Path
   from ecm.config import ECMConfig

   # Create default configuration
   cfg = ECMConfig()

   # Set data paths
   cfg.paths.data_dir = Path("./calibration_data")
   cfg.paths.calibration_output_dir = Path("./results")

   # Modify acquisition parameters
   cfg.acquisition.n_angular_positions = 192
   cfg.acquisition.wavelength_range = (400, 800)

   # Save configuration for later use
   cfg.to_yaml("my_config.yaml")

   # Load configuration from file
   cfg = ECMConfig.from_yaml("my_config.yaml")

Running Calibration
-------------------

Using Python API
~~~~~~~~~~~~~~~~

.. code-block:: python

   from ecm.config import ECMConfig
   from ecm.core import calibrate_transmission
   from ecm.io import save_calibration

   # Load configuration
   cfg = ECMConfig()
   cfg.paths.data_dir = Path("./calibration_data")

   # Run calibration
   result, diagnostics = calibrate_transmission(cfg)

   # Save results
   save_calibration(result, diagnostics, cfg)

Using Command Line
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Basic calibration
   ecm-calibrate --data-dir ./calibration_data

   # With custom output directory
   ecm-calibrate --data-dir ./calibration_data --output-dir ./results

   # With custom configuration file
   ecm-calibrate --config my_config.yaml

Processing Samples
------------------

After calibration, process sample measurements:

Using Python API
~~~~~~~~~~~~~~~~

.. code-block:: python

   from ecm.io import load_calibration
   from ecm.core import process_sample
   from ecm.utils.io import load_spectral_data

   # Load saved calibration
   result, diagnostics, cfg, metadata = load_calibration("calibration.npz")

   # Load sample data
   sample_data, info = load_spectral_data("sample.bin", cfg)

   # Process sample
   M, M_normalized = process_sample(sample_data, result, cfg)

   # M is the Mueller matrix [4, 4, n_wavelengths]
   print(f"Mueller matrix shape: {M.shape}")

Using Command Line
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Process all samples in a directory
   ecm-process calibration.npz --sample-dir ./samples

   # With plots
   ecm-process calibration.npz --sample-dir ./samples --plot

Lu-Chipman Decomposition
------------------------

Extract physical parameters from Mueller matrices:

.. code-block:: python

   from ecm.postprocessing import lu_chipman_decomposition
   import numpy as np

   # Decompose Mueller matrix
   lu_result = lu_chipman_decomposition(M_normalized)

   # Access extracted parameters
   print(f"Diattenuation (mean): {np.mean(lu_result.D):.4f}")
   print(f"Retardance (mean): {np.mean(lu_result.R_deg):.1f} degrees")
   print(f"Depolarization Index (mean): {np.mean(lu_result.DI):.4f}")
   print(f"Fast axis azimuth (mean): {np.mean(lu_result.psi_deg):.1f} degrees")

Using Command Line
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Basic post-processing
   ecm-postprocess ./results

   # With plots
   ecm-postprocess ./results --plot --verbose

   # Specific sample only
   ecm-postprocess ./results --sample QWP_0deg

Visualization
-------------

Generate publication-quality plots:

.. code-block:: python

   from ecm.visualization import (
       plot_mueller_matrix,
       plot_polarimetric_parameters,
   )

   # Plot Mueller matrix elements
   fig = plot_mueller_matrix(
       M_normalized,
       wavelengths,
       title="Sample Mueller Matrix"
   )
   fig.savefig("mueller_matrix.png", dpi=150)

   # Plot Lu-Chipman parameters
   figures = plot_polarimetric_parameters(
       lu_result,
       wavelengths,
       sample_name="QWP"
   )
   for name, fig in figures.items():
       fig.savefig(f"{name}.png", dpi=150)

Complete Workflow Example
-------------------------

Here's a complete example from calibration to analysis:

.. code-block:: python

   from pathlib import Path
   from ecm.config import ECMConfig
   from ecm.core import calibrate_transmission, process_sample
   from ecm.io import save_calibration, load_calibration, discover_sample_files
   from ecm.utils.io import load_spectral_data
   from ecm.postprocessing import lu_chipman_decomposition
   from ecm.visualization import plot_mueller_matrix, plot_polarimetric_parameters

   # 1. Configure and calibrate
   cfg = ECMConfig()
   cfg.paths.data_dir = Path("./calibration_data")

   result, diagnostics = calibrate_transmission(cfg)
   save_calibration(result, diagnostics, cfg, filename="my_calibration.npz")

   # 2. Discover and process samples
   cfg.paths.samples_dir = Path("./samples")
   samples = discover_sample_files(cfg)

   for name, path in zip(samples.names, samples.paths):
       # Load sample
       sample_data, _ = load_spectral_data(path, cfg)

       # Extract Mueller matrix
       M, M_norm = process_sample(sample_data, result, cfg)

       # Lu-Chipman decomposition
       lu_result = lu_chipman_decomposition(M_norm)

       # Generate plots
       plot_mueller_matrix(M_norm, result.wavelengths, title=name)
       plot_polarimetric_parameters(lu_result, result.wavelengths, sample_name=name)

       print(f"{name}: R = {lu_result.R_deg.mean():.1f} deg, D = {lu_result.D.mean():.4f}")
