"""
ECM I/O Package

This package provides functions for saving and loading calibration results,
and for discovering sample measurement files.

Functions
---------
save_calibration(result, diagnostics, cfg, ...)
    Save calibration results to .npz file with metadata.

load_calibration(filepath)
    Load saved calibration from .npz file.

discover_sample_files(samples_dir, cfg, ...)
    Auto-discover sample measurement files in a directory.

Data Structures
---------------
SampleFiles
    Discovered sample files with names and paths.

CalibrationMetadata
    Metadata stored with calibration (timestamp, version, etc.).
"""

from ecm.io.calibration_io import (
    save_calibration,
    load_calibration,
    CalibrationMetadata,
)

from ecm.io.sample_discovery import (
    discover_sample_files,
    SampleFiles,
)

__all__ = [
    # Calibration I/O
    'save_calibration',
    'load_calibration',
    'CalibrationMetadata',
    # Sample discovery
    'discover_sample_files',
    'SampleFiles',
]
