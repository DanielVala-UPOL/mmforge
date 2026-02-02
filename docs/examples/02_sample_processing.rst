Sample Processing Example
=========================

This example demonstrates how to process sample measurements using a saved
calibration to extract Mueller matrices.

Setup
-----

.. code-block:: python

   from pathlib import Path
   import numpy as np
   import matplotlib.pyplot as plt

   from ecm.io import load_calibration, discover_sample_files
   from ecm.core import process_sample
   from ecm.utils.io import load_spectral_data
   from ecm.visualization import plot_mueller_matrix

Loading Calibration
-------------------

Load a previously saved calibration:

.. code-block:: python

   # Load calibration
   calibration_path = Path("./calibration_output/ecm_calibration.npz")
   result, diagnostics, cfg, metadata = load_calibration(calibration_path)

   print(f"Calibration loaded from: {calibration_path}")
   print(f"Created: {metadata['timestamp']}")
   print(f"Wavelengths: {len(result.wavelengths)}")

Discovering Samples
-------------------

Auto-discover sample files in a directory:

.. code-block:: python

   # Configure sample directory
   cfg.paths.samples_dir = Path("/path/to/samples")

   # Discover sample files
   samples = discover_sample_files(cfg)

   print(f"Found {len(samples)} samples:")
   for name in samples.names:
       print(f"  - {name}")

Processing a Single Sample
--------------------------

Process one sample measurement:

.. code-block:: python

   # Load sample data
   sample_path = Path("/path/to/sample.bin")
   sample_data, info = load_spectral_data(sample_path, cfg)

   print(f"Sample data shape: {sample_data.shape}")
   print(f"Angular positions: {info.n_angles}")
   print(f"Wavelengths: {info.n_wavelengths}")

   # Extract Mueller matrix
   M, M_normalized = process_sample(sample_data, result, cfg)

   print(f"Mueller matrix shape: {M.shape}")
   print(f"M[0,0] range: {M[0,0,:].min():.2f} - {M[0,0,:].max():.2f}")

Visualizing Results
-------------------

Plot the Mueller matrix elements:

.. code-block:: python

   # Create 4x4 Mueller matrix plot
   fig = plot_mueller_matrix(
       M_normalized,
       result.wavelengths,
       title="Sample Mueller Matrix (Normalized)"
   )
   plt.show()

   # Save the figure
   fig.savefig("mueller_matrix.png", dpi=150, bbox_inches='tight')

Examining Specific Elements
---------------------------

Analyze individual Mueller matrix elements:

.. code-block:: python

   wavelengths = result.wavelengths

   # Plot diagonal elements (often most informative)
   fig, axes = plt.subplots(2, 2, figsize=(10, 8))

   for i, ax in enumerate(axes.flat):
       ax.plot(wavelengths, M_normalized[i, i, :])
       ax.set_xlabel('Wavelength (nm)')
       ax.set_ylabel(f'm{i+1}{i+1}')
       ax.set_title(f'Diagonal element m{i+1}{i+1}')
       ax.grid(True, alpha=0.3)

   plt.tight_layout()
   plt.show()

Batch Processing
----------------

Process all discovered samples:

.. code-block:: python

   results_dir = Path("./processed_samples")
   results_dir.mkdir(exist_ok=True)

   for name, path in zip(samples.names, samples.paths):
       print(f"Processing: {name}")

       # Load and process
       sample_data, _ = load_spectral_data(path, cfg)
       M, M_norm = process_sample(sample_data, result, cfg)

       # Save results
       sample_dir = results_dir / name
       sample_dir.mkdir(exist_ok=True)

       np.savez(
           sample_dir / "mueller_matrices.npz",
           M=M,
           M_normalized=M_norm,
           M00=M[0, 0, :],
           wavelengths=result.wavelengths
       )

       # Generate plot
       fig = plot_mueller_matrix(M_norm, result.wavelengths, title=name)
       fig.savefig(sample_dir / "mueller_matrix.png", dpi=150)
       plt.close(fig)

   print(f"\nProcessed {len(samples)} samples to {results_dir}")

Validating Results
------------------

Check Mueller matrix physical validity:

.. code-block:: python

   from ecm.core.sample_processing import validate_mueller_matrix

   # Validate a Mueller matrix
   validation = validate_mueller_matrix(M_normalized)

   print(f"M[0,0] positive: {validation['m00_positive']}")
   print(f"Physically realizable: {validation['physical']}")

   if not validation['physical']:
       print(f"Warning: Mueller matrix may not be physically valid")
       print(f"Consider checking calibration or sample alignment")
