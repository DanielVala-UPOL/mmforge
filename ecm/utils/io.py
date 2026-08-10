"""
Data I/O Module for ECM Calibration

This module provides functions for loading binary spectral measurement data
and wavelength calibration files from the polarimeter.

Functions
---------
detect_angular_positions(file_paths, n_wavelengths, ...)
    Auto-detect number of angular positions from binary data file dimensions.
load_spectral_data(filepath, cfg)
    Load binary spectral measurement data from polarimeter.
load_wavelengths(cfg)
    Load wavelength calibration data and select analysis range.

Data Structures
---------------
SpectralDataInfo
    Metadata from loading spectral data (filepath, dimensions, timing).
WavelengthInfo
    Metadata from loading wavelengths (range, indices, totals).

Binary File Format
------------------
The polarimeter produces binary files with the following format:
    - Data type: 32-bit float (float32)
    - Byte order: Little-endian (IEEE 754)
    - Layout: [n_wavelengths x n_angles], wavelength-first
    - Typical dimensions: 2048 wavelengths x 96 angles = 786,432 bytes

After loading and transpose, the output is [n_angles x n_wavelengths],
so each row is a spectrum at one angular position.

References
----------
[1] PROJECT_GUIDELINES.md, Section 5: Data File Specifications

Example
-------
>>> from ecm.config import ECMConfig
>>> from ecm.utils.io import load_spectral_data, load_wavelengths
>>>
>>> cfg = ECMConfig()
>>> wavelengths, idx_range, wl_info = load_wavelengths(cfg)
>>> data, info = load_spectral_data('calibration/transmission/260109_ST_ECM_1', cfg)
>>>
>>> # Select wavelengths in range
>>> data_in_range = data[:, idx_range]
>>> print(f"Shape: {data_in_range.shape}")  # (96, n_selected_wavelengths)
"""

import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Union, Optional, List

import numpy as np
from numpy import ndarray

# Import config for type hints (avoid circular import with TYPE_CHECKING)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ecm.config import ECMConfig


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SpectralDataInfo:
    """
    Metadata from loading spectral data.

    Attributes
    ----------
    filepath : Path
        Full path to the loaded file.
    n_wavelengths : int
        Number of wavelength channels in the loaded data.
    n_angles : int
        Number of angular positions in the loaded data.
    file_size : int
        Actual file size in bytes.
    expected_size : int
        Expected file size based on configuration.
    load_time : float
        Time taken to load the file [seconds].
    """
    filepath: Path
    n_wavelengths: int
    n_angles: int
    file_size: int
    expected_size: int
    load_time: float


@dataclass
class WavelengthInfo:
    """
    Metadata from loading wavelength calibration.

    Attributes
    ----------
    filepath : Path
        Path to the wavelength calibration file.
    all_wavelengths : ndarray
        Complete wavelength array [nm] (all channels).
    n_total : int
        Total number of wavelength channels.
    n_selected : int
        Number of wavelengths within the analysis range.
    range_nm : Tuple[float, float]
        Actual [min, max] of selected wavelengths [nm].
    idx_first : int
        Index of first selected wavelength in full array.
    idx_last : int
        Index of last selected wavelength in full array.
    """
    filepath: Path
    all_wavelengths: ndarray
    n_total: int
    n_selected: int
    range_nm: Tuple[float, float]
    idx_first: int
    idx_last: int


# =============================================================================
# AUTO-DETECT ANGULAR POSITIONS
# =============================================================================

