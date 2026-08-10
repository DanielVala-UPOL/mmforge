# MMForge ECM v8.0.0 Integration Specification

**Version:** 1.0
**Date:** 2026-04-01
**Author:** Generated from comparative analysis of ECM-PURE v8.0.0 and MMForge v1.2 (ECM v6.5.5)
**Purpose:** Step-by-step implementation guide for Claude Code to integrate ECM v8.0.0 features into MMForge.
**MMForge version after integration** v2.0, update footer in the sidebar

---

## Table of Contents

1. [Overview & Scope](#1-overview--scope)
2. [Architecture & Conventions](#2-architecture--conventions)
3. [Part 1 — ECM Backend Updates (Transmission Fixes)](#3-part-1--ecm-backend-updates-transmission-fixes)
4. [Part 2 — Reflection Mode Backend](#4-part-2--reflection-mode-backend)
5. [Part 3 — Reflection Mode GUI Integration](#5-part-3--reflection-mode-gui-integration)
6. [Part 4 — Post-Processing Overhaul](#6-part-4--post-processing-overhaul)
7. [Part 5 — UI Polish & Home Page](#7-part-5--ui-polish--home-page)
8. [Part 6 — Full Integration Test Checklist](#8-part-6--full-integration-test-checklist)
9. [Appendix A — File Inventory](#appendix-a--file-inventory)
10. [Appendix B — Session State Schema](#appendix-b--session-state-schema)
11. [Appendix C — Uncertainties & Assumptions](#appendix-c--uncertainties--assumptions)

---

## 1. Overview & Scope

### What MMForge Currently Has (v1.2, ECM v6.5.5)

- Transmission calibration (fully working)
- Transmission sample processing (fully working)
- Lu-Chipman polar decomposition (fully working)
- Streamlit GUI with 6 pages (HOME, CONFIGURATION, CALIBRATION, PROCESSING, PARAMETERS, ADVANCED)
- Save/load calibrations as .npz
- Export results as .npz and .csv
- Tutorial mode with bundled example data

### What ECM-PURE v8.0.0 Adds

- **Reflection calibration** with wafer characterization + TMM physics refinement
- **Reflection sample processing** with ellipsometric parameter extraction (Psi, Delta, pseudo-epsilon)
- **Auto-detection of angular positions** from file dimensions
- **Three new decomposition methods:** Differential, Cloude spectral, Purity space
- **Wafer terminology:** `WAFER25NM` / `WAFER10NM` instead of old "reflector 1" / "reflector 2"
- **Config validation** (`validate_paths()`)
- **New config classes:** `ReflectionOptConfig`, `ThicknessFitConfig`, `ReflectionCalConfig`
- Minor transmission improvements (auto-detect n_angular, dynamic step counting)

### Integration Goals

1. **Primary:** Add reflection calibration, reflection sample processing, and ellipsometric parameter extraction as a new mode in MMForge.
2. **Secondary:** Update transmission backend to match ECM-PURE v8.0.0 (auto-detection, config improvements).
3. **Tertiary:** Add all four decomposition methods to the PARAMETERS page.
4. **Constraint:** The existing transmission pipeline must remain untouched and fully functional.

### Design Decisions (Confirmed with User)

| Decision | Choice |
|----------|--------|
| Angular positions | Auto-detect from file dimensions (match ECM-PURE) |
| Wavelength range default | Keep 400–1000 nm (MMForge current) |
| Wafer characterization files | Auto-discover from assets dir + manual UI fallback |
| Decomposition UI location | All 4 methods on page 4 (PARAMETERS) as tabs |
| Ellipsometric extraction | Automatic after reflection sample processing |
| TMM refinement | Always runs as part of reflection calibration |
| Reflection quality display | Match transmission style (eigenvalue categories) + expandable detail |
| UI polish | Include HOME page, sidebar, help text updates |

---

## 2. Architecture & Conventions

### Directory Layout (After Integration)

```
ECM-GUI/
├── ecm/
│   ├── __init__.py                         # UPDATE: bump version, add new imports
│   ├── config/
│   │   └── ecm_config.py                   # UPDATE: add reflection config classes
│   ├── core/
│   │   ├── transmission_calibration.py      # UPDATE: auto-detect angular positions
│   │   ├── reflection_calibration.py        # NEW: copy from ECM-PURE
│   │   ├── ellipsometry.py                  # NEW: copy from ECM-PURE
│   │   ├── tmm.py                           # NEW: copy from ECM-PURE
│   │   ├── ecm_solver.py                    # UPDATE: add solve_A_reflection()
│   │   ├── ecm_matrices.py                  # NO CHANGE
│   │   ├── ecm_optimization.py              # NO CHANGE
│   │   ├── modulation.py                    # NO CHANGE
│   │   ├── fourier.py                       # NO CHANGE
│   │   ├── sample_processing.py             # NO CHANGE
│   │   ├── parameter_extraction.py          # NO CHANGE
│   │   └── file_discovery.py                # UPDATE: add reflection file discovery
│   ├── postprocessing/
│   │   ├── lu_chipman.py                    # NO CHANGE (already matches PURE)
│   │   ├── differential_decomposition.py    # NEW: copy from ECM-PURE
│   │   ├── cloude_decomposition.py          # NEW: copy from ECM-PURE
│   │   ├── purity_space.py                  # NEW: copy from ECM-PURE
│   │   └── _validation.py                   # NEW: copy from ECM-PURE
│   ├── io/
│   │   ├── calibration_io.py                # UPDATE: support reflection calibration save/load
│   │   └── sample_discovery.py              # NO CHANGE
│   ├── utils/
│   │   ├── io.py                            # UPDATE: add detect_angular_positions()
│   │   └── mueller_matrices.py              # NO CHANGE (already matches PURE)
│   ├── visualization/                       # NO CHANGE (GUI uses its own Plotly plots)
│   └── diagnostics/
│       └── calibration_diagnostics.py       # NO CHANGE
├── streamlit_app/
│   ├── HOME.py                              # UPDATE: reflection info, new decompositions
│   ├── pages/
│   │   ├── 1_CONFIGURATION.py               # UPDATE: reflection config UI
│   │   ├── 2_CALIBRATION.py                 # UPDATE: reflection calibration workflow
│   │   ├── 3_PROCESSING.py                  # UPDATE: reflection processing + ellipsometry
│   │   ├── 4_PARAMETERS.py                  # UPDATE: add 3 new decomposition tabs
│   │   ├── 5_ADVANCED.py                    # UPDATE: reflection-specific settings
│   │   └── 6_About.py                       # UPDATE: version bump
│   ├── components/
│   │   ├── sidebar.py                       # UPDATE: reflection status indicator
│   │   ├── plots_plotly.py                  # UPDATE: add reflection + decomposition plots
│   │   ├── mueller_selector.py              # NO CHANGE
│   │   └── file_browser.py                  # NO CHANGE
│   └── utils/
│       ├── session_state.py                 # UPDATE: add reflection + decomposition state
│       ├── styling.py                       # NO CHANGE
│       └── export.py                        # UPDATE: support reflection + new decomp exports
```

### Key Conventions

1. **Source of truth:** ECM-PURE v8.0.0 is the reference for all algorithms. Copy algorithm code from PURE; adapt only the integration layer.
2. **Don't modify working code:** If a file is marked NO CHANGE, do not touch it. If a file needs UPDATE, make surgical changes only.
3. **Session state naming:** All new reflection keys use prefix `refl_` (e.g., `refl_calibration_result`). New decomposition keys use prefix matching the method (e.g., `differential_results`, `cloude_results`, `purity_results`).
4. **Terminology:** Use `WAFER25NM` / `WAFER10NM` in all code, file discovery, config, and UI. Never use "reflector 1" / "reflector 2".
5. **Data shapes:** Mueller matrices are always `(4, 4, n_wavelengths)`. Parameters are always `(n_wavelengths,)`.

---

## 3. Part 1 — ECM Backend Updates (Transmission Fixes)

**Goal:** Bring the ECM backend in MMForge up to v8.0.0 parity for transmission-related code. These are minor, surgical updates.

### 1.1 Update `ecm/utils/io.py` — Add `detect_angular_positions()`

**Source:** Copy `detect_angular_positions()` from `ECM-PURE/ecm/utils/io.py`.

**What to do:**
1. Read `ECM-PURE/ecm/utils/io.py` and locate the `detect_angular_positions()` function.
2. Add it to `ECM-GUI/ecm/utils/io.py` at the end of the file (after existing functions).
3. Add the function to `__all__` if the module uses one.

**Function signature (from ECM-PURE):**
```python
def detect_angular_positions(
    file_paths: List[Path],
    n_wavelengths: int,
    n_rotation_cycles: int,
    labels: List[str]
) -> int:
```

**Verification:**
- Import the function: `from ecm.utils.io import detect_angular_positions`
- Verify it auto-detects correctly from a known binary file (tutorial data: 96 positions, 2048 wavelengths).

### 1.2 Update `ecm/config/ecm_config.py` — Auto-detect Angular Positions

**What to do:**
1. Change `n_angular_positions` default from `96` to `None` in `AcquisitionConfig`:
   ```python
   # Before:
   n_angular_positions: int = 96
   # After:
   n_angular_positions: Optional[int] = None
   ```
2. Update the `angular_step_deg` property to handle `None`:
   ```python
   @property
   def angular_step_deg(self) -> float:
       if self.n_angular_positions is None:
           raise RuntimeError(
               "n_angular_positions not set. Run auto-detection first or set manually."
           )
       return self.acquisition.angular_range_deg / self.n_angular_positions
   ```
3. Add `from typing import Optional` if not already imported.

**Do NOT change:**
- `wavelength.range_nm` — keep `(400.0, 1000.0)` as the MMForge default.
- Any other existing config defaults.

**Verification:**
- Create an `ECMConfig()` with default settings. Confirm `n_angular_positions` is `None`.
- Confirm that `angular_step_deg` raises `RuntimeError` if `n_angular_positions` is still `None`.
- Confirm that setting `cfg.acquisition.n_angular_positions = 96` makes `angular_step_deg` return `3.75`.

### 1.3 Update `ecm/core/transmission_calibration.py` — Auto-detect Integration

**What to do:**
1. Add import: `from ecm.utils.io import detect_angular_positions`
2. In `calibrate_transmission()`, after file discovery and before building modulation basis, add auto-detection logic. Find the exact location by reading the ECM-PURE version of this function and replicating the auto-detect block (approximately lines 340-354 in PURE).
3. The logic should be: if `cfg.acquisition.n_angular_positions is None`, call `detect_angular_positions()` with all discovered calibration file paths, then set `cfg.acquisition.n_angular_positions` to the result.

**Verification:**
- Run full transmission calibration on tutorial data with `n_angular_positions=None`.
- Confirm it auto-detects 96 positions and calibrates successfully.
- Run with `n_angular_positions=96` (explicit). Confirm identical result.

### 1.4 Update `ecm/core/ecm_solver.py` — Add `solve_A_reflection()`

**Source:** Copy `solve_A_reflection()` from `ECM-PURE/ecm/core/ecm_solver.py`.

**What to do:**
1. Read the ECM-PURE version and locate `solve_A_reflection()`.
2. Append it to `ECM-GUI/ecm/core/ecm_solver.py`.
3. Ensure all imports it needs are present (likely just numpy, existing dataclasses).

**Function signature:**
```python
def solve_A_reflection(
    W: ndarray,
    B_ref: ndarray,
    M_ref: ndarray
) -> Tuple[ndarray, ADiagnostics]:
```

**Verification:**
- Import succeeds: `from ecm.core.ecm_solver import solve_A_reflection`
- No runtime errors on import.

### 1.5 Update `ecm/__init__.py` — Version Bump and New Exports

**What to do:**
1. Update version string to `"8.0.0"` (or `"8.0.0-mmforge"`).
2. Add lazy imports for new modules that will be created in later parts. For now, just update the version.

**Verification:**
```python
import ecm
assert ecm.__version__ == "8.0.0"
```

### Part 1 — Verification Checkpoint

Run the existing transmission calibration end-to-end:
1. Start MMForge: `streamlit run streamlit_app/HOME.py`
2. Go to Configuration → select Tutorial Data mode
3. Go to Calibration → Discover Files → Run Calibration
4. Confirm calibration completes successfully with quality metrics matching previous behavior
5. Go to Processing → Process a sample → confirm Mueller matrix looks correct
6. Go to Parameters → Run Lu-Chipman → confirm decomposition works

**If anything breaks, stop and fix before proceeding to Part 2.**

---

## 4. Part 2 — Reflection Mode Backend

**Goal:** Add all reflection-mode backend modules to the ECM library in MMForge.

### 2.1 Add New Config Classes to `ecm/config/ecm_config.py`

**Source:** Copy from `ECM-PURE/ecm/config/ecm_config.py`.

**What to add (3 new dataclasses + 1 new field on ECMConfig):**

1. **`ReflectionOptConfig`** — Optimization bounds for wafer characterization:
   - psi_bound_deg, delta_bound_deg, R_bound (for both wafers)
   - tau_pol_bounds, theta_pol_bounds
   - multi_start_threshold, n_random_starts
   - Copy the entire dataclass from ECM-PURE.

2. **`ThicknessFitConfig`** — TMM physics-informed fitting parameters:
   - d1_bounds_nm (SiO2 thickness range)
   - d2_bounds_nm (interlayer thickness range)
   - delta_aoi_bounds_deg (AOI correction range)
   - stage2 tighter bounds
   - Copy the entire dataclass from ECM-PURE.

3. **`ReflectionCalConfig`** — Reflection calibration settings:
   - aoi_deg (default 65.0)
   - polarizer_azimuth_deg
   - wafer25nm_label, wafer10nm_label
   - wafer characterization directory paths
   - opt: ReflectionOptConfig
   - thickness_fit: ThicknessFitConfig
   - Copy the entire dataclass from ECM-PURE.

4. **Add field to `ECMConfig`:**
   ```python
   reflection_cal: ReflectionCalConfig = field(default_factory=ReflectionCalConfig)
   ```

5. **Add `validate_paths()` method to ECMConfig** if present in ECM-PURE.

**CRITICAL — Terminology check:** Verify that the config uses `wafer25nm_label` / `wafer10nm_label` (WAFER terminology, not REFLECTOR). The ECM-PURE source should already use this. If you see any "reflector" references, replace with "wafer".

**Verification:**
```python
from ecm.config import ECMConfig
cfg = ECMConfig()
assert cfg.reflection_cal.aoi_deg == 65.0
assert cfg.reflection_cal.opt is not None
assert cfg.reflection_cal.thickness_fit is not None
```

### 2.2 Add `ecm/core/tmm.py` — Transfer Matrix Method

**Source:** Copy `ECM-PURE/ecm/core/tmm.py` verbatim into `ECM-GUI/ecm/core/tmm.py`.

This module is self-contained (depends only on numpy). No modifications needed.

**Verification:**
```python
from ecm.core.tmm import tmm_reflectance
import numpy as np
wl = np.linspace(450, 900, 100)
# Should run without error (exact values depend on layer params)
```

### 2.3 Add `ecm/core/ellipsometry.py` — Ellipsometric Parameter Extraction

**Source:** Copy `ECM-PURE/ecm/core/ellipsometry.py` verbatim into `ECM-GUI/ecm/core/ellipsometry.py`.

This module depends on numpy and its own dataclass `EllipsometricResult`. No modifications needed.

**Verification:**
```python
from ecm.core.ellipsometry import extract_ellipsometric_parameters, EllipsometricResult
```

### 2.4 Update `ecm/core/file_discovery.py` — Add Reflection File Discovery

**Source:** Copy the following from `ECM-PURE/ecm/core/file_discovery.py`:
1. The `ReflectionCalibrationFiles` dataclass
2. The `discover_reflection_calibration_files()` function
3. Any helper functions these depend on (e.g., wafer characterization file search)

**What to do:**
1. Read both versions of `file_discovery.py` carefully.
2. The ECM-PURE version is ~205 lines longer. Identify the new code blocks.
3. Append the new dataclass and functions to the end of the MMForge version.
4. Ensure imports match (Path, dataclass, etc.).

**CRITICAL — Terminology:** The file keywords must use `_WAFER25NM_ECM_`, `_WAFER10NM_ECM_`, `_WAFER25NM_POL_BEFORE_ECM_`, `_WAFER25NM_POL_AFTER_ECM_`. Verify these are correct in the source. If you see `_REFLECTOR1_` or similar old terminology, replace with WAFER equivalents.

**Verification:**
```python
from ecm.core.file_discovery import (
    discover_calibration_files,              # existing
    discover_reflection_calibration_files,    # new
    CalibrationFiles,                         # existing
    ReflectionCalibrationFiles               # new
)
```

### 2.5 Add `ecm/core/reflection_calibration.py` — Full Reflection Calibration

**Source:** Copy `ECM-PURE/ecm/core/reflection_calibration.py` into `ECM-GUI/ecm/core/reflection_calibration.py`.

**This is the largest new file (~1650 lines).** It orchestrates the entire reflection calibration workflow.

**What to do:**
1. Copy the file verbatim from ECM-PURE.
2. Verify all imports resolve correctly against the MMForge ecm package structure:
   - `from ecm.config import ECMConfig` (must include new reflection config classes from step 2.1)
   - `from ecm.core.ecm_solver import solve_W, solve_A_reflection` (solve_A_reflection added in 1.4)
   - `from ecm.core.ecm_matrices import build_H_matrix, build_K_matrix`
   - `from ecm.core.modulation import build_modulation_basis`
   - `from ecm.core.tmm import tmm_reflectance` (added in 2.2)
   - `from ecm.core.file_discovery import discover_reflection_calibration_files` (added in 2.4)
   - `from ecm.utils.io import load_spectral_data, load_wavelengths, detect_angular_positions`
   - `from ecm.utils.mueller_matrices import reflector, polarizer, rotation`
3. Check for any imports of `ecm.utils.terminal_colors`. If present, either:
   - Copy `terminal_colors.py` from ECM-PURE to MMForge (preferred), OR
   - Remove color formatting calls (they're cosmetic console output only).

**CRITICAL — Data loading logic:** The reflection calibration loads wafer characterization files (Psi/Delta from Woollam). The function `_load_wafer_characterization()` reads these files and interpolates to measurement wavelengths using PCHIP. Verify this function is included and that file paths resolve using the config's `reflection_cal` settings.

**CRITICAL — Terminology:** Grep the copied file for any occurrence of "reflector" (case-insensitive). Replace with appropriate "wafer" terminology. Expected keywords in the file:
- Variable names: `wafer25nm`, `wafer10nm`, `B_wafer25nm`, `B_wafer10nm`
- Config references: `cfg.reflection_cal.wafer25nm_label`, `cfg.reflection_cal.wafer10nm_label`
- File discovery: `_WAFER25NM_`, `_WAFER10NM_`

**Verification:**
```python
from ecm.core.reflection_calibration import calibrate_reflection
# Import should succeed without errors
```

### 2.6 Update `ecm/io/calibration_io.py` — Support Reflection Calibrations

**What to do:**
1. Read both versions of `calibration_io.py`.
2. The ECM-PURE version likely includes:
   - Saving/loading `ReflectionCalibrationDiagnostics` alongside standard diagnostics
   - Additional metadata fields for reflection mode (AOI, wafer labels, optimization results)
3. If the PURE version has these additions, replicate them in the MMForge version.
4. If the save/load format is backward-compatible (loads old transmission .npz files), this is safe. If not, add a version field to distinguish formats.

**IMPORTANT:** The save format must remain backward-compatible with existing transmission calibration .npz files. Old files should load without error.

**Verification:**
- Save a transmission calibration → load it back → verify all fields match.
- (Reflection save/load will be testable after Part 3.)

### 2.7 Add `ecm/utils/terminal_colors.py` (if needed)

If `reflection_calibration.py` imports from `ecm.utils.terminal_colors`, copy this file from ECM-PURE. It's a simple utility (~50 lines) with ANSI color functions: `bold()`, `green()`, `red()`, `yellow()`, `cyan()`, `dim()`.

### Part 2 — Verification Checkpoint

1. **Import test:** Run this in a Python shell from the ECM-GUI directory:
   ```python
   from ecm.core.reflection_calibration import calibrate_reflection
   from ecm.core.ellipsometry import extract_ellipsometric_parameters
   from ecm.core.tmm import tmm_reflectance
   from ecm.core.file_discovery import discover_reflection_calibration_files
   from ecm.core.ecm_solver import solve_A_reflection
   from ecm.config import ECMConfig
   cfg = ECMConfig()
   print(cfg.reflection_cal.aoi_deg)  # Should print 65.0
   ```
2. **Transmission regression:** Re-run the full transmission workflow (Part 1 checkpoint). Nothing should have changed.

---

## 5. Part 3 — Reflection Mode GUI Integration

**Goal:** Wire up the reflection calibration and processing backend to the Streamlit GUI.

### 3.1 Update `streamlit_app/utils/session_state.py` — New State Keys

**What to add to the default session state initialization:**

```python
# Reflection calibration
'refl_calibration_result': None,      # CalibrationResult from reflection calibration
'refl_calibration_diag': None,        # ReflectionCalibrationDiagnostics
'refl_is_calibrated': False,          # Boolean
'refl_discovered_files': None,        # ReflectionCalibrationFiles

# Reflection processing
'refl_processed_samples': {},         # Dict[name -> MuellerMatrixResult]
'refl_ellipsometry_results': {},      # Dict[name -> EllipsometricResult]
'refl_current_sample': None,

# Reflection config
'refl_data_dir_path': '',
'refl_assets_dir_path': '',           # Wafer characterization files location
'refl_aoi_deg': 65.0,

# Reflection processing UI state
'refl_discovered_samples': None,
'refl_selected_samples': [],
'refl_view_mode': '4x4 Grid',
```

**Verification:** Start MMForge, confirm no crashes on any page (new keys should initialize to defaults).

### 3.2 Update `streamlit_app/pages/1_CONFIGURATION.py` — Reflection Config

**What to change:**

1. **Remove the warning** that says "Reflection and Combined modes will be available in a future release."

2. **Remove "Combined" from the mode selector.** The valid modes are now: "Transmission", "Reflection", "Tutorial Data". Delete all code paths, UI elements, and session state references related to "Combined" mode.

3. **Add reflection-specific configuration UI** when mode is "Reflection":
   ```
   If mode == "Reflection":
       Show reflection data directory selector → session_state['refl_data_dir_path']
       Show assets directory selector (wafer characterization) → session_state['refl_assets_dir_path']
       Show AOI input (default 65°) → session_state['refl_aoi_deg']
   ```

4. **Wavelength range:** Keep the 400–1000 nm slider. No change.

**UI Layout (Reflection mode):**
```
Data Paths:
├── Reflection Data Directory: [path selector]
├── Wafer Characterization (Assets): [path selector]
│   └── info: "Directory containing Psi/Delta files from Woollam for 25nm and 10nm wafers"
├── Output Directory: [path selector]
└── AOI (degrees): [number input, default 65.0]

Wavelength Settings:
└── Range: [400 — 1000] nm slider
```

**Verification:**
- Select "Reflection" mode → reflection-specific UI appears.
- Select "Transmission" mode → only transmission UI appears (unchanged).
- Confirm "Combined" mode no longer exists in the mode selector.

### 3.3 Update `streamlit_app/pages/2_CALIBRATION.py` — Reflection Calibration

**This is the most complex GUI change.** The page must support both transmission and reflection calibration.

**What to change:**

1. **Mode branching:** At the top of the calibration logic, branch on `calibration_mode`:
   ```python
   if mode in ("Transmission", "Tutorial Data"):
       # Existing transmission workflow (DO NOT MODIFY)
       ...
   elif mode == "Reflection":
       # New reflection workflow
       ...
   ```

2. **Reflection calibration workflow** (new code block):

   a. **File Discovery:**
   ```python
   from ecm.core.file_discovery import discover_reflection_calibration_files

   # Build config with reflection settings from session state
   cfg = build_reflection_config_from_session()
   refl_files = discover_reflection_calibration_files(cfg)
   st.session_state['refl_discovered_files'] = refl_files
   ```

   Display discovered files in an expander:
   - Wafer 25 nm (bare): filename
   - Wafer 25 nm + Pol (before): filename
   - Wafer 25 nm + Pol (after): filename
   - Wafer 10 nm (bare): filename
   - Wafer characterization files: filenames (auto-discovered or manually selected)

   b. **Auto-detect angular positions:**
   ```python
   from ecm.utils.io import detect_angular_positions
   # Same logic as transmission, applied to reflection files
   ```

   c. **Run Calibration:**
   ```python
   from ecm.core.reflection_calibration import calibrate_reflection

   result, diag = calibrate_reflection(cfg, progress_callback=update_progress)
   st.session_state['refl_calibration_result'] = result
   st.session_state['refl_calibration_diag'] = diag
   st.session_state['refl_is_calibrated'] = True
   ```

   d. **Quality Display:**
   - Use the same eigenvalue-ratio categories (excellent/good/acceptable/marginal/poor).
   - Add an expandable section for reflection-specific metrics:
     - Optimization convergence (fraction of wavelengths converged)
     - TMM fit quality (if available in diagnostics)
     - Wafer parameter deviations from nominal

   e. **Save/Load:** Extend existing save/load to handle reflection calibrations. Include mode metadata so loading knows whether it's transmission or reflection.

3. **Helper function: `build_reflection_config_from_session()`**

   Create a new helper (similar to existing `build_config_from_session()`) that maps reflection session state to an `ECMConfig` with reflection settings:
   ```python
   def build_reflection_config_from_session():
       cfg = ECMConfig()
       cfg.paths.data_dir = Path(st.session_state['refl_data_dir_path'])
       cfg.paths.assets_dir = Path(st.session_state['refl_assets_dir_path'])
       cfg.reflection_cal.aoi_deg = st.session_state['refl_aoi_deg']
       cfg.wavelength.range_nm = (st.session_state['wl_min'], st.session_state['wl_max'])
       cfg.spectrometer.n_wavelengths = st.session_state['n_wavelengths']
       # n_angular_positions left as None for auto-detection
       return cfg
   ```

4. **Wafer characterization file handling:**
   - First, try auto-discovery from `refl_assets_dir_path` (matching ECM-PURE's logic in `_load_wafer_characterization()`).
   - If auto-discovery fails (files not found), show a file browser UI for manual selection.
   - Display which characterization files were found/selected.

**UNCERTAINTY:** The exact progress_callback signature for `calibrate_reflection()` may differ from `calibrate_transmission()`. Check the ECM-PURE source for the callback signature and adapt the Streamlit progress bar accordingly. If `calibrate_reflection()` does not accept a progress_callback, you may need to add one or use a spinner instead.

**Verification:**
- Select Reflection mode → Discover Files finds wafer files (need reflection test data).
- Run Reflection Calibration → completes without error.
- Quality metrics display correctly.
- Save reflection calibration → load it back → state restored.
- Switch to Transmission mode → existing calibration workflow unchanged.

### 3.4 Update `streamlit_app/pages/3_PROCESSING.py` — Reflection Processing

**What to change:**

1. **Mode branching:** Branch on `calibration_mode` to decide which calibration result to use:
   ```python
   if mode in ("Transmission", "Tutorial Data"):
       cal_result = st.session_state['calibration_result']
       cal_diag = st.session_state['calibration_diag']
       is_calibrated = st.session_state['is_calibrated']
       processed_key = 'processed_samples'
       data_dir = st.session_state['data_dir_path']
   elif mode == "Reflection":
       cal_result = st.session_state['refl_calibration_result']
       cal_diag = st.session_state['refl_calibration_diag']
       is_calibrated = st.session_state['refl_is_calibrated']
       processed_key = 'refl_processed_samples'
       data_dir = st.session_state['refl_data_dir_path']
   ```

2. **Sample discovery:** Use the same `discover_sample_files()` function but pointed at the reflection data directory. Sample files for reflection should be discovered from the same directory as calibration files (or a subdirectory — check ECM-PURE's convention).

3. **Processing loop:** The `process_sample()` function is the same for transmission and reflection (it just applies M = A^-1 @ B @ W^-1). The difference is that for reflection mode, after processing, we also extract ellipsometric parameters:
   ```python
   from ecm.core.ellipsometry import extract_ellipsometric_parameters

   mueller_result = process_sample(sample_data, A, W, inv_W_mod, dark, cfg)

   if mode == "Reflection":
       aoi_deg = st.session_state['refl_aoi_deg']
       ellips_result = extract_ellipsometric_parameters(mueller_result.M_normalized, aoi_deg)
       st.session_state['refl_ellipsometry_results'][sample_name] = ellips_result
   ```

4. **Results display — Reflection mode additions:**
   After the Mueller matrix display (same as transmission), add an "Ellipsometric Parameters" expander:
   ```
   Ellipsometric Parameters:
   ├── Tab: Psi & Delta
   │   └── Plot: Psi(λ) and Delta(λ) vs wavelength
   ├── Tab: N, C, S
   │   └── Plot: N(λ), C(λ), S(λ) vs wavelength
   └── Tab: Pseudo Optical Constants
       ├── Plot: ⟨ε₁⟩(λ), ⟨ε₂⟩(λ) vs wavelength (real/imag of pseudo-epsilon)
       └── Plot: ⟨n⟩(λ), ⟨k⟩(λ) vs wavelength
   ```

5. **Export:** Add ellipsometric parameters to CSV export for reflection samples:
   - Columns: wavelength_nm, psi_deg, delta_deg, N, C, S, pseudo_n, pseudo_k, pseudo_eps_real, pseudo_eps_imag

**Verification:**
- Process a reflection sample → Mueller matrix appears.
- Ellipsometric parameters display automatically.
- Export CSV includes ellipsometric data.
- Process a transmission sample → no ellipsometric section appears (unchanged behavior).

### 3.5 Add Reflection Plots to `streamlit_app/components/plots_plotly.py`

**What to add:**

1. **`create_ellipsometry_plot(wavelengths, ellips_result, parameter='psi_delta')`**
   - `parameter='psi_delta'`: Dual-axis plot with Psi (left y-axis) and Delta (right y-axis)
   - `parameter='ncs'`: Three traces for N, C, S
   - `parameter='pseudo_epsilon'`: Real and imaginary parts of ⟨ε⟩
   - `parameter='pseudo_nk'`: ⟨n⟩ and ⟨k⟩

2. **`create_ellipsometry_comparison_plot(wavelengths, ellips_results_dict, parameter)`**
   - Multi-sample comparison for ellipsometric parameters.

**Style:** Match existing plot conventions (font size 20pt, primary color #FF1F5B, grid on).

**Verification:** Visual inspection — plots render correctly with test data.

### Part 3 — Verification Checkpoint

1. **Transmission regression:** Full transmission workflow still works identically.
2. **Reflection workflow (if test data available):**
   - Configuration → Reflection mode → set directories
   - Calibration → Discover → Run → quality metrics display
   - Processing → Process sample → Mueller + ellipsometric parameters
   - Export → CSV includes all data
3. **Mode switching:** Switch between Transmission and Reflection modes. Session state for each mode is independent.

---

## 6. Part 4 — Post-Processing Overhaul

**Goal:** Add three new decomposition methods and restructure the PARAMETERS page.

### 4.1 Add New Decomposition Modules to ECM Backend

**Files to copy from ECM-PURE (verbatim, no modifications needed):**

1. `ecm/postprocessing/differential_decomposition.py` → `ECM-GUI/ecm/postprocessing/differential_decomposition.py`
2. `ecm/postprocessing/cloude_decomposition.py` → `ECM-GUI/ecm/postprocessing/cloude_decomposition.py`
3. `ecm/postprocessing/purity_space.py` → `ECM-GUI/ecm/postprocessing/purity_space.py`
4. `ecm/postprocessing/_validation.py` → `ECM-GUI/ecm/postprocessing/_validation.py`

These modules are self-contained (depend only on numpy/scipy and their own dataclasses).

**Verification:**
```python
from ecm.postprocessing.differential_decomposition import differential_decomposition, DifferentialDecompositionResult
from ecm.postprocessing.cloude_decomposition import cloude_decomposition, CloudeDecompositionResult
from ecm.postprocessing.purity_space import purity_analysis, PurityResult
```

### 4.2 Update `ecm/postprocessing/__init__.py` (if exists)

If there's an `__init__.py` in the postprocessing directory, update it to export the new modules:

```python
from .lu_chipman import lu_chipman_decomposition, LuChipmanResult
from .differential_decomposition import differential_decomposition, DifferentialDecompositionResult
from .cloude_decomposition import cloude_decomposition, CloudeDecompositionResult
from .purity_space import purity_analysis, PurityResult
```

If no `__init__.py` exists, create one with these exports.

### 4.3 Update `streamlit_app/utils/session_state.py` — Decomposition State

**Add new keys:**
```python
# Differential decomposition
'differential_results': {},   # Dict[name -> DifferentialDecompositionResult]

# Cloude decomposition
'cloude_results': {},         # Dict[name -> CloudeDecompositionResult]

# Purity analysis
'purity_results': {},         # Dict[name -> PurityResult]
```

### 4.4 Restructure `streamlit_app/pages/4_PARAMETERS.py` — Tabbed Decompositions

**Current structure:** Single decomposition (Lu-Chipman) fills the entire page.

**New structure:** Top-level tabs for each decomposition method.

**What to do:**

1. **Add top-level tab selector:**
   ```python
   decomp_tab = st.tabs([
       "Lu-Chipman",
       "Differential",
       "Cloude Spectral",
       "Purity Space"
   ])
   ```

2. **Tab 1: Lu-Chipman** — Move ALL existing page 4 code into this tab. Do not modify the logic, just indent it into the tab context.

3. **Tab 2: Differential Decomposition**

   **Algorithm:** Takes normalized Mueller matrix M, returns L_m (polarization), L_u (depolarization), M_m, M_u.

   **UI structure:**
   ```
   Sample Selection (same pattern as Lu-Chipman):
   ├── Select samples from processed_samples (or refl_processed_samples)
   └── Run Decomposition button

   Results:
   ├── Decomposed Matrices expander:
   │   ├── Tab: Mean Nondepolarizing (M_m) — 4x4 grid plot
   │   └── Tab: Depolarization (M_u) — 4x4 grid plot
   └── Logarithmic Components expander:
       ├── Tab: L_m (polarization properties)
       └── Tab: L_u (depolarization properties)

   Export:
   ├── Save (.npz)
   └── Export (.csv)
   ```

   **Calling the backend:**
   ```python
   from ecm.postprocessing.differential_decomposition import differential_decomposition

   for name in selected_samples:
       M_norm = get_processed_mueller(name)  # from either transmission or reflection
       result = differential_decomposition(M_norm)
       st.session_state['differential_results'][name] = result
   ```

   **What is `get_processed_mueller(name)`?** A helper that returns the correct Mueller matrix based on current mode:
   ```python
   def get_processed_mueller(name):
       mode = st.session_state['calibration_mode']
       if mode in ("Transmission", "Tutorial Data"):
           return st.session_state['processed_samples'][name].M_normalized
       elif mode == "Reflection":
           return st.session_state['refl_processed_samples'][name].M_normalized
   ```

4. **Tab 3: Cloude Spectral Decomposition**

   **Algorithm:** Takes normalized Mueller matrix M, returns eigenvalues [4], M_components [4 matrices], coherency matrix H.

   **UI structure:**
   ```
   Sample Selection + Run button

   Results:
   ├── Eigenvalues expander:
   │   └── Plot: λ₀(λ), λ₁(λ), λ₂(λ), λ₃(λ) vs wavelength
   ├── Component Mueller Matrices expander:
   │   ├── Tab: M₀ (dominant component) — 4x4 grid
   │   ├── Tab: M₁ — 4x4 grid
   │   ├── Tab: M₂ — 4x4 grid
   │   └── Tab: M₃ — 4x4 grid
   └── Coherency Matrix expander:
       └── Plot: |H_ij| vs wavelength (selected elements)

   Export: .npz / .csv
   ```

   **Calling the backend:**
   ```python
   from ecm.postprocessing.cloude_decomposition import cloude_decomposition

   result = cloude_decomposition(M_norm)
   # result.eigenvalues: (4, n_wl)
   # result.M_components: (4, 4, 4, n_wl) — 4 component matrices
   # result.H: (4, 4, n_wl) — coherency matrix
   ```

5. **Tab 4: Purity Space Analysis**

   **Algorithm:** Takes normalized Mueller matrix M, returns P_P, P_S, P_Delta, D_vec, P_vec.

   **UI structure:**
   ```
   Sample Selection + Run button

   Results:
   ├── Purity Indices expander:
   │   ├── Plot: P_P(λ), P_S(λ), P_Δ(λ) vs wavelength
   │   └── (Multi-sample comparison if multiple selected)
   ├── Purity Space expander:
   │   └── Plot: P_S vs P_P scatter (2D purity space diagram)
   │       Include theoretical bounds (triangle: P_S ≤ 1, P_P ≤ 1, P_Δ boundary)
   └── Vectors expander:
       ├── Plot: |D_vec| components vs wavelength
       └── Plot: |P_vec| components vs wavelength

   Export: .npz / .csv
   ```

   **Calling the backend:**
   ```python
   from ecm.postprocessing.purity_space import purity_analysis

   result = purity_analysis(M_norm)
   # result.P_P: (n_wl,) — degree of polarizance
   # result.P_S: (n_wl,) — degree of spherical purity
   # result.P_Delta: (n_wl,) — degree of polarimetric purity
   ```

6. **Mode-aware sample selection:**
   All four tabs should work with both transmission and reflection processed samples. Use the `get_processed_mueller()` helper to abstract this.

### 4.5 Add Decomposition Plots to `plots_plotly.py`

**New plot functions needed:**

1. **Differential decomposition:**
   - `create_differential_matrix_plot(wavelengths, L_m_or_L_u)` — 4x4 grid of matrix elements
   - `create_differential_comparison_plot(wavelengths, results_dict)` — multi-sample

2. **Cloude decomposition:**
   - `create_eigenvalue_spectrum_plot(wavelengths, eigenvalues)` — 4 traces
   - `create_component_mueller_plot(wavelengths, M_component)` — 4x4 grid for one component
   - `create_coherency_matrix_plot(wavelengths, H)` — selected elements of |H|

3. **Purity space:**
   - `create_purity_indices_plot(wavelengths, P_P, P_S, P_Delta)` — 3 traces
   - `create_purity_space_scatter(P_S, P_P)` — 2D scatter with theoretical bounds
   - `create_purity_comparison_plot(wavelengths, results_dict)` — multi-sample

**All plots should follow existing conventions:**
- Font size: 20pt base
- Primary color: #FF1F5B
- Grid: always on
- Layout: consistent margins, axis labels with units

### 4.6 Update Export Functions

**In `streamlit_app/utils/export.py` (or inline in pages):**

Add export support for each new decomposition:

1. **Differential:** CSV columns: wavelength_nm, L_m_ij, L_u_ij (16+16 matrix elements)
2. **Cloude:** CSV columns: wavelength_nm, lambda_0, lambda_1, lambda_2, lambda_3, M0_ij, M1_ij, M2_ij, M3_ij
3. **Purity:** CSV columns: wavelength_nm, P_P, P_S, P_Delta, D_1, D_2, D_3, P_1, P_2, P_3

### Part 4 — Verification Checkpoint

1. **Lu-Chipman:** Existing decomposition still works identically (now in first tab).
2. **Differential:** Run on a processed sample → L_m, L_u, M_m, M_u display correctly.
3. **Cloude:** Run on a processed sample → eigenvalues, component matrices display.
4. **Purity:** Run on a processed sample → P_P, P_S, P_Δ display. Purity space scatter renders.
5. **Mode independence:** Run decompositions on both transmission and reflection samples.
6. **Export:** Each decomposition exports to CSV/NPZ correctly.

---

## 7. Part 5 — UI Polish & Home Page

**Goal:** Update non-functional pages and components for reflection mode awareness.

### 5.1 Update `streamlit_app/components/sidebar.py`

**What to change:**

1. **Add reflection calibration status indicator:**
   ```
   Current display:
   🟢 Calibrated (Transmission)

   New display (when reflection is also calibrated):
   🟢 Transmission: Calibrated
   🟢 Reflection: Calibrated

   Or if only one mode is calibrated:
   🟢 Transmission: Calibrated
   🔴 Reflection: Not calibrated
   ```

2. **Mode display:** Show current calibration mode in sidebar.

3. **Version info:** Update to:
   ```
   MMForge v2.0
   ECM-Calibration v8.0.0
   ```

### 5.2 Update `streamlit_app/HOME.py`

**What to change:**

1. **Workflow cards:** Add reflection-related steps or indicate that both modes are supported.

2. **Tutorial tabs — CALIBRATE section:**
   Add reflection calibration file naming patterns:
   ```
   | Sample                    | Pattern                        | Mode       |
   |---------------------------|--------------------------------|------------|
   | Background                | _DARK_ECM_                     | Both       |
   | Air (straight-through)    | _ST_ECM_                       | Transmission |
   | Polarizer 0°              | _P0_ECM_                       | Transmission |
   | Polarizer 45°             | _P45_ECM_                      | Transmission |
   | Fresnel Prism 90°         | _RET90_FP1_ECM_                | Transmission |
   | Fresnel Prism 45°         | _RET45_FP2_ECM_                | Transmission (optional) |
   | Wafer 25 nm (bare)        | _WAFER25NM_ECM_                | Reflection |
   | Wafer 25 nm + Pol before  | _WAFER25NM_POL_BEFORE_ECM_     | Reflection |
   | Wafer 25 nm + Pol after   | _WAFER25NM_POL_AFTER_ECM_      | Reflection |
   | Wafer 10 nm (bare)        | _WAFER10NM_ECM_                | Reflection |
   ```

3. **Tutorial tabs — PARAMETERS section:**
   Update to mention all four decomposition methods:
   - Lu-Chipman polar decomposition
   - Differential decomposition
   - Cloude spectral decomposition
   - Purity space analysis

4. **Add brief description of reflection mode** in the CONFIGURE tab info.

### 5.3 Update `streamlit_app/pages/5_ADVANCED.py`

**What to change:**

Replace the placeholder content with reflection-specific advanced settings:

1. **Reflection Optimization Bounds:**
   - Psi bound (default ±4°)
   - Delta bound (default ±12°)
   - Reflectance bound (default ±2%)
   - Multi-start threshold and n_random_starts

2. **TMM Fit Settings:**
   - SiO2 thickness bounds (nm)
   - Interlayer thickness bounds (nm)
   - AOI correction bounds (deg)

3. **General Advanced Settings:**
   - Eigenvalue ratio threshold for optimization fallback
   - Warm start toggle
   - Extended method toggle

These settings map to `ECMConfig.reflection_cal.opt` and `ECMConfig.reflection_cal.thickness_fit`. Changes should update session state, which is read by `build_reflection_config_from_session()`.

### 5.4 Update `streamlit_app/pages/6_About.py`

**What to change:**
- Version: MMForge v2.0
- ECM version: v8.0.0
- Add reflection mode and new decompositions to the feature list.

### Part 5 — Verification Checkpoint

1. **Sidebar:** Shows correct status for transmission and reflection independently.
2. **HOME page:** Tutorial tabs show updated content including reflection file patterns.
3. **ADVANCED page:** Reflection settings render and are editable.
4. **About page:** Correct version info.

---

## 8. Part 6 — Full Integration Test Checklist

### A. Transmission Regression Tests

- [ ] **T1:** Tutorial mode calibration succeeds (auto-detect angular positions)
- [ ] **T2:** Tutorial mode processing produces Mueller matrices
- [ ] **T3:** Lu-Chipman decomposition on tutorial data matches previous results
- [ ] **T4:** Save calibration (.npz) → load → state fully restored
- [ ] **T5:** Export Mueller matrices to CSV → file contains correct columns
- [ ] **T6:** Export Lu-Chipman to CSV → file contains D, R, DI, ψ, χ
- [ ] **T7:** Custom data directory calibration works (non-tutorial)
- [ ] **T8:** Explicit n_angular_positions=96 gives same result as auto-detect

### B. Reflection Mode Tests

- [ ] **R1:** Reflection mode config UI shows correct fields (data dir, assets dir, AOI)
- [ ] **R2:** File discovery finds WAFER25NM, WAFER10NM, POL_BEFORE, POL_AFTER files
- [ ] **R3:** Wafer characterization files auto-discovered from assets directory
- [ ] **R4:** Reflection calibration runs to completion
- [ ] **R5:** Eigenvalue-ratio quality display renders for reflection
- [ ] **R6:** Reflection calibration save/load works
- [ ] **R7:** Reflection sample processing produces Mueller matrices
- [ ] **R8:** Ellipsometric parameters (Psi, Delta) automatically computed
- [ ] **R9:** Pseudo-epsilon and pseudo-n/k computed correctly
- [ ] **R10:** Ellipsometric parameter plots render (Psi/Delta, NCS, pseudo-epsilon, pseudo-nk)
- [ ] **R11:** Export reflection results to CSV includes ellipsometric columns

### C. Decomposition Tests

- [ ] **D1:** Lu-Chipman tab works (existing functionality, now in tab)
- [ ] **D2:** Differential decomposition runs on transmission sample
- [ ] **D3:** Differential decomposition runs on reflection sample
- [ ] **D4:** Differential results display: L_m, L_u, M_m, M_u matrices
- [ ] **D5:** Cloude decomposition runs on transmission sample
- [ ] **D6:** Cloude decomposition runs on reflection sample
- [ ] **D7:** Cloude results display: eigenvalues, 4 component matrices, coherency
- [ ] **D8:** Purity analysis runs on transmission sample
- [ ] **D9:** Purity analysis runs on reflection sample
- [ ] **D10:** Purity results display: P_P, P_S, P_Δ plots and purity space scatter
- [ ] **D11:** All decompositions export to CSV correctly
- [ ] **D12:** All decompositions export to NPZ correctly
- [ ] **D13:** Multi-sample comparison works for each decomposition

### D. Mode Switching & State Independence

- [ ] **M1:** Switching from Transmission to Reflection preserves transmission calibration
- [ ] **M2:** Switching from Reflection to Transmission preserves reflection calibration
- [ ] **M3:** "Combined" mode no longer exists in the UI (fully removed)
- [ ] **M4:** Session reset clears all state (transmission + reflection + decompositions)
- [ ] **M5:** Re-calibration dialog works for both modes

### E. UI & Navigation

- [ ] **U1:** HOME page tutorial content includes reflection file patterns
- [ ] **U2:** Sidebar shows dual calibration status (transmission + reflection)
- [ ] **U3:** Sidebar version shows MMForge v2.0 / ECM v8.0.0
- [ ] **U4:** ADVANCED page shows reflection optimization settings
- [ ] **U5:** About page updated
- [ ] **U6:** No Python errors or Streamlit warnings on any page navigation sequence

### F. Edge Cases

- [ ] **E1:** Reflection calibration with missing wafer characterization files → graceful error message
- [ ] **E2:** Processing before calibration → clear error message
- [ ] **E3:** Decomposition before processing → clear error message
- [ ] **E4:** Very narrow wavelength range (e.g., 500-510 nm) → still works
- [ ] **E5:** Loading old transmission .npz file (pre-v8) → backward compatible
- [ ] **E6:** Auto-detect angular positions with inconsistent file sizes → clear error message

---

## Appendix A — File Inventory

### Files to Copy from ECM-PURE (Verbatim)

| Source (ECM-PURE) | Destination (ECM-GUI) | Size |
|---|---|---|
| `ecm/core/reflection_calibration.py` | `ecm/core/reflection_calibration.py` | ~1650 lines |
| `ecm/core/ellipsometry.py` | `ecm/core/ellipsometry.py` | ~160 lines |
| `ecm/core/tmm.py` | `ecm/core/tmm.py` | ~380 lines |
| `ecm/postprocessing/differential_decomposition.py` | `ecm/postprocessing/differential_decomposition.py` | ~150 lines |
| `ecm/postprocessing/cloude_decomposition.py` | `ecm/postprocessing/cloude_decomposition.py` | ~175 lines |
| `ecm/postprocessing/purity_space.py` | `ecm/postprocessing/purity_space.py` | ~125 lines |
| `ecm/postprocessing/_validation.py` | `ecm/postprocessing/_validation.py` | ~varies |
| `ecm/utils/terminal_colors.py` | `ecm/utils/terminal_colors.py` | ~50 lines |

### Files to Modify in ECM-GUI

| File | Change Type | Scope |
|---|---|---|
| `ecm/__init__.py` | Version bump, new exports | Small |
| `ecm/config/ecm_config.py` | Add 3 config classes, modify AcquisitionConfig | Medium |
| `ecm/core/ecm_solver.py` | Add `solve_A_reflection()` | Small |
| `ecm/core/file_discovery.py` | Add reflection file discovery | Medium |
| `ecm/core/transmission_calibration.py` | Add auto-detect logic | Small |
| `ecm/utils/io.py` | Add `detect_angular_positions()` | Small |
| `ecm/io/calibration_io.py` | Support reflection save/load | Medium |
| `streamlit_app/utils/session_state.py` | Add reflection + decomposition keys | Small |
| `streamlit_app/pages/1_CONFIGURATION.py` | Reflection config UI | Medium |
| `streamlit_app/pages/2_CALIBRATION.py` | Reflection calibration workflow | Large |
| `streamlit_app/pages/3_PROCESSING.py` | Reflection processing + ellipsometry | Medium |
| `streamlit_app/pages/4_PARAMETERS.py` | Tabbed decompositions (major restructure) | Large |
| `streamlit_app/pages/5_ADVANCED.py` | Reflection advanced settings | Medium |
| `streamlit_app/pages/6_About.py` | Version update | Small |
| `streamlit_app/HOME.py` | Tutorial content update | Medium |
| `streamlit_app/components/sidebar.py` | Dual calibration status | Small |
| `streamlit_app/components/plots_plotly.py` | New plot functions | Large |
| `streamlit_app/utils/export.py` | New export formats | Medium |

### Files NOT Modified

| File | Reason |
|---|---|
| `ecm/core/ecm_matrices.py` | Identical between versions |
| `ecm/core/ecm_optimization.py` | Identical between versions |
| `ecm/core/modulation.py` | Identical between versions |
| `ecm/core/fourier.py` | Identical between versions |
| `ecm/core/sample_processing.py` | Identical between versions |
| `ecm/core/parameter_extraction.py` | Identical between versions |
| `ecm/io/sample_discovery.py` | Identical between versions |
| `ecm/utils/mueller_matrices.py` | Identical between versions |
| `ecm/postprocessing/lu_chipman.py` | Identical between versions |
| `streamlit_app/components/mueller_selector.py` | No change needed |
| `streamlit_app/components/file_browser.py` | No change needed |
| `streamlit_app/utils/styling.py` | No change needed |

---

## Appendix B — Session State Schema (Complete After Integration)

```python
{
    # ─── Core Transmission ───
    'config': ECMConfig | None,
    'is_calibrated': bool,
    'calibration_result': CalibrationResult | None,
    'calibration_diag': CalibrationDiagnostics | None,
    'processed_samples': dict[str, MuellerMatrixResult],
    'lu_chipman_results': dict[str, LuChipmanResult],

    # ─── Core Reflection (NEW) ───
    'refl_calibration_result': CalibrationResult | None,
    'refl_calibration_diag': ReflectionCalibrationDiagnostics | None,
    'refl_is_calibrated': bool,
    'refl_discovered_files': ReflectionCalibrationFiles | None,
    'refl_processed_samples': dict[str, MuellerMatrixResult],
    'refl_ellipsometry_results': dict[str, EllipsometricResult],
    'refl_current_sample': str | None,
    'refl_discovered_samples': SampleDiscoveryResult | None,
    'refl_selected_samples': list[str],
    'refl_view_mode': str,

    # ─── New Decompositions (NEW) ───
    'differential_results': dict[str, DifferentialDecompositionResult],
    'cloude_results': dict[str, CloudeDecompositionResult],
    'purity_results': dict[str, PurityResult],

    # ─── Configuration ───
    'data_dir_path': str,
    'output_dir_path': str,
    'reflection_dir_path': str,              # existing but now functional
    'refl_data_dir_path': str,               # NEW
    'refl_assets_dir_path': str,             # NEW (wafer characterization)
    'refl_aoi_deg': float,                   # NEW (default 65.0)
    'calibration_mode': str,                 # Transmission | Reflection | Tutorial Data
    'n_positions': int | None,
    'wl_min': float,
    'wl_max': float,
    'wl_ref': float,
    'n_wavelengths': int,
    'tutorial_mode': bool,
    'saving_disabled': bool,

    # ─── UI State ───
    'current_sample': str | None,
    'selected_elements': list[tuple[int, int]],
    'view_mode': str,
    'discovered_files': CalibrationFiles | None,
    'discovered_samples': SampleDiscoveryResult | None,
    'selected_samples': list[str],
    'decomp_selected_samples': list[str],
    'decomp_current_sample': str | None,
    'decomp_view_mode': str,
    'decomp_selected_elements': list[tuple[int, int]],

    # ─── Temporary Flags ───
    '_processing_done': bool,
    '_processing_count': int,
    '_processing_total': int,
    '_processing_errors': list[str],
    '_decomp_done': bool,
    '_decomp_count': int,
    '_decomp_total': int,
    '_decomp_errors': list[str],
    '_show_recal_dialog': bool,
    '_run_calibration': bool,
    '_show_csv_export': bool,
    '_show_decomp_csv_export': bool,
    '_confirm_reset': bool,
}
```

---

## Appendix C — Uncertainties & Assumptions

### Known Uncertainties

1. **`calibrate_reflection()` progress callback:** The ECM-PURE `calibrate_reflection()` function may or may not accept a `progress_callback` parameter. Check the function signature. If it doesn't support callbacks, either:
   - Add a callback parameter (preferred), or
   - Use `st.spinner()` instead of a progress bar.

2. **Reflection sample file discovery convention:** ECM-PURE's `discover_sample_files()` may expect samples in the same directory as calibration data, or in a subdirectory. Check `ecm/io/sample_discovery.py` to confirm the convention. The function likely searches for files that don't match any calibration keyword pattern.

3. **`calibration_io.py` backward compatibility:** The exact .npz save format may have changed between ECM v6.5 and v8.0.0. Before modifying `calibration_io.py`, load an existing v6.5 .npz file and document its structure. The v8.0 format must be able to load old files.

4. **`reflection_calibration.py` import paths:** The copied file may import `from ecm.utils.terminal_colors import ...` which only exists in ECM-PURE. Either copy `terminal_colors.py` or remove/replace those calls. Terminal colors are cosmetic only (console output formatting); removing them has no functional impact.

5. **Cloude decomposition data shapes:** The `M_components` array from `cloude_decomposition()` may be shaped as `(4, 4, 4, n_wl)` (4 component matrices of 4x4 each per wavelength). Verify the exact shape by reading the function and checking: is it `[n_components, 4, 4, n_wl]` or `[4, 4, n_components, n_wl]`? This affects how the plotting code indexes the array.

6. **Purity space theoretical bounds:** The purity space scatter plot should show theoretical bounds (the triangle/curve in P_S vs P_P space). The exact boundary equations should be taken from Gil & Ossikovski (2022) or from ECM-PURE's visualization code in `purity_plots.py`.

### Assumptions

1. **ECM-PURE modules are self-contained:** The copied modules (`tmm.py`, `ellipsometry.py`, `reflection_calibration.py`, decomposition modules) are assumed to have no circular dependencies or hidden state. This is verified by the ECM-PURE test suite passing.

2. **Streamlit session state is sufficient:** All intermediate results fit in memory via session state. For very large datasets (many wavelengths × many samples), this may become an issue. Not addressed in this spec.

3. **No new Python dependencies:** ECM-PURE v8.0.0 uses only numpy, scipy, and matplotlib (which are already in MMForge's requirements). The TMM module and decomposition modules use numpy and scipy only. No new pip packages are needed.

4. **Plotting library remains Plotly:** All new plots use the same Plotly-based approach as existing MMForge plots. ECM-PURE's matplotlib-based visualization modules are NOT used in the GUI.

---

*End of specification.*
