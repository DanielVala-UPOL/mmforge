# MMForge — Developer / Claude Primer

This document is the starting point for anyone — human or AI — picking up
work on MMForge. It explains the architecture, the conventions, and the
non-obvious pitfalls you will run into.

> **Version target:** MMForge **v2.1.0**, built on **ECM-Calibration v8.0.0**.
> If the version numbers in [`ecm/__init__.py`](ecm/__init__.py) or
> [`streamlit_app/components/sidebar.py`](streamlit_app/components/sidebar.py)
> have drifted from those, the doc is stale — update it before doing
> serious work.

---

## What MMForge is

A Streamlit GUI on top of the **ECM** (Eigenvalue Calibration Method)
algorithm for Mueller-matrix spectroscopic polarimetry. The instrument
the GUI is hard-coded for is the dual-rotating-compensator polarimeter
at the Department of Optics, Palacký University Olomouc. Two operating
modes:

- **Transmission** — straight-through configuration; calibration uses
  air (ST), two linear polarizers (P0, P45) and one or two Fresnel
  prisms (FP1 at 90°, optional FP2 at 45°).
- **Reflection** — oblique-incidence configuration (default AOI 70°);
  calibration uses two reference SiO₂/Si wafers (25 nm and 10 nm bare)
  plus two polarizer-bearing measurements (POL_BEFORE, POL_AFTER) on the
  25 nm wafer. Includes a physics-informed TMM step that fits the actual
  oxide thicknesses and corrects the AOI.

---

## Repository layout

```
MMForge/
├── ecm/                          # algorithms (the "ECM library")
│   ├── config/ecm_config.py      # ECMConfig + reflection sub-configs
│   ├── core/
│   │   ├── transmission_calibration.py
│   │   ├── reflection_calibration.py    ← multi-stage, has step_callback
│   │   ├── tmm.py                       ← Transfer Matrix Method
│   │   ├── ellipsometry.py              ← Ψ, Δ, ⟨ε⟩, ⟨n⟩, ⟨k⟩
│   │   ├── ecm_solver.py                ← solve_W, solve_A, solve_A_reflection
│   │   ├── ecm_matrices.py              ← H, K matrices
│   │   ├── ecm_optimization.py
│   │   ├── modulation.py
│   │   ├── fourier.py
│   │   ├── sample_processing.py         ← mode-agnostic process_sample
│   │   ├── parameter_extraction.py
│   │   └── file_discovery.py            ← keyword-based file matching
│   ├── postprocessing/
│   │   ├── lu_chipman.py
│   │   ├── differential_decomposition.py
│   │   ├── cloude_decomposition.py
│   │   ├── purity_space.py
│   │   └── _validation.py
│   ├── io/
│   │   ├── calibration_io.py    ← save/load .npz, version 1.1.0
│   │   └── sample_discovery.py  ← keyword-based exclusion of cal files
│   ├── utils/
│   │   ├── io.py                ← load_spectral_data, detect_angular_positions
│   │   ├── mueller_matrices.py  ← polarizer, retarder, reflector, …
│   │   └── terminal_colors.py
│   └── visualization/           ← matplotlib plots (notebook-oriented)
├── streamlit_app/                # GUI
│   ├── HOME.py
│   ├── pages/
│   │   ├── 1_CONFIGURATION.py
│   │   ├── 2_CALIBRATION.py     ← per-mode workflows + dialogs
│   │   ├── 3_PROCESSING.py
│   │   ├── 4_PARAMETERS.py      ← 4 decomposition tabs, unified layout
│   │   └── 5_About.py
│   ├── components/
│   │   ├── sidebar.py           ← dual-mode status + Reset Session
│   │   ├── plots_plotly.py      ← all Plotly figures (the GUI's plot lib)
│   │   ├── mueller_selector.py  ← 4×4 element-picker widget
│   │   └── file_browser.py      ← directory text input
│   └── utils/
│       ├── session_state.py     ← SESSION_KEYS + persist loop (see below)
│       │                           + DEFAULT_OUTPUT_DIR / get_output_dir()
│       ├── styling.py
│       └── export.py
├── tools/                        # launcher + installer internals
│   ├── launch_mmforge.py         ← shared: port, checks, starts Streamlit
│   ├── setup_env.py              ← shared: venv + pip + self-check
│   ├── create_windows_shortcut.ps1
│   ├── create_macos_app.sh       ← builds ~/Applications/MMForge.app
│   ├── mmforge.ico               ← Windows shortcut icon
│   └── mmforge.png               ← source for the macOS .icns
├── MMForge.bat                   # Windows: double-click to run
├── MMForge.command               # macOS:   double-click to run
├── Install-Windows.bat           # Windows: one-time setup
├── Install-macOS.command         # macOS:   one-time setup
├── README.md                     # the user-facing install story
├── LICENSE
├── .gitattributes                # CRLF for .bat, LF for .command
└── data/
    ├── assets/                   ← BUNDLED: Woollam Ψ/Δ + Rp/Rs files,
    │                                BlackComet wavelengths, FP1/FP2 char,
    │                                TMM n/k (Si, SiO2, Interlayer), …
    └── tutorial/                 ← bundled transmission demo data
```

