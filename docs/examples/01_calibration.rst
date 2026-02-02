ECM Calibration Example
=======================

This example demonstrates how to perform ECM calibration using Python.

Setup
-----

First, import the necessary modules:

.. code-block:: python

   from pathlib import Path
   import numpy as np
   import matplotlib.pyplot as plt

   from ecm.config import ECMConfig
   from ecm.core import calibrate_transmission
   from ecm.io import save_calibration
   from ecm.diagnostics import run_calibration_diagnostics

Configuration
-------------

Create and configure the ECM settings:

.. code-block:: python

   # Create default configuration
   cfg = ECMConfig()

   # Set paths to your calibration data
   cfg.paths.data_dir = Path("/path/to/calibration/data")
   cfg.paths.calibration_output_dir = Path("./calibration_output")
   cfg.paths.wavelength_file = Path("/path/to/wavelengths.txt")

   # Configure acquisition parameters
   cfg.acquisition.n_angular_positions = 192
   cfg.acquisition.wavelength_range = (400, 800)

   # Review configuration
   print(cfg)

Running Calibration
-------------------

Execute the calibration:

.. code-block:: python

   # Run calibration
   print("Starting ECM calibration...")
   result, diagnostics = calibrate_transmission(cfg)

   print(f"Calibration complete!")
   print(f"W matrix shape: {result.W.shape}")
   print(f"A matrix shape: {result.A.shape}")
   print(f"Wavelengths: {result.wavelengths.min():.1f} - {result.wavelengths.max():.1f} nm")

Examining Results
-----------------

The calibration result contains:

.. code-block:: python

   # Instrument matrices
   W = result.W  # Polarization state generator matrix [4, 4, n_wavelengths]
   A = result.A  # Analyzer arm matrix [4, 4, n_wavelengths]

   # Wavelengths
   wavelengths = result.wavelengths

   # Extracted retarder parameters
   delta_1 = result.retarder_1_delta  # First retarder retardance
   delta_2 = result.retarder_2_delta  # Second retarder retardance

   # Plot retardance vs wavelength
   plt.figure(figsize=(10, 4))
   plt.plot(wavelengths, np.degrees(delta_1), label='Retarder 1')
   plt.plot(wavelengths, np.degrees(delta_2), label='Retarder 2')
   plt.xlabel('Wavelength (nm)')
   plt.ylabel('Retardance (degrees)')
   plt.legend()
   plt.title('Extracted Retarder Parameters')
   plt.show()

Diagnostics
-----------

Review calibration quality:

.. code-block:: python

   # Eigenvalue ratio (should be small, < 1e-6 ideally)
   print(f"Eigenvalue ratio: {diagnostics.eigenvalue_ratio.mean():.2e}")

   # Condition numbers
   print(f"W condition number: {diagnostics.condition_number_W.mean():.1f}")
   print(f"A condition number: {diagnostics.condition_number_A.mean():.1f}")

   # Generate diagnostic report
   report = run_calibration_diagnostics(
       result, diagnostics, cfg,
       save_dir=cfg.paths.calibration_output_dir,
       verbose=True
   )

Saving Results
--------------

Save the calibration for later use:

.. code-block:: python

   # Save calibration
   filepath = save_calibration(result, diagnostics, cfg)
   print(f"Calibration saved to: {filepath}")

   # The calibration can be loaded later with:
   # from ecm.io import load_calibration
   # result, diagnostics, cfg, metadata = load_calibration(filepath)