def detect_angular_positions(
    file_paths: List[Path],
    n_wavelengths: int,
    n_rotation_cycles: int = 1,
    file_labels: Optional[List[str]] = None,
) -> int:
    """
    Auto-detect the number of angular positions from binary data file dimensions.

    Each binary file contains float32 values with total size:
        file_size = n_wavelengths x n_angular_positions x n_rotation_cycles x 4 bytes

    Parameters
    ----------
    file_paths : list of Path
        Paths to binary data files to check.
    n_wavelengths : int
        Number of wavelength channels (e.g. 2048 for BlackComet).
    n_rotation_cycles : int
        Number of rotation cycles per file (default: 1).
    file_labels : list of str, optional
        Human-readable labels for error messages (e.g. ['DARK', 'ST', 'P0']).

    Returns
    -------
    int
        Detected number of angular positions per rotation cycle.

    Raises
    ------
    ValueError
        If files have inconsistent dimensions or file sizes are invalid.
    """
    bytes_per_value = 4  # float32
    detected = {}

    for i, path in enumerate(file_paths):
        label = file_labels[i] if file_labels else path.name
        file_size = path.stat().st_size

        total_values = file_size // bytes_per_value
        if file_size % bytes_per_value != 0:
            raise ValueError(
                f"File '{label}' size ({file_size} bytes) not divisible by 4. "
                "File may be corrupted or not in float32 format."
            )

        n_total_angles = total_values // n_wavelengths
        remainder = total_values % n_wavelengths
        if remainder != 0:
            raise ValueError(
                f"File '{label}' dimension error: {total_values} values "
                f"not divisible by {n_wavelengths} wavelengths."
            )

        if n_total_angles % n_rotation_cycles != 0:
            raise ValueError(
                f"File '{label}': inferred {n_total_angles} total angles "
                f"not divisible by n_rotation_cycles={n_rotation_cycles}."
            )

        n_angular = n_total_angles // n_rotation_cycles
        detected[label] = n_angular

    # Check consistency
    unique_values = set(detected.values())
    if len(unique_values) > 1:
        details = ", ".join(f"{k}: {v}" for k, v in detected.items())
        raise ValueError(
            f"Inconsistent angular positions across files: {details}. "
            "All files must have the same number of angular positions."
        )

    if len(unique_values) == 0:
        raise ValueError("No valid files provided for angular position detection.")

    return unique_values.pop()


# =============================================================================
# LOAD SPECTRAL DATA
# =============================================================================

