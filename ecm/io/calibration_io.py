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
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, Union

import numpy as np
from numpy import ndarray

logger = logging.getLogger(__name__)

from ecm.config.ecm_config import ECMConfig
from ecm.core.transmission_calibration import (
    CalibrationResult,
    CalibrationDiagnostics,
    RetarderCalibrationParams,
)
from ecm.core.file_discovery import CalibrationFiles
from ecm.core.reflection_calibration import (
    ReflectionCalibrationDiagnostics,
    ReflectionOptimizationResult,
)


# =============================================================================
# VERSION INFO
# =============================================================================

# File format version for compatibility checking
CALIBRATION_FILE_VERSION = "1.1.0"

# Library version (should match package version)
LIBRARY_VERSION = "8.0.0"


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

    n_angular_positions : int
        Number of angular positions per rotation cycle (auto-detected from data).

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
    n_angular_positions: int
    wavelength_range: Tuple[float, float]
    use_ret45: bool
    mean_eigenvalue_ratio: float
    calibration_files: Dict[str, str]


# =============================================================================
# SAVE CALIBRATION
# =============================================================================

def save_calibration(
    result: CalibrationResult,
    diagnostics: Union[CalibrationDiagnostics, ReflectionCalibrationDiagnostics],
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
        n_angular_positions=cfg.acquisition.n_angular_positions,
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

        # Use flags
        'use_ret45': np.array([result.use_ret45]),

        # Angular positions (top-level for quick access)
        'n_angular_positions': np.array([cfg.acquisition.n_angular_positions]),

        # Configuration and metadata as JSON strings
        'config_json': np.array([json.dumps(cfg.to_dict())]),
        'metadata_json': np.array([json.dumps(asdict(metadata))]),
    }

    # Mode-specific diagnostics
    if cfg.mode == 'reflection':
        # Reflection B matrices and characterization
        save_dict['B_ref1'] = diagnostics.B_ref1
        save_dict['B_pol_before'] = diagnostics.B_pol_before
        save_dict['B_pol_after'] = diagnostics.B_pol_after
        save_dict['B_ref2'] = diagnostics.B_ref2
        save_dict['M_R1'] = diagnostics.M_R1
        save_dict['M_R2'] = diagnostics.M_R2
        save_dict['wafer25nm_psi'] = diagnostics.wafer25nm_psi
        save_dict['wafer25nm_delta'] = diagnostics.wafer25nm_delta
        save_dict['wafer10nm_psi'] = diagnostics.wafer10nm_psi
        save_dict['wafer10nm_delta'] = diagnostics.wafer10nm_delta

        # Reflectance arrays
        if diagnostics.wafer25nm_Rp is not None:
            save_dict['wafer25nm_Rp'] = diagnostics.wafer25nm_Rp
        if diagnostics.wafer25nm_Rs is not None:
            save_dict['wafer25nm_Rs'] = diagnostics.wafer25nm_Rs
        if diagnostics.wafer10nm_Rp is not None:
            save_dict['wafer10nm_Rp'] = diagnostics.wafer10nm_Rp
        if diagnostics.wafer10nm_Rs is not None:
            save_dict['wafer10nm_Rs'] = diagnostics.wafer10nm_Rs

        # Nominal (Woollam) psi/delta before optimization
        if diagnostics.wafer25nm_psi_nominal is not None:
            save_dict['wafer25nm_psi_nominal'] = diagnostics.wafer25nm_psi_nominal
        if diagnostics.wafer25nm_delta_nominal is not None:
            save_dict['wafer25nm_delta_nominal'] = diagnostics.wafer25nm_delta_nominal
        if diagnostics.wafer10nm_psi_nominal is not None:
            save_dict['wafer10nm_psi_nominal'] = diagnostics.wafer10nm_psi_nominal
        if diagnostics.wafer10nm_delta_nominal is not None:
            save_dict['wafer10nm_delta_nominal'] = diagnostics.wafer10nm_delta_nominal

        # Nominal (Woollam) Rp/Rs before optimization
        if diagnostics.wafer25nm_Rp_nominal is not None:
            save_dict['wafer25nm_Rp_nominal'] = diagnostics.wafer25nm_Rp_nominal
        if diagnostics.wafer25nm_Rs_nominal is not None:
            save_dict['wafer25nm_Rs_nominal'] = diagnostics.wafer25nm_Rs_nominal
        if diagnostics.wafer10nm_Rp_nominal is not None:
            save_dict['wafer10nm_Rp_nominal'] = diagnostics.wafer10nm_Rp_nominal
        if diagnostics.wafer10nm_Rs_nominal is not None:
            save_dict['wafer10nm_Rs_nominal'] = diagnostics.wafer10nm_Rs_nominal

        # Wafer optimization result
        opt_result = diagnostics.optimization_result
        if opt_result is not None:
            save_dict['opt_psi1'] = opt_result.psi1_opt
            save_dict['opt_delta1'] = opt_result.delta1_opt
            save_dict['opt_R1'] = opt_result.R1_opt
            save_dict['opt_psi2'] = opt_result.psi2_opt
            save_dict['opt_delta2'] = opt_result.delta2_opt
            save_dict['opt_R2'] = opt_result.R2_opt
            save_dict['opt_tau_pol'] = opt_result.tau_pol_opt
            save_dict['opt_theta_pol_offset'] = opt_result.theta_pol_offset_opt
            # Derived Rp/Rs (for backward compatibility and diagnostics)
            save_dict['opt_Rp1'] = opt_result.Rp1_opt
            save_dict['opt_Rs1'] = opt_result.Rs1_opt
            save_dict['opt_Rp2'] = opt_result.Rp2_opt
            save_dict['opt_Rs2'] = opt_result.Rs2_opt
            save_dict['opt_ratio_pre'] = opt_result.eigenvalue_ratio_pre
            save_dict['opt_ratio_post'] = opt_result.eigenvalue_ratio_post
            save_dict['opt_converged'] = opt_result.converged
            save_dict['opt_n_iterations'] = opt_result.n_iterations

        # Fitted polarizer parameters
        if diagnostics.tau_pol_fitted is not None:
            save_dict['tau_pol_fitted'] = diagnostics.tau_pol_fitted
        if diagnostics.theta_pol_offset_fitted is not None:
            save_dict['theta_pol_offset_fitted'] = diagnostics.theta_pol_offset_fitted

        # Physics-informed (TMM) calibration result
        if diagnostics.thickness_result is not None:
            tr = diagnostics.thickness_result
            pr = tr.physics_result
            save_dict['phase_c_d1_fitted'] = np.array([pr.d1_fitted_nm])
            save_dict['phase_c_d2_fitted'] = np.array([pr.d2_fitted_nm])
            save_dict['phase_c_delta_aoi'] = np.array([pr.delta_aoi_fitted_deg])
            save_dict['phase_c_aoi_fitted'] = np.array([pr.aoi_fitted_deg])
            save_dict['phase_c_physics_cost'] = np.array([pr.total_cost])
            save_dict['phase_c_psi1_tmm'] = tr.psi1_tmm
            save_dict['phase_c_delta1_tmm'] = tr.delta1_tmm
            save_dict['phase_c_Rs1_tmm'] = tr.Rs1_tmm
            save_dict['phase_c_Rp1_tmm'] = tr.Rp1_tmm
            save_dict['phase_c_psi2_tmm'] = tr.psi2_tmm
            save_dict['phase_c_delta2_tmm'] = tr.delta2_tmm
            save_dict['phase_c_Rs2_tmm'] = tr.Rs2_tmm
            save_dict['phase_c_Rp2_tmm'] = tr.Rp2_tmm
            save_dict['phase_c_ratio_stage0'] = tr.eigenvalue_ratio_stage0
            save_dict['phase_c_ratio_stage2'] = tr.eigenvalue_ratio_stage2
            # Save initial optimization result under separate prefix
            s0 = tr.optimization_result_stage0
            save_dict['phase_c_s0_psi1'] = s0.psi1_opt
            save_dict['phase_c_s0_delta1'] = s0.delta1_opt
            save_dict['phase_c_s0_R1'] = s0.R1_opt
            save_dict['phase_c_s0_psi2'] = s0.psi2_opt
            save_dict['phase_c_s0_delta2'] = s0.delta2_opt
            save_dict['phase_c_s0_R2'] = s0.R2_opt
            save_dict['phase_c_s0_tau_pol'] = s0.tau_pol_opt
            save_dict['phase_c_s0_theta_pol_offset'] = s0.theta_pol_offset_opt
            save_dict['phase_c_s0_ratio_pre'] = s0.eigenvalue_ratio_pre
            save_dict['phase_c_s0_ratio_post'] = s0.eigenvalue_ratio_post
    else:
        # Transmission B matrices and polarizer parameters
        save_dict['B_air'] = diagnostics.B_air
        save_dict['B_pol0'] = diagnostics.B_pol0
        save_dict['B_pol45'] = diagnostics.B_pol45
        save_dict['B_ret'] = diagnostics.B_ret
        save_dict['pol0_tau'] = diagnostics.pol0_params.get('tau', np.array([]))
        save_dict['pol45_tau'] = diagnostics.pol45_params.get('tau', np.array([]))

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
) -> Tuple[CalibrationResult, Union[CalibrationDiagnostics, ReflectionCalibrationDiagnostics], ECMConfig, CalibrationMetadata]:
    """
    Load saved calibration from .npz file.

    Reconstructs CalibrationResult and diagnostics (type depends on mode)
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

    # Backward compat: old files may not have n_angular_positions in metadata
    if 'n_angular_positions' in metadata_dict:
        n_angular_positions = metadata_dict['n_angular_positions']
    elif 'n_angular_positions' in data:
        n_angular_positions = int(data['n_angular_positions'][0])
    elif 'inv_W_mod' in data:
        n_angular_positions = data['inv_W_mod'].shape[1]
    else:
        n_angular_positions = 96  # legacy fallback
        logger.warning(
            "Calibration file lacks n_angular_positions metadata. "
            "Using legacy fallback of 96. Consider re-running calibration "
            "with the current version to store this metadata."
        )

    metadata = CalibrationMetadata(
        timestamp=metadata_dict['timestamp'],
        file_version=metadata_dict['file_version'],
        library_version=metadata_dict['library_version'],
        mode=metadata_dict['mode'],
        n_wavelengths=metadata_dict['n_wavelengths'],
        n_angular_positions=n_angular_positions,
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
    # Reconstruct diagnostics (type depends on mode)
    # -------------------------------------------------------------------------
    if metadata.mode == 'reflection':
        # Reconstruct optional optimization result
        opt_result = None
        if 'opt_psi1' in data:
            opt_result = ReflectionOptimizationResult(
                psi1_opt=data['opt_psi1'],
                delta1_opt=data['opt_delta1'],
                R1_opt=data['opt_R1'] if 'opt_R1' in data else (data['opt_Rs1'] + data['opt_Rp1']) / 2.0,
                psi2_opt=data['opt_psi2'],
                delta2_opt=data['opt_delta2'],
                R2_opt=data['opt_R2'] if 'opt_R2' in data else (data['opt_Rs2'] + data['opt_Rp2']) / 2.0,
                tau_pol_opt=data['opt_tau_pol'] if 'opt_tau_pol' in data else np.ones_like(data['opt_psi1']),
                theta_pol_offset_opt=data['opt_theta_pol_offset'] if 'opt_theta_pol_offset' in data else np.zeros_like(data['opt_psi1']),
                Rs1_opt=data['opt_Rs1'] if 'opt_Rs1' in data else None,
                Rp1_opt=data['opt_Rp1'] if 'opt_Rp1' in data else None,
                Rs2_opt=data['opt_Rs2'] if 'opt_Rs2' in data else None,
                Rp2_opt=data['opt_Rp2'] if 'opt_Rp2' in data else None,
                eigenvalue_ratio_pre=data['opt_ratio_pre'],
                eigenvalue_ratio_post=data['opt_ratio_post'],
                converged=data['opt_converged'],
                n_iterations=data['opt_n_iterations'],
            )

        diagnostics = ReflectionCalibrationDiagnostics(
            eigenvalue_ratio=data['eigenvalue_ratio'],
            cond_W=data['cond_W'],
            cond_A=data['cond_A'],
            B_ref1=data['B_ref1'],
            B_pol_before=data['B_pol_before'],
            B_pol_after=data['B_pol_after'],
            B_ref2=data['B_ref2'],
            I_dark=data['I_dark'],
            M_R1=data['M_R1'],
            M_R2=data['M_R2'],
            wafer25nm_psi=data['wafer25nm_psi'] if 'wafer25nm_psi' in data else data.get('reflector1_psi'),
            wafer25nm_delta=data['wafer25nm_delta'] if 'wafer25nm_delta' in data else data.get('reflector1_delta'),
            wafer10nm_psi=data['wafer10nm_psi'] if 'wafer10nm_psi' in data else data.get('reflector2_psi'),
            wafer10nm_delta=data['wafer10nm_delta'] if 'wafer10nm_delta' in data else data.get('reflector2_delta'),
            wafer25nm_Rp=data['wafer25nm_Rp'] if 'wafer25nm_Rp' in data else data.get('reflector1_Rp'),
            wafer25nm_Rs=data['wafer25nm_Rs'] if 'wafer25nm_Rs' in data else data.get('reflector1_Rs'),
            wafer10nm_Rp=data['wafer10nm_Rp'] if 'wafer10nm_Rp' in data else data.get('reflector2_Rp'),
            wafer10nm_Rs=data['wafer10nm_Rs'] if 'wafer10nm_Rs' in data else data.get('reflector2_Rs'),
            wafer25nm_psi_nominal=data['wafer25nm_psi_nominal'] if 'wafer25nm_psi_nominal' in data else data.get('reflector1_psi_nominal'),
            wafer25nm_delta_nominal=data['wafer25nm_delta_nominal'] if 'wafer25nm_delta_nominal' in data else data.get('reflector1_delta_nominal'),
            wafer10nm_psi_nominal=data['wafer10nm_psi_nominal'] if 'wafer10nm_psi_nominal' in data else data.get('reflector2_psi_nominal'),
            wafer10nm_delta_nominal=data['wafer10nm_delta_nominal'] if 'wafer10nm_delta_nominal' in data else data.get('reflector2_delta_nominal'),
            wafer25nm_Rp_nominal=data['wafer25nm_Rp_nominal'] if 'wafer25nm_Rp_nominal' in data else data.get('reflector1_Rp_nominal'),
            wafer25nm_Rs_nominal=data['wafer25nm_Rs_nominal'] if 'wafer25nm_Rs_nominal' in data else data.get('reflector1_Rs_nominal'),
            wafer10nm_Rp_nominal=data['wafer10nm_Rp_nominal'] if 'wafer10nm_Rp_nominal' in data else data.get('reflector2_Rp_nominal'),
            wafer10nm_Rs_nominal=data['wafer10nm_Rs_nominal'] if 'wafer10nm_Rs_nominal' in data else data.get('reflector2_Rs_nominal'),
            optimization_result=opt_result,
            tau_pol_fitted=data['tau_pol_fitted'] if 'tau_pol_fitted' in data else None,
            theta_pol_offset_fitted=data['theta_pol_offset_fitted'] if 'theta_pol_offset_fitted' in data else None,
        )

        # Reconstruct physics-informed (TMM) result if present
        if 'phase_c_d1_fitted' in data:
            from ecm.core.reflection_calibration import (
                PhysicsExtractionResult,
                ThicknessOptimizationResult,
            )

            physics_result = PhysicsExtractionResult(
                d1_fitted_nm=float(data['phase_c_d1_fitted'][0]),
                d2_fitted_nm=float(data['phase_c_d2_fitted'][0]),
                delta_aoi_fitted_deg=float(data['phase_c_delta_aoi'][0]),
                aoi_fitted_deg=float(data['phase_c_aoi_fitted'][0]),
                residual_psi1_std_deg=0.0,  # Not stored (derivable)
                residual_delta1_std_deg=0.0,
                residual_psi2_std_deg=0.0,
                residual_delta2_std_deg=0.0,
                total_cost=float(data['phase_c_physics_cost'][0]),
            )

            # Reconstruct initial optimization result
            stage0_opt = None
            if 'phase_c_s0_psi1' in data:
                stage0_opt = ReflectionOptimizationResult(
                    psi1_opt=data['phase_c_s0_psi1'],
                    delta1_opt=data['phase_c_s0_delta1'],
                    R1_opt=data['phase_c_s0_R1'],
                    psi2_opt=data['phase_c_s0_psi2'],
                    delta2_opt=data['phase_c_s0_delta2'],
                    R2_opt=data['phase_c_s0_R2'],
                    tau_pol_opt=data['phase_c_s0_tau_pol'],
                    theta_pol_offset_opt=data['phase_c_s0_theta_pol_offset'],
                    Rs1_opt=None,
                    Rp1_opt=None,
                    Rs2_opt=None,
                    Rp2_opt=None,
                    eigenvalue_ratio_pre=data['phase_c_s0_ratio_pre'],
                    eigenvalue_ratio_post=data['phase_c_s0_ratio_post'],
                    converged=np.ones_like(data['phase_c_s0_psi1'], dtype=bool),
                    n_iterations=np.zeros_like(data['phase_c_s0_psi1'], dtype=int),
                )

            diagnostics.thickness_result = ThicknessOptimizationResult(
                physics_result=physics_result,
                psi1_tmm=data['phase_c_psi1_tmm'],
                delta1_tmm=data['phase_c_delta1_tmm'],
                Rs1_tmm=data['phase_c_Rs1_tmm'],
                Rp1_tmm=data['phase_c_Rp1_tmm'],
                psi2_tmm=data['phase_c_psi2_tmm'],
                delta2_tmm=data['phase_c_delta2_tmm'],
                Rs2_tmm=data['phase_c_Rs2_tmm'],
                Rp2_tmm=data['phase_c_Rp2_tmm'],
                eigenvalue_ratio_stage0=data['phase_c_ratio_stage0'],
                eigenvalue_ratio_stage2=data['phase_c_ratio_stage2'],
                optimization_result_stage0=stage0_opt,
            )
    else:
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

        # Backward compat: old files may not have n_angular_positions
        if 'n_angular_positions' in metadata_dict:
            n_angular_positions = metadata_dict['n_angular_positions']
        elif 'n_angular_positions' in data:
            n_angular_positions = int(data['n_angular_positions'][0])
        elif 'inv_W_mod' in data:
            n_angular_positions = data['inv_W_mod'].shape[1]
        else:
            n_angular_positions = 96  # legacy fallback
            logger.warning(
                "Calibration file lacks n_angular_positions metadata. "
                "Using legacy fallback of 96. Consider re-running calibration "
                "with the current version to store this metadata."
            )

    return CalibrationMetadata(
        timestamp=metadata_dict['timestamp'],
        file_version=metadata_dict['file_version'],
        library_version=metadata_dict['library_version'],
        mode=metadata_dict['mode'],
        n_wavelengths=metadata_dict['n_wavelengths'],
        n_angular_positions=n_angular_positions,
        wavelength_range=tuple(metadata_dict['wavelength_range']),
        use_ret45=metadata_dict['use_ret45'],
        mean_eigenvalue_ratio=metadata_dict['mean_eigenvalue_ratio'],
        calibration_files=metadata_dict['calibration_files'],
    )
