"""
ECM Configuration Module

This module provides dataclass-based configuration for the ECM calibration pipeline.
All parameters are centralized here as the single source of truth.

The configuration structure mirrors the MATLAB ecm_config.m file, preserving
all parameter names and default values for compatibility.

References
----------
[1] Compain et al., "General and self-consistent method for the calibration
    of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
    Appl. Opt. 38, 3490-3502 (1999)
[2] Rosales et al., "Extended eigenvalue calibration method for overdetermined
    Mueller matrix polarimeters", Opt. Lett. 49, 1165-1168 (2024)

Example
-------
>>> from ecm.config import ECMConfig
>>>
>>> # Create default configuration
>>> cfg = ECMConfig()
>>>
>>> # Access nested settings
>>> print(cfg.acquisition.n_angular_positions)  # None (auto-detected)
>>> print(cfg.wavelength.range_nm)              # (400.0, 1000.0)
>>>
>>> # Modify and save
>>> cfg.wavelength.range_nm = (450.0, 900.0)
>>> cfg.to_yaml(Path("my_config.yaml"))
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Tuple, Literal, Optional, Any, List
import json
import warnings


# =============================================================================
# NESTED CONFIGURATION DATACLASSES
# =============================================================================

@dataclass
class InstrumentConfig:
    """
    PSG/PSA instrument geometry settings.

    The polarimeter uses a dual rotating compensator configuration:
    - PSG (Polarization State Generator): Polarizer -> Rotating Compensator
    - PSA (Polarization State Analyzer): Rotating Compensator -> Analyzer

    Light path: Source -> PSG -> Sample -> PSA -> Detector

    Coordinate system (looking into the beam toward detector):
        - z-axis: toward detector (beam propagation direction)
        - x-axis: horizontal, positive to the right
        - y-axis: vertical, positive upward
        - Positive rotation: counterclockwise (right-hand rule around z)

    Attributes
    ----------
    psg_freq_ratio : int
        PSG compensator rotation frequency ratio (relative to base frequency).
        Default: 1
    psa_freq_ratio : int
        PSA compensator rotation frequency ratio.
        For 1:5 ratio system: PSA rotates 5x faster than PSG.
        Default: 5
    psg_start_angle_deg : float
        Starting angular position of PSG compensator [degrees].
        Default: 0.0
    psa_start_angle_deg : float
        Starting angular position of PSA compensator [degrees].
        Default: 0.0
    psg_polarizer_angle_deg : float
        Fixed polarizer orientation in PSG (after source) [degrees].
        Convention: 0 degrees = horizontal (x-axis).
        Default: 0.0
    psa_analyzer_angle_deg : float
        Fixed analyzer orientation in PSA (before detector) [degrees].
        Default: 0.0
    """
    psg_freq_ratio: int = 1
    psa_freq_ratio: int = 5
    psg_start_angle_deg: float = 0.0
    psa_start_angle_deg: float = 0.0
    psg_polarizer_angle_deg: float = 0.0
    psa_analyzer_angle_deg: float = 0.0


@dataclass
class AcquisitionConfig:
    """
    Data acquisition parameters.

    Attributes
    ----------
    n_angular_positions : int or None
        Number of angular positions per full rotation cycle.
        Auto-detected from data file dimensions during calibration.
        Default: None (auto-detect).
    n_rotation_cycles : int
        Number of rotation cycles in each measurement file.
        Default: 1
    angular_range_deg : float
        Total angular range covered [degrees].
        Default: 360.0
    """
    n_angular_positions: Optional[int] = None
    n_rotation_cycles: int = 1
    angular_range_deg: float = 360.0

    @property
    def angular_step_deg(self) -> float:
        """
        Angular step between measurements [degrees].

        Derived from angular_range_deg / n_angular_positions.
        """
        if self.n_angular_positions is None:
            raise RuntimeError(
                "n_angular_positions has not been set. "
                "Run calibration or load calibration data first."
            )
        return self.angular_range_deg / self.n_angular_positions


@dataclass
class SpectrometerConfig:
    """
    Spectrometer hardware settings.

    Attributes
    ----------
    model : str
        Spectrometer model identifier.
        Default: 'StellarNet_BlackComet'
    n_wavelengths : int
        Total number of wavelength channels (pixels).
        Default: 2048
    wavelength_file : Optional[Path]
        Path to wavelength calibration file.
        File format: single column of wavelengths in nm.
        Default: None (set by ECMConfig based on paths)
    saturation_level : int
        Detector saturation level (for quality checks).
        Default: 65536 (16-bit detector)
    """
    model: str = 'StellarNet_BlackComet'
    n_wavelengths: int = 2048
    wavelength_file: Optional[Path] = None
    saturation_level: int = 65536  # 2^16 for 16-bit detector


@dataclass
class WavelengthConfig:
    """
    Wavelength range and reference settings.

    Attributes
    ----------
    range_nm : Tuple[float, float]
        Wavelength range to use for analysis [nm].
        Data outside this range will be excluded.
        Default: (400.0, 1000.0)
    reference_nm : float
        Reference wavelength for diagnostics [nm].
        Default: 633.0 (HeNe laser wavelength)
    """
    range_nm: Tuple[float, float] = (400.0, 1000.0)
    reference_nm: float = 633.0


@dataclass
class FileFormatConfig:
    """
    Binary file format specifications.

    Attributes
    ----------
    data_type : str
        Binary file data type.
        Default: 'float32' (32-bit float)
    byte_order : str
        Byte order for binary files.
        Default: 'little' (little-endian)
    data_layout : str
        Data organization in binary files.
        'wavelength_first': data stored as [n_wavelengths x n_angles]
        Default: 'wavelength_first'
    """
    data_type: str = 'float32'
    byte_order: str = 'little'
    data_layout: str = 'wavelength_first'


@dataclass
class RetarderCharConfig:
    """
    Retarder characterization file names.

    Attributes
    ----------
    fp1 : str
        Filename for primary retarder (90 deg orientation) characterization.
        Format: wavelength [nm], retardation [degrees]
        Default: 'FP1_retardance_deg.txt'
    fp2 : str
        Filename for secondary retarder (45 deg orientation) characterization.
        Default: 'FP2_retardance_deg.txt'
    """
    fp1: str = 'FP1_retardance_deg.txt'
    fp2: str = 'FP2_retardance_deg.txt'


@dataclass
class ReflectionOptConfig:
    """
    Reflection-mode reflector characterization optimization settings.

    Controls the bounded per-wavelength optimization that minimizes the
    eigenvalue ratio λ₁₆/λ₁₅ by adjusting 8 parameters: δψ₁, δΔ₁, δR₁,
    δψ₂, δΔ₂, δR₂, τ_pol, δθ_pol.

    Attributes
    ----------
    optimize : bool
        Whether to run the reflector optimization. When False, the
        calibration uses the raw Woollam characterization without correction.
        Default: True
    psi1_bound_deg : float
        Max offset for reflector 1 psi [degrees]. Default: 4.0
    delta1_bound_deg : float
        Max offset for reflector 1 delta [degrees]. Default: 12.0
    R1_bound_frac : float
        Max fractional offset for reflector 1 unpolarized reflectance
        R₁ = (Rs₁+Rp₁)/2 (±fraction of nominal). Default: 0.02 (±2%)
    psi2_bound_deg : float
        Max offset for reflector 2 psi [degrees]. Default: 2.0
    delta2_bound_deg : float
        Max offset for reflector 2 delta [degrees]. Default: 6.0
    R2_bound_frac : float
        Max fractional offset for reflector 2 unpolarized reflectance
        R₂ = (Rs₂+Rp₂)/2 (±fraction of nominal). Default: 0.02 (±2%)
    tau_pol_min : float
        Lower bound for polarizer transmittance. Default: 0.3
    tau_pol_max : float
        Upper bound for polarizer transmittance. Default: 0.97
    tau_pol_start : float
        Starting value for polarizer transmittance. Default: 0.45
    theta_pol_bound_deg : float
        Max polarizer azimuth offset [degrees]. Default: 4.0
    multistart_threshold : float
        Eigenvalue ratio threshold for multi-start re-optimization.
        Wavelengths with ratio > threshold are re-optimized with multiple
        random starts. Default: 0.01.
    multistart_n_starts : int
        Number of additional random starts for multi-start. Default: 3.
    enable_regularization : bool
        Enable Tikhonov spectral smoothness regularization (optional,
        post-processing step). Default: False.
    regularization_weight : float
        Weight for spectral smoothness penalty. Default: 0.1.
    """
    optimize: bool = True
    psi1_bound_deg: float = 4.0
    delta1_bound_deg: float = 12.0
    R1_bound_frac: float = 0.02
    psi2_bound_deg: float = 2.0
    delta2_bound_deg: float = 6.0
    R2_bound_frac: float = 0.02
    tau_pol_min: float = 0.3
    tau_pol_max: float = 0.97
    tau_pol_start: float = 0.45
    theta_pol_bound_deg: float = 4.0
    multistart_threshold: float = 0.01
    multistart_n_starts: int = 3
    enable_regularization: bool = False
    regularization_weight: float = 0.1


@dataclass
class ThicknessFitConfig:
    """
    Physics-informed reflection calibration settings (TMM thickness fitting).

    Extracts real wafer thicknesses and angle of incidence from the initial
    optimization results using TMM fitting (differential_evolution), then
    re-runs the per-wavelength optimization with the improved TMM baseline
    and tighter bounds.

    Three-step process:
      1. Initial per-wavelength optimization (Woollam nominal baseline)
      2. Physics extraction (d1, d2, delta_AOI) from effective curves
      3. Refined per-wavelength optimization (TMM baseline + tighter bounds)

    Attributes
    ----------
    enable_thickness_fit : bool
        Enable physics-informed TMM calibration. Default: True.
    d1_start_nm : float
        Reflector 1 SiO2 starting thickness [nm]. Default: 25.0.
    d2_start_nm : float
        Reflector 2 SiO2 starting thickness [nm]. Default: 10.0.
    d1_bounds_nm : Tuple[float, float]
        Reflector 1 thickness bounds [nm]. Default: (15.0, 35.0).
    d2_bounds_nm : Tuple[float, float]
        Reflector 2 thickness bounds [nm]. Default: (5.0, 15.0).
    d_interlayer_nm : float
        Fixed interlayer thickness [nm]. Default: 1.0. Do NOT fit.
    delta_aoi_bound_deg : float
        AOI correction bound for TMM fitting [degrees]. Default: 3.0.
    stage2_psi1_bound_deg : float
        Tighter psi1 bound for refined optimization pass [degrees]. Default: 3.0.
    stage2_delta1_bound_deg : float
        Tighter Delta1 bound for refined optimization pass [degrees]. Default: 5.0.
    stage2_psi2_bound_deg : float
        Tighter psi2 bound for refined optimization pass [degrees]. Default: 2.0.
    stage2_delta2_bound_deg : float
        Tighter Delta2 bound for refined optimization pass [degrees]. Default: 5.0.
    """
    enable_thickness_fit: bool = True
    d1_start_nm: float = 25.0
    d2_start_nm: float = 10.0
    d1_bounds_nm: Tuple[float, float] = (15.0, 35.0)
    d2_bounds_nm: Tuple[float, float] = (5.0, 15.0)
    d_interlayer_nm: float = 1.0
    delta_aoi_bound_deg: float = 3.0
    stage2_psi1_bound_deg: float = 3.0
    stage2_delta1_bound_deg: float = 5.0
    stage2_psi2_bound_deg: float = 2.0
    stage2_delta2_bound_deg: float = 5.0


@dataclass
class ReflectionCalConfig:
    """
    Reflection-mode calibration settings.

    Attributes
    ----------
    angle_of_incidence_deg : float
        Angle of incidence for reflection measurements [degrees].
        Determines which column to extract from characterization files.
        Default: 65.0
    polarizer_azimuth_deg : float
        Fixed polarizer azimuth used in POL_BEFORE/POL_AFTER measurements [degrees].
        Default: 45.0
    wafer25nm_label : str
        Filename prefix for wafer 25 nm characterization asset lookup.
        Default: '25nm'
    wafer10nm_label : str
        Filename prefix for wafer 10 nm characterization asset lookup.
        Default: '10nm'
    aoi_range_deg : Tuple[float, float]
        Range of AOI values in characterization files [degrees].
        Default: (55.0, 75.0)
    aoi_step_deg : float
        AOI step size in characterization files [degrees].
        Default: 1.0
    optimization : ReflectionOptConfig
        Wafer characterization optimization settings.
        Default: ReflectionOptConfig()
    thickness_fit : ThicknessFitConfig
        Physics-informed TMM calibration settings.
        Default: ThicknessFitConfig()
    """
    angle_of_incidence_deg: float = 65.0
    polarizer_azimuth_deg: float = 45.0
    wafer25nm_label: str = '25nm'
    wafer10nm_label: str = '10nm'
    aoi_range_deg: Tuple[float, float] = (55.0, 75.0)
    aoi_step_deg: float = 1.0
    optimization: ReflectionOptConfig = field(default_factory=ReflectionOptConfig)
    thickness_fit: ThicknessFitConfig = field(default_factory=ThicknessFitConfig)

    @property
    def aoi_column_indices(self) -> Tuple[int, int]:
        """0-based column indices in characterization files for configured AOI.

        Returns (col_psi_or_Rp, col_delta_or_Rs). For AOI=65 with range
        55-75 in 1-degree steps: returns (21, 22).
        """
        offset = int(
            (self.angle_of_incidence_deg - self.aoi_range_deg[0])
            / self.aoi_step_deg
        )
        return 1 + offset * 2, 2 + offset * 2


@dataclass
class PathsConfig:
    """
    Directory and file path configuration.

    All paths are relative to the configuration file location or can be
    set as absolute paths.

    Attributes
    ----------
    data_dir : Optional[Path]
        Base data directory.
    assets_dir : Optional[Path]
        Assets directory (wavelength files, characterization files).
    calibration_output_dir : Optional[Path]
        Output directory for saved calibration .mat files.
    calibration_dir : Optional[Path]
        Base calibration directory.
    calibration_transmission_dir : Optional[Path]
        Transmission calibration files directory.
    calibration_reflection_dir : Optional[Path]
        Reflection calibration files directory.
    samples_dir : Optional[Path]
        Base samples directory.
    samples_transmission_dir : Optional[Path]
        Transmission sample files directory.
    samples_reflection_dir : Optional[Path]
        Reflection sample files directory.
    retarder_char : RetarderCharConfig
        Retarder characterization file names.
    """
    data_dir: Optional[Path] = None
    assets_dir: Optional[Path] = None
    calibration_output_dir: Optional[Path] = None
    calibration_dir: Optional[Path] = None
    calibration_transmission_dir: Optional[Path] = None
    calibration_reflection_dir: Optional[Path] = None
    samples_dir: Optional[Path] = None
    samples_transmission_dir: Optional[Path] = None
    samples_reflection_dir: Optional[Path] = None
    retarder_char: RetarderCharConfig = field(default_factory=RetarderCharConfig)


@dataclass
class CalibrationSampleConfig:
    """
    Properties of a single calibration sample.

    Attributes
    ----------
    type : str
        Sample type: 'polarizer' or 'retarder'.
    orientation_deg : float
        Nominal orientation [degrees].
    transmittance : float
        Transmission coefficient.
        Default: 0.5 for polarizers, 1.0 for retarders.
    """
    type: str = 'polarizer'
    orientation_deg: float = 0.0
    transmittance: float = 0.5


@dataclass
class BoundsConfig:
    """
    Bounds for bounded optimization.

    Attributes
    ----------
    tau_min : float
        Minimum transmission coefficient.
        Default: 0.0
    tau_max : float
        Maximum transmission coefficient.
        Default: 1.0
    theta_tolerance_deg : float
        Search range around nominal angle [degrees].
        Default: 30.0
    """
    tau_min: float = 0.0
    tau_max: float = 1.0
    theta_tolerance_deg: float = 30.0


@dataclass
class ECMAlgorithmConfig:
    """
    ECM algorithm parameters and optimization settings.

    Attributes
    ----------
    eigenvalue_ratio_warning : float
        Warn if eigenvalue ratio (lambda_16/lambda_15) exceeds this.
        A well-conditioned calibration has this ratio << 1.
        See Compain Eq. (20) and Appendix C.
        Default: 1e-3
    eigenvalue_ratio_error : float
        Error if eigenvalue ratio exceeds this.
        Default: 0.1
    use_retarder_45 : bool
        Use second retarder at 45 deg (if available).
        Adds additional constraints, can improve calibration quality.
        Default: True
    optimize_polarizer_angles : bool
        Optimize polarizer orientations (P0 and P45).
        Default: True
    optimize_retarder_angle : bool
        Optimize retarder fast-axis angle.
        Default: True
    optimize_retarder_psi : bool
        Optimize retarder ellipsometric Psi.
        Not recommended, can be unstable.
        Default: False
    optimization_tolerance : float
        Optimization convergence tolerance.
        Default: 1e-14
    optimization_max_iterations : int
        Maximum optimization iterations.
        Default: 50000
    optimization_method : str
        Optimization method: 'unbounded' (faster) or 'bounded' (physical).
        Default: 'unbounded'
    use_warm_start : bool
        Use previous wavelength result as initial guess.
        Set to False to prevent drift.
        Default: False
    wrap_angles : bool
        Wrap angles to [-pi, pi] after optimization.
        Default: True
    method : str
        ECM method: 'standard' (Compain) or 'extended' (Rosales).
        Default: 'extended'
    bounds : BoundsConfig
        Bounds for bounded optimization.
    """
    eigenvalue_ratio_warning: float = 1e-3
    eigenvalue_ratio_error: float = 0.1
    use_retarder_45: bool = True
    optimize_polarizer_angles: bool = True
    optimize_retarder_angle: bool = True
    optimize_retarder_psi: bool = False
    optimization_tolerance: float = 1e-14
    optimization_max_iterations: int = 50000
    optimization_method: str = 'unbounded'
    use_warm_start: bool = False
    wrap_angles: bool = True
    method: str = 'extended'
    bounds: BoundsConfig = field(default_factory=BoundsConfig)


@dataclass
class FourierConfig:
    """
    Fourier analysis parameters.

    For rotating compensator systems, intensity is analyzed via Fourier decomposition:
        I(theta) = a0 + sum(a_n * cos(n*theta) + b_n * sin(n*theta))

    For 1:5 frequency ratio, relevant harmonics are even: 2, 4, 6, 8, 10, 12.

    Attributes
    ----------
    max_harmonic : int
        Maximum harmonic order to extract.
        Default: 24
    mueller_harmonics : Tuple[int, ...]
        Harmonics containing Mueller matrix information for 1:5 system.
        Default: (2, 4, 6, 8, 10, 12)
    """
    max_harmonic: int = 24
    mueller_harmonics: Tuple[int, ...] = (2, 4, 6, 8, 10, 12)


@dataclass
class MuellerConfig:
    """
    Mueller matrix conventions.

    Attributes
    ----------
    normalization : str
        Normalization convention for output Mueller matrices.
        'none': Raw (M_11 = total transmitted/reflected intensity)
        'm11': Normalized so m_11 = 1 (standard for sample characterization)
        Default: 'm11'
    check_physical : bool
        Enable checks for valid Mueller matrix properties.
        Default: True
    physical_tolerance : float
        Tolerance for physical realizability (accounts for noise).
        Default: 0.1
    """
    normalization: str = 'm11'
    check_physical: bool = True
    physical_tolerance: float = 0.1


@dataclass
class ProcessingConfig:
    """
    Data processing options.

    Attributes
    ----------
    subtract_dark : bool
        Perform dark subtraction.
        Default: True
    wavelength_smoothing_points : int
        Spectral smoothing window (1 = no smoothing).
        Default: 1
    angular_smoothing_points : int
        Angular smoothing window (1 = no smoothing).
        Default: 1
    """
    subtract_dark: bool = True
    wavelength_smoothing_points: int = 1
    angular_smoothing_points: int = 1


@dataclass
class OutputConfig:
    """
    Output and diagnostic settings.

    Attributes
    ----------
    verbosity : int
        Verbosity level: 0 = silent, 1 = basic, 2 = detailed.
        Default: 1
    save_intermediates : bool
        Save intermediate results.
        Default: True
    results_dir : Optional[Path]
        Output directory for results.
    generate_plots : bool
        Generate diagnostic plots during calibration.
        Default: True
    save_figures_processing : bool
        Save figures during process_samples.
        Default: True
    save_figures_postprocessing : bool
        Save figures during postprocess_samples.
        Default: True
    """
    verbosity: int = 1
    save_intermediates: bool = True
    results_dir: Optional[Path] = None
    generate_plots: bool = True
    save_figures_processing: bool = True
    save_figures_postprocessing: bool = True


@dataclass
class FigureConfig:
    """
    Plotting and visualization settings.

    Attributes
    ----------
    fontsize : int
        Font size for labels, titles, axes.
        Default: 16
    linewidth : float
        Line width for plots.
        Default: 1.5
    background_color : str
        Figure background color.
        Default: 'white'
    default_size : Tuple[int, int]
        Default figure size [width, height] in pixels.
        Default: (800, 600)
    """
    fontsize: int = 16
    linewidth: float = 1.5
    background_color: str = 'white'
    default_size: Tuple[int, int] = (800, 600)


# =============================================================================
# MAIN CONFIGURATION DATACLASS
# =============================================================================

@dataclass
class ECMConfig:
    """
    Main configuration container for ECM calibration.

    This dataclass contains all parameters needed for the Eigenvalue Calibration
    Method (ECM) pipeline. It serves as the single source of truth for all
    instrument settings, file paths, physical constants, and processing options.

    The structure mirrors the MATLAB ecm_config.m for compatibility.

    Attributes
    ----------
    mode : str
        Measurement configuration: 'transmission' or 'reflection'.
        Default: 'transmission'
    instrument : InstrumentConfig
        PSG/PSA instrument geometry settings.
    acquisition : AcquisitionConfig
        Data acquisition parameters.
    spectrometer : SpectrometerConfig
        Spectrometer hardware settings.
    wavelength : WavelengthConfig
        Wavelength range and reference settings.
    file_format : FileFormatConfig
        Binary file format specifications.
    paths : PathsConfig
        Directory and file path configuration.
    calibration_samples : Dict[str, CalibrationSampleConfig]
        Properties of calibration samples (pol_0, pol_45, ret_90, ret_45).
    ecm : ECMAlgorithmConfig
        ECM algorithm parameters and optimization settings.
    fourier : FourierConfig
        Fourier analysis parameters.
    mueller : MuellerConfig
        Mueller matrix conventions.
    processing : ProcessingConfig
        Data processing options.
    output : OutputConfig
        Output and diagnostic settings.
    figure : FigureConfig
        Plotting and visualization settings.

    Examples
    --------
    >>> cfg = ECMConfig()
    >>> print(cfg.acquisition.n_angular_positions)
    96
    >>> cfg.wavelength.range_nm = (450.0, 900.0)
    >>> cfg.to_json(Path("my_config.json"))
    """
    mode: Literal['transmission', 'reflection'] = 'transmission'
    instrument: InstrumentConfig = field(default_factory=InstrumentConfig)
    acquisition: AcquisitionConfig = field(default_factory=AcquisitionConfig)
    spectrometer: SpectrometerConfig = field(default_factory=SpectrometerConfig)
    wavelength: WavelengthConfig = field(default_factory=WavelengthConfig)
    file_format: FileFormatConfig = field(default_factory=FileFormatConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    calibration_samples: Dict[str, CalibrationSampleConfig] = field(default_factory=dict)
    ecm: ECMAlgorithmConfig = field(default_factory=ECMAlgorithmConfig)
    fourier: FourierConfig = field(default_factory=FourierConfig)
    mueller: MuellerConfig = field(default_factory=MuellerConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    figure: FigureConfig = field(default_factory=FigureConfig)
    reflection_cal: ReflectionCalConfig = field(default_factory=ReflectionCalConfig)

    def __post_init__(self) -> None:
        """
        Post-initialization: set up paths and validate configuration.
        """
        self._setup_paths()
        self._setup_calibration_samples()
        self._validate()

    def _setup_paths(self) -> None:
        """
        Set up default paths relative to the package location.

        Paths are configured relative to the data directory, which should
        be located at the project root level.
        """
        # Determine the project root (parent of ecm package)
        # This assumes the config file is at ecm/config/ecm_config.py
        config_file = Path(__file__)
        ecm_package = config_file.parent.parent  # ecm/
        project_root = ecm_package.parent  # ecm_calibration 6.5.5 PYTHON/

        # Set up data directory paths if not already set
        if self.paths.data_dir is None:
            self.paths.data_dir = project_root / 'data'

        # Set up derived paths
        data_dir = self.paths.data_dir

        if self.paths.assets_dir is None:
            self.paths.assets_dir = data_dir / 'assets'

        if self.paths.calibration_output_dir is None:
            # Default to current working directory for user convenience
            self.paths.calibration_output_dir = Path.cwd() / 'calibration_output'

        if self.paths.calibration_dir is None:
            self.paths.calibration_dir = data_dir / 'calibration'

        if self.paths.calibration_transmission_dir is None:
            self.paths.calibration_transmission_dir = self.paths.calibration_dir / 'transmission'

        if self.paths.calibration_reflection_dir is None:
            self.paths.calibration_reflection_dir = self.paths.calibration_dir / 'reflection'

        if self.paths.samples_dir is None:
            self.paths.samples_dir = data_dir / 'samples'

        if self.paths.samples_transmission_dir is None:
            self.paths.samples_transmission_dir = self.paths.samples_dir / 'transmission'

        if self.paths.samples_reflection_dir is None:
            self.paths.samples_reflection_dir = self.paths.samples_dir / 'reflection'

        # Set wavelength file path
        if self.spectrometer.wavelength_file is None:
            self.spectrometer.wavelength_file = (
                self.paths.assets_dir / 'BlackCommet_wavelengths.txt'
            )

        # Set results directory
        if self.output.results_dir is None:
            self.output.results_dir = project_root / 'results'

    def _setup_calibration_samples(self) -> None:
        """
        Set up default calibration sample configurations.

        Creates configurations for:
        - pol_0: Polarizer at nominal 0 degree orientation
        - pol_45: Polarizer at nominal 45 degree orientation
        - ret_90: Retarder at nominal 90 degree orientation (FP1)
        - ret_45: Retarder at nominal 45 degree orientation (FP2)
        """
        if not self.calibration_samples:
            self.calibration_samples = {
                'pol_0': CalibrationSampleConfig(
                    type='polarizer',
                    orientation_deg=0.0,
                    transmittance=0.5
                ),
                'pol_45': CalibrationSampleConfig(
                    type='polarizer',
                    orientation_deg=45.0,
                    transmittance=0.5
                ),
                'ret_90': CalibrationSampleConfig(
                    type='retarder',
                    orientation_deg=90.0,
                    transmittance=1.0
                ),
                'ret_45': CalibrationSampleConfig(
                    type='retarder',
                    orientation_deg=45.0,
                    transmittance=1.0
                ),
            }

    def _validate(self) -> None:
        """
        Validate configuration for internal consistency.

        Issues warnings or raises errors for problematic settings.
        """
        # Check frequency ratios are positive integers
        if self.instrument.psg_freq_ratio < 1:
            warnings.warn(
                "PSG frequency ratio should be positive integer, "
                f"got {self.instrument.psg_freq_ratio}",
                UserWarning
            )

        if self.instrument.psa_freq_ratio < 1:
            warnings.warn(
                "PSA frequency ratio should be positive integer, "
                f"got {self.instrument.psa_freq_ratio}",
                UserWarning
            )

        # Check angular positions sufficient for Fourier analysis
        # Need at least 2x the maximum harmonic (Nyquist)
        # Skip if n_angular_positions is None (will be auto-detected later)
        if self.acquisition.n_angular_positions is not None:
            min_positions = 2 * self.fourier.max_harmonic
            if self.acquisition.n_angular_positions < min_positions:
                warnings.warn(
                    f"Angular positions ({self.acquisition.n_angular_positions}) may be "
                    f"insufficient for harmonic {self.fourier.max_harmonic}. "
                    f"Need >= {min_positions}.",
                    UserWarning
                )

        # Check wavelength range is valid
        wl_min, wl_max = self.wavelength.range_nm
        if wl_min >= wl_max:
            raise ValueError(
                f"Invalid wavelength range: min ({wl_min}) >= max ({wl_max}). "
                f"Wavelength range must be (min, max) with min < max."
            )

        # Check mode is valid
        valid_modes = ('transmission', 'reflection')
        if self.mode not in valid_modes:
            raise ValueError(
                f"Invalid mode '{self.mode}'. Must be one of: {valid_modes}"
            )

        # Check ECM method is valid
        valid_methods = ('standard', 'extended')
        if self.ecm.method not in valid_methods:
            raise ValueError(
                f"Invalid ECM method '{self.ecm.method}'. "
                f"Must be one of: {valid_methods}"
            )

        # Check reflection AOI is within characterization range
        aoi = self.reflection_cal.angle_of_incidence_deg
        aoi_min, aoi_max = self.reflection_cal.aoi_range_deg
        if not (aoi_min <= aoi <= aoi_max):
            raise ValueError(
                f"Reflection AOI ({aoi}°) is outside characterization range "
                f"({aoi_min}°–{aoi_max}°)."
            )

        # Verify calibration samples exist
        required_samples = ('pol_0', 'pol_45', 'ret_90', 'ret_45')
        for sample in required_samples:
            if sample not in self.calibration_samples:
                warnings.warn(
                    f"Missing calibration_samples['{sample}']. "
                    f"This may cause issues during calibration.",
                    UserWarning
                )

    def validate_paths(self, base_dir: Optional[Path] = None) -> List[str]:
        """
        Validate that configured paths exist on disk.

        Checks for characterization files, wavelength file, and data
        directories. Returns a list of warning messages for any missing
        paths.

        Parameters
        ----------
        base_dir : Path, optional
            Base directory to resolve relative paths against.
            Default: project root (auto-detected).

        Returns
        -------
        warnings_list : List[str]
            Warning messages for missing paths (empty if all OK).
        """
        warns: List[str] = []

        # Wavelength file
        wl_file = self.spectrometer.wavelength_file
        if wl_file is not None and not Path(wl_file).exists():
            warns.append(f"Wavelength file not found: {wl_file}")

        # Assets directory
        if self.paths.assets_dir is not None and not Path(self.paths.assets_dir).exists():
            warns.append(f"Assets directory not found: {self.paths.assets_dir}")

        # Retarder characterization files
        if self.paths.assets_dir is not None and Path(self.paths.assets_dir).exists():
            assets = Path(self.paths.assets_dir)
            fp1 = assets / self.paths.retarder_char.fp1
            fp2 = assets / self.paths.retarder_char.fp2
            if not fp1.exists():
                warns.append(f"Retarder FP1 file not found: {fp1}")
            if not fp2.exists():
                warns.append(f"Retarder FP2 file not found: {fp2}")

        # Calibration data directories
        if self.mode == 'transmission':
            cal_dir = self.paths.calibration_transmission_dir
            if cal_dir is not None and not Path(cal_dir).exists():
                warns.append(f"Transmission calibration directory not found: {cal_dir}")
        elif self.mode == 'reflection':
            cal_dir = self.paths.calibration_reflection_dir
            if cal_dir is not None and not Path(cal_dir).exists():
                warns.append(f"Reflection calibration directory not found: {cal_dir}")

        return warns

    # =========================================================================
    # SERIALIZATION METHODS
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to a dictionary.

        Converts Path objects to strings for JSON serialization.

        Returns
        -------
        Dict[str, Any]
            Dictionary representation of the configuration.
        """
        def convert_value(obj: Any) -> Any:
            """Recursively convert values for serialization."""
            if isinstance(obj, Path):
                return str(obj)
            elif isinstance(obj, dict):
                return {k: convert_value(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_value(item) for item in obj]
            elif hasattr(obj, '__dataclass_fields__'):
                return {k: convert_value(v) for k, v in asdict(obj).items()}
            else:
                return obj

        return convert_value(asdict(self))

    def to_json(self, path: Path, indent: int = 2) -> None:
        """
        Save configuration to a JSON file.

        Parameters
        ----------
        path : Path
            Output file path.
        indent : int, optional
            JSON indentation level. Default: 2
        """
        path = Path(path)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=indent)

    @classmethod
    def from_json(cls, path: Path) -> 'ECMConfig':
        """
        Load configuration from a JSON file.

        Parameters
        ----------
        path : Path
            Input file path.

        Returns
        -------
        ECMConfig
            Loaded configuration.
        """
        path = Path(path)
        with open(path, 'r') as f:
            data = json.load(f)

        return cls._from_dict(data)

    def to_yaml(self, path: Path) -> None:
        """
        Save configuration to a YAML file.

        Parameters
        ----------
        path : Path
            Output file path.

        Raises
        ------
        ImportError
            If PyYAML is not installed.
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAML serialization. "
                "Install it with: pip install pyyaml"
            )

        path = Path(path)
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, path: Path) -> 'ECMConfig':
        """
        Load configuration from a YAML file.

        Parameters
        ----------
        path : Path
            Input file path.

        Returns
        -------
        ECMConfig
            Loaded configuration.

        Raises
        ------
        ImportError
            If PyYAML is not installed.
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAML deserialization. "
                "Install it with: pip install pyyaml"
            )

        path = Path(path)
        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> 'ECMConfig':
        """
        Create configuration from a dictionary.

        Parameters
        ----------
        data : Dict[str, Any]
            Dictionary with configuration data.

        Returns
        -------
        ECMConfig
            Configuration instance.
        """
        # Convert nested dictionaries to dataclasses
        def convert_to_dataclass(dc_class, d):
            """Convert a dict to a dataclass, handling nested structures."""
            if d is None:
                return dc_class()

            field_types = {f.name: f.type for f in dc_class.__dataclass_fields__.values()}
            kwargs = {}

            for key, value in d.items():
                if key not in field_types:
                    continue

                field_type = field_types[key]

                # Handle Path fields
                if field_type == Path or field_type == Optional[Path]:
                    kwargs[key] = Path(value) if value is not None else None

                # Handle nested dataclasses
                elif hasattr(field_type, '__dataclass_fields__'):
                    kwargs[key] = convert_to_dataclass(field_type, value)

                # Handle Tuple fields
                elif hasattr(field_type, '__origin__') and field_type.__origin__ is tuple:
                    kwargs[key] = tuple(value) if value is not None else None

                # Handle Dict with CalibrationSampleConfig values
                elif key == 'calibration_samples' and isinstance(value, dict):
                    kwargs[key] = {
                        k: CalibrationSampleConfig(**v) if isinstance(v, dict) else v
                        for k, v in value.items()
                    }

                else:
                    kwargs[key] = value

            return dc_class(**kwargs)

        # Special handling for top-level ECMConfig
        kwargs = {}

        # Simple fields
        if 'mode' in data:
            kwargs['mode'] = data['mode']

        # Nested dataclass fields
        nested_fields = {
            'instrument': InstrumentConfig,
            'acquisition': AcquisitionConfig,
            'spectrometer': SpectrometerConfig,
            'wavelength': WavelengthConfig,
            'file_format': FileFormatConfig,
            'paths': PathsConfig,
            'ecm': ECMAlgorithmConfig,
            'fourier': FourierConfig,
            'mueller': MuellerConfig,
            'processing': ProcessingConfig,
            'output': OutputConfig,
            'figure': FigureConfig,
            'reflection_cal': ReflectionCalConfig,
        }

        for field_name, field_class in nested_fields.items():
            if field_name in data and data[field_name] is not None:
                kwargs[field_name] = convert_to_dataclass(field_class, data[field_name])

        # Handle calibration_samples specially
        if 'calibration_samples' in data and data['calibration_samples']:
            kwargs['calibration_samples'] = {
                k: CalibrationSampleConfig(**v) if isinstance(v, dict) else v
                for k, v in data['calibration_samples'].items()
            }

        return cls(**kwargs)

    def __repr__(self) -> str:
        """Return a concise string representation."""
        return (
            f"ECMConfig(mode='{self.mode}', "
            f"n_angular_positions={self.acquisition.n_angular_positions}, "
            f"n_wavelengths={self.spectrometer.n_wavelengths}, "
            f"wavelength_range={self.wavelength.range_nm})"
        )
