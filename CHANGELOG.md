# Changelog

All notable changes to MMForge will be documented in this file.

---

## [v2.0] - 2026-05-14

Built on **ECM-Calibration v8.0.0**. Major release adding reflection-mode
calibration end-to-end, ellipsometric parameter extraction, three new
Mueller-matrix decompositions, and a substantial GUI cleanup.

### Added
- **Reflection-mode calibration** (oblique incidence). Calibration uses
  two reference wafers (25 nm and 10 nm SiO₂/Si) plus two
  polarizer-bearing measurements. Includes a physics-informed TMM step
  that fits wafer thicknesses (d₁, d₂) and an AOI correction (δAOI) and
  refines the calibration with tighter wafer Ψ/Δ bounds. New ECM-PURE
  modules: `ecm/core/reflection_calibration.py`, `ecm/core/tmm.py`,
  `ecm/core/ellipsometry.py`.
- **Ellipsometric parameter extraction** for reflection samples:
  Ψ, Δ, NCS, pseudo-dielectric function ⟨ε⟩, pseudo-n, pseudo-k.
  Computed automatically after each reflection-mode sample processing.
- **Three new decompositions** on the PARAMETERS page, plus the existing
  Lu-Chipman:
  - **Differential (Minkowski)** — L_m, L_u, M_m, M_u
  - **Cloude spectral** — coherency matrix eigendecomposition into four
    Mueller components weighted by eigenvalues λ₀…λ₃
  - **Purity space** — P_P, P_S, P_Δ indices with the (P_S, P_P)
    diagram (boundary curves per Gil & Ossikovski 2022)
- **Auto-detection of angular positions** from binary file dimensions.
  `cfg.acquisition.n_angular_positions` defaults to `None` and is set by
  the backend at calibration time.
- **Mode-aware save/load** — the same `.npz` format covers both
  transmission and reflection calibrations. Loading auto-dispatches
  session state by mode.
- **Step + per-step progress display** during calibration. The
  reflection workflow shows `Steps [k/9] completed.` + `Step [n/9]:
  <name>` + a per-stage progress bar, with separate progress for the
  multi-start re-optimization phase.
- **Dual-mode sidebar status** — independent green/yellow/red indicators
  for transmission and reflection calibration state.
- Unified PARAMETERS layout: every decomposition tab has the same
  "Decomposed Matrices" roller (View mode: 4x4 Grid / Selected Elements
  / Compare Samples).

### Changed
- **"Combined" mode removed.** Valid calibration modes are now
  Transmission, Reflection, and Tutorial Data only.
- **WAFER25NM / WAFER10NM terminology** replaces "reflector 1" /
  "reflector 2" throughout file discovery, config, GUI, and docs.
- ECM library updated to v8.0.0 (was 6.5.5).
- Calibration file format bumped to **1.1.0** (backward compatible: old
  1.0.0 transmission files still load).
- Wafer characterization (Woollam Ψ/Δ and Rp/Rs files) and TMM reference
  n/k data live in the bundled `data/assets/` directory — the user no
  longer manages them via the GUI.
- AOI default is **70°** (locked behind an "I understand the risks"
  checkbox on the Configuration page).
- Solver moved to `solve_A_reflection` for the reflection calibration's
  A-matrix recovery.

### Removed
- The **ADVANCED page** and the corresponding session-state overrides
  (`refl_opt_*`, `refl_tmm_*`). Reflection optimization and TMM fit now
  use the ECM-PURE defaults baked into `ReflectionOptConfig` and
  `ThicknessFitConfig`.
- "Diattenuation & Polarizance Vector Magnitudes" expander from the
  Purity tab.

### Fixed
- **Streamlit widget-state cleanup gotcha** — session-state keys bound
  to widgets (`calibration_mode`, `wavelength_range`, `refl_aoi_deg`)
  now survive page navigation. The persist loop in
  `initialize_session_state()` only re-binds keys explicitly listed in
  `SESSION_KEYS`, avoiding `StreamlitValueAssignmentNotAllowedError` on
  transient widget keys (buttons, inner checkboxes).
- Reflection sample discovery excludes wafer/POL calibration files
  (`_WAFER25NM_ECM_`, `_WAFER10NM_ECM_`, `_WAFER25NM_POL_BEFORE_ECM_`,
  `_WAFER25NM_POL_AFTER_ECM_`).
- `_search_for_file()` produces a clear "Hint: search is non-recursive
  — try one of these subdirectories" message when files are missing.
- Cross-mode re-calibration triggers a dialog warning that the entire
  session (both modes' calibrations + processed samples + all four
  decomposition result dicts) will be reset on Proceed.

### Notes
- New tests / hardware compatibility: validated against the custom
  Mueller-matrix spectroscopic ellipsometer at the Department of Optics,
  Palacký University Olomouc.

---

## [v1.2] - 2026-02-09

### Added
- **Tutorial Data mode**: Bundled example calibration and sample data for learning the workflow
- New "Tutorial Data" option in Calibration Mode selector

### Changed
- Data Paths inputs disabled in Tutorial mode (auto-configured)
- Save/Load/Export buttons disabled in Tutorial mode
- Session state keys: `tutorial_mode`, `saving_disabled`

### Notes
- Tutorial data includes: calibration files + HWP and QWP samples
- Perfect for first-time users to explore without real measurements

---

## [v1.1] - 2026-02-09

### Added
- **Auto-detect rotator steps**: Rotator steps (n_positions) are now automatically detected from calibration file dimensions during file discovery
- **Calibration Mode selector**: New mode selector (Transmission/Reflection/Combined) replaces manual "Acquisition Settings" input
- **Changelog expander**: About page now includes version history

### Changed
- Removed manual "Angular Positions" input from Configuration page
- File discovery now validates dimension consistency across all calibration files

### Notes
- Reflection and Combined modes are placeholders for future releases
- ECM calibration algorithm unchanged

---

## [v1.0] - 2026-02-01

### Initial Release
- ECM calibration for Mueller matrix spectroscopic polarimetry
- Transmission mode support
- Lu-Chipman polar decomposition
- Interactive Plotly visualizations
- Save/load calibration results
