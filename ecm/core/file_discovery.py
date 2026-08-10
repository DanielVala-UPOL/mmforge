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
                hint = _format_missing_file_hint(data_dir, keyword)
                raise FileNotFoundError(
                    f"Required calibration file not found.\n"
                    f"  Looking for: filename containing '{keyword}'\n"
                    f"  In directory: {data_dir}\n"
                    f"  Sample type: {name}"
                    f"{hint}"
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

def _suggest_subdirs_with_keyword(
    directory: Path, keyword: str, exclude_pattern: Optional[str] = None
) -> List[Path]:
    """Return immediate subdirectories of ``directory`` that contain at least
    one file whose name matches ``keyword`` (case-insensitive). Used to make
    "file not found" errors actionable when the user pointed at a parent
    directory.
    """
    kw = keyword.lower()
    excl = exclude_pattern.lower() if exclude_pattern else None
    hits: List[Path] = []
    if not directory.exists() or not directory.is_dir():
        return hits
    for sub in directory.iterdir():
        if not sub.is_dir() or sub.name.startswith('.'):
            continue
        for f in sub.iterdir():
            if f.is_dir():
                continue
            name_lower = f.name.lower()
            if kw not in name_lower:
                continue
            if excl is not None and excl in name_lower:
                continue
            hits.append(sub)
            break
    return hits


def _format_missing_file_hint(
    directory: Path, keyword: str, exclude_pattern: Optional[str] = None
) -> str:
    """Build a one-line hint suggesting subdirectories where the file might be."""
    suggestions = _suggest_subdirs_with_keyword(directory, keyword, exclude_pattern)
    if not suggestions:
        return (
            "\n  Hint: only the directory you specified is searched (not its "
            "subdirectories). If your data is in a subfolder, point the data "
            "directory at that subfolder directly."
        )
    paths_str = '\n'.join(f'    - {p}' for p in suggestions)
    return (
        "\n  Hint: the search is non-recursive. The following subdirectories "
        "of the path you specified contain a matching file:\n"
        f"{paths_str}\n"
        "  Update the data directory in CONFIGURATION to one of those paths."
    )


def _search_for_file(
    directory: Path,
    keyword: str,
    extension: Optional[str] = None,
    secondary_pattern: Optional[str] = None,
    exclude_pattern: Optional[str] = None
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

    exclude_pattern : str, optional
        Pattern that must NOT be present in the filename.
        Useful for excluding variants (e.g., exclude '_POL_' when
        searching for bare reflector files).

    Returns
    -------
    FileSearchResult
        Search result with found flag, path, and matches.
    """
    matches = []

    # Normalize keyword for case-insensitive comparison
    keyword_lower = keyword.lower()
    secondary_lower = secondary_pattern.lower() if secondary_pattern else None
    exclude_lower = exclude_pattern.lower() if exclude_pattern else None

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

        # Check exclude pattern
        if exclude_lower is not None:
            if exclude_lower in name_lower:
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


# =============================================================================
# REFLECTION MODE FILE DISCOVERY
# =============================================================================

@dataclass
class ReflectionCalibrationFiles:
    """
    Discovered reflection calibration file paths.

    Attributes
    ----------
    dark : Path
        Dark/background measurement file.
    wafer25nm : Path
        Bare wafer 25 nm measurement (no polarizer).
    wafer25nm_pol_before : Path
        Wafer 25 nm with polarizer before sample.
    wafer25nm_pol_after : Path
        Wafer 25 nm with polarizer after sample.
    wafer10nm : Path
        Bare wafer 10 nm measurement.
    wafer25nm_char_psi_delta : Path, optional
        Wafer 25 nm psi/delta characterization file.
    wafer25nm_char_RpRs : Path, optional
        Wafer 25 nm Rp/Rs characterization file.
    wafer10nm_char_psi_delta : Path, optional
        Wafer 10 nm psi/delta characterization file.
    wafer10nm_char_RpRs : Path, optional
        Wafer 10 nm Rp/Rs characterization file.
    """
    dark: Path
    wafer25nm: Path
    wafer25nm_pol_before: Path
    wafer25nm_pol_after: Path
    wafer10nm: Path
    wafer25nm_char_psi_delta: Optional[Path] = None
    wafer25nm_char_RpRs: Optional[Path] = None
    wafer10nm_char_psi_delta: Optional[Path] = None
    wafer10nm_char_RpRs: Optional[Path] = None


def discover_reflection_calibration_files(cfg: 'ECMConfig') -> ReflectionCalibrationFiles:
    """
    Auto-discover reflection calibration files by filename keywords.

    Searches the reflection calibration data directory for measurement files
    and the assets directory for wafer characterization files.

    Parameters
    ----------
    cfg : ECMConfig
        ECM configuration with paths and reflection_cal settings.

    Returns
    -------
    ReflectionCalibrationFiles
        Dataclass with paths to all discovered files.

    Raises
    ------
    FileNotFoundError
        If a required calibration or characterization file is not found.
    ValueError
        If multiple files match the same keyword pattern.
    """
    # -------------------------------------------------------------------------
    # Get data directory
    # -------------------------------------------------------------------------
    data_dir = cfg.paths.calibration_reflection_dir
    if data_dir is None:
        raise ValueError(
            "cfg.paths.calibration_reflection_dir must be set. "
            "Set it to the directory containing reflection calibration measurements."
        )

    data_dir = Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(
            f"Reflection calibration directory does not exist: {data_dir}"
        )

    # -------------------------------------------------------------------------
    # Define keyword patterns for reflection mode
    # -------------------------------------------------------------------------
    # Required measurement files
    # Note: WAFER25NM_ECM_ and WAFER10NM_ECM_ use exclude_pattern='_POL_'
    # to avoid matching POL_BEFORE and POL_AFTER variants
    required_keywords = {
        'dark': ('_DARK_ECM_', None),
        'wafer25nm': ('_WAFER25NM_ECM_', '_POL_'),           # exclude POL variants
        'wafer25nm_pol_before': ('_WAFER25NM_POL_BEFORE_ECM_', None),
        'wafer25nm_pol_after': ('_WAFER25NM_POL_AFTER_ECM_', None),
        'wafer10nm': ('_WAFER10NM_ECM_', '_POL_'),           # exclude POL variants
    }

    # -------------------------------------------------------------------------
    # Search for required measurement files
    # -------------------------------------------------------------------------
    found_files: Dict[str, Path] = {}

    print("\nSearching for reflection calibration files...")
    print(f"  Data directory: {data_dir}")
    print()

    for name, (keyword, exclude) in required_keywords.items():
        result = _search_for_file(data_dir, keyword, exclude_pattern=exclude)

        if not result.found:
            if len(result.matches) == 0:
                hint = _format_missing_file_hint(data_dir, keyword, exclude)
                raise FileNotFoundError(
                    f"Required reflection calibration file not found.\n"
                    f"  Looking for: filename containing '{keyword}'"
                    + (f" (excluding '{exclude}')" if exclude else "") +
                    f"\n  In directory: {data_dir}\n"
                    f"  Sample type: {name}"
                    f"{hint}"
                )
            else:
                raise ValueError(
                    f"Multiple files match '{keyword}':\n" +
                    '\n'.join(f"    {p.name}" for p in result.matches) +
                    f"\n  Please ensure only one file matches each pattern."
                )

        found_files[name] = result.path
        print(f"  Found {name:25s}: {result.path.name}")

    # -------------------------------------------------------------------------
    # Search for wafer characterization files in assets directory
    # -------------------------------------------------------------------------
    char_files: Dict[str, Optional[Path]] = {
        'wafer25nm_char_psi_delta': None,
        'wafer25nm_char_RpRs': None,
        'wafer10nm_char_psi_delta': None,
        'wafer10nm_char_RpRs': None,
    }

    assets_dir = cfg.paths.assets_dir
    if assets_dir is None or not Path(assets_dir).exists():
        raise FileNotFoundError(
            f"Assets directory not found: {assets_dir}. "
            f"Wafer characterization files are required for reflection calibration."
        )

    assets_dir = Path(assets_dir)
    r1_label = cfg.reflection_cal.wafer25nm_label
    r2_label = cfg.reflection_cal.wafer10nm_label

    print()
    print(f"  Searching for wafer characterization in: {assets_dir}")

    # Wafer characterization files
    char_patterns = {
        'wafer25nm_char_psi_delta': (r1_label, 'psi_delta'),
        'wafer25nm_char_RpRs': (r1_label, 'Rp_Rs'),
        'wafer10nm_char_psi_delta': (r2_label, 'psi_delta'),
        'wafer10nm_char_RpRs': (r2_label, 'Rp_Rs'),
    }

    for name, (label, secondary) in char_patterns.items():
        result = _search_for_file(
            assets_dir, label, extension='.txt', secondary_pattern=secondary
        )
        if result.found:
            char_files[name] = result.path
            print(f"  Found {name:35s}: {result.path.name}")
        else:
            raise FileNotFoundError(
                f"Required wafer characterization file not found.\n"
                f"  Looking for: '{label}' + '{secondary}' in {assets_dir}\n"
                f"  File type: {name}"
            )

    # -------------------------------------------------------------------------
    # Build result
    # -------------------------------------------------------------------------
    result = ReflectionCalibrationFiles(
        dark=found_files['dark'],
        wafer25nm=found_files['wafer25nm'],
        wafer25nm_pol_before=found_files['wafer25nm_pol_before'],
        wafer25nm_pol_after=found_files['wafer25nm_pol_after'],
        wafer10nm=found_files['wafer10nm'],
        wafer25nm_char_psi_delta=char_files['wafer25nm_char_psi_delta'],
        wafer25nm_char_RpRs=char_files['wafer25nm_char_RpRs'],
        wafer10nm_char_psi_delta=char_files['wafer10nm_char_psi_delta'],
        wafer10nm_char_RpRs=char_files['wafer10nm_char_RpRs'],
    )

    print()
    print("  All reflection calibration files found successfully")

    return result
