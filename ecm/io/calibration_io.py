"""
Calibration Save/Load Functions

This module provides functions for saving ECM calibration results to disk
and loading them back for sample processing.

Functions
---------
save_calibration(result, diagnostics, cfg, ...)
    Save calibration results to .npz file with metadata.

load_calibration(filepath)
    Load saved calibration from .npz file.

Data Structures
---------------
CalibrationMetadata
    Metadata stored with calibration (timestamp, version, etc.).

File Format
-----------
Calibration is saved as a NumPy .npz archive containing:
- W, A matrices (4×4×n_wavelengths)
- Wavelengths
- Retarder parameters (delta, tau, theta, psi)
- Diagnostics (eigenvalue_ratios, condition_numbers)
- Configuration snapshot (as JSON)
- Metadata (timestamp, version, mode)

Example
-------
>>> from ecm.core import calibrate_transmission
>>> from ecm.io import save_calibration, load_calibration
>>>
>>> # Run calibration
>>> result, diagnostics = calibrate_transmission(cfg)
>>>
>>> # Save to file
>>> filepath = save_calibration(result, diagnostics, cfg)
>>> print(f"Saved to: {filepath}")
>>>
>>> # Load later for sample processing
>>> result, diagnostics, cfg, metadata = load_calibration(filepath)
>>> print(f"Loaded calibration from {metadata.timestamp}")
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import numpy as np
from numpy import ndarray

from ecm.config.ecm_config import ECMConfig
from ecm.core.transmission_calibration import (
    CalibrationResult,
    CalibrationDiagnostics,
    RetarderCalibrationParams,
)
from ecm.core.file_discovery import CalibrationFiles


# =============================================================================
# VERSION INFO
# =============================================================================

# File format version for compatibility checking
CALIBRATION_FILE_VERSION = "1.0.0"

# Library version (should match package version)
LIBRARY_VERSION = "6.5.5"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class CalibrationMetadata:
    """
    Metadata stored with calibration file.

    Attributes
    ----------
    timestamp : str
        ISO format timestamp when calibration was saved.

    file_version : str
        Calibration file format version.

    library_version : str
        ECM library version used for calibration.

    mode : str
        Measurement mode ('transmission' or 'reflection').

    n_wavelengths : int
        Number of wavelengths in calibration.

    wavelength_range : Tuple[float, float]
        Wavelength range in nm (min, max).

    use_ret45 : bool
        Whether second retarder was used.

    mean_eigenvalue_ratio : float
        Mean eigenvalue ratio (quality metric).

    calibration_files : Dict[str, str]
        Paths to calibration files used (as strings).
    """
    timestamp: str
    file_version: str
    library_version: str
    mode: str
    n_wavelengths: int
    wavelength_range: Tuple[float, float]
    use_ret45: bool
    mean_eigenvalue_ratio: float
    calibration_files: Dict[str, str]


# =============================================================================
# SAVE CALIBRATION
# =============================================================================

def save_calibration(
    result: CalibrationResult,
    diagnostics: CalibrationDiagnostics,
    cfg: ECMConfig,
    output_path: Optional[Path] = None,
    filename: Optional[str] = None,
    verbose: bool = True,
) -> Path:
    """
    Save calibration results to .npz file with metadata.

    Creates a timestamped .npz file containing all calibration matrices,
    diagnostics, configuration, and metadata for later use.

    Parameters
    ----------
    result : CalibrationResult
        Calibration matrices (W, A) and associated parameters.

    diagnostics : CalibrationDiagnostics
        Quality metrics and intermediate results.

    cfg : ECMConfig
        Configuration used for calibration.

    output_path : Path, optional
        Output directory or full file path.
        If directory: creates timestamped filename.
        If None: uses cfg.paths.calibration_output_dir.

    filename : str, optional
        Custom filename (without path).
        Default: ecm_calibration_transmission_YYYYMMDD_HHMMSS.npz

    verbose : bool, optional
        Print save confirmation. Default: True.

    Returns
    -------
    filepath : Path
        Path to saved calibration file.

    Examples
    --------
    >>> # Save with default settings
    >>> filepath = save_calibration(result, diagnostics, cfg)
    >>> print(f"Saved to: {filepath}")

    >>> # Save to specific directory
    >>> filepath = save_calibration(result, diagnostics, cfg,
    ...                             output_path=Path('/output'))

    >>> # Save with custom filename
    >>> filepath = save_calibration(result, diagnostics, cfg,
    ...                             filename='my_calibration.npz')

    Notes
    -----
    **File Contents:**

    The .npz archive contains:
    - ``W``: PSG modulation matrices [4×4×n_wl]
    - ``A``: PSA modulation matrices [4×4×n_wl]
    - ``wavelengths``: Wavelength values [n_wl]
    - ``wl_indices``: Indices into full wavelength array [n_wl]
    - ``inv_W_mod``: Pseudo-inverse of modulation basis [16×n_angles]
    - ``pol_theta``: Polarizer angles [2×n_wl]
    - ``ret_delta``: Retarder retardation [n_wl]
    - ``ret_tau``: Retarder transmission [n_wl]
    - ``ret_theta``: Retarder orientation [n_wl]
    - ``ret_psi``: Retarder ellipsometric angle [n_wl]
    - ``eigenvalue_ratio``: Quality metric [n_wl]
    - ``cond_W``: W condition numbers [n_wl]
    - ``cond_A``: A condition numbers [n_wl]
    - ``I_dark``: Dark intensity [n_angles×n_wl]
    - ``config_json``: Configuration as JSON string
    - ``metadata_json``: Metadata as JSON string

    If second retarder was used, also includes:
    - ``ret45_delta``, ``ret45_tau``, ``ret45_theta``, ``ret45_psi``
    """
    # -------------------------------------------------------------------------
    # Determine output path
    # -------------------------------------------------------------------------
    if output_path is None:
        output_dir = cfg.paths.calibration_output_dir
        if output_dir is None:
            raise ValueError(
                "No output path specified and cfg.paths.calibration_output_dir is None. "
                "Provide output_path or set calibration_output_dir in configuration."
            )
    else:
        output_path = Path(output_path)
        if output_path.suffix == '.npz':
            # Full file path provided
            output_dir = output_path.parent
            filename = output_path.name
        else:
            # Directory provided
            output_dir = output_path

    output_dir = Path(output_dir)

    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Generate filename if not provided
    # -------------------------------------------------------------------------
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ecm_calibration_{cfg.mode}_{timestamp}.npz"

    filepath = output_dir / filename

    # -------------------------------------------------------------------------
    # Build metadata
    # -------------------------------------------------------------------------
    cal_files_dict = {}
    if result.cal_files is not None:
        cal_files_dict = {
            'dark': str(result.cal_files.dark) if result.cal_files.dark else None,
            'air': str(result.cal_files.air) if result.cal_files.air else None,
            'pol_0': str(result.cal_files.pol_0) if result.cal_files.pol_0 else None,
            'pol_45': str(result.cal_files.pol_45) if result.cal_files.pol_45 else None,
            'ret_90': str(result.cal_files.ret_90) if result.cal_files.ret_90 else None,
            'ret_45': str(result.cal_files.ret_45) if result.cal_files.ret_45 else None,
        }

    metadata = CalibrationMetadata(
        timestamp=datetime.now().isoformat(),
        file_version=CALIBRATION_FILE_VERSION,
        library_version=LIBRARY_VERSION,
        mode=cfg.mode,
        n_wavelengths=len(result.wavelengths),
        wavelength_range=(float(result.wavelengths.min()), float(result.wavelengths.max())),
        use_ret45=result.use_ret45,
        mean_eigenvalue_ratio=float(np.mean(diagnostics.eigenvalue_ratio)),
        calibration_files=cal_files_dict,
    )

    # -------------------------------------------------------------------------
    # Build save dictionary
    # -------------------------------------------------------------------------
    save_dict = {
        # Core calibration matrices
        'W': result.W,
        'A': result.A,
        'wavelengths': result.wavelengths,
        'wl_indices': result.wl_indices,
        'inv_W_mod': result.inv_W_mod,

        # Polarizer angles
        'pol_theta': result.pol_theta,

        # Primary retarder parameters
        'ret_delta': result.ret_params.delta,
        'ret_tau': result.ret_params.tau,
        'ret_theta': result.ret_params.theta,
        'ret_psi': result.ret_params.psi,

        # Diagnostics
        'eigenvalue_ratio': diagnostics.eigenvalue_ratio,
        'cond_W': diagnostics.cond_W,
        'cond_A': diagnostics.cond_A,
        'I_dark': diagnostics.I_dark,

        # B matrices (intensity matrices)
        'B_air': diagnostics.B_air,
        'B_pol0': diagnostics.B_pol0,
        'B_pol45': diagnostics.B_pol45,
        'B_ret': diagnostics.B_ret,

        # Polarizer extracted parameters
        'pol0_tau': diagnostics.pol0_params.get('tau', np.array([])),
        'pol45_tau': diagnostics.pol45_params.get('tau', np.array([])),

        # Use flags
        'use_ret45': np.array([result.use_ret45]),

        # Configuration and metadata as JSON strings
        'config_json': np.array([json.dumps(cfg.to_dict())]),
        'metadata_json': np.array([json.dumps(asdict(metadata))]),
    }

    # Add second retarder if used
    if result.use_ret45 and result.ret45_params is not None:
        save_dict['ret45_delta'] = result.ret45_params.delta
        save_dict['ret45_tau'] = result.ret45_params.tau
        save_dict['ret45_theta'] = result.ret45_params.theta
        save_dict['ret45_psi'] = result.ret45_params.psi

        if diagnostics.B_ret45 is not None:
            save_dict['B_ret45'] = diagnostics.B_ret45

    # -------------------------------------------------------------------------
    # Save to file
    # -------------------------------------------------------------------------
    np.savez_compressed(filepath, **save_dict)

    if verbose:
        print(f"\nCalibration saved to: {filepath}")
        print(f"  Wavelengths: {len(result.wavelengths)}")
        print(f"  Range: {result.wavelengths.min():.1f} - {result.wavelengths.max():.1f} nm")
        print(f"  Mean eigenvalue ratio: {np.mean(diagnostics.eigenvalue_ratio):.2e}")
        print(f"  File size: {filepath.stat().st_size / 1024:.1f} KB")

    return filepath


# =============================================================================
# LOAD CALIBRATION
# =============================================================================

def load_calibration(
    filepath: Path,
    verbose: bool = True,
) -> Tuple[CalibrationResult, CalibrationDiagnostics, ECMConfig, CalibrationMetadata]:
    """
    Load saved calibration from .npz file.

    Reconstructs CalibrationResult, CalibrationDiagnostics, and ECMConfig
    from a saved calibration file.

    Parameters
    ----------
    filepath : Path
        Path to saved calibration .npz file.

    verbose : bool, optional
        Print load confirmation. Default: True.

    Returns
    -------
    result : CalibrationResult
        Calibration matrices and parameters.

    diagnostics : CalibrationDiagnostics
        Quality metrics and intermediate results.

    cfg : ECMConfig
        Configuration used for calibration.

    metadata : CalibrationMetadata
        File metadata (timestamp, version, etc.).

    Raises
    ------
    FileNotFoundError
        If calibration file does not exist.

    ValueError
        If file format is incompatible or corrupted.

    Examples
    --------
    >>> from ecm.io import load_calibration
    >>>
    >>> result, diagnostics, cfg, metadata = load_calibration('calibration.npz')
    >>> print(f"Loaded {metadata.n_wavelengths} wavelengths")
    >>> print(f"Calibration from: {metadata.timestamp}")

    Notes
    -----
    **Version Compatibility:**

    The function checks the file format version and warns if it differs
    from the current version. Future versions will maintain backwards
    compatibility where possible.
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Calibration file not found: {filepath}")

    # -------------------------------------------------------------------------
    # Load .npz file
    # -------------------------------------------------------------------------
    try:
        data = np.load(filepath, allow_pickle=True)
    except Exception as e:
        raise ValueError(f"Error loading calibration file: {e}")

    # -------------------------------------------------------------------------
    # Extract metadata
    # -------------------------------------------------------------------------
    if 'metadata_json' not in data:
        raise ValueError(
            "Calibration file missing metadata. "
            "File may be corrupted or from an incompatible version."
        )

    metadata_dict = json.loads(str(data['metadata_json'][0]))
    metadata = CalibrationMetadata(
        timestamp=metadata_dict['timestamp'],
        file_version=metadata_dict['file_version'],
        library_version=metadata_dict['library_version'],
        mode=metadata_dict['mode'],
        n_wavelengths=metadata_dict['n_wavelengths'],
        wavelength_range=tuple(metadata_dict['wavelength_range']),
        use_ret45=metadata_dict['use_ret45'],
        mean_eigenvalue_ratio=metadata_dict['mean_eigenvalue_ratio'],
        calibration_files=metadata_dict['calibration_files'],
    )

    # Check version compatibility
    if metadata.file_version != CALIBRATION_FILE_VERSION:
        import warnings
        warnings.warn(
            f"Calibration file version ({metadata.file_version}) differs from "
            f"current version ({CALIBRATION_FILE_VERSION}). "
            f"Some features may not work correctly.",
            UserWarning
        )

    # -------------------------------------------------------------------------
    # Extract configuration
    # -------------------------------------------------------------------------
    if 'config_json' not in data:
        raise ValueError("Calibration file missing configuration data.")

    config_dict = json.loads(str(data['config_json'][0]))
    cfg = ECMConfig._from_dict(config_dict)

    # -------------------------------------------------------------------------
    # Extract calibration files info
    # -------------------------------------------------------------------------
    cal_files = None
    if metadata.calibration_files:
        cal_files = CalibrationFiles(
            dark=Path(metadata.calibration_files.get('dark', '')) if metadata.calibration_files.get('dark') else Path('.'),
            air=Path(metadata.calibration_files.get('air', '')) if metadata.calibration_files.get('air') else Path('.'),
            pol_0=Path(metadata.calibration_files.get('pol_0', '')) if metadata.calibration_files.get('pol_0') else Path('.'),
            pol_45=Path(metadata.calibration_files.get('pol_45', '')) if metadata.calibration_files.get('pol_45') else Path('.'),
            ret_90=Path(metadata.calibration_files.get('ret_90', '')) if metadata.calibration_files.get('ret_90') else Path('.'),
            ret_45=Path(metadata.calibration_files.get('ret_45', '')) if metadata.calibration_files.get('ret_45') else None,
            has_second_retarder=metadata.use_ret45,
        )

    # -------------------------------------------------------------------------
    # Reconstruct CalibrationResult
    # -------------------------------------------------------------------------
    use_ret45 = bool(data['use_ret45'][0])

    ret_params = RetarderCalibrationParams(
        tau=data['ret_tau'],
        delta=data['ret_delta'],
        theta=data['ret_theta'],
        psi=data['ret_psi'],
    )

    ret45_params = None
    if use_ret45 and 'ret45_delta' in data:
        ret45_params = RetarderCalibrationParams(
            tau=data['ret45_tau'],
            delta=data['ret45_delta'],
            theta=data['ret45_theta'],
            psi=data['ret45_psi'],
        )

    result = CalibrationResult(
        W=data['W'],
        A=data['A'],
        wavelengths=data['wavelengths'],
        pol_theta=data['pol_theta'],
        ret_params=ret_params,
        ret45_params=ret45_params,
        inv_W_mod=data['inv_W_mod'],
        wl_indices=data['wl_indices'],
        cal_files=cal_files,
        use_ret45=use_ret45,
    )

    # -------------------------------------------------------------------------
    # Reconstruct CalibrationDiagnostics
    # -------------------------------------------------------------------------
    B_ret45 = data['B_ret45'] if 'B_ret45' in data else None

    diagnostics = CalibrationDiagnostics(
        eigenvalue_ratio=data['eigenvalue_ratio'],
        cond_W=data['cond_W'],
        cond_A=data['cond_A'],
        B_air=data['B_air'],
        B_pol0=data['B_pol0'],
        B_pol45=data['B_pol45'],
        B_ret=data['B_ret'],
        B_ret45=B_ret45,
        I_dark=data['I_dark'],
        pol0_params={'tau': data['pol0_tau']} if 'pol0_tau' in data else {},
        pol45_params={'tau': data['pol45_tau']} if 'pol45_tau' in data else {},
    )

    # -------------------------------------------------------------------------
    # Print summary
    # -------------------------------------------------------------------------
    if verbose:
        print(f"\nLoaded calibration from: {filepath}")
        print(f"  Timestamp: {metadata.timestamp}")
        print(f"  Wavelengths: {metadata.n_wavelengths}")
        print(f"  Range: {metadata.wavelength_range[0]:.1f} - {metadata.wavelength_range[1]:.1f} nm")
        print(f"  Mode: {metadata.mode}")
        print(f"  Second retarder: {metadata.use_ret45}")
        print(f"  Mean eigenvalue ratio: {metadata.mean_eigenvalue_ratio:.2e}")

    return result, diagnostics, cfg, metadata


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_calibration_info(filepath: Path) -> CalibrationMetadata:
    """
    Get metadata from a calibration file without loading full data.

    Parameters
    ----------
    filepath : Path
        Path to calibration .npz file.

    Returns
    -------
    metadata : CalibrationMetadata
        File metadata.

    Examples
    --------
    >>> from ecm.io.calibration_io import get_calibration_info
    >>>
    >>> info = get_calibration_info('calibration.npz')
    >>> print(f"Wavelengths: {info.n_wavelengths}")
    >>> print(f"Created: {info.timestamp}")
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Calibration file not found: {filepath}")

    # Load only metadata
    with np.load(filepath, allow_pickle=True) as data:
        if 'metadata_json' not in data:
            raise ValueError("Calibration file missing metadata.")

        metadata_dict = json.loads(str(data['metadata_json'][0]))

    return CalibrationMetadata(
        timestamp=metadata_dict['timestamp'],
        file_version=metadata_dict['file_version'],
        library_version=metadata_dict['library_version'],
        mode=metadata_dict['mode'],
        n_wavelengths=metadata_dict['n_wavelengths'],
        wavelength_range=tuple(metadata_dict['wavelength_range']),
        use_ret45=metadata_dict['use_ret45'],
        mean_eigenvalue_ratio=metadata_dict['mean_eigenvalue_ratio'],
        calibration_files=metadata_dict['calibration_files'],
    )
