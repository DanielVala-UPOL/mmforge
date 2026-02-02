#!/usr/bin/env python
"""
ECM Post-Processing Script

Performs Lu-Chipman polar decomposition on processed Mueller matrices
to extract physical polarimetric parameters.

Usage
-----
    python postprocess_samples.py RESULTS_DIR [OPTIONS]

Arguments
---------
    RESULTS_DIR         Directory containing processed Mueller matrices

Options
-------
    --sample NAME       Process only this sample (can be repeated)
    --output-dir PATH   Output directory for decomposition results
    --plot              Generate parameter plots
    --verbose           Increase output verbosity

Examples
--------
    # Post-process all samples in results directory
    python postprocess_samples.py results/samples

    # Process specific sample
    python postprocess_samples.py results/samples --sample QWP_0deg

    # Generate plots
    python postprocess_samples.py results/samples --plot --verbose

Output Files
------------
For each sample, creates:
    - lu_chipman_decomposition.npz: Decomposed matrices and parameters
    - DI.png, retardance.png, diattenuation.png, axis.png (if --plot)

Parameters Extracted
--------------------
    - D: Diattenuation magnitude [0, 1]
    - R: Retardance in degrees and waves
    - DI: Depolarization Index [0, 1]
    - ψ: Fast-axis azimuth [degrees]
    - χ: Ellipticity angle [degrees]

References
----------
[1] Lu & Chipman, "Interpretation of Mueller matrices based on polar
    decomposition", J. Opt. Soc. Am. A 13, 1106-1113 (1996)
"""

import argparse
import sys
from pathlib import Path
import numpy as np


def main():
    """
    Main entry point for ECM post-processing.
    """
    # -------------------------------------------------------------------------
    # Parse command line arguments
    # -------------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="ECM Post-Processing (Lu-Chipman Decomposition)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "results_dir",
        type=Path,
        help="Directory containing processed Mueller matrices"
    )

    parser.add_argument(
        "--sample", "-s",
        type=str,
        action="append",
        help="Process only this sample (can be repeated)"
    )

    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        help="Output directory for decomposition results"
    )

    parser.add_argument(
        "--plot", "-p",
        action="store_true",
        help="Generate parameter plots"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Increase output verbosity"
    )

    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # Import ECM modules
    # -------------------------------------------------------------------------
    try:
        from ecm.postprocessing import lu_chipman_decomposition
        from ecm.visualization import (
            plot_polarimetric_parameters,
            plot_decomposed_matrices,
        )
        import matplotlib.pyplot as plt
    except ImportError as e:
        print(f"Error importing ECM modules: {e}")
        print("Make sure the ecm package is installed or in your PYTHONPATH.")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Validate results directory
    # -------------------------------------------------------------------------
    if not args.results_dir.exists():
        print(f"Error: Results directory not found: {args.results_dir}")
        sys.exit(1)

    if not args.results_dir.is_dir():
        print(f"Error: Path is not a directory: {args.results_dir}")
        sys.exit(1)

    print(f"Results directory: {args.results_dir}")

    # -------------------------------------------------------------------------
    # Find sample directories with Mueller matrices
    # -------------------------------------------------------------------------
    sample_dirs = []

    for entry in sorted(args.results_dir.iterdir()):
        if not entry.is_dir():
            continue

        mueller_path = entry / 'mueller_matrices.npz'
        if mueller_path.exists():
            sample_dirs.append(entry)

    if not sample_dirs:
        print("No processed samples found (looking for mueller_matrices.npz)")
        sys.exit(0)

    # Filter by sample name if specified
    if args.sample:
        filtered_dirs = []
        for sample_dir in sample_dirs:
            if sample_dir.name in args.sample:
                filtered_dirs.append(sample_dir)
            elif any(s in sample_dir.name for s in args.sample):
                filtered_dirs.append(sample_dir)

        if not filtered_dirs:
            print(f"No samples match: {args.sample}")
            print(f"Available samples: {', '.join(d.name for d in sample_dirs)}")
            sys.exit(1)

        sample_dirs = filtered_dirs

    print(f"\nPost-processing {len(sample_dirs)} sample(s)...")

    # -------------------------------------------------------------------------
    # Determine output directory
    # -------------------------------------------------------------------------
    if args.output_dir:
        output_base = args.output_dir
    else:
        output_base = args.results_dir

    output_base = Path(output_base)

    # -------------------------------------------------------------------------
    # Process each sample
    # -------------------------------------------------------------------------
    processed_count = 0
    error_count = 0

    for sample_dir in sample_dirs:
        sample_name = sample_dir.name
        print(f"\n{'=' * 60}")
        print(f"Post-processing: {sample_name}")
        print(f"{'=' * 60}")

        try:
            # Load Mueller matrices
            mueller_path = sample_dir / 'mueller_matrices.npz'
            data = np.load(mueller_path)

            M_normalized = data['M_normalized']
            wavelengths = data['wavelengths']

            if args.verbose:
                print(f"  Loaded: {M_normalized.shape[2]} wavelengths")
                print(f"  Range: {wavelengths.min():.1f} - {wavelengths.max():.1f} nm")

            # Perform Lu-Chipman decomposition
            lu_result = lu_chipman_decomposition(M_normalized)

            if args.verbose:
                print(f"  Diattenuation (mean): {np.mean(lu_result.D):.4f}")
                print(f"  Retardance (mean): {np.mean(lu_result.R_deg):.1f}°")
                print(f"  Depolarization Index (mean): {np.mean(lu_result.DI):.4f}")

            # Determine output directory for this sample
            if args.output_dir:
                sample_output = output_base / sample_name
            else:
                sample_output = sample_dir

            sample_output.mkdir(parents=True, exist_ok=True)

            # Save decomposition results
            output_path = sample_output / 'lu_chipman_decomposition.npz'
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
            print(f"  Saved: {output_path.name}")

            # Generate plots if requested
            if args.plot:
                try:
                    # Polarimetric parameters plots
                    param_figures = plot_polarimetric_parameters(
                        lu_result,
                        wavelengths,
                        sample_name=sample_name,
                        save_dir=sample_output,
                    )

                    for name, fig in param_figures.items():
                        print(f"  Saved: {name}.png")
                        plt.close(fig)

                    # Decomposed matrices plots (optional, can be large)
                    if args.verbose:
                        decomp_figures = plot_decomposed_matrices(
                            lu_result,
                            wavelengths,
                            sample_name=sample_name,
                            save_dir=sample_output,
                        )
                        for name, fig in decomp_figures.items():
                            print(f"  Saved: {name}.png")
                            plt.close(fig)

                except Exception as e:
                    print(f"  Warning: Plotting failed: {e}")
                    if args.verbose:
                        import traceback
                        traceback.print_exc()

            processed_count += 1
            print(f"  Status: Success")

        except Exception as e:
            print(f"  Error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            error_count += 1

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("POST-PROCESSING COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Processed: {processed_count}")
    print(f"  Errors: {error_count}")
    print(f"  Output: {output_base}")

    return processed_count, error_count


if __name__ == "__main__":
    main()
