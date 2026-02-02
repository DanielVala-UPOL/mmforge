#!/usr/bin/env python
"""
ECM Transmission Calibration Script

Main entry point for performing ECM calibration in transmission mode.
Auto-discovers calibration files, runs calibration, saves results,
and generates diagnostic figures.

Usage
-----
    python calibrate_transmission.py [OPTIONS]

Options
-------
    --config PATH       Configuration file (YAML/JSON)
    --data-dir PATH     Calibration data directory
    --output-dir PATH   Output directory for saved calibration
    --no-diagnostics    Skip diagnostic plots
    --no-save           Skip saving calibration to file
    --verbose           Increase output verbosity

Examples
--------
    # Use default configuration
    python calibrate_transmission.py

    # Specify data directory
    python calibrate_transmission.py --data-dir /path/to/calibration/data

    # Use custom configuration
    python calibrate_transmission.py --config my_config.yaml

    # Full workflow with custom paths
    python calibrate_transmission.py \\
        --data-dir /data/calibration \\
        --output-dir /results/calibration \\
        --verbose

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999)
"""

import argparse
import sys
from pathlib import Path


def main():
    """
    Main entry point for ECM transmission calibration.
    """
    # -------------------------------------------------------------------------
    # Parse command line arguments
    # -------------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="ECM Transmission Calibration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="Configuration file (YAML/JSON)"
    )

    parser.add_argument(
        "--data-dir", "-d",
        type=Path,
        help="Calibration data directory"
    )

    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        help="Output directory for saved calibration"
    )

    parser.add_argument(
        "--no-diagnostics",
        action="store_true",
        help="Skip diagnostic plots"
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Skip saving calibration to file"
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
        from ecm.config import ECMConfig
        from ecm.core import calibrate_transmission
        from ecm.io import save_calibration
        from ecm.diagnostics import run_calibration_diagnostics
    except ImportError as e:
        print(f"Error importing ECM modules: {e}")
        print("Make sure the ecm package is installed or in your PYTHONPATH.")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Load or create configuration
    # -------------------------------------------------------------------------
    if args.config:
        if not args.config.exists():
            print(f"Error: Configuration file not found: {args.config}")
            sys.exit(1)

        if args.config.suffix.lower() in ['.yaml', '.yml']:
            cfg = ECMConfig.from_yaml(args.config)
        elif args.config.suffix.lower() == '.json':
            cfg = ECMConfig.from_json(args.config)
        else:
            print(f"Error: Unsupported config format: {args.config.suffix}")
            print("Supported formats: .yaml, .yml, .json")
            sys.exit(1)

        print(f"Loaded configuration from: {args.config}")
    else:
        cfg = ECMConfig()
        print("Using default configuration")

    # -------------------------------------------------------------------------
    # Override paths from command line
    # -------------------------------------------------------------------------
    if args.data_dir:
        if not args.data_dir.exists():
            print(f"Error: Data directory not found: {args.data_dir}")
            sys.exit(1)
        cfg.paths.data_dir = args.data_dir
        # Update derived paths
        cfg.paths.calibration_transmission_dir = args.data_dir
        print(f"Data directory: {args.data_dir}")

    if args.output_dir:
        cfg.paths.calibration_output_dir = args.output_dir
        print(f"Output directory: {args.output_dir}")

    if args.verbose:
        cfg.output.verbosity = 2

    # -------------------------------------------------------------------------
    # Run calibration
    # -------------------------------------------------------------------------
    try:
        result, diagnostics = calibrate_transmission(cfg)
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nCalibration failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Save calibration
    # -------------------------------------------------------------------------
    if not args.no_save:
        try:
            filepath = save_calibration(
                result, diagnostics, cfg,
                verbose=True
            )
            print(f"\nCalibration saved to: {filepath}")
        except Exception as e:
            print(f"\nError saving calibration: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    # -------------------------------------------------------------------------
    # Run diagnostics
    # -------------------------------------------------------------------------
    if not args.no_diagnostics:
        try:
            # Create diagnostics output directory
            diag_dir = cfg.paths.calibration_output_dir
            if diag_dir is None:
                diag_dir = Path('calibration_output')
            diag_dir = Path(diag_dir) / 'diagnostics'

            report = run_calibration_diagnostics(
                result.W,
                result.A,
                result.wavelengths,
                diagnostics.eigenvalue_ratio,
                diagnostics.cond_W,
                diagnostics.cond_A,
                save_dir=diag_dir,
                verbose=args.verbose
            )

            print(f"\nDiagnostic figures saved to: {diag_dir}")

            # Close figures to free memory
            import matplotlib.pyplot as plt
            for fig in report.figures.values():
                plt.close(fig)

        except Exception as e:
            print(f"\nWarning: Diagnostics failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()

    print("\nCalibration complete.")
    return result, diagnostics


if __name__ == "__main__":
    main()