def load_spectral_data(
    filepath: Union[str, Path],
    cfg: 'ECMConfig'
) -> Tuple[ndarray, SpectralDataInfo]:
    """
    Load binary spectral measurement data from polarimeter.

    Reads a binary file containing spectral intensity measurements and
    returns the data as a 2D numpy array along with metadata.

    Parameters
    ----------
    filepath : str or Path
        Path to the binary data file. Can be:
        - Absolute path to the file
        - Relative path from current directory
        - Filename only (will search in calibration/sample directories)

    cfg : ECMConfig
        Configuration structure containing file format specifications
        and directory paths.

    Returns
    -------
    data : ndarray, shape (n_angles, n_wavelengths)
        Intensity matrix. Each row is one spectrum at a given angular
        position. Each column is intensity vs angle at one wavelength.
        data[i, j] = intensity at angle i, wavelength j.

    info : SpectralDataInfo
        Metadata about the loaded file including dimensions and timing.

    Raises
    ------
    FileNotFoundError
        If the file cannot be found in any search directory.
    ValueError
        If the file size doesn't match expected dimensions and cannot
        be automatically resolved.

    Notes
    -----
    **Binary File Format:**
    - Data type: 32-bit float (float32)
    - Byte order: Little-endian (IEEE 754)
    - Layout: [n_wavelengths x n_angles], wavelength-first
    - The output is transposed to [n_angles x n_wavelengths]

    **Search Order:**
    If filepath is not absolute or doesn't exist, the function searches:
    1. calibration_transmission_dir
    2. calibration_reflection_dir
    3. samples_transmission_dir
    4. samples_reflection_dir
    5. data_dir

    **Data Quality Checks:**
    The function warns about:
    - Negative values (possible data corruption)
    - Saturated values (>= saturation_level)
    - NaN or Inf values

    References
    ----------
    [1] PROJECT_GUIDELINES.md, Section 5: Data File Specifications

    Examples
    --------
    >>> from ecm.config import ECMConfig
    >>> from ecm.utils.io import load_spectral_data
    >>>
    >>> cfg = ECMConfig()
    >>> data, info = load_spectral_data('260109_ST_ECM_1', cfg)
    >>> print(f"Loaded {info.n_angles} angles x {info.n_wavelengths} wavelengths")
    """
    # =========================================================================
    # Start timing
    # =========================================================================
    start_time = time.time()

    # =========================================================================
    # Convert to Path object
    # =========================================================================
    filepath = Path(filepath)

    # =========================================================================
    # Find the file
    # =========================================================================
    resolved_path = _find_data_file(filepath, cfg)

    if resolved_path is None:
        # Build helpful error message with search locations
        search_dirs = _get_search_directories(cfg)
        search_locations = "\n  - ".join(str(d) for d in search_dirs if d is not None)

        raise FileNotFoundError(
            f"File not found: {filepath}\n"
            f"Searched in:\n  - {search_locations}\n\n"
            f"Suggestions:\n"
            f"  1. Check that the file exists\n"
            f"  2. Use an absolute path\n"
            f"  3. Verify cfg.paths settings"
        )

    filepath = resolved_path

    # =========================================================================
    # Get expected dimensions from config
    # =========================================================================
    n_wavelengths_expected = cfg.spectrometer.n_wavelengths
    n_angles_expected = (
        cfg.acquisition.n_angular_positions *
        cfg.acquisition.n_rotation_cycles
    )

    # Expected file size in bytes (float32 = 4 bytes per value)
    bytes_per_value = 4
    expected_size = n_wavelengths_expected * n_angles_expected * bytes_per_value

    # =========================================================================
    # Check actual file size
    # =========================================================================
    actual_size = filepath.stat().st_size

    # Determine actual dimensions
    n_wavelengths = n_wavelengths_expected
    n_angles = n_angles_expected

    if actual_size != expected_size:
        # Try to infer dimensions from file size
        total_values = actual_size // bytes_per_value

        if actual_size % bytes_per_value != 0:
            raise ValueError(
                f"File size ({actual_size} bytes) is not divisible by {bytes_per_value}. "
                f"File may be corrupted or not in float32 format."
            )

        # Check if file matches expected wavelengths with different angle count
        if total_values % n_wavelengths_expected == 0:
            n_angles = total_values // n_wavelengths_expected

            warnings.warn(
                f"File size mismatch.\n"
                f"  Expected: {expected_size} bytes "
                f"({n_wavelengths_expected} wavelengths x {n_angles_expected} angles x 4 bytes)\n"
                f"  Actual:   {actual_size} bytes\n"
                f"  Inferred: {n_angles} angular positions",
                UserWarning
            )
        else:
            raise ValueError(
                f"File size ({actual_size} bytes) does not match expected dimensions.\n"
                f"Expected: {n_wavelengths_expected} wavelengths x {n_angles_expected} angles = "
                f"{expected_size} bytes.\n"
                f"Cannot infer dimensions from file size."
            )

    # =========================================================================
    # Read binary data
    # =========================================================================
    # Determine numpy dtype based on byte order
    if cfg.file_format.byte_order == 'little':
        dtype = '<f4'  # Little-endian float32
    else:
        dtype = '>f4'  # Big-endian float32

    # Read file as flat array
    raw_data = np.fromfile(filepath, dtype=dtype)

    # Verify we got the expected number of values
    expected_values = n_wavelengths * n_angles
    if len(raw_data) != expected_values:
        raise ValueError(
            f"Read {len(raw_data)} values, expected {expected_values}. "
            f"File may be corrupted."
        )

    # Reshape to [n_wavelengths x n_angles] using FORTRAN (column-major) order
    #
    # CRITICAL: The binary file is written by MATLAB in column-major order.
    # MATLAB's fread(fid, [n_wl, n_ang]) fills the matrix column-by-column:
    #   - raw_bytes[0:n_wl*4] → column 0 (all wavelengths for angle 0)
    #   - raw_bytes[n_wl*4:2*n_wl*4] → column 1 (all wavelengths for angle 1)
    #   - etc.
    #
    # NumPy's default reshape uses row-major (C) order, which would be WRONG.
    # We must use order='F' to match MATLAB's column-major convention.
    raw_data = raw_data.reshape((n_wavelengths, n_angles), order='F')

    # Transpose to [n_angles x n_wavelengths] (analysis layout)
    # This makes each row a spectrum, which is more intuitive
    data = raw_data.T.astype(np.float64)  # Convert to double precision

    # =========================================================================
    # Calculate load time
    # =========================================================================
    load_time = time.time() - start_time

    # =========================================================================
    # Prepare metadata
    # =========================================================================
    info = SpectralDataInfo(
        filepath=filepath,
        n_wavelengths=data.shape[1],
        n_angles=data.shape[0],
        file_size=actual_size,
        expected_size=expected_size,
        load_time=load_time
    )

    # =========================================================================
    # Data quality checks
    # =========================================================================
    _check_data_quality(data, cfg, filepath)

    # =========================================================================
    # Verbose output
    # =========================================================================
    if cfg.output.verbosity > 1:
        print(f"Loaded: {filepath}")
        print(f"  Size: {info.n_angles} angles x {info.n_wavelengths} wavelengths")
        print(f"  Value range: [{data.min():.2f}, {data.max():.2f}]")
        print(f"  Load time: {load_time:.3f} s")

    return data, info


