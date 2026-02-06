# ECM Polarimetry GUI - Implementation Progress

**Project**: Streamlit GUI for ECM Mueller Matrix Polarimeter Calibration
**Author**: Daniel Vala
**Last Updated**: February 2026

---

## COMPLETION STATUS

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0 | COMPLETED | Pre-implementation debugging (4 bugs fixed) |
| Phase 1 | COMPLETED | Project setup & basic layout |
| Phase 2 (UI/UX) | COMPLETED | UI/UX refinement (icons removed, file browser updated) |
| Phase 3 | COMPLETED | Calibration page with full ECM integration |
| Phase 3.1 | COMPLETED | UI/UX polish & bug fixes |
| Phase 4 | COMPLETED | Sample processing page |
| Phase 4.1 | COMPLETED | Bug fixes and UI cleanup |
| Phase 4.2 | COMPLETED | Minor plot styling fixes |
| Phase 4.3 | COMPLETED | Minor UI/plot fixes |
| Phase 4.4 | COMPLETED | Final quality display fixes |
| Phase 5 | COMPLETED | Lu-Chipman decomposition page |
| Phase 6 | COMPLETED | Polish & enhancements |
| Phase 7 | NOT STARTED | Testing, documentation & deployment |

---

## DETAILED PROGRESS

### Phase 0: Pre-Implementation Debugging - COMPLETED

**All 4 bugs fixed and verified with pytest (383 tests pass):**

- [x] **BUG 1**: Font glyph warnings - Replaced Unicode subscripts with matplotlib mathtext (`r'$W_{11}$'` format)
- [x] **BUG 2**: Figures not displaying - Added `--show-plots` flag to calibrate_transmission.py
- [x] **BUG 3**: Output files wrong directory - Changed default to `Path.cwd() / 'calibration_output'`
- [x] **BUG 4**: Quality threshold "Excellent" - Updated to < 1e-4, added Marginal category

**Files modified:**
- `ecm/diagnostics/calibration_diagnostics.py`
- `ecm/visualization/mueller_plots.py`
- `ecm/visualization/decomposition_plots.py`
- `ecm/config/ecm_config.py`
- `ecm/core/transmission_calibration.py`
- `scripts/calibrate_transmission.py`

---

### Phase 1: Project Setup & Basic Layout - COMPLETED

**Created streamlit_app/ directory structure:**

```
streamlit_app/
├── HOME.py                     # Home page (MMForge - HOME)
├── pages/
│   ├── 1_CONFIGURATION.py      # Configuration page
│   ├── 2_CALIBRATION.py        # Calibration page
│   ├── 3_PROCESSING.py         # Sample processing page
│   ├── 4_PARAMETERS.py         # Lu-Chipman decomposition
│   └── 5_ADVANCED.py           # Advanced analysis (placeholder)
├── components/
│   ├── __init__.py
│   ├── sidebar.py              # Status indicator (🟢/🔴)
│   ├── file_browser.py         # Path input with validation (editable text)
│   ├── plots_plotly.py         # Interactive Plotly plots
│   └── mueller_selector.py     # 4x4 element selector
├── utils/
│   ├── __init__.py
│   ├── session_state.py        # Session state management
│   └── export.py               # PNG/CSV export functions
└── assets/
    └── style.css               # Custom styling
```

**requirements-gui.txt created with:**
- streamlit>=1.30.0
- plotly>=5.18.0
- streamlit-antd-components>=0.3.0
- pandas>=2.0.0
- watchdog>=3.0.0
- kaleido>=0.2.1
- openpyxl>=3.1.0