`ECM-PURE` is the upstream algorithm source at
`/Users/danielvala/Documents/PYTHON/VS/ECM/ECM-PURE` (also mirrored at
`…/CONVERSION/ECM-PURE`). The `ecm/` tree here was lifted from that
project and adapted only at the integration layer; **algorithm code
should track ECM-PURE upstream verbatim wherever possible**.

---

## Key concepts

### 1. Two operating modes, two parallel state trees

The Streamlit session state has parallel keys for transmission and
reflection:

```
calibration_result, calibration_diag, is_calibrated,
processed_samples, lu_chipman_results
  vs.
refl_calibration_result, refl_calibration_diag, refl_is_calibrated,
refl_processed_samples, refl_ellipsometry_results,
refl_discovered_files, refl_discovered_samples, refl_selected_samples
```

Anywhere a page touches "the calibration" or "the samples", it must
branch on `st.session_state['calibration_mode']`. Helpers:

- `is_calibrated()` / `is_reflection_calibrated()` / `has_any_calibration()`
- `get_calibration_result()` / `get_reflection_calibration_result()`
- `get_active_processed_samples()` — mode-aware (pages 4 and beyond)
- `clear_calibration()` / `clear_reflection_calibration()`
- `full_session_reset()` — clears *both* modes plus all decomposition
  results, but preserves config (paths, AOI, wavelength range)

### 2. ECMConfig has a `mode` field that drives the backend

```python
cfg.mode = 'transmission'   # or 'reflection'
```

The mode is set by `build_config_from_session()` /
`build_reflection_config_from_session()` in
[`streamlit_app/pages/2_CALIBRATION.py`](streamlit_app/pages/2_CALIBRATION.py).

### 3. WAFER terminology

The 25 nm and 10 nm reference wafers are called **WAFER25NM** and
**WAFER10NM** everywhere — file keywords, config field names, GUI labels,
docs. Don't introduce "reflector 1 / reflector 2" terminology — that's
what ECM-PURE migrated *away* from when it hit v8.0.0.

Keyword patterns (case-insensitive):
- `_DARK_ECM_` — background (both modes)
- `_ST_ECM_`, `_P0_ECM_`, `_P45_ECM_`, `_RET90_FP1_ECM_`,
  `_RET45_FP2_ECM_` — transmission
- `_WAFER25NM_ECM_`, `_WAFER25NM_POL_BEFORE_ECM_`,
  `_WAFER25NM_POL_AFTER_ECM_`, `_WAFER10NM_ECM_` — reflection
- The `_WAFER25NM_ECM_` and `_WAFER10NM_ECM_` matches exclude `_POL_`
  variants via `exclude_pattern` in `_search_for_file`.

### 4. Bundled vs user-supplied data

- **`data/assets/`** — bundled with the app; user never touches it.
  Contains: BlackComet wavelength table, FP1/FP2 retardance, **wafer Ψ/Δ
  and Rp/Rs files**, TMM n/k references (Si, SiO2, Interlayer), reference
  Mueller matrices for sample wafers.
- **User's data dir** — contains only the user's `.bin` measurement
  files (DARK + calibration measurements + samples).

`build_reflection_config_from_session()` hard-codes
`cfg.paths.assets_dir = <project>/data/assets/` so the user can't
accidentally point it elsewhere.

### 5. Auto-detection of angular positions

`cfg.acquisition.n_angular_positions` defaults to `None`. The backend
unconditionally calls `detect_angular_positions()` at the start of each
calibration, infers the count from file size, and writes it back to the
config. Setting it manually has no effect.

### 6. Mode-aware save/load

`save_calibration()` and `load_calibration()` auto-detect the mode from
`cfg.mode` / `metadata.mode`. The `.npz` format is **1.1.0**, backward-
compatible with 1.0.0 transmission files (fallbacks for missing
`n_angular_positions`).

### 7. Progress reporting for long calibrations

The backend calibration functions take **two** optional callbacks:

