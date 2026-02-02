Configuration Guide
===================

ECM Polarimetry uses a hierarchical dataclass-based configuration system that
provides sensible defaults while allowing full customization.

ECMConfig Structure
-------------------

The main configuration class ``ECMConfig`` contains several nested configuration
sections:

.. code-block:: python

   from ecm.config import ECMConfig

   cfg = ECMConfig()

   # Access nested sections
   cfg.paths          # File paths
   cfg.instrument     # Instrument parameters
   cfg.acquisition    # Acquisition settings
   cfg.ecm            # ECM algorithm parameters
   cfg.calibration    # Calibration sample definitions

Paths Configuration
-------------------

.. code-block:: python

   cfg.paths.data_dir                  # Root data directory
   cfg.paths.calibration_output_dir    # Where to save calibration results
   cfg.paths.samples_dir               # Sample measurement files
   cfg.paths.wavelength_file           # Wavelength calibration file

Instrument Configuration
------------------------

.. code-block:: python

   cfg.instrument.mode                 # 'transmission' or 'reflection'
   cfg.instrument.freq_ratio_1         # First retarder frequency ratio
   cfg.instrument.freq_ratio_2         # Second retarder frequency ratio

Acquisition Configuration
-------------------------

.. code-block:: python

   cfg.acquisition.n_angular_positions # Number of measurement angles
   cfg.acquisition.wavelength_range    # (min, max) wavelength in nm
   cfg.acquisition.n_wavelengths       # Number of spectral points

ECM Algorithm Configuration
---------------------------

.. code-block:: python

   cfg.ecm.method                      # 'overdetermined' or 'standard'
   cfg.ecm.optimization_enabled        # Enable/disable optimization
   cfg.ecm.max_iterations              # Maximum optimization iterations

Calibration Samples
-------------------

Define calibration samples with their expected Mueller matrices:

.. code-block:: python

   cfg.calibration.samples['air'].enabled = True
   cfg.calibration.samples['air'].expected_mueller = np.eye(4)

   cfg.calibration.samples['pol_0'].enabled = True
   cfg.calibration.samples['pol_0'].type = 'polarizer'
   cfg.calibration.samples['pol_0'].angle = 0.0

   cfg.calibration.samples['qwp_0'].enabled = True
   cfg.calibration.samples['qwp_0'].type = 'retarder'
   cfg.calibration.samples['qwp_0'].retardance = 90.0  # degrees
   cfg.calibration.samples['qwp_0'].angle = 0.0

Saving and Loading
------------------

Configuration can be saved and loaded from YAML or JSON files:

.. code-block:: python

   # Save to YAML
   cfg.to_yaml("my_config.yaml")

   # Load from YAML
   cfg = ECMConfig.from_yaml("my_config.yaml")

   # Save to JSON
   cfg.to_json("my_config.json")

   # Load from JSON
   cfg = ECMConfig.from_json("my_config.json")

Example YAML Configuration
--------------------------

.. code-block:: yaml

   paths:
     data_dir: "./calibration_data"
     calibration_output_dir: "./results"
     wavelength_file: "wavelengths.txt"

   instrument:
     mode: "transmission"
     freq_ratio_1: 5
     freq_ratio_2: 3

   acquisition:
     n_angular_positions: 192
     wavelength_range: [400, 800]

   ecm:
     method: "overdetermined"
     optimization_enabled: true

   calibration:
     samples:
       air:
         enabled: true
       pol_0:
         enabled: true
         type: "polarizer"
         angle: 0.0
       qwp_0:
         enabled: true
         type: "retarder"
         retardance: 90.0
         angle: 0.0

Validation
----------

The configuration is validated on creation and modification:

.. code-block:: python

   # This will raise ValueError
   cfg.acquisition.wavelength_range = (800, 400)  # min > max

   # This will raise ValueError
   cfg.instrument.mode = "invalid_mode"

Best Practices
--------------

1. **Always use Path objects** for file paths
2. **Save your configuration** alongside calibration results for reproducibility
3. **Use YAML format** for human-readable configuration files
4. **Validate wavelength ranges** match your spectrometer calibration