def _find_data_file(filepath: Path, cfg: 'ECMConfig') -> Optional[Path]:
    """
    Find a data file, searching in configured directories if needed.

    Parameters
    ----------
    filepath : Path
        File path (absolute, relative, or filename only).
    cfg : ECMConfig
        Configuration with directory paths.

    Returns
    -------
    Optional[Path]
        Resolved path if found, None otherwise.
    """
    # If file exists at given path, return it
    if filepath.is_file():
        return filepath.resolve()

    # Get list of directories to search
    search_dirs = _get_search_directories(cfg)

    # Try each directory
    for search_dir in search_dirs:
        if search_dir is None:
            continue

        candidate = search_dir / filepath
        if candidate.is_file():
            return candidate.resolve()

        # Also try just the filename
        if filepath.name != str(filepath):
            candidate = search_dir / filepath.name
            if candidate.is_file():
                return candidate.resolve()

    return None


def _get_search_directories(cfg: 'ECMConfig') -> List[Optional[Path]]:
    """
    Get list of directories to search for data files.

    Parameters
    ----------
    cfg : ECMConfig
        Configuration with directory paths.

    Returns
    -------
    List[Optional[Path]]
        List of directory paths to search.
    """
    return [
        cfg.paths.calibration_transmission_dir,
        cfg.paths.calibration_reflection_dir,
        cfg.paths.samples_transmission_dir,
        cfg.paths.samples_reflection_dir,
        cfg.paths.data_dir,
    ]


def _check_data_quality(data: ndarray, cfg: 'ECMConfig', filepath: Path) -> None:
    """
    Check loaded data for quality issues.

    Parameters
    ----------
    data : ndarray
        Loaded intensity data.
    cfg : ECMConfig
        Configuration with saturation level.
    filepath : Path
        File path (for error messages).
    """
    # Check for negative values
    n_negative = np.sum(data < 0)
    if n_negative > 0:
        warnings.warn(
            f"Data from {filepath.name} contains {n_negative} negative values "
            f"({100 * n_negative / data.size:.2f}%). "
            f"This may indicate data corruption.",
            UserWarning
        )

    # Check for saturation
    saturation_level = cfg.spectrometer.saturation_level
    n_saturated = np.sum(data >= saturation_level)
    if n_saturated > 0:
        warnings.warn(
            f"Data from {filepath.name} contains {n_saturated} saturated values "
            f"({100 * n_saturated / data.size:.2f}%) at or above {saturation_level}. "
            f"Consider reducing integration time.",
            UserWarning
        )

    # Check for NaN/Inf
    n_invalid = np.sum(~np.isfinite(data))
    if n_invalid > 0:
        warnings.warn(
            f"Data from {filepath.name} contains {n_invalid} NaN or Inf values. "
            f"Data may be corrupted.",
            UserWarning
        )


# =============================================================================
# LOAD WAVELENGTHS
# =============================================================================

