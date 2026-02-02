"""
ECM Command-Line Interface Entry Points

This module provides entry points for the CLI commands:
    - ecm-calibrate: Run ECM calibration
    - ecm-process: Process samples using calibration
    - ecm-postprocess: Lu-Chipman decomposition on processed samples
"""

import sys
from pathlib import Path


def calibrate_main():
    """Entry point for ecm-calibrate command."""
    # Import here to avoid slow startup
    scripts_dir = Path(__file__).parent.parent / "scripts"
    script_path = scripts_dir / "calibrate_transmission.py"

    if script_path.exists():
        # Execute the script
        import runpy
        sys.argv[0] = str(script_path)
        runpy.run_path(str(script_path), run_name="__main__")
    else:
        print(f"Error: Script not found: {script_path}")
        sys.exit(1)


def process_main():
    """Entry point for ecm-process command."""
    scripts_dir = Path(__file__).parent.parent / "scripts"
    script_path = scripts_dir / "process_samples.py"

    if script_path.exists():
        import runpy
        sys.argv[0] = str(script_path)
        runpy.run_path(str(script_path), run_name="__main__")
    else:
        print(f"Error: Script not found: {script_path}")
        sys.exit(1)


def postprocess_main():
    """Entry point for ecm-postprocess command."""
    scripts_dir = Path(__file__).parent.parent / "scripts"
    script_path = scripts_dir / "postprocess_samples.py"

    if script_path.exists():
        import runpy
        sys.argv[0] = str(script_path)
        runpy.run_path(str(script_path), run_name="__main__")
    else:
        print(f"Error: Script not found: {script_path}")
        sys.exit(1)


if __name__ == "__main__":
    # For testing
    print("ECM CLI module")
    print("Available commands:")
    print("  ecm-calibrate   - Run ECM calibration")
    print("  ecm-process     - Process samples")
    print("  ecm-postprocess - Lu-Chipman decomposition")
