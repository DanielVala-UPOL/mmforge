"""
Sample File Discovery

This module provides automatic discovery of sample measurement files
in a directory, excluding calibration files based on filename patterns.

Functions
---------
discover_sample_files(samples_dir, cfg, ...)
    Auto-discover sample measurement files.

Data Structures
---------------
SampleFiles
    Discovered sample files with names and paths.

Example
-------
>>> from ecm.io import discover_sample_files
>>> from ecm.config import ECMConfig
>>>
>>> cfg = ECMConfig()
>>> samples = discover_sample_files(cfg.paths.samples_transmission_dir, cfg)
>>> print(f"Found {len(samples.names)} sample files")
>>> for name, path in zip(samples.names, samples.paths):
...     print(f"  {name}: {path.name}")
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ecm.config.ecm_config import ECMConfig


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SampleFiles:
    """
    Discovered sample files.

    Attributes
    ----------
    names : List[str]
        Sample names extracted from filenames.
        Typically the filename without path and ECM-specific suffixes.

    paths : List[Path]
        Full paths to sample files.

    mode : str
        Measurement mode ('transmission' or 'reflection').

    n_samples : int
        Number of discovered samples.

    Examples
    --------
    >>> samples = discover_sample_files(samples_dir, cfg)
    >>> for name, path in zip(samples.names, samples.paths):
    ...     data, _ = load_spectral_data(path, cfg)
    ...     M = process_sample(data, result, cfg)
    """
    names: List[str]
    paths: List[Path]
    mode: str

    @property
    def n_samples(self) -> int:
        """Number of discovered samples."""
        return len(self.names)

    def __len__(self) -> int:
        """Return number of samples."""
        return len(self.names)

    def __iter__(self):
        """Iterate over (name, path) pairs."""
        return iter(zip(self.names, self.paths))

    def __repr__(self) -> str:
        return f"SampleFiles(n_samples={self.n_samples}, mode='{self.mode}')"


# =============================================================================
# CALIBRATION KEYWORDS (to exclude)
# =============================================================================

# These keywords identify calibration files that should be excluded
CALIBRATION_KEYWORDS = [
    '_DARK_ECM_',
    '_ST_ECM_',
    '_P0_ECM_',
    '_P45_ECM_',
    '_RET90_FP1_ECM_',
    '_RET45_FP2_ECM_',
    '_RET90_ECM_',
    '_RET45_ECM_',
    '_ECM_CAL_',
    '_CALIBRATION_',
]


# =============================================================================
# SAMPLE DISCOVERY
# =============================================================================

def discover_sample_files(
    samples_dir: Path,
    cfg: 'ECMConfig',
    exclude_patterns: Optional[List[str]] = None,
    include_extensions: Optional[List[str]] = None,
    verbose: bool = True,
) -> SampleFiles:
    """
    Auto-discover sample measurement files in a directory.

    Searches for binary measurement files and excludes files that match
    calibration filename patterns.

    Parameters
    ----------
    samples_dir : Path
        Directory to search for sample files.

    cfg : ECMConfig
        Configuration (used for mode and verbosity settings).

    exclude_patterns : List[str], optional
        Additional filename patterns to exclude (case-insensitive).
        Default: uses CALIBRATION_KEYWORDS.

    include_extensions : List[str], optional
        File extensions to include.
        Default: ['.bin', ''] (binary files and extensionless).

    verbose : bool, optional
        Print discovery results. Default: True.

    Returns
    -------
    samples : SampleFiles
        Discovered sample files with names and paths.

    Raises
    ------
    FileNotFoundError
        If samples_dir does not exist.

    Examples
    --------
    >>> from ecm.io import discover_sample_files
    >>> from ecm.config import ECMConfig
    >>>
    >>> cfg = ECMConfig()
    >>> samples = discover_sample_files(
    ...     cfg.paths.samples_transmission_dir, cfg
    ... )
    >>> print(f"Found {samples.n_samples} samples")

    >>> # Exclude additional patterns
    >>> samples = discover_sample_files(
    ...     samples_dir, cfg,
    ...     exclude_patterns=['_TEST_', '_DEBUG_']
    ... )

    Notes
    -----
    **Exclusion Logic:**

    A file is excluded if its name contains ANY of the calibration
    keywords (case-insensitive). This prevents accidentally processing
    calibration measurements as samples.

    **Sample Name Extraction:**

    Sample names are extracted from filenames by:
    1. Removing the file extension
    2. Removing common ECM-related suffixes
    3. Cleaning up underscores and whitespace

    **Sorting:**

    Files are returned sorted alphabetically by name for reproducibility.
    """
    samples_dir = Path(samples_dir)

    if not samples_dir.exists():
        raise FileNotFoundError(f"Samples directory not found: {samples_dir}")

    if not samples_dir.is_dir():
        raise ValueError(f"Path is not a directory: {samples_dir}")

    # -------------------------------------------------------------------------
    # Set up exclusion patterns
    # -------------------------------------------------------------------------
    all_exclude_patterns = list(CALIBRATION_KEYWORDS)
    if exclude_patterns:
        all_exclude_patterns.extend(exclude_patterns)

    # Compile case-insensitive patterns
    exclude_patterns_lower = [p.lower() for p in all_exclude_patterns]

    # -------------------------------------------------------------------------
    # Set up extension filter
    # -------------------------------------------------------------------------
    if include_extensions is None:
        # Default: binary files and extensionless files
        include_extensions = ['.bin', '']

    include_extensions_lower = [ext.lower() for ext in include_extensions]

    # -------------------------------------------------------------------------
    # Scan directory
    # -------------------------------------------------------------------------
    sample_paths: List[Path] = []
    sample_names: List[str] = []
    excluded_count = 0

    for entry in sorted(samples_dir.iterdir()):
        # Skip directories and hidden files
        if entry.is_dir() or entry.name.startswith('.'):
            continue

        # Check extension
        ext = entry.suffix.lower()
        if ext not in include_extensions_lower:
            continue

        # Check exclusion patterns
        name_lower = entry.name.lower()
        is_calibration = any(pattern in name_lower for pattern in exclude_patterns_lower)

        if is_calibration:
            excluded_count += 1
            continue

        # Extract sample name
        sample_name = _extract_sample_name(entry.name)

        sample_paths.append(entry)
        sample_names.append(sample_name)

    # -------------------------------------------------------------------------
    # Build result
    # -------------------------------------------------------------------------
    result = SampleFiles(
        names=sample_names,
        paths=sample_paths,
        mode=cfg.mode,
    )

    # -------------------------------------------------------------------------
    # Print summary
    # -------------------------------------------------------------------------
    if verbose:
        print(f"\nSample file discovery in: {samples_dir}")
        print(f"  Found: {len(sample_names)} sample files")
        print(f"  Excluded: {excluded_count} calibration files")

        if sample_names:
            print(f"\n  Samples:")
            for name, path in zip(sample_names, sample_paths):
                print(f"    {name}: {path.name}")

    return result


def _extract_sample_name(filename: str) -> str:
    """
    Extract a clean sample name from a filename.

    Parameters
    ----------
    filename : str
        Filename (with or without extension).

    Returns
    -------
    name : str
        Cleaned sample name.

    Examples
    --------
    >>> _extract_sample_name("260109_QWP_45deg_SAMPLE")
    '260109_QWP_45deg'
    >>> _extract_sample_name("HWP_measurement.bin")
    'HWP_measurement'
    """
    # Remove extension
    name = Path(filename).stem

    # Remove common suffixes (case-insensitive)
    suffixes_to_remove = [
        '_SAMPLE',
        '_sample',
        '_MEASUREMENT',
        '_measurement',
        '_DATA',
        '_data',
    ]

    for suffix in suffixes_to_remove:
        if name.endswith(suffix):
            name = name[:-len(suffix)]

    # Clean up trailing underscores
    name = name.rstrip('_')

    return name


def list_all_files(
    directory: Path,
    verbose: bool = True,
) -> dict:
    """
    List all files in a directory with categorization.

    Useful for debugging when sample discovery doesn't find expected files.

    Parameters
    ----------
    directory : Path
        Directory to scan.

    verbose : bool, optional
        Print results. Default: True.

    Returns
    -------
    files : dict
        Dictionary with keys:
        - 'calibration': Files matching calibration patterns
        - 'samples': Other binary/extensionless files
        - 'other': Files with other extensions

    Examples
    --------
    >>> from ecm.io.sample_discovery import list_all_files
    >>> files = list_all_files(Path('/data/samples'))
    >>> print(f"Calibration: {len(files['calibration'])}")
    >>> print(f"Samples: {len(files['samples'])}")
    """
    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    calibration_files = []
    sample_files = []
    other_files = []

    exclude_patterns_lower = [p.lower() for p in CALIBRATION_KEYWORDS]

    for entry in sorted(directory.iterdir()):
        if entry.is_dir() or entry.name.startswith('.'):
            continue

        name_lower = entry.name.lower()
        ext = entry.suffix.lower()

        # Check if calibration file
        is_calibration = any(pattern in name_lower for pattern in exclude_patterns_lower)

        if is_calibration:
            calibration_files.append(entry)
        elif ext in ['.bin', '']:
            sample_files.append(entry)
        else:
            other_files.append(entry)

    result = {
        'calibration': calibration_files,
        'samples': sample_files,
        'other': other_files,
    }

    if verbose:
        print(f"\nFiles in: {directory}")
        print("=" * 60)

        print(f"\nCalibration files ({len(calibration_files)}):")
        for f in calibration_files:
            print(f"    {f.name}")

        print(f"\nSample files ({len(sample_files)}):")
        for f in sample_files:
            print(f"    {f.name}")

        print(f"\nOther files ({len(other_files)}):")
        for f in other_files[:10]:  # Limit to first 10
            print(f"    {f.name}")
        if len(other_files) > 10:
            print(f"    ... and {len(other_files) - 10} more")

    return result