```python
calibrate_transmission(cfg, progress_callback=..., step_callback=...)
calibrate_reflection(cfg, progress_callback=..., step_callback=...)
```

- `step_callback(step_idx, total_steps, label)` — fires at the start of
  each major stage (`[1/9] Discovering…`, `[2/9] Loading wavelengths…`,
  etc.). The GUI uses this to update a "Steps [k/total] completed" line
  + a "Step [n/total]: <label>" line and reset the inner progress bar.
- `progress_callback(current_wl, total_wl, eigenvalue_ratio)` — fires
  per-wavelength during the heavy stages (wafer optimization, refined
  optimization, multi-start re-optimization, final K/W/A solve). The
  GUI uses this for the inner percentage bar.

Multi-start re-optimization fires `step_callback` again with the *same*
parent step index but a different label (e.g. "Multi-start
re-optimization (NN difficult wavelengths)") — implemented via a
`substep_callback` parameter on `optimize_reflection_characterization()`
plus a closure in `calibrate_reflection`. The GUI's `last_parent_step`
guard makes sure these substeps don't bump the completed-counter.

### 8. The four decompositions and their data shapes

| Decomposition | Result class | Key fields and shapes |
|---|---|---|
| Lu-Chipman | `LuChipmanResult` | `M_D, M_R, M_Delta: (4,4,n_wl)`; scalars `D, DI, R_deg, R_rad, R_waves, psi_deg, chi_deg: (n_wl,)` |
| Differential | `DifferentialDecompositionResult` | `L_m, L_u, M_m, M_u: (4,4,n_wl)` |
| Cloude | `CloudeDecompositionResult` | `eigenvalues: (4, n_wl)`; `M_components: (4, 4, 4, n_wl)` (first axis = component index 0..3); `H: (4, 4, n_wl) complex` |
| Purity | `PurityResult` | `P_P, P_S, P_Delta: (n_wl,)`; `D_vec, P_vec: (3, n_wl)` |

`PARAMETERS` page renders each decomposition in a top-level tab with a
**unified roller layout**:

- "Decomposed Matrices" expander — View mode radio (4x4 Grid / Selected
  Elements / Compare Samples), sample selector, then one tab per matrix.
  Implemented via the shared `_render_matrix_roller()` helper in
  `4_PARAMETERS.py`.
- Optional "Decomposition Parameters" expander — used by Lu-Chipman
  (D / DI / R / eigenmodes) and Cloude (eigenvalue spectrum + |H_ij|).
- Optional "Summary Table" — Lu-Chipman only.
- Per-tab Save (.npz) and Export (.csv) buttons at the bottom.

---

## The Streamlit widget-state gotcha (this caught us twice)

Streamlit multi-page apps **garbage-collect session-state entries that
are bound to widgets** on a page once that page is unmounted. If you do:

```python
mode = st.selectbox("Mode", options=opts, key="calibration_mode")
```

then navigate to a different page, `st.session_state['calibration_mode']`
is wiped — the selectbox reverts to its default on return.

**Fix** — at the top of every page, re-bind the keys we care about so
Streamlit considers them "non-widget-owned":

```python
# inside initialize_session_state()
for k in SESSION_KEYS:
    if k in st.session_state:
        st.session_state[k] = st.session_state[k]
```

Three subtle but important rules:

1. The re-bind loop iterates **only over `SESSION_KEYS`** — the keys we
   explicitly manage. Iterating over *all* of `st.session_state` triggers
   `StreamlitValueAssignmentNotAllowedError` on transient widget keys
   (buttons, internal checkboxes inside `mueller_element_selector`,
   `sidebar_confirm_reset`, etc.).
2. Widgets whose `key=` is in `SESSION_KEYS` must NOT pass `value=` /
   `index=` parameters, or Streamlit warns about "default value but also
   had its value set via Session State". The widget reads from
   pre-initialized session state instead.
3. `full_session_reset()` (and the sidebar Reset button) only deletes
   `SESSION_KEYS` entries, never widget-bound keys.

If you see widget state reverting on navigation, or a
`StreamlitValueAssignmentNotAllowedError`, it's almost certainly one of
these three rules being violated.

---

## How the launchers work (v2.1.0)

Users are not expected to touch a terminal. Four files at the repository
root cover both platforms, and all four are thin — the real logic lives
in `tools/` and is shared.

```
Install-Windows.bat  ─┐                      ┌─ tools/create_windows_shortcut.ps1
                      ├─→ tools/setup_env.py ─┤
Install-macOS.command ┘                      └─ tools/create_macos_app.sh

MMForge.bat          ─┐
                      ├─→ tools/launch_mmforge.py ─→ streamlit run HOME.py
MMForge.command      ─┘
```

Design rules, each of which exists for a reason:

1. **Never activate an environment.** The launchers call
   `.venv/Scripts/python.exe` or `.venv/bin/python` by absolute path.
   That is equivalent to activation and cannot pick up the wrong
   interpreter. The old lab `.bat` spent half its length hunting for
   `conda.bat`; none of that is needed.
2. **Self-location, not configuration.** `%~dp0` and
   `${BASH_SOURCE[0]}` give the project root. There is no path for the
   user to edit. A recorded fallback
   (`%LOCALAPPDATA%\MMForge\install_path.txt`,
   `~/Library/Application Support/MMForge/install_path`) covers a
   launcher copied out of the project.
3. **Shortcuts, not copies.** The Desktop entry on Windows is a `.lnk`
   and the macOS entry is an `.app` in `~/Applications`. Both point back
   at the in-project launcher. Windows cannot put an icon on a `.bat`,
   and a copied script loses its self-location.
4. **The macOS `.app` is generated, never committed.** An `.app` that
   arrives inside a downloaded ZIP carries a quarantine flag and
   Gatekeeper refuses it as "damaged". One built locally does not.
5. **Streamlit runs headless and we open the browser.** Non-headless
   mode stops on a first-run e-mail prompt on any machine where
   Streamlit has never run, and waits forever. `launch_mmforge.py`
   passes `--server.headless true`, polls `/_stcore/health`, then calls
   `webbrowser.open`.
6. **Bind `127.0.0.1`.** No Windows Firewall prompt, and the app is not
   exposed on the lab network. Change `SERVER_ADDRESS` in
   `launch_mmforge.py` if LAN access is ever wanted.
7. **`.gitattributes` is load-bearing.** `.bat`/`.cmd`/`.ps1` are pinned
   to CRLF and `.command`/`.sh` to LF. Without it a checked-out
   `.command` dies with `bad interpreter: /bin/bash^M`. This is why both
   platforms live on one branch instead of two — the only genuinely
   platform-specific problem is line endings, and one file solves it.

If you add a file that either platform executes, add its extension to
`.gitattributes` and set the exec bit with
`git update-index --chmod=+x`.

---

## How to extend

### Add a new decomposition method

1. **Backend**: add `ecm/postprocessing/<your_decomp>.py` with a
   `@dataclass class YourDecompResult` and a `your_decomposition(M)`
   function. Re-export from `ecm/postprocessing/__init__.py`.
2. **Session state**: add `'your_decomp_results': {}` to `SESSION_KEYS`
   in `streamlit_app/utils/session_state.py`. Add it to
   `full_session_reset()`.
3. **Plots**: add the figure functions to
   `streamlit_app/components/plots_plotly.py`, reusing
   `apply_common_styling`, `PRIMARY_COLOR`, `TRACE_COLORS`,
   `FONT_SIZE_*`. For matrix tabs you may not need a new function — the
   existing `create_mueller_matrix_plot` works for any 4×4×n_wl array.
4. **PARAMETERS page**: add a new top-level tab in `4_PARAMETERS.py`'s
   `main()`. Inside the tab function:
   - Reuse `_generic_sample_selection('your_decomp')` for sample picking.
   - Reuse `_run_button_block` + `_run_generic_decomp` for the Run
     button + execution.
   - Reuse `_render_matrix_roller()` for the "Decomposed Matrices"
     expander.
   - Add per-tab save/export helpers (see `_save_differential` etc. for
     templates).

### Add a new calibration mode

If a third mode is needed, follow the reflection-mode pattern:

1. New file `ecm/core/<mode>_calibration.py` with a top-level
   `calibrate_<mode>(cfg, progress_callback=None, step_callback=None)`
   function returning `(CalibrationResult, <Mode>Diagnostics)`.
2. New config dataclass(es) in `ecm/config/ecm_config.py`; add a field
   to `ECMConfig` and to `_from_dict`'s `nested_fields`.
3. New file-discovery function in `ecm/core/file_discovery.py`.
4. Update `discover_sample_files()` in `ecm/io/sample_discovery.py` —
   add this mode's calibration keywords to `CALIBRATION_KEYWORDS` so
   they get excluded from sample discovery.
5. Update `calibration_io.py`'s save_dict and load branches to handle
   the new diagnostics class.
6. In the GUI: add parallel session-state keys (`<mode>_calibration_*`),
   parallel helpers in `session_state.py`, parallel `build_<mode>_config_from_session`
   and `run_<mode>_workflow` in `2_CALIBRATION.py`, mode branching in
   `3_PROCESSING.py`'s `_active_state()`, mode branching in
   `4_PARAMETERS.py`'s active-cal helpers, status row in
   `sidebar.py:_render_status_row()`.

### Change the default AOI / Woollam thickness ranges

- AOI default: `'refl_aoi_deg': 70.0` in `SESSION_KEYS`
  (`streamlit_app/utils/session_state.py`).
- Woollam thickness ranges: `WOOLLAM_D1_RANGE` and `WOOLLAM_D2_RANGE`
  constants inside `_display_reflection_physics()` in
  `streamlit_app/pages/2_CALIBRATION.py`.

---

## Test data

- `data/tutorial/` — bundled transmission demo (HWP, QWP samples). Used
  for tutorial mode and as a backend regression fixture. Median
  λ₁₆/λ₁₅ ≈ 2.8e-04 on this data; if a change pushes it materially
  higher, something regressed.
- `data/test/` **was removed in v2.1.0** (31 MB of real measurements and
  reference exports). Nothing referenced it and there is no test suite.
  It is still in git history if a regression fixture is ever wanted:
  `git show v2.0.1:data/test/...`. Reflection calibration on that set
  took ~1–2 min.

Quick smoke test (no Streamlit needed):

```python
import sys; sys.path.insert(0, '<project_root>')
from ecm.config import ECMConfig
from ecm.core import calibrate_transmission
import numpy as np

cfg = ECMConfig()
cfg.paths.data_dir = Path('data/tutorial')
cfg.paths.calibration_transmission_dir = Path('data/tutorial')
cfg.output.verbosity = 0
result, diag = calibrate_transmission(cfg)
assert cfg.acquisition.n_angular_positions == 96
assert np.median(diag.eigenvalue_ratio) < 1e-3
print('OK')
```

---

## Common pitfalls (saved you a debugging session at least once each)

1. **An editable install of `ecm-polarimetry` may shadow the worktree.**
   `pip show ecm-polarimetry` might point to a different path. If your
   imports are picking up ECM-PURE instead of this repo's `ecm/`, add
   `sys.path.insert(0, <worktree>)` at the top of test scripts.
2. **`python /tmp/script.py` doesn't auto-add the project root to
   sys.path.** Streamlit pages do it via
   `sys.path.insert(0, str(Path(__file__).parent.parent.parent))`. For
   ad-hoc scripts, do the same.
3. **`tqdm` output and `print()` calls inside the backend appear in
   the Streamlit *terminal*, not the browser.** Use the
   `progress_callback` / `step_callback` for in-app feedback.
4. **Streamlit assigns to widget-bound keys are rejected.** See the
   widget-state gotcha section above.
5. **`pandas` is in `requirements.txt`** but not always in your local
   Python env — CSV-writing code paths import it lazily and fail loudly
   in dev. Use `numpy.savetxt` for ad-hoc tests if needed.
6. **Reflection sample discovery used to leak calibration files** —
   make sure any new reflection-mode calibration keyword is added to
   `CALIBRATION_KEYWORDS` in `ecm/io/sample_discovery.py`.
7. **`st.session_state.get(key, default)` never returns your default for
   a key listed in `SESSION_KEYS`.** `initialize_session_state()` creates
   every key, so `.get()` finds it and returns its value — including `''`.
   This silently broke every output path until v2.1.0: `Path('')` is `.`,
   so saves landed in the working directory. Use an explicit helper like
   `get_output_dir()` that treats blank as "unset".
8. **Streamlit's first-run e-mail prompt blocks startup.** On a machine
   where Streamlit has never run, non-headless mode stops and waits for
   input. Always pass `--server.headless true` from a launcher.
9. **Check the Streamlit floor before using a new `st.*` API.**
   `st.dialog` needs 1.37; `requirements.txt` allowed 1.30 for months.
   The pinned range there is the contract — update it in the same commit
   as the API use.

---

## Reference papers

- Compain et al., *Appl. Opt.* **38**, 3490–3502 (1999) — ECM algorithm.
- Rosales et al., *Opt. Lett.* **49**, 1165–1168 (2024) — extended ECM
  for overdetermined polarimeters.
- Lu & Chipman, *J. Opt. Soc. Am. A* **13**, 1106–1113 (1996) —
  polar decomposition.
- Gil & Ossikovski, *Polarized Light and the Mueller Matrix Approach*,
  2nd ed., CRC Press (2022) — differential, Cloude, purity-space
  decompositions; (P_S, P_P) boundary curves.

---

*Last updated: 2026-08-13 (MMForge v2.1.0).*