def load_wavelengths(
    cfg: 'ECMConfig'
) -> Tuple[ndarray, ndarray, WavelengthInfo]:
    """
    Load wavelength calibration data and select analysis range.

    Reads the wavelength calibration file and returns wavelengths within
    the configured analysis range along with indices for extracting
    corresponding data columns.

    Parameters
    ----------
    cfg : ECMConfig
        Configuration structure containing:
        - spectrometer.wavelength_file: Path to calibration file
        - wavelength.range_nm: (min, max) analysis range [nm]

    Returns
    -------
    wavelengths : ndarray, shape (n_selected,)
        Wavelengths [nm] within the analysis range.

    idx_range : ndarray, shape (n_selected,)
        Indices into the full wavelength array for the selected range.
        Use this to extract corresponding data columns:
        data_in_range = data[:, idx_range]

    info : WavelengthInfo
        Metadata including full wavelength array and range information.

    Raises
    ------
    FileNotFoundError
        If the wavelength calibration file is not found.
    ValueError
        If no wavelengths are found within the specified range.

    Notes
    -----
    **File Format:**
    The wavelength calibration file is a text file with one wavelength
    value (in nm) per line. For the StellarNet BlackComet spectrometer,
    this is typically 2048 values ranging from ~187 to ~1076 nm.

    **Index Usage:**
    The returned idx_range array contains indices that can be used to
    extract wavelength-matched data from loaded spectral files:

        wavelengths, idx_range, info = load_wavelengths(cfg)
        data, _ = load_spectral_data(filepath, cfg)
        data_in_range = data[:, idx_range]  # Now matches wavelengths

    Examples
    --------
    >>> from ecm.config import ECMConfig
    >>> from ecm.utils.io import load_wavelengths
    >>>
    >>> cfg = ECMConfig()
    >>> cfg.wavelength.range_nm = (500.0, 900.0)
    >>> wavelengths, idx_range, info = load_wavelengths(cfg)
    >>> print(f"Selected {info.n_selected} wavelengths from {info.n_total} total")
    >>> print(f"Range: {info.range_nm[0]:.1f} - {info.range_nm[1]:.1f} nm")
    """
    # =========================================================================
    # Find wavelength file
    # =========================================================================
    wavelength_file = cfg.spectrometer.wavelength_file

    if wavelength_file is None:
        raise ValueError(
            "cfg.spectrometer.wavelength_file is not set. "
            "Please configure the wavelength calibration file path."
        )

    wavelength_file = Path(wavelength_file)

    # If not found at configured path, try alternative locations
    if not wavelength_file.is_file():
        alternative_paths = [
            wavelength_file,
            cfg.paths.assets_dir / 'BlackCommet_wavelengths.txt' if cfg.paths.assets_dir else None,
            cfg.paths.data_dir / 'assets' / 'BlackCommet_wavelengths.txt' if cfg.paths.data_dir else None,
            cfg.paths.assets_dir / 'StellarNet_BlackCommet_wavelength_list.txt' if cfg.paths.assets_dir else None,
            Path('BlackCommet_wavelengths.txt'),
        ]

        found = False
        for alt_path in alternative_paths:
            if alt_path is not None and alt_path.is_file():
                wavelength_file = alt_path
                found = True
                break

        if not found:
            raise FileNotFoundError(
                f"Wavelength calibration file not found: {cfg.spectrometer.wavelength_file}\n"
                f"Searched in:\n"
                f"  - {cfg.spectrometer.wavelength_file}\n"
                f"  - {cfg.paths.assets_dir / 'BlackCommet_wavelengths.txt' if cfg.paths.assets_dir else 'N/A'}\n\n"
                f"Suggestions:\n"
                f"  1. Ensure the wavelength file exists in data/assets/\n"
                f"  2. Set cfg.spectrometer.wavelength_file to the correct path"
            )

    # =========================================================================
    # Load wavelength data
    # =========================================================================
    try:
        all_wavelengths = np.loadtxt(wavelength_file)
    except Exception as e:
        raise ValueError(
            f"Error loading wavelength file {wavelength_file}: {e}\n"
            f"File should contain one wavelength value (in nm) per line."
        )

    # Ensure 1D array
    all_wavelengths = all_wavelengths.flatten()
    n_total = len(all_wavelengths)

    # Verify count matches spectrometer config
    if n_total != cfg.spectrometer.n_wavelengths:
        warnings.warn(
            f"Wavelength file has {n_total} entries "
            f"(expected {cfg.spectrometer.n_wavelengths} from config). "
            f"Using actual count from file.",
            UserWarning
        )

    # =========================================================================
    # Select wavelength range
    # =========================================================================
    wl_min, wl_max = cfg.wavelength.range_nm

    # Find indices within range
    mask = (all_wavelengths >= wl_min) & (all_wavelengths <= wl_max)
    idx_range = np.where(mask)[0]

    if len(idx_range) == 0:
        raise ValueError(
            f"No wavelengths found in range [{wl_min:.1f}, {wl_max:.1f}] nm.\n"
            f"Wavelength file contains: [{all_wavelengths.min():.1f}, {all_wavelengths.max():.1f}] nm.\n"
            f"Please adjust cfg.wavelength.range_nm."
        )

    wavelengths = all_wavelengths[idx_range]
    n_selected = len(wavelengths)

    # =========================================================================
    # Prepare metadata
    # =========================================================================
    info = WavelengthInfo(
        filepath=wavelength_file,
        all_wavelengths=all_wavelengths,
        n_total=n_total,
        n_selected=n_selected,
        range_nm=(wavelengths.min(), wavelengths.max()),
        idx_first=idx_range[0],
        idx_last=idx_range[-1]
    )

    # =========================================================================
    # Verbose output
    # =========================================================================
    if cfg.output.verbosity > 0:
        print(f"Wavelengths loaded from: {wavelength_file}")
        print(f"  Total channels: {n_total} ({all_wavelengths.min():.1f} - {all_wavelengths.max():.1f} nm)")
        print(f"  Selected range: {n_selected} channels ({info.range_nm[0]:.1f} - {info.range_nm[1]:.1f} nm)")

    return wavelengths, idx_range, info
