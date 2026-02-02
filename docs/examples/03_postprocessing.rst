Lu-Chipman Decomposition Example
=================================

This example demonstrates how to perform Lu-Chipman polar decomposition
on processed Mueller matrices to extract physical polarimetric parameters.

Setup
-----

.. code-block:: python

   from pathlib import Path
   import numpy as np
   import matplotlib.pyplot as plt

   from ecm.postprocessing import lu_chipman_decomposition
   from ecm.visualization import (
       plot_polarimetric_parameters,
       plot_decomposed_matrices,
   )

Loading Mueller Matrices
------------------------

Load previously processed Mueller matrices:

.. code-block:: python

   # Load processed data
   data = np.load("./processed_samples/QWP_0deg/mueller_matrices.npz")

   M_normalized = data['M_normalized']
   wavelengths = data['wavelengths']

   print(f"Mueller matrix shape: {M_normalized.shape}")
   print(f"Wavelength range: {wavelengths.min():.1f} - {wavelengths.max():.1f} nm")

Lu-Chipman Decomposition
------------------------

Perform the polar decomposition:

.. code-block:: python

   # Decompose Mueller matrix
   lu_result = lu_chipman_decomposition(M_normalized)

   # The result contains:
   # - M_D: Diattenuator matrices [4, 4, n_wavelengths]
   # - M_R: Retarder matrices [4, 4, n_wavelengths]
   # - M_Delta: Depolarizer matrices [4, 4, n_wavelengths]
   # - D: Diattenuation magnitude [n_wavelengths]
   # - R_rad: Retardance in radians [n_wavelengths]
   # - R_deg: Retardance in degrees [n_wavelengths]
   # - R_waves: Retardance in waves [n_wavelengths]
   # - DI: Depolarization Index [n_wavelengths]
   # - psi_deg: Fast axis azimuth [n_wavelengths]
   # - chi_deg: Ellipticity angle [n_wavelengths]

Examining Parameters
--------------------

Print summary statistics:

.. code-block:: python

   print("Lu-Chipman Decomposition Results:")
   print(f"{'Parameter':<20} {'Mean':>10} {'Std':>10} {'Min':>10} {'Max':>10}")
   print("-" * 60)

   params = [
       ('Diattenuation (D)', lu_result.D),
       ('Retardance (deg)', lu_result.R_deg),
       ('Retardance (waves)', lu_result.R_waves),
       ('Depol. Index (DI)', lu_result.DI),
       ('Azimuth psi (deg)', lu_result.psi_deg),
       ('Ellipticity chi (deg)', lu_result.chi_deg),
   ]

   for name, values in params:
       print(f"{name:<20} {np.mean(values):>10.4f} {np.std(values):>10.4f} "
             f"{np.min(values):>10.4f} {np.max(values):>10.4f}")

Parameter Plots
---------------

Generate publication-quality parameter plots:

.. code-block:: python

   # Create parameter plots
   figures = plot_polarimetric_parameters(
       lu_result,
       wavelengths,
       sample_name="Quarter-Wave Plate",
       save_dir=Path("./plots")  # Optional: saves automatically
   )

   # The returned dictionary contains:
   # - 'DI': Depolarization Index plot
   # - 'retardance': Retardance plot (degrees and waves)
   # - 'diattenuation': Diattenuation plot
   # - 'axis': Fast axis orientation plot (psi and chi)

   # Display figures
   for name, fig in figures.items():
       print(f"Generated: {name}")
       plt.figure(fig.number)
       plt.show()

Individual Parameter Plots
--------------------------

Create custom parameter plots:

.. code-block:: python

   fig, axes = plt.subplots(2, 2, figsize=(12, 10))

   # Retardance
   ax = axes[0, 0]
   ax.plot(wavelengths, lu_result.R_deg)
   ax.axhline(90, color='r', linestyle='--', alpha=0.5, label='QWP (90°)')
   ax.set_xlabel('Wavelength (nm)')
   ax.set_ylabel('Retardance (degrees)')
   ax.set_title('Retardance')
   ax.legend()
   ax.grid(True, alpha=0.3)

   # Diattenuation
   ax = axes[0, 1]
   ax.plot(wavelengths, lu_result.D)
   ax.set_xlabel('Wavelength (nm)')
   ax.set_ylabel('Diattenuation')
   ax.set_title('Diattenuation')
   ax.set_ylim(0, 0.1)  # Ideal retarder: D ≈ 0
   ax.grid(True, alpha=0.3)

   # Depolarization Index
   ax = axes[1, 0]
   ax.plot(wavelengths, lu_result.DI)
   ax.set_xlabel('Wavelength (nm)')
   ax.set_ylabel('Depolarization Index')
   ax.set_title('Depolarization Index')
   ax.set_ylim(0.9, 1.0)  # Non-depolarizing: DI ≈ 1
   ax.grid(True, alpha=0.3)

   # Fast axis azimuth
   ax = axes[1, 1]
   ax.plot(wavelengths, lu_result.psi_deg)
   ax.set_xlabel('Wavelength (nm)')
   ax.set_ylabel('Azimuth (degrees)')
   ax.set_title('Fast Axis Azimuth')
   ax.grid(True, alpha=0.3)

   plt.tight_layout()
   plt.savefig('lu_chipman_parameters.png', dpi=150)
   plt.show()

Decomposed Matrices
-------------------

Visualize the decomposed Mueller matrices:

.. code-block:: python

   # Plot decomposed matrices
   decomp_figures = plot_decomposed_matrices(
       lu_result,
       wavelengths,
       sample_name="QWP"
   )

   # Contains separate figures for M_D, M_R, M_Delta

Reconstruction Verification
---------------------------

Verify the decomposition by reconstruction:

.. code-block:: python

   # Reconstruct Mueller matrix
   n_wl = M_normalized.shape[2]
   M_reconstructed = np.zeros_like(M_normalized)

   for k in range(n_wl):
       M_D = lu_result.M_D[:, :, k]
       M_R = lu_result.M_R[:, :, k]
       M_Delta = lu_result.M_Delta[:, :, k]

       # M = M_Delta @ M_R @ M_D
       M_reconstructed[:, :, k] = M_Delta @ M_R @ M_D

   # Calculate reconstruction error
   error = np.abs(M_normalized - M_reconstructed)
   max_error = np.max(error)
   mean_error = np.mean(error)

   print(f"Reconstruction verification:")
   print(f"  Max error: {max_error:.2e}")
   print(f"  Mean error: {mean_error:.2e}")

   if max_error < 1e-10:
       print("  ✓ Perfect reconstruction")
   elif max_error < 1e-6:
       print("  ✓ Excellent reconstruction")
   else:
       print("  ⚠ Check Mueller matrix validity")

Comparing Multiple Samples
--------------------------

Compare parameters across samples:

.. code-block:: python

   samples = ['QWP_0deg', 'QWP_45deg', 'HWP_0deg']
   colors = ['blue', 'green', 'red']

   fig, ax = plt.subplots(figsize=(10, 6))

   for sample, color in zip(samples, colors):
       data = np.load(f"./processed_samples/{sample}/mueller_matrices.npz")
       M_norm = data['M_normalized']
       wl = data['wavelengths']

       lu = lu_chipman_decomposition(M_norm)
       ax.plot(wl, lu.R_deg, color=color, label=sample)

   ax.axhline(90, color='gray', linestyle='--', alpha=0.5, label='QWP (90°)')
   ax.axhline(180, color='gray', linestyle=':', alpha=0.5, label='HWP (180°)')

   ax.set_xlabel('Wavelength (nm)')
   ax.set_ylabel('Retardance (degrees)')
   ax.set_title('Retardance Comparison')
   ax.legend()
   ax.grid(True, alpha=0.3)

   plt.tight_layout()
   plt.savefig('retardance_comparison.png', dpi=150)
   plt.show()

Saving Decomposition Results
----------------------------

Save decomposition results for later analysis:

.. code-block:: python

   output_path = Path("./processed_samples/QWP_0deg/lu_chipman_decomposition.npz")

   np.savez(
       output_path,
       # Decomposed matrices
       M_D=lu_result.M_D,
       M_R=lu_result.M_R,
       M_Delta=lu_result.M_Delta,
       # Scalar parameters
       D=lu_result.D,
       R_rad=lu_result.R_rad,
       R_deg=lu_result.R_deg,
       R_waves=lu_result.R_waves,
       DI=lu_result.DI,
       psi_deg=lu_result.psi_deg,
       chi_deg=lu_result.chi_deg,
       # Wavelengths
       wavelengths=wavelengths,
   )

   print(f"Saved decomposition to: {output_path}")
