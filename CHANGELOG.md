# Changelog

All notable changes to MMForge will be documented in this file.

---

## [v2.1.0] - 2026-08-13

Still built on **ECM-Calibration v8.0.0**. No changes to the algorithms or
to any numerical result. This release is about getting MMForge running on
a normal computer without a terminal, an IDE, or any knowledge of Python.

### Added
- **Platform launchers.** `MMForge.bat` (Windows) and `MMForge.command`
  (macOS) start the application by double-click. Both locate the project
  from their own file path, so the working directory is irrelevant, and
  both fall back to a location recorded at install time if the file is
  copied elsewhere. Neither activates an environment: they call the
  virtual environment's own Python directly, which is equivalent and
  cannot pick up the wrong interpreter.
- **One-time installers.** `Install-Windows.bat` and
  `Install-macOS.command` create `.venv`, install `requirements.txt`,
  verify every import, and offer a desktop entry. Re-running them is the
  documented fix for a broken installation; `--recreate` rebuilds the
  environment from scratch.
- **Desktop integration.** On Windows, a Desktop shortcut carrying
  `tools/mmforge.ico` (a shortcut rather than a copy: Windows cannot put
  an icon on a `.bat`, and the `.bat` must stay next to the project). On
  macOS, `~/Applications/MMForge.app`, generated locally so Gatekeeper
  does not refuse it, with an icon built by `sips` and `iconutil`.
- **Shared launcher core** in `tools/`: `launch_mmforge.py` names any
  missing dependency instead of raising a traceback, picks a free port
  between 8501 and 8520, binds `127.0.0.1` (which also avoids the Windows
  Firewall prompt), and opens the browser once the server answers.
  `setup_env.py` rejects a too-old Python and the Microsoft Store
  `python.exe` stub, and warns when the project sits in a cloud-synced
  folder.
- **README.md** with self-contained, step-by-step Windows and macOS
  sections, a troubleshooting list, and developer notes.
- **LICENSE.** The repository is public but previously had no licence
  file.
- **`.gitattributes`** pinning `.bat`/`.cmd`/`.ps1` to CRLF and
  `.command`/`.sh` to LF, so one branch can ship working launchers for
  both platforms. Without it a checked-out `.command` fails with
  `bad interpreter: /bin/bash^M`.

### Fixed
- **Results were written to the current working directory.**
  `output_dir_path` is initialised to `''` in `SESSION_KEYS`, so
  `st.session_state.get('output_dir_path', <default>)` always returned
  `''` and the intended fallback was dead code. `Path('')` resolves to
  `.`, so every save landed wherever the app happened to be started
  from — which is how loose `.npz` and `.csv` exports ended up among the
  source files. MMForge now defaults to `~/MMForge_output`, pre-fills the
  Output Directory box, and treats a blank box as "use the default".
- **The Streamlit lower bound was wrong.** `2_CALIBRATION.py` uses
  `st.dialog`, added in Streamlit 1.37, but `requirements.txt` allowed
  1.30. A fresh install could resolve to a version without it.
- **First launch could hang forever.** On a computer where Streamlit had
  never run, it stops and asks for an e-mail address before starting.
  The launcher now runs Streamlit headless, which skips that prompt, and
  opens the browser itself once `/_stcore/health` answers.

### Changed
- Every dependency has a tested upper bound. Verified working set:
  Streamlit 1.61.1, numpy 2.2.6, scipy 1.15.3, plotly 6.9.0, pandas
  2.3.3, matplotlib 3.10.9. Streamlit is capped below 1.62 while the GUI
  still passes `use_container_width`, which Streamlit has deprecated in
  favour of `width`; that rename is deferred to a later release.
- Streamlit usage telemetry disabled (`gatherUsageStats = false`).
- `pyproject.toml`: version 6.5.5 → 8.0.0 to match `ecm/__init__.py`,
  `requires-python` raised to 3.10, real project URLs, dependency upper
  bounds, and a note that it versions the ECM library rather than the
  GUI. MMForge and ECM-Calibration are versioned independently.

### Removed
- `plans/` (design spec, 56 KB) and `data/test/` (31 MB of measurements
  and reference exports). Neither is referenced by any code, config or
  script, and there is no test suite that consumes them. Both remain in
  git history. `data/assets/` and `data/tutorial/` are untouched — the
  reflection workflow reads the former at runtime and Tutorial mode
  needs the latter.
- `streamlit_app/jupy-test.ipynb`, a one-cell scratch notebook.
- The accidentally committed `.claude/worktrees` marker; `.claude/` is
  now ignored.

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