**Note**: `streamlit-file-browser` was removed after Phase 3 bug fixes (didn't work correctly for folder selection).

---

### Phase 2 (UI/UX Refinement) - COMPLETED

Based on `UI_UX_PHASE2_INSTRUCTIONS.md`:

- [x] **Removed all emoji icons** from all pages (except 🟢/🔴 status indicators in sidebar)
- [x] **Renamed 4_Lu_Chipman.py** to **4_Parameters.py** (title: "Parameters Extraction")
- [x] **Updated file_browser.py** to use `streamlit-file-browser` for web-based folder selection
- [x] **Removed sections**: Current Status on home, Quick Actions, Config Summary, navigation buttons
- [x] **Added wavelength range slider** (replaced min/max inputs)
- [x] **Hardcoded reference wavelength** internally (633nm, removed from UI)
- [x] **Sticky header** - Created but then REMOVED (didn't work as expected)

**Note**: Sticky header was removed per user request. Default Streamlit header (hamburger menu) is used.

---

### Phase 3: Calibration Page - COMPLETED (with bug fixes)

Full ECM calibration integration implemented:

- [x] **File Discovery** with FP2 auto-detection
  - Uses `discover_calibration_files(cfg)` from `ecm.core.file_discovery`
  - Displays found files with status icons
  - Shows FP2 detection status

- [x] **Run Calibration** with progress bar
  - Connects to `calibrate_transmission(cfg, progress_callback)`
  - Progress bar updates during calibration
  - Quality summary displayed after completion

- [x] **Quality Breakdown Visualization**
  - Metrics: total wavelengths, mean/median ratio, excellent %
  - Table with counts and percentages for each tier
  - Horizontal bar chart using Plotly

- [x] **Interactive Diagnostic Plots** (4 tabs)
  - Eigenvalue Ratio vs wavelength (log scale with threshold lines)
  - W Matrix elements (4x4 subplot grid)
  - A Matrix elements (4x4 subplot grid)
  - Air Validation (A @ W compared to identity)

- [x] **Save/Load Calibration**
  - Save to .npz file using `save_calibration()`
  - Load from file using `load_calibration()`
  - Session state updated on load

**Files modified:**
- `streamlit_app/pages/2_Calibration.py` - Complete rewrite with full functionality
- `streamlit_app/components/plots_plotly.py` - Added `create_matrix_elements_plot()` and `create_air_validation_plot()`
- `streamlit_app/utils/session_state.py` - Already had necessary helpers

---

### Phase 3 Bug Fixes - COMPLETED

Critical bugs fixed after initial Phase 3 implementation:

- [x] **BUG: File browser not working** - `streamlit-file-browser` didn't return folder paths correctly
  - Root cause: Package returns event data with `type`/`target` keys, not `current_path`
  - Solution: Replaced with simple editable text inputs for path entry (type/paste)
  - Removed drag-and-drop zone (non-functional in Streamlit)
  - Removed `streamlit-file-browser` dependency from `requirements-gui.txt`

- [x] **BUG: Wavelength slider wrong range** - Was 200-2000nm with 10nm step
  - Fixed to 400-1000nm range with 5nm step

- [x] **BUG: Sidebar version not at bottom** - "ECM Polarimetry v6.5.5" was in middle
  - Added CSS styling to position version at absolute bottom of sidebar

**Files modified:**
- `streamlit_app/components/file_browser.py` - Complete rewrite with editable text inputs
- `streamlit_app/pages/1_Configuration.py` - Fixed wavelength slider parameters
- `streamlit_app/components/sidebar.py` - Added CSS for bottom-positioned version
- `requirements-gui.txt` - Removed `streamlit-file-browser` dependency

---

### Phase 3.1: UI/UX Polish & Bug Fixes - COMPLETED

UI refinements and visual polish based on user feedback:

#### 1. Layout Changes
- [x] **Page width**: Changed from `wide` to custom 58rem width (~1.25x centered default)
  - Applied `st.html()` CSS override to all 5 pages
- [x] **Uniform box heights**: Fixed workflow boxes on Home page and settings boxes on Configuration page
  - Used CSS flexbox with fixed height for consistent appearance
- [x] **Run Calibration button**: Made wider and centered using 3-column layout
- [x] **File discovery list**: Made full width (was squeezed under button)

#### 2. Calibration Page Restructure
- [x] **Removed FP2 label** from top status row (now 3 columns instead of 4)
- [x] **Renamed "Mean Ratio"** → **"Mean Quality"** (and "Median Quality")
- [x] **Progress bar**: Now shows only percentage (0-100%), removed wavelength/ratio details
- [x] **Quality Summary**:
  - Changed "Excellent (%)" metric to **">=Good (%)"** (excellent + good combined)
  - Moved Eigenvalue Ratio plot INTO the Quality Summary expander
- [x] **Removed Diagnostic Plots section** (W matrix, A matrix, Air Validation tabs)
- [x] **Moved Save/Load** section to bottom of page

#### 3. Figure Styling
- [x] **Font size ~1.5x**: Applied to all plots (base=18, titles=22, axis=18, ticks=14)
- [x] **Grid lines**: Enabled on all plots EXCEPT Quality Breakdown bar chart
- [x] **Subscript labels**: Mueller matrix elements now use m<sub>11</sub> format
  - Top-left element (intensity): M<sub>11</sub> (capital M)
  - Other elements: m<sub>ij</sub> (lowercase m, normalized)
- [x] **Common axis labels**: Added shared "Wavelength (nm)" label below 4x4 subplot grids
- [x] **Fixed "100μ" bug**: Eigenvalue plot y-axis now shows proper scientific notation (1e-4)
- [x] **Quality Breakdown x-axis**: Changed label to "Percentage (%)"

#### 4. Sidebar Changes
- [x] **Removed FP2** from Calibration Details expander
- [x] **Added ">=Good: XX%"** to show combined excellent + good percentage
- [x] **Status indicator logic** (visual display only, internal state unchanged):
  - >=Good >= 50%: 🟢 **Calibrated**
  - >=Good 25-50%: 🟡 **Marginal Calibration**
  - >=Good < 25%: 🟡 **Poor Calibration**
  - Not calibrated: 🔴 **Not calibrated**

#### 5. Bug Fix: .bin File Detection
- [x] **Root cause**: Session state key mismatch in `file_browser.py`
  - `text_input` used `{key}_input` key, but code checked `{key}_path`
- [x] **Solution**: Use `{key}_path` directly as the `text_input` key
  - This ensures the text input value IS the session state value

**Files modified:**
- `streamlit_app/app.py` - Layout CSS, uniform workflow boxes
- `streamlit_app/pages/1_Configuration.py` - Layout CSS, uniform settings boxes
- `streamlit_app/pages/2_Calibration.py` - Major restructure (removed FP2, diagnostic plots, etc.)
- `streamlit_app/pages/3_Processing.py` - Layout CSS
- `streamlit_app/pages/4_Parameters.py` - Layout CSS
- `streamlit_app/components/sidebar.py` - Status logic, removed FP2, added >=Good%
- `streamlit_app/components/file_browser.py` - Fixed session state key bug
- `streamlit_app/components/plots_plotly.py` - Font sizes, grid lines, subscripts, y-axis fix

---

### Phase 4: Sample Processing Page - COMPLETED

Full ECM sample processing integration implemented:

- [x] **Sample Discovery**
  - Uses `discover_sample_files(samples_dir, cfg)` from `ecm.io`
  - Displays available samples with checkboxes
  - Select All / Deselect All buttons
  - Session state persistence for sample directory path

- [x] **Process Samples**
  - "Process Selected" button (centered, wide, consistent with Calibration page)
  - Progress bar shows percentage during batch processing
  - Uses `process_sample()` from `ecm.core.sample_processing`
  - Uses `load_spectral_data()` to load .bin files
  - Stores `MuellerMatrixResult` in `st.session_state['processed_samples']`
  - Error handling with expandable error list

- [x] **Mueller Matrix Visualization**
  - Sample dropdown to select which result to view
  - View mode toggle: "4x4 Grid" / "Selected Elements"
  - 4x4 normalized Mueller matrix plot using `create_mueller_matrix_plot()`
  - Mueller element selector (4x4 checkbox grid) with quick select buttons
  - Selected elements overlay plot using `create_selected_elements_plot()`
  - m₀₀ transmission plot using new `create_m00_plot()`

- [x] **Export Functionality**
  - Save Results (.npz) - saves all processed samples with wavelengths
  - Export Data (.csv) - exports current sample's Mueller matrix elements
  - Export Plot (.png) - placeholder (TODO: implement with kaleido)

**Files modified:**
- `streamlit_app/pages/3_Processing.py` - Complete rewrite with full functionality
- `streamlit_app/components/plots_plotly.py` - Added `create_m00_plot()` and `create_m00_comparison_plot()`

**Key ECM Functions used:**
```python
from ecm.io import discover_sample_files
from ecm.core.sample_processing import process_sample
from ecm.utils.io import load_spectral_data
```

---

### Phase 4.1: Bug Fixes and UI Cleanup - COMPLETED

Minor bug fixes, UI cleanup, and new functionality based on user feedback:

#### 1. Symbol Fixes
- [x] **Sidebar**: Changed `>=Good:` → `≥Good:`
- [x] **Calibration page**: Changed `">= 0.1"` → `"≥ 0.1"` in threshold table

#### 2. Layout Cleanup
- [x] **Configuration page**: Removed divider below title
- [x] **Calibration page**: Removed divider and "Eigenvalue Ratio:" label before plot
- [x] **Calibration page**: Changed status message from "Calibration loaded" to "Calibrated"
- [x] **Processing page**: Removed "Looking in: ..." text

#### 3. File Discovery Simplification (Calibration Page)
- [x] Replaced detailed file list with simple status messages:
  - Green: "Found all calibration files."
  - Green: "Found all calibration files. FP2 not included (optional)."
  - Red: "Found X/5 calibration files. Missing: DARK, ST, ..."

#### 4. Mueller Matrix Figure Restructure
- [x] **Top-left subplot (M₁₁)**: Now plots M₀₀ (transmission) instead of normalized m₁₁ (always 1)
- [x] **Auto-scale y-axis**: Top-left subplot auto-scales instead of fixed [0.95, 1.05]
- [x] **Removed standalone transmission plot**: M₀₀ is now in the 4×4 grid

#### 5. Element Selector Fixes
- [x] **Removed duplicate title**: "Select Mueller Elements" removed
- [x] **Removed "Diagonal" button**: Only "Clear All" and "Select All" remain
- [x] **Fixed button instantiation order**: Buttons now work correctly (moved BEFORE checkboxes)

#### 6. Multi-Sample Comparison Feature (NEW)
- [x] **New view mode**: "Compare Samples" added to Processing page (when ≥2 samples)
- [x] **User selection**: Checkboxes to select which samples to compare
- [x] **4×4 comparison plot**: All selected samples overlaid with different colors and legend
- [x] **New function**: `create_mueller_comparison_plot()` in plots_plotly.py

#### 7. Re-Calibration Confirmation Dialog (NEW)
- [x] When "Run Calibration" clicked while already calibrated, shows `@st.dialog()` popup
- [x] Options: "New Calibration" (clears existing results) or "Cancel"
- [x] Uses `clear_calibration()` from session_state.py

#### 8. Settings Menu (NEW)
- [x] **Created `.streamlit/config.toml`** with:
  - `toolbarMode = "minimal"` - Reduces hamburger menu options
  - `theme.base = "light"` - Locks to light theme

#### 9. Export CSV Bug Fix
- [x] **Root cause**: Line 412 used `shape[0]` (=4) instead of `shape[2]` (=n_wavelengths)
- [x] **Fix**: Changed to `M[i, j, :]` indexing and `shape[2]` for wavelength count
- [x] **Removed redundant m00 line**: Now adds `M00_transmission` column

**Files modified:**
- `streamlit_app/components/sidebar.py` - ≥ symbol
- `streamlit_app/pages/1_Configuration.py` - Removed divider
- `streamlit_app/pages/2_Calibration.py` - Multiple fixes, re-calibration dialog
- `streamlit_app/pages/3_Processing.py` - Multiple fixes, multi-sample comparison
- `streamlit_app/components/plots_plotly.py` - M₀₀ in top-left, comparison plot
- `streamlit_app/components/mueller_selector.py` - Button fixes
- `streamlit_app/.streamlit/config.toml` - NEW FILE

---

### Phase 4.2: Minor Plot Styling Fixes - COMPLETED

Minor visual fixes to Plotly figures:

#### 1. Font Size Increase
- [x] Increased axis labels from 18 → 20
- [x] Increased tick labels from 14 → 16
- [x] Increased legend font size to 16 (explicit setting)
- [x] Increased subplot titles from 14 → 16
- [x] Title size unchanged (22 - already good)

#### 2. M₀₀ Y-Axis Range Fix
- [x] Changed M₀₀ subplot from auto-scale to fixed range `[0, 1.05]`
- [x] Applied to both `create_mueller_matrix_plot()` and `create_mueller_comparison_plot()`

#### 3. Box Frames Added
- [x] Added black border (box frame) to all figures using `showline=True, mirror=True`
- [x] Quality Breakdown chart excluded (no box frame)
- [x] Updated `apply_common_styling()` with new `show_box` parameter

**Files modified:**
- `streamlit_app/components/plots_plotly.py` - Font sizes, M₀₀ range, box frames

---

### Phase 4.3: Minor UI/Plot Fixes - COMPLETED

Minor UI and plot fixes based on user feedback:

#### 1. Remove Box Frames (Undo 4.2)
- [x] Removed `show_box` parameter from `apply_common_styling()`
- [x] Plots no longer have black borders

#### 2. Explicit Blue Color for Mueller Matrix
- [x] Added `line=dict(color='#1f77b4')` to all 16 traces in `create_mueller_matrix_plot()`
- [x] Ensures consistent blue color in 4×4 grid view

#### 3. Wider Page Layout
- [x] Changed page width from `58rem` → `61rem` (~5% wider)
- [x] Applied to all 5 pages (app.py, 1_Configuration.py, 2_Calibration.py, 3_Processing.py, 4_Parameters.py)

#### 4. Rename psi → ν (nu) in Parameters Page
- [x] Updated docstring, description, table headers, and plot labels
- [x] ECM code still uses `psi` internally, but GUI displays `ν`

#### 5. Phase 5 Styling Standards
- [x] Added comment block at top of `plots_plotly.py` documenting styling standards for Phase 5 implementation

**Files modified:**
- `streamlit_app/components/plots_plotly.py` - Remove box frames, add blue color, add styling standards
- `streamlit_app/app.py` - Width 58rem → 61rem
- `streamlit_app/pages/1_Configuration.py` - Width 58rem → 61rem
- `streamlit_app/pages/2_Calibration.py` - Width 58rem → 61rem
- `streamlit_app/pages/3_Processing.py` - Width 58rem → 61rem
- `streamlit_app/pages/4_Parameters.py` - Width 58rem → 61rem, psi → ν

---

### Phase 4.4: Final Quality Display Fixes - COMPLETED

Final quality display and sidebar cleanup:

#### 1. Quality Metric Label Fix
- [x] Changed `">=Good (%)"` → `"≥Good (%)"` in Calibration page

#### 2. Quality Bar Colors Swapped
- [x] Excellent now cyan/blue (#17a2b8), Good now green (#28a745)
- [x] Colors array swapped in `create_quality_breakdown_chart()`

#### 3. Eigenvalue Threshold Line Colors
- [x] Threshold line colors now match bar colors:
  - Excellent: #17a2b8 (cyan/blue)
  - Good: #28a745 (green)
  - Acceptable: #ffc107 (yellow)

#### 4. Sidebar Simplified
- [x] Removed "Calibration Details" expander
- [x] Kept only status indicator (🟢/🟡/🔴) and status text
- [x] Removed unused `get_calibration_info` import

**Files modified:**
- `streamlit_app/pages/2_Calibration.py` - ≥Good metric label
- `streamlit_app/components/plots_plotly.py` - Bar colors, threshold line colors
- `streamlit_app/components/sidebar.py` - Removed Calibration Details expander

---

### Phase 5: Lu-Chipman Decomposition Page - COMPLETED

Full Lu-Chipman polar decomposition implementation:

#### 1. New Plot Functions (plots_plotly.py)
- [x] `create_diattenuation_plot()` - Single-sample diattenuation
- [x] `create_diattenuation_comparison_plot()` - Multi-sample diattenuation overlay
- [x] `create_di_plot()` - Single-sample depolarization index
- [x] `create_di_comparison_plot()` - Multi-sample DI overlay
- [x] `create_retardance_plot()` - Single-sample retardance with unit selector
- [x] `create_retardance_comparison_plot()` - Multi-sample retardance overlay

#### 2. Retardance Unit Selector
- [x] Y-axis unit toggle: degrees (default), radians, waves
- [x] QWP/HWP reference lines adjust based on unit
- [x] Works for both single sample and comparison views

#### 3. Parameters Page Rewrite (4_Parameters.py)
- [x] Sample selection with Select All / Clear All buttons
- [x] Run Decomposition button with progress bar
- [x] Decomposed Matrices section with tabs (M_D, M_R, M_Δ)
  - View modes: 4x4 Grid, Selected Elements, Compare Samples
  - Element selector for Selected Elements mode
- [x] Decomposition Parameters section with tabs (D, DI, R)
  - Retardance tab has unit selector
  - Multi-sample overlay with legend toggle

#### 4. Export Functionality
- [x] Save Decomposition (.npz) - all matrices and parameters
- [x] Export Data (.csv) - one file per sample with all parameters
- [x] Export Plot (.png) - placeholder (TODO: implement with kaleido)

#### 5. ECM Integration
- [x] Uses `lu_chipman_decomposition()` from `ecm.postprocessing`
- [x] Stores results in `st.session_state['lu_chipman_results']`
- [x] ECM `psi_deg` displayed as `ν` (nu) in GUI

**Files modified:**
- `streamlit_app/components/plots_plotly.py` - Added 6 new plot functions
- `streamlit_app/pages/4_Parameters.py` - Complete rewrite with full functionality

---

### Phase 5.1: UI Fixes & Enhancements - COMPLETED

UI tuning, new figures, and summary table:

#### 1. Processing Page Cleanup
- [x] Removed redundant "Wavelengths", "Range", "Mean Quality" display fields
- [x] Removed unused `get_calibration_info` import

#### 2. Parameters Page - Matrix Tab Reordering
- [x] Reordered tabs: Diattenuator → Depolarizer → Retarder (was: Diattenuator → Retarder → Depolarizer)
- [x] Added HTML subscripts to plot titles (M<sub>D</sub>, M<sub>Δ</sub>, M<sub>R</sub>)

#### 3. Unified Sample Selection for Decomposition Parameters
- [x] Moved sample selection above parameter tabs (shared across all)
- [x] Selection now persists when switching between D, DI, R, ν/χ tabs
- [x] Removed duplicate Select All/Clear All buttons from each tab

#### 4. New Figure: Fast Axis (ν) & Ellipticity (χ)
- [x] Added `create_fast_axis_plot()` - single sample, 2-subplot vertical figure
- [x] Added `create_fast_axis_comparison_plot()` - multi-sample overlay
- [x] Unit selector: degrees (default) / radians (no waves for angles)
- [x] Reference lines at 0 (linear retarder)
- [x] New "Fast Axis (ν, χ)" tab in Decomposition Parameters

#### 5. Summary Table Section
- [x] New "Summary Table" expander between Decomposition Parameters and Export
- [x] Expander open by default (expanded=True)
- [x] Table: columns=samples, rows=D, DI, R, ν, χ
- [x] View mode toggle: "Mean ± Std" or "Single wavelength"
- [x] Wavelength slider shows actual wavelength values (not indices)
- [x] Angle unit selector: degrees/radians

**Files modified:**
- `streamlit_app/pages/3_Processing.py` - Removed redundant metrics
- `streamlit_app/pages/4_Parameters.py` - Matrix reorder, unified selection, new tab, summary table
- `streamlit_app/components/plots_plotly.py` - Added 2 new Fast Axis plot functions

---

## Phase 6 - Polish & Enhancements

### Phase 6.1 - Revisions Complete ✓

Based on user feedback, the following changes were made:

#### 1. PNG Export Buttons - REMOVED ✓
- [x] Removed all "Download Plot (.png)" buttons from Processing and Parameters pages
- [x] Plotly's native download icon in plot toolbar is sufficient
- [x] Removed unused `export_figure_png` imports

#### 2. Streamlit Caching - REMOVED ✓
- [x] Removed `@st.cache_data` decorators from all plot functions (caused slowdown)
- [x] Removed `import streamlit as st` from plots_plotly.py

#### 3. Reset Session Button - MOVED TO SIDEBAR ✓
- [x] Moved from Home page to sidebar under new "Session" section
- [x] Appears below Status section in sidebar
- [x] Confirmation dialog with warning message preserved
- [x] Clears all session state keys on confirm

#### 4. CSV Export Dialogs - ADDED ✓
- [x] **Processing page**: "Export Data (.csv)" now shows selection dialog
  - Select which samples to export
  - Select data to include (Normalized Mueller Matrix, M00 Transmission)
  - "Export Selected" button performs export
- [x] **Parameters page**: "Export Data (.csv)" now shows selection dialog
  - Select which samples to export
  - Select parameters to include (D, DI, R, ν, χ)
  - Select matrices to include (M_D, M_Δ, M_R)
  - "Export Selected" button performs export

#### 5. Batch Export Helper - KEPT ✓
- [x] `create_export_zip()` function kept in `utils/export.py` for future use

**Files modified (Phase 6.1 Revisions):**
- `streamlit_app/pages/3_Processing.py` - Removed PNG buttons, added CSV export dialog
- `streamlit_app/pages/4_Parameters.py` - Removed PNG buttons, added CSV export dialog
- `streamlit_app/app.py` - Removed Reset Session button
- `streamlit_app/components/sidebar.py` - Added Session section with Reset button
- `streamlit_app/components/plots_plotly.py` - Removed caching decorators

---

### Phase 6.2: Polish & Enhancements (Priority 2 & 3) - COMPLETED

#### 1. Improved Error Messages ✓
- [x] Updated 3 error messages in `file_browser.py` with path context
- [x] Updated 10 error messages in `2_Calibration.py` with actionable suggestions
- [x] Updated 8 error messages in `3_Processing.py` with guidance
- [x] Error messages now include:
  - Path being accessed (when relevant)
  - Actionable suggestion (what to check/do)
  - Reference to correct page (when applicable)

#### 2. Configuration Validation Warnings ✓
- [x] **Wavelength range warnings** (1_Configuration.py):
  - Warning if min < 350 nm (most polarimeters operate 400-800 nm)
  - Warning if max > 1200 nm (verify detector supports range)
- [x] **Angular positions info** (1_Configuration.py):
  - Info note if n_positions not in [36, 72, 96, 144] (common values)

#### 3. Comparison Selections Persistence ✓
- [x] **Already working** - Streamlit automatically persists widget states via keys
  - Processing page uses `st.session_state[f"compare_cb_{name}"]`
  - Parameters page uses similar pattern
  - No changes needed

**Files modified (Phase 6.2):**
- `streamlit_app/components/file_browser.py` - Improved error messages
- `streamlit_app/pages/1_Configuration.py` - Added validation warnings
- `streamlit_app/pages/2_Calibration.py` - Improved error messages
- `streamlit_app/pages/3_Processing.py` - Improved error messages

---

### Phase 6.3: MMForge Branding & UI Polish - COMPLETED

#### 1. MMForge Branding ✓
- [x] **Color scheme**: Primary brand color `#FF1F5B` applied throughout
- [x] **Page titles**: Updated to "MMForge - PAGE_NAME" format
- [x] **Sidebar footer**: "MMForge v1.0" with "Built on ECM-Calibration v6.5.5"
- [x] **Logo placement**: MMForge logo on HOME page in two-column layout with title

#### 2. Page Naming (UPPERCASE) ✓
- [x] Renamed all page files using `git mv`:
  - `1_Configuration.py` → `1_CONFIGURATION.py`
  - `2_Calibration.py` → `2_CALIBRATION.py`
  - `3_Processing.py` → `3_PROCESSING.py`
  - `4_Parameters.py` → `4_PARAMETERS.py`
- [x] Created new `5_ADVANCED.py` placeholder page

#### 3. CSS Theming ✓
- [x] **Primary buttons**: Brand color with white text (`type="primary"`)
  - Run Calibration button
  - Process Selected button
  - Run Decomposition button
- [x] **Expander headers**: Brand color background with white text
- [x] **Sidebar active page indicator**: Pink highlight with left border
- [x] **Workflow boxes**: Muted brand color background (rgba(255, 31, 91, 0.15))
- [x] **Interactive elements**: Sliders, checkboxes, progress bars in brand color

#### 4. Quality Tier Colors ✓
- [x] Updated quality tier colors in eigenvalue chart:
  - Excellent: `#0C8AB3` (cyan/blue)
  - Good: `#56D39A` (green)
  - Acceptable: `#E8C34A` (yellow)
  - Marginal: `#FF1F5B` (brand pink)
  - Poor: `#C22026` (red)
- [x] Trace colors palette for multi-sample comparison

#### 5. Sidebar Updates ✓
- [x] Removed logo from sidebar (placed on HOME page instead)
- [x] Updated footer: removed "All rights reserved."
- [x] Status indicator colors match brand theme

**Files modified (Phase 6.3):**
- `streamlit_app/app.py` - Logo+title layout, workflow boxes CSS, expander CSS, page title
- `streamlit_app/components/sidebar.py` - Removed logo, updated footer
- `streamlit_app/pages/1_CONFIGURATION.py` - Page title, expander CSS, button CSS
- `streamlit_app/pages/2_CALIBRATION.py` - Page title, type=primary button, expander CSS
- `streamlit_app/pages/3_PROCESSING.py` - Page title, type=primary button, expander CSS
- `streamlit_app/pages/4_PARAMETERS.py` - Page title, type=primary button, expander CSS
- `streamlit_app/pages/5_ADVANCED.py` - NEW placeholder page with all CSS theming
- `streamlit_app/components/plots_plotly.py` - Quality tier colors, trace colors
- `streamlit_app/.streamlit/config.toml` - Theme locked to light with primaryColor

---

### Phase 6.4: Minor Fixes - COMPLETED

#### 1. Eigenvalue Plot - Removed Text Labels ✓
- [x] Removed stacked text annotations ("Poor", "Marginal", "Acceptable", "Good", "Excellent") from right side of plot
- [x] Kept colored shading regions for quality tiers
- [x] Removed `annotation_text`, `annotation_position`, `annotation_font_size` from `add_hrect()` calls

#### 2. Home Page Renamed to "HOME" ✓
- [x] Renamed `app.py` to `HOME.py` using `git mv`
- [x] Sidebar now shows "HOME" instead of just a home icon
- [x] Run command changed to: `streamlit run HOME.py`
- [x] Consistent UPPERCASE naming with other pages (CONFIGURATION, CALIBRATION, etc.)
- Based on official Streamlit Hello.py example pattern (https://github.com/streamlit/hello)

#### 3. Sidebar Footer Updated ✓
- [x] New 5-line footer format:
  - **MMForge v1.0** (bold)
  - Built with Streamlit
  - Powered by ECM-Calibration v6.5.5
  - *Implements the Eigenvalue Calibration Method (ECM)* (italic)
  - © 2026 Daniel Vala

**Files modified (Phase 6.4):**
- `streamlit_app/components/plots_plotly.py` - Removed annotation text from eigenvalue plot
- `streamlit_app/app.py` → `streamlit_app/HOME.py` - Renamed for sidebar label
- `streamlit_app/components/sidebar.py` - Updated footer format

---

### Phase 6.5: Design & UX Polish - COMPLETED

Based on professional design review to reduce visual fatigue and improve code maintainability.

#### 1. Consolidated CSS Utility ✓
- [x] Created new `utils/styling.py` with all shared CSS
- [x] Single `inject_custom_css()` function replaces ~60 lines of inline CSS per page
- [x] ~360 lines of duplicated CSS removed from page files
- [x] Color constants defined: PRIMARY_COLOR, SECONDARY_COLOR, etc.

#### 2. Color Scheme Refinement ✓
- [x] Introduced `#2D3E50` (slate blue) as secondary/structural color
- [x] Expander headers: `#FF1F5B` → `#2D3E50` (reduce magenta overuse)
- [x] Sidebar active indicator: `#FF1F5B` → `#2D3E50`
- [x] Workflow boxes: `rgba(255,31,91,0.15)` → `rgba(45,62,80,0.08)`
- [x] Primary buttons KEPT at `#FF1F5B` (brand recognition)
- [x] Sliders/checkboxes KEPT at `#FF1F5B`

#### 3. Homepage Title Changed ✓
- [x] Changed from `st.title("MMForge")` to `st.markdown("### Your Mueller Matrix Workbench")`
- [x] Tagline now serves as the main header alongside logo

#### 4. Enhanced Plotly Figure Styling ✓
- [x] Updated `apply_common_styling()` function in `plots_plotly.py`
- [x] Cleaner backgrounds (`paper_bgcolor='white'`, `plot_bgcolor='white'`)
- [x] Refined margins and axis styling
- [x] Better hover label styling with `#2D3E50` border
- [x] Consistent font family (Arial, sans-serif)

#### 5. Additional CSS Improvements ✓
- [x] Secondary button styling (gray background, slate hover)
- [x] Form input focus states with slate border/shadow
- [x] Dataframe header styling with slate background

**Files created (Phase 6.5):**
- `streamlit_app/utils/styling.py` - NEW centralized CSS utility

**Files modified (Phase 6.5):**
- `streamlit_app/HOME.py` - Removed inline CSS, new title, updated workflow boxes
- `streamlit_app/pages/1_CONFIGURATION.py` - Removed inline CSS, added import
- `streamlit_app/pages/2_CALIBRATION.py` - Removed inline CSS, added import
- `streamlit_app/pages/3_PROCESSING.py` - Removed inline CSS, added import
- `streamlit_app/pages/4_PARAMETERS.py` - Removed inline CSS, added import
- `streamlit_app/pages/5_ADVANCED.py` - Removed inline CSS, added import
- `streamlit_app/components/plots_plotly.py` - Enhanced apply_common_styling()

---

### Phase 6.6: UI Polish & Layout Fixes - COMPLETED

Minor UI polish and layout fixes from UX review.

#### 1. Calibration Page Fixes ✓
- [x] **Added spacing** after Run Calibration button section
- [x] **Removed redundant stats** (Wavelengths, Range, Mean Quality) below page title
  - These were duplicated in the Quality Summary expander
- [x] **Quality Breakdown chart** - Reversed order (Excellent at top, Poor at bottom)

#### 2. Figure Improvements ✓
- [x] **Mueller matrix x-axis label** - Moved lower (`y=-0.10`) to avoid tick label overlap
- [x] **Legend positioning** - Default placement above plot (`y=1.02`) to avoid overlaps

#### 3. Parameters Page Tabs ✓
- [x] **Larger tab fonts** - Added CSS for 1.1rem font size on tabs
- [x] **Simplified tab labels** - Using Unicode subscript-style characters (Mᴅ, M∆, Mᴿ)

#### 4. Sidebar Logo ✓
- [x] **Logo at top** - MMForge logo now displayed above Status section in sidebar

#### 5. Home Page Tagline ✓
- [x] **Larger tagline** - Changed from `###` to `##` for bigger font size

**Files modified (Phase 6.6):**
- `streamlit_app/components/plots_plotly.py` - Chart order, x-axis label position, legend position
- `streamlit_app/pages/2_CALIBRATION.py` - Spacing, removed redundant stats
- `streamlit_app/utils/styling.py` - Tab font CSS
- `streamlit_app/pages/4_PARAMETERS.py` - Tab labels
- `streamlit_app/components/sidebar.py` - Logo at top
- `streamlit_app/HOME.py` - Larger tagline

---

### Phase 6.7: UI Polish & Layout Fixes - COMPLETED

Additional UI polish based on visual review.

#### 1. Sidebar Logo Position ✓
- [x] Logo now appears ABOVE navigation links using CSS background-image injection
- [x] SVG logo embedded as base64 data URI in `utils/styling.py`
- [x] Removed `st.image()` call from `sidebar.py`

#### 2. Range Slider Track Color ✓
- [x] Updated CSS to style slider track segments separately
- [x] Track outside selected range now styled differently

#### 3. Figure Margins & X-Axis Label ✓
- [x] Increased bottom margin (`b=80`) for x-axis label visibility
- [x] Increased top margin (`t=80`) for legend clearance
- [x] Adjusted x-axis label position from `y=-0.10` to `y=-0.06`

#### 4. Decomposed Matrix Tab Labels ✓
- [x] Renamed tabs from Unicode subscripts to clear text:
  - "MM of Diattenuator"
  - "MM of Depolarizer"
  - "MM of Retarder"

#### 5. Eigenmodes Renaming ✓
- [x] "Fast Axis (ν, χ)" tab renamed to "Eigenmodes"
- [x] Figure titles changed:
  - `create_fast_axis_plot()`: "Fast Axis & Ellipticity" → "Eigenmodes"
  - `create_fast_axis_comparison_plot()`: "Fast Axis Comparison" → "Eigenmodes Comparison"

**Files modified (Phase 6.7):**
- `streamlit_app/utils/styling.py` - Sidebar logo CSS, slider track CSS
- `streamlit_app/components/plots_plotly.py` - Margins, x-axis label position, eigenmodes titles
- `streamlit_app/pages/4_PARAMETERS.py` - Tab labels (MM of..., Eigenmodes)
- `streamlit_app/components/sidebar.py` - Removed st.image logo code

---

## WHAT'S NEXT: Phase 7 - Testing & Documentation

#### Remaining Optional Items (Low Priority)

- UI Micro-Improvements (placeholder text, help tooltips)
- Cross-session state persistence (cookies/localStorage)

#### Removed from Original Plan (with reasoning)

- ~~Cross-plot wavelength highlighting~~ → Already have Plotly unified hover mode
- ~~Zoom synchronization~~ → Already have `shared_xaxes=True` in subplots
- ~~Keyboard shortcuts~~ → Complex to implement in Streamlit, not essential
- ~~Lazy loading~~ → Not needed for typical dataset sizes (hundreds of wavelengths)
- ~~Loading spinners~~ → Already have progress bars for all long operations
- ~~PNG Export Buttons~~ → Plotly native download sufficient
- ~~Caching~~ → Caused slowdown instead of improvement

---

## FILES REFERENCE

### Core ECM Package (don't modify unless debugging):
- `ecm/config/ecm_config.py` - Configuration dataclass
- `ecm/core/transmission_calibration.py` - Main calibration function
- `ecm/core/sample_processing.py` - Mueller matrix extraction
- `ecm/io/calibration_io.py` - Save/load calibration
- `ecm/diagnostics/calibration_diagnostics.py` - Quality analysis

### GUI Files (modify freely):
- `streamlit_app/app.py` - Home page
- `streamlit_app/pages/*.py` - All pages
- `streamlit_app/components/*.py` - Reusable components
- `streamlit_app/utils/*.py` - Utilities

---

## RUNNING THE APP

```bash
cd /Users/danielvala/Documents/PYTHON/VS/ECM-GUI/streamlit_app
streamlit run HOME.py
```

Or with auto-reload:
```bash
streamlit run HOME.py --server.runOnSave true
```

---

## QUALITY THRESHOLDS (Reference)

| Quality | Eigenvalue Ratio Threshold |
|---------|---------------------------|
| Excellent | < 1e-4 |
| Good | < 1e-3 |
| Acceptable | < 1e-2 |
| Marginal | < 0.1 |
| Poor | ≥ 0.1 |
