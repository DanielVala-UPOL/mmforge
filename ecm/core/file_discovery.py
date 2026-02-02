"""
Calibration File Discovery

This module provides automatic discovery of calibration files based on
filename keyword patterns. It searches for required calibration measurements
(dark, air, polarizers, retarders) in the data directory.

Functions
---------
discover_calibration_files(cfg)
    Auto-discover calibration files by filename keywords

Theory
------
The ECM calibration requires several measurements:

**Transmission Mode:**
- Dark: Background/dark current measurement
- Air (Straight-through): Reference measurement with no sample
- Polarizer at 0°: Linear polarizer with transmission axis horizontal
- Polarizer at 45°: Linear polarizer with transmission axis at 45°
- Retarder at 90°: Quarter/half waveplate with fast axis at 90°
- Retarder at 45° (optional): Second retarder measurement for robustness

**File Naming Convention:**
Files are identified by keywords in their names:
- _DARK_ECM_       : Dark/background measurement
- _ST_ECM_         : Straight-through (air) measurement
- _P0_ECM_         : Polarizer at 0°
- _P45_ECM_        : Polarizer at 45°
- _RET90_FP1_ECM_  : Primary retarder at 90°
- _RET45_FP2_ECM_  : Secondary retarder at 45° (optional)

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999)
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ecm.config.ecm_config import ECMConfig


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CalibrationFiles:
    """
    Discovered calibration file paths.

    Attributes
    ----------
    dark : Path
        Dark/background measurement file.

    air : Path
        Straight-through (air) measurement file.

    pol_0 : Path
        Polarizer at 0° measurement file.

    pol_45 : Path
        Polarizer at 45° measurement file.

    ret_90 : Path
        Primary retarder at 90° measurement file.

    ret_45 : Path, optional
        Secondary retarder at 45° measurement file.
        None if not found.

    ret_90_char : Path, optional
        Retardation characterization file for primary retarder.
        Contains wavelength-dependent retardation values.

    ret_45_char : Path, optional
        Retardation characterization file for secondary retarder.

    has_second_retarder : bool
        True if secondary retarder (FP2) files were found.

    Notes
    -----
    **Required Files:**
    - dark, air, pol_0, pol_45, ret_90

    **Optional Files:**
    - ret_45 (improves calibration robustness)
    - ret_90_char, ret_45_char (for wavelength-dependent retardation)

    If characterization files are not provided, the retardation is
    assumed constant (ideal quarter-wave plate at reference wavelength).
    """
    dark: Path
    air: Path
    pol_0: Path
    pol_45: Path
    ret_90: Path
    ret_45: Optional[Path] = None
    ret_90_char: Optional[Path] = None
    ret_45_char: Optional[Path] = None
    has_second_retarder: bool = False


@dataclass
class FileSearchResult:
    """
    Result of searching for a calibration file.

    Attributes
    ----------
    found : bool
        True if exactly one matching file was found.

    path : Path, optional
        Path to the found file (None if not found or ambiguous).

    matches : List[Path]
        All files matching the keyword pattern.
        len(matches) == 1 for successful search.

    keyword : str
        The keyword pattern used for the search.

    message : str
        Status message (success, not found, or ambiguous).
    """
    found: bool
    path: Optional[Path]
    matches: List[Path]
    keyword: str
    message: str


# =============================================================================
# FILE DISCOVERY
# =============================================================================

def discover_calibration_files(cfg: 'ECMConfig') -> CalibrationFiles:
    """
    Auto-discover calibration files by filename keywords.

    Searches the data directory for files matching the ECM calibration
    file naming convention.

    Parameters
    ----------
    cfg : ECMConfig
        ECM configuration with paths.data_dir set.

    Returns
    -------
    CalibrationFiles
        Dataclass with paths to all discovered files.

    Raises
    ------
    FileNotFoundError
        If a required calibration file is not found.

    ValueError
        If multiple files match the same keyword pattern.

    Examples
    --------
    >>> from ecm.config import ECMConfig
    >>> cfg = ECMConfig()
    >>> cfg.paths.data_dir = Path('/path/to/calibration/data')
    >>>
    >>> files = discover_calibration_files(cfg)
    >>> print(f"Dark file: {files.dark}")
    >>> print(f"Air file: {files.air}")
    >>> print(f"Second retarder: {files.has_second_retarder}")

    Notes
    -----
    **Keyword Patterns (Transmission Mode):**

    ============== ==========================================
    Sample         Keyword
    ============== ==========================================
    Dark           _DARK_ECM_
    Air            _ST_ECM_
    Polarizer 0°   _P0_ECM_
    Polarizer 45°  _P45_ECM_
    Retarder 90°   _RET90_FP1_ECM_
    Retarder 45°   _RET45_FP2_ECM_ (optional)
    ============== ==========================================

    **Case Sensitivity:**
    Keyword matching is case-insensitive to accommodate different
    file naming conventions.

    **Characterization Files:**
    Retarder characterization files (wavelength-dependent retardation)
    are searched for in the assets directory using patterns like:
    - *FP1*retardation*.txt
    - *FP2*retardation*.txt
    """
    # -------------------------------------------------------------------------
    # Get data directory
    # -------------------------------------------------------------------------
    data_dir = cfg.paths.data_dir
    if data_dir is None:
        raise ValueError(
            "cfg.paths.data_dir must be set before discovering files. "
            "Set it to the directory containing calibration measurements."
        )

    data_dir = Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(
            f"Data directory does not exist: {data_dir}"
        )

    # -------------------------------------------------------------------------
    # Define keyword patterns for transmission mode
    # -------------------------------------------------------------------------
    # Required files
    required_keywords = {
        'dark': '_DARK_ECM_',
        'air': '_ST_ECM_',
        'pol_0': '_P0_ECM_',
        'pol_45': '_P45_ECM_',
        'ret_90': '_RET90_FP1_ECM_'
    }

    # Optional files
    optional_keywords = {
        'ret_45': '_RET45_FP2_ECM_'
    }

    # -------------------------------------------------------------------------
    # Search for required files
    # -------------------------------------------------------------------------
    found_files: Dict[str, Path] = {}

    print("\nSearching for calibration files...")
    print(f"  Data directory: {data_dir}")
    print()

    for name, keyword in required_keywords.items():
        result = _search_for_file(data_dir, keyword)

        if not result.found:
            if len(result.matches) == 0:
                raise FileNotFoundError(
                    f"Required calibration file not found.\n"
                    f"  Looking for: filename containing '{keyword}'\n"
                    f"  In directory: {data_dir}\n"
                    f"  Sample type: {name}"
                )
            else:
                raise ValueError(
                    f"Multiple files match '{keyword}':\n" +
                    '\n'.join(f"    {p.name}" for p in result.matches) +
                    f"\n  Please ensure only one file matches each pattern."
                )

        found_files[name] = result.path
        print(f"  Found {name:8s}: {result.path.name}")

    # -------------------------------------------------------------------------
    # Search for optional files
    # -------------------------------------------------------------------------
    print()
    for name, keyword in optional_keywords.items():
        result = _search_for_file(data_dir, keyword)

        if result.found:
            found_files[name] = result.path
            print(f"  Found {name:8s}: {result.path.name}")
        elif len(result.matches) > 1:
            print(f"  Warning: Multiple files match '{keyword}', skipping.")
        else:
            print(f"  Optional {name:8s}: not found (continuing without)")

    # -------------------------------------------------------------------------
    # Search for retarder characterization files
    # -------------------------------------------------------------------------
    ret_90_char = None
    ret_45_char = None

    assets_dir = cfg.paths.assets_dir
    if assets_dir is not None and Path(assets_dir).exists():
        print()
        print(f"  Searching for retarder characterization in: {assets_dir}")

        # Search for FP1 retardation file
        fp1_result = _search_for_file(
            Path(assets_dir),
            'FP1',
            extension='.txt',
            secondary_pattern='retard'
        )
        if fp1_result.found:
            ret_90_char = fp1_result.path
            print(f"  Found FP1 char: {fp1_result.path.name}")
        else:
            print(f"  FP1 characterization: not found (using ideal)")

        # Search for FP2 retardation file
        if 'ret_45' in found_files:
            fp2_result = _search_for_file(
                Path(assets_dir),
                'FP2',
                extension='.txt',
                secondary_pattern='retard'
            )
            if fp2_result.found:
                ret_45_char = fp2_result.path
                print(f"  Found FP2 char: {fp2_result.path.name}")
            else:
                print(f"  FP2 characterization: not found (using ideal)")

    # -------------------------------------------------------------------------
    # Determine if second retarder is available
    # -------------------------------------------------------------------------
    has_second_retarder = 'ret_45' in found_files

    # -------------------------------------------------------------------------
    # Build result
    # -------------------------------------------------------------------------
    result = CalibrationFiles(
        dark=found_files['dark'],
        air=found_files['air'],
        pol_0=found_files['pol_0'],
        pol_45=found_files['pol_45'],
        ret_90=found_files['ret_90'],
        ret_45=found_files.get('ret_45'),
        ret_90_char=ret_90_char,
        ret_45_char=ret_45_char,
        has_second_retarder=has_second_retarder
    )

    print()
    print(f"  Second retarder available: {has_second_retarder}")

    return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _search_for_file(
    directory: Path,
    keyword: str,
    extension: Optional[str] = None,
    secondary_pattern: Optional[str] = None
) -> FileSearchResult:
    """
    Search for files containing a keyword in a directory.

    Parameters
    ----------
    directory : Path
        Directory to search in.

    keyword : str
        Keyword to search for (case-insensitive).

    extension : str, optional
        File extension filter (e.g., '.txt', '.bin').
        If None, searches all files.

    secondary_pattern : str, optional
        Additional pattern that must also be present.
        Useful for narrowing down matches.

    Returns
    -------
    FileSearchResult
        Search result with found flag, path, and matches.
    """
    matches = []

    # Normalize keyword for case-insensitive comparison
    keyword_lower = keyword.lower()
    secondary_lower = secondary_pattern.lower() if secondary_pattern else None

    # Search for matching files
    for entry in directory.iterdir():
        # Skip directories and hidden files
        if entry.is_dir() or entry.name.startswith('.'):
            continue

        # Check extension filter
        if extension is not None:
            if not entry.suffix.lower() == extension.lower():
                continue

        # Check keyword match (case-insensitive)
        name_lower = entry.name.lower()
        if keyword_lower not in name_lower:
            continue

        # Check secondary pattern if specified
        if secondary_lower is not None:
            if secondary_lower not in name_lower:
                continue

        matches.append(entry)

    # Build result
    if len(matches) == 1:
        return FileSearchResult(
            found=True,
            path=matches[0],
            matches=matches,
            keyword=keyword,
            message=f"Found: {matches[0].name}"
        )
    elif len(matches) == 0:
        return FileSearchResult(
            found=False,
            path=None,
            matches=matches,
            keyword=keyword,
            message=f"No files found matching '{keyword}'"
        )
    else:
        return FileSearchResult(
            found=False,
            path=None,
            matches=matches,
            keyword=keyword,
            message=f"Multiple files ({len(matches)}) match '{keyword}'"
        )


def list_calibration_files(
    directory: Path,
    verbose: bool = True
) -> Dict[str, List[Path]]:
    """
    List all potential calibration files in a directory.

    Useful for debugging when file discovery fails.

    Parameters
    ----------
    directory : Path
        Directory to search.

    verbose : bool, optional
        If True, print results to console. Default: True.

    Returns
    -------
    files : dict
        Dictionary mapping keywords to lists of matching files.
        Keys: 'dark', 'air', 'pol_0', 'pol_45', 'ret_90', 'ret_45', 'other'
    """
    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    # Define patterns
    patterns = {
        'dark': '_DARK_ECM_',
        'air': '_ST_ECM_',
        'pol_0': '_P0_ECM_',
        'pol_45': '_P45_ECM_',
        'ret_90': '_RET90_FP1_ECM_',
        'ret_45': '_RET45_FP2_ECM_'
    }

    # Initialize results
    results: Dict[str, List[Path]] = {k: [] for k in patterns}
    results['other'] = []

    # Scan directory
    for entry in directory.iterdir():
        if entry.is_dir() or entry.name.startswith('.'):
            continue

        name_lower = entry.name.lower()
        matched = False

        for key, pattern in patterns.items():
            if pattern.lower() in name_lower:
                results[key].append(entry)
                matched = True
                break

        if not matched:
            results['other'].append(entry)

    # Print results if verbose
    if verbose:
        print(f"\nCalibration files in: {directory}")
        print("=" * 60)

        for key in ['dark', 'air', 'pol_0', 'pol_45', 'ret_90', 'ret_45']:
            files = results[key]
            if len(files) == 1:
                status = "OK"
            elif len(files) == 0:
                status = "MISSING" if key != 'ret_45' else "optional"
            else:
                status = f"AMBIGUOUS ({len(files)} files)"

            pattern = patterns[key]
            print(f"{key:10s} ({pattern:20s}): {status}")
            for f in files:
                print(f"    {f.name}")

        if results['other']:
            print(f"\nOther files ({len(results['other'])}): not matched to ECM patterns")

    return results
