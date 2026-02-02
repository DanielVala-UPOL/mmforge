#!/usr/bin/env python
"""
ECM Sample Processing Script

Applies saved calibration to sample measurements to extract Mueller matrices.

Usage
-----
    python process_samples.py CALIBRATION_FILE [OPTIONS]

Arguments
---------
    CALIBRATION_FILE    Path to saved calibration .npz file

Options
-------
    --sample-dir PATH   Directory containing sample measurement files
    --output-dir PATH   Output directory for processed results
    --samples NAMES     Comma-separated list of sample names to process
    --plot              Generate Mueller matrix plots
    --verbose           Increase output verbosity

Examples
--------
    # Process all samples in default directory
    python process_samples.py calibration.npz

    # Process specific samples
    python process_samples.py calibration.npz --samples QWP_0deg,QWP_45deg

    # Specify directories
    python process_samples.py calibration.npz \\
        --sample-dir /data/samples \\
        --output-dir /results/samples \\
        --plot

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999)
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional
import numpy as np


def main():
    """
    Main entry point for ECM sample processing.
    """
    # -------------------------------------------------------------------------
    # Parse command line arguments
    # -------------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="ECM Sample Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "calibration",
        type=Path,
        help="Path to saved calibration .npz file"
    )

    parser.add_argument(
        "--sample-dir", "-d",
        type=Path,
        help="Directory containing sample measurement files"
    )

    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        help="Output directory for processed results"
    )

    parser.add_argument(
        "--samples", "-s",
        type=str,
        help="Comma-separated list of sample names to process"
    )

    parser.add_argument(
        "--plot", "-p",
        action="store_true",
        help="Generate Mueller matrix plots"
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
        from ecm.io import load_calibration, discover_sample_files
        from ecm.utils.io import load_spectral_data
        from ecm.core.sample_processing import process_sample
        from ecm.visualization import plot_mueller_matrix
        import matplotlib.pyplot as plt
    except ImportError as e:
        print(f"Error importing ECM modules: {e}")
        print("Make sure the ecm package is installed or in your PYTHONPATH.")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Load calibration
    # -------------------------------------------------------------------------
    if not args.calibration.exists():
        print(f"Error: Calibration file not found: {args.calibration}")
        sys.exit(1)

    print(f"Loading calibration from: {args.calibration}")
    try:
        result, diagnostics, cfg, metadata = load_calibration(
            args.calibration, verbose=args.verbose
        )
    except Exception as e:
        print(f"Error loading calibration: {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Determine sample directory
    # -------------------------------------------------------------------------
    if args.sample_dir:
        sample_dir = args.sample_dir
    elif cfg.paths.samples_transmission_dir and cfg.paths.samples_transmission_dir.exists():
        sample_dir = cfg.paths.samples_transmission_dir
    elif cfg.paths.samples_dir and cfg.paths.samples_dir.exists():
        sample_dir = cfg.paths.samples_dir
    else:
        print("Error: No sample directory specified and none found in configuration.")
        print("Use --sample-dir to specify the sample directory.")
        sys.exit(1)

    if not sample_dir.exists():
        print(f"Error: Sample directory not found: {sample_dir}")
        sys.exit(1)

    print(f"Sample directory: {sample_dir}")

    # -------------------------------------------------------------------------
    # Discover or filter samples
    # -------------------------------------------------------------------------
    samples = discover_sample_files(sample_dir, cfg, verbose=args.verbose)

    if samples.n_samples == 0:
        print("No sample files found.")
        sys.exit(0)

    # Filter by name if specified
    if args.samples:
        requested_names = [n.strip() for n in args.samples.split(',')]
        filtered_names = []
        filtered_paths = []

        for name, path in zip(samples.names, samples.paths):
            if name in requested_names or any(r in name for r in requested_names):
                filtered_names.append(name)
                filtered_paths.append(path)

        if not filtered_names:
            print(f"No samples match: {args.samples}")
            print(f"Available samples: {', '.join(samples.names)}")
            sys.exit(1)

        samples_to_process = list(zip(filtered_names, filtered_paths))
    else:
        samples_to_process = list(zip(samples.names, samples.paths))

    print(f"\nProcessing {len(samples_to_process)} sample(s)...")

    # -------------------------------------------------------------------------
    # Determine output directory
    # -------------------------------------------------------------------------
    if args.output_dir:
        output_dir = args.output_dir
    elif cfg.output.results_dir:
        output_dir = Path(cfg.output.results_dir) / 'samples'
    else:
        output_dir = Path('results') / 'samples'

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # -------------------------------------------------------------------------
    # Process each sample
    # -------------------------------------------------------------------------
    processed_count = 0
    error_count = 0

    for name, path in samples_to_process:
        print(f"\n{'=' * 60}")
        print(f"Processing: {name}")
        print(f"{'=' * 60}")

        try:
            # Load sample data
            sample_data, _ = load_spectral_data(path, cfg)
            sample_data = sample_data[:, result.wl_indices]  # Select wavelengths

            # Subtract dark
            sample_data = sample_data - diagnostics.I_dark

            # Process sample
            sample_result = process_sample(
                sample_data,
                result.A,
                result.W,
                result.inv_W_mod
            )

            # Create sample output directory
            sample_output_dir = output_dir / name
            sample_output_dir.mkdir(parents=True, exist_ok=True)

            # Save results
            output_path = sample_output_dir / 'mueller_matrices.npz'
            np.savez(
                output_path,
                M=sample_result.M,
                M_normalized=sample_result.M_normalized,
                M00=sample_result.m00,
                wavelengths=result.wavelengths
            )
            print(f"  Saved: {output_path.name}")

            # Generate plot if requested
            if args.plot:
                try:
                    fig = plot_mueller_matrix(
                        sample_result.M_normalized,
                        result.wavelengths,
                        title=f'{name} - Normalized Mueller Matrix'
                    )
                    plot_path = sample_output_dir / 'mueller_matrix.png'
                    fig.savefig(plot_path, dpi=150, bbox_inches='tight')
                    plt.close(fig)
                    print(f"  Saved: {plot_path.name}")
                except Exception as e:
                    print(f"  Warning: Plot failed: {e}")

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
    print("PROCESSING COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Processed: {processed_count}")
    print(f"  Errors: {error_count}")
    print(f"  Output: {output_dir}")

    return processed_count, error_count


if __name__ == "__main__":
    main()
