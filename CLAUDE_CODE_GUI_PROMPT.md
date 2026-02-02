# ECM Polarimetry GUI - Claude Code Implementation Prompt

**Project**: Streamlit GUI for ECM (Eigenvalue Calibration Method) Mueller Matrix Polarimeter Calibration
**Author**: Daniel Vala
**Date**: February 2026
**Version**: 1.1

---

## TABLE OF CONTENTS

1. [Project Overview](#1-project-overview)
2. [Codebase Summary](#2-codebase-summary)
3. [Implementation Phases](#3-implementation-phases)
4. [GUI Scheme](#4-gui-scheme)
5. [Code Style Requirements](#5-code-style-requirements)
6. [Phase Instructions](#6-phase-instructions)
7. [Technical Notes](#7-technical-notes)

---

## 1. PROJECT OVERVIEW

### 1.1 What This Project Does

This is a Python implementation of the ECM (Eigenvalue Calibration Method) algorithm for calibrating spectroscopic Mueller matrix polarimeters with dual rotating compensators. The workflow consists of:

1. **Calibration**: Process calibration samples (air, polarizers, retarders) to determine instrument matrices W (PSG) and A (PSA)
2. **Sample Processing**: Apply calibration to sample measurements to extract Mueller matrices
3. **Post-processing**: Lu-Chipman polar decomposition to extract physical parameters (Diattenuation, Retardance, Depolarization Index)

### 1.2 Goal

Create a **modern, user-friendly** Streamlit GUI that provides an intuitive interface for researchers to:
- Configure and run ECM calibration
- Process sample measurements
- Perform Lu-Chipman decomposition
- Visualize results with **interactive Plotly plots**
- Save and load calibration/results
- Export figures (PNG) and data (CSV)

### 1.3 Why Streamlit

Streamlit was chosen because:
- Simple Python API (no frontend knowledge needed)
- Excellent for scientific/research applications
- **Plotly integration for interactive plots** (hover info, curve toggling, zoom, etc.)
- Interactive widgets for parameters
- Easy session state management for multi-step workflows
- **Deployable** for remote access (lab, elsewhere)

### 1.4 User Experience Priorities

- **Modern and clean** interface with drag-and-drop file handling
- **Interactive plots** with hover information, curve checkboxes, zoom/pan
- **Simple configuration** - hide advanced ECM algorithm parameters
- **Automatic detection** of second retarder (no manual toggle)
- **Researcher-friendly code** that is easy to understand and modify

---

## 2. CODEBASE SUMMARY

### 2.1 Package Structure

```
ecm/
├── config/
│   └── ecm_config.py          # Dataclass-based configuration (ECMConfig)
├── core/
│   ├── transmission_calibration.py  # Main calibration (calibrate_transmission)
│   ├── sample_processing.py         # Mueller matrix extraction (process_sample)
│   ├── ecm_solver.py                # ECM eigenvalue solver
│   ├── ecm_matrices.py              # H, K matrix construction
│   ├── parameter_extraction.py      # Extract sample parameters
│   ├── modulation.py                # Modulation basis
│   ├── fourier.py                   # Fourier analysis
│   └── file_discovery.py            # Auto-discover calibration files
├── io/
│   ├── calibration_io.py      # Save/load calibration (save_calibration, load_calibration)
│   └── sample_discovery.py    # Discover sample files
├── visualization/
│   ├── mueller_plots.py       # 4×4 Mueller matrix plots
│   ├── parameter_plots.py     # Lu-Chipman parameter plots
│   ├── decomposition_plots.py # Decomposed matrix plots
│   ├── intensity_plots.py     # Intensity diagnostics
│   └── figure_utils.py        # Publication styling
├── postprocessing/
│   └── lu_chipman.py          # Lu-Chipman decomposition
├── diagnostics/
│   └── calibration_diagnostics.py  # Calibration quality analysis
└── cli.py                     # CLI entry points
```

### 2.2 Key Functions to Use in GUI

```python
# Calibration
from ecm.config import ECMConfig
from ecm.core import calibrate_transmission
from ecm.io import save_calibration, load_calibration

# Sample Processing
from ecm.core.sample_processing import process_sample
from ecm.utils.io import load_spectral_data
from ecm.io import discover_sample_files

# Post-processing
from ecm.postprocessing import lu_chipman_decomposition

# Visualization (existing Matplotlib - will create Plotly versions)
from ecm.visualization import (
    plot_mueller_matrix,
    plot_polarimetric_parameters,
    plot_decomposed_matrices,
)
from ecm.diagnostics import run_calibration_diagnostics
```

### 2.3 Key Data Structures

| Class | Module | Description |
|-------|--------|-------------|
| `ECMConfig` | `ecm.config` | All configuration parameters (nested dataclasses) |
| `CalibrationResult` | `ecm.core.transmission_calibration` | W, A matrices, wavelengths, parameters |
| `CalibrationDiagnostics` | `ecm.core.transmission_calibration` | Quality metrics (eigenvalue ratio, condition numbers) |
| `MuellerMatrixResult` | `ecm.core.sample_processing` | Extracted Mueller matrices (M, M_normalized, m00) |
| `LuChipmanResult` | `ecm.postprocessing.lu_chipman` | Decomposition results (D, R, DI, ψ, χ) |

---

## 3. IMPLEMENTATION PHASES

### Phase 0: Pre-Implementation Debugging

**These bugs must be fixed before starting GUI implementation.**

```
===========================================================================
DEBUGGING INSTRUCTIONS
===========================================================================

BUG 1: Missing Font Glyph Warning
---------------------------------
Location: ecm/diagnostics/calibration_diagnostics.py (line ~392)

Error Message:
  UserWarning: Glyph 8321 (\N{SUBSCRIPT ONE}) missing from current font.
  fig.tight_layout()

Problem: Unicode subscript characters (₁, ₂, ₃, ₄) are not available in
the default Matplotlib font.

Expected: No warning messages during calibration.

Fix: Replace Unicode subscripts with regular text subscripts using
Matplotlib's mathtext (e.g., r'$W_{11}$' instead of 'W₁₁') OR configure
a font that supports these glyphs. Apply fix to all affected files in
ecm/diagnostics/ and ecm/visualization/.


BUG 2: Figures Not Displaying Interactively
-------------------------------------------
Location: scripts/calibrate_transmission.py (and related scripts)

Problem: After successful calibration, figures are saved to disk but do
NOT pop up in interactive windows. User cannot inspect plots during
calibration.

Expected: Figures should open in separate interactive windows (using
plt.show()) in addition to being saved.

Fix: Add plt.show() calls after saving figures, or provide an option
(e.g., --show-plots flag) to display figures interactively. Ensure
matplotlib backend supports interactive display.


BUG 3: Output Files Saved to Wrong Directory
---------------------------------------------
Location: ecm/io/calibration_io.py, scripts/calibrate_transmission.py

Problem: Calibration results and diagnostics are NOT saved to the
current working directory. They go to some other location defined in
the config.

Expected: By default, save all outputs (calibration.npz, diagnostic
plots, etc.) to the current working directory where the user runs
the script.

Fix: When output_path is not explicitly specified, default to
Path.cwd() / 'calibration_output' instead of a path relative to
the package installation. Make the output directory configurable
but sensible by default.


BUG 4: Incorrect Quality Threshold for "Excellent"
---------------------------------------------------
Location: ecm/diagnostics/calibration_diagnostics.py (quality assessment)

Problem: The quality breakdown thresholds in the code use incorrect
boundaries. The "Excellent" threshold should be < 1e-4, not < 1e-5. The marginal branch is added.

Expected thresholds:
  - Excellent: eigenvalue_ratio < 1e-4
  - Good: eigenvalue_ratio < 1e-3
  - Acceptable: eigenvalue_ratio < 1e-2
  - Marginal: eigenvalue_ratio < 0.1
  - Poor: eigenvalue_ratio >= 0.1

Fix: Find where quality categories are defined in the diagnostics
module and update according to the description above. Also, 
ensure consistency across all files that reference these thresholds!

===========================================================================
END OF DEBUGGING INSTRUCTIONS
===========================================================================
```

**Phase 0 Deliverables:**
- [ ] BUG 1 fixed: No font glyph warnings
- [ ] BUG 2 fixed: Figures display interactively
- [ ] BUG 3 fixed: Outputs save to current working directory
- [ ] BUG 4 fixed: Quality threshold "Excellent" is < 1e-4
- [ ] Existing tests still pass (`pytest`)
- [ ] No changes to physics/math logic

---

### Phase 1: Project Setup & Basic Layout

**Goal**: Create the Streamlit app structure with modern file handling.

**Tasks:**
1. Create `streamlit_app/` directory in project root
2. Create `app.py` (main entry point)
3. Create `pages/` directory with placeholder pages
4. Set up sidebar navigation with workflow status
5. Implement drag-and-drop file upload component
6. Create `requirements-gui.txt` with all dependencies
7. Test that the app runs with `streamlit run app.py`

**Required Packages (add to requirements-gui.txt):**
```
streamlit>=1.30.0
plotly>=5.18.0
streamlit-file-browser>=0.2.0
pandas>=2.0.0
watchdog>=3.0.0
```

**Files to Create:**
```
streamlit_app/
├── app.py                 # Main entry point (Home page)
├── pages/
│   ├── 1_Configuration.py # Configuration page
│   ├── 2_Calibration.py   # Calibration page
│   ├── 3_Processing.py    # Sample processing page
│   └── 4_Lu_Chipman.py    # Post-processing page
├── components/
│   ├── __init__.py
│   ├── sidebar.py         # Sidebar with status indicator
│   ├── file_browser.py    # Drag-and-drop + directory browser
│   ├── plots_plotly.py    # Interactive Plotly plot functions
│   └── mueller_selector.py # Mueller element selection component
├── utils/
│   ├── __init__.py
│   ├── session_state.py   # Session state helpers
│   └── export.py          # Export helpers (PNG, CSV)
└── assets/
    └── style.css          # Custom styling (optional)
```

**Phase 1 Deliverables:**
- [ ] App launches without errors
- [ ] Sidebar shows "Calibrated" / "Not calibrated" status
- [ ] Drag-and-drop zone visible on config page
- [ ] Directory browser component working

---

### Phase 2: Configuration Page

**Goal**: Create a simplified, user-friendly configuration UI.

**Tasks:**
1. Implement path selection with BOTH:
   - Text input for manual path entry
   - Drag-and-drop zone for folders/files
   - Directory browser button
2. Add wavelength range configuration (min/max sliders or inputs)
3. Add angular positions input (default 96)
4. **Remove** rotation cycles field (always 1)
5. **Remove** ECM Algorithm section (use sensible defaults internally)
6. **Auto-detect** second retarder from files (no manual toggle)
7. Implement config save/load (YAML/JSON)
8. Store config in session state

**Simplified Config Sections:**
- **Paths**: Data directory, Output directory (with drag-drop + browse)
- **Wavelength**: Range (nm), Reference wavelength
- **Acquisition**: Angular positions only

**Phase 2 Deliverables:**
- [ ] Clean, simple configuration interface
- [ ] Drag-and-drop works for directory selection
- [ ] Config persists in session state
- [ ] Save/load config to file works

---

### Phase 3: Calibration Page

**Goal**: Implement calibration with progress bar and quality breakdown.

**Tasks:**
1. Display current configuration summary
2. Add "Discover Files" button to find calibration files
3. Display found files with validation status
4. **Auto-detect** if second retarder (FP2) file exists
5. Add "Run Calibration" button
6. Show **progress bar only** during calibration (no wavelength/ratio text)
7. Display calibration summary with **quality breakdown**:
   - Show count AND percentage for each quality level:
     - Excellent (< 1e-4)
     - Good (< 1e-3)
     - Acceptable (< 1e-2)
     - Marginal (< 0.1)
     - Poor (≥ 0.1)
   - Show a **horizontal bar chart** for visual breakdown
8. Show diagnostic plots using **interactive Plotly**
9. Add "Save Calibration" button (saves to output directory)
10. Add "Load Calibration" button

**Phase 3 Deliverables:**
- [ ] Calibration runs from GUI
- [ ] Progress bar shows smoothly
- [ ] Quality breakdown with percentages and bar chart
- [ ] Interactive Plotly diagnostic plots
- [ ] Save/load calibration works
- [ ] Files save to specified output directory

---

### Phase 4: Sample Processing Page

**Goal**: Enable processing samples with loaded calibration.

**Tasks:**
1. Check if calibration is loaded - show "Calibrated" or "Not calibrated"
2. Add sample directory selection (drag-drop + browse)
3. Discover and list available samples with checkboxes
4. Allow single or batch sample selection
5. Add "Process Selected Samples" button with progress bar
6. Display **NORMALIZED** Mueller matrix plots (4×4 grid) using Plotly
7. Add **Mueller Element Selector**:
   - "Select Elements" button opens a 4×4 checkbox grid
   - User can select one or multiple elements
   - Selected elements are overlaid on a single plot
   - "Show Full Matrix" button returns to 4×4 view
8. Show m00 (transmission) spectrum
9. Add "Save Results" button (NPZ format)
10. Add "Export Plot" button (PNG format)
11. Add "Export Data" button (CSV format)

**Phase 4 Deliverables:**
- [ ] Samples can be selected and processed
- [ ] Mueller matrices displayed as interactive 4×4 Plotly grid
- [ ] Element selector works (select, overlay, return to full)
- [ ] Export to PNG and CSV works

---

### Phase 5: Post-Processing Page (Lu-Chipman)

**Goal**: Implement Lu-Chipman decomposition with interactive visualization.

**Tasks:**
1. Load processed Mueller matrices (from Phase 4 or file)
2. Run Lu-Chipman decomposition
3. Display **interactive Plotly** parameter plots:
   - Depolarization Index (DI)
   - Retardance (degrees and waves)
   - Diattenuation (D)
   - Fast-axis angles (ψ, χ)
4. Add hover information showing exact values
5. Add curve toggle checkboxes (for multi-curve plots)
6. Display decomposed matrices (M_D, M_R, M_Δ) - **NORMALIZED**
7. Show summary statistics table
8. Add export options:
   - "Save Decomposition" (NPZ)
   - "Export Plots" (PNG)
   - "Export Data" (CSV)

**Phase 5 Deliverables:**
- [ ] Lu-Chipman decomposition runs
- [ ] All parameter plots are interactive (hover, zoom, toggle)
- [ ] Export to PNG and CSV works

---

### Phase 6: Interactive Features & Polish

**Goal**: Add advanced interactive features and improve UX.

**Tasks:**
1. Add wavelength slider/selector for single-wavelength view
2. Add sample comparison feature (overlay multiple samples)
3. Implement batch processing with queue display
4. Add comprehensive error handling with user-friendly messages
5. Add help tooltips for all parameters
6. Create "About" page with references
7. Performance optimization using `@st.cache_data`
8. Add keyboard shortcuts for common actions
9. Ensure consistent styling across all pages

**Phase 6 Deliverables:**
- [ ] Interactive features polished
- [ ] Smooth user experience
- [ ] Good error handling with clear messages

---

### Phase 7: Testing, Documentation & Deployment Prep

**Goal**: Ensure reliability and prepare for deployment.

**Tasks:**
1. Test all workflows end-to-end
2. Test with edge cases (missing files, invalid data)
3. Create `README_GUI.md` with usage instructions
4. Add inline comments to all new code
5. Verify no regressions in core library
6. Add deployment configuration (`.streamlit/config.toml`)
7. Test deployment to Streamlit Cloud (or document process)

**Phase 7 Deliverables:**
- [ ] All workflows tested
- [ ] Documentation complete
- [ ] Ready for deployment
- [ ] Core library unchanged

---

## 4. GUI SCHEME

### 4.1 Visual Layout (ASCII Wireframe)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ECM Polarimetry                                            [About] [Help]  │
├─────────────────┬───────────────────────────────────────────────────────────┤
│                 │                                                           │
│  [SIDEBAR]      │                    [MAIN CONTENT AREA]                    │
│                 │                                                           │
│  ┌───────────┐  │  Page content varies by selection.                        │
│  │  🏠 Home  │  │  All plots are interactive Plotly.                        │
│  ├───────────┤  │  All Mueller matrices shown NORMALIZED.                   │
│  │ ⚙️ Config │  │                                                           │
│  ├───────────┤  │                                                           │
│  │ 🔧 Calib  │  │                                                           │
│  ├───────────┤  │                                                           │
│  │ 📈 Process│  │                                                           │
│  ├───────────┤  │                                                           │
│  │ 🎯 Lu-Chip│  │                                                           │
│  └───────────┘  │                                                           │
│                 │                                                           │
│  ─────────────  │                                                           │
│                 │                                                           │
│  Status:        │                                                           │
│  ● Calibrated   │                                                           │
│    (or)         │                                                           │
│  ○ Not calibr.  │                                                           │
│                 │                                                           │
└─────────────────┴───────────────────────────────────────────────────────────┘
```

### 4.2 Page-by-Page Layout

#### HOME PAGE
```
┌─────────────────────────────────────────────────────────────────┐
│                     ECM Polarimetry GUI                         │
│                                                                 │
│  Welcome to the ECM calibration interface for Mueller matrix    │
│  polarimetry.                                                   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  WORKFLOW                                                │   │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────┐│   │
│  │  │ Config   │ -> │ Calibrate│ -> │ Process  │ -> │L-C ││   │
│  │  └──────────┘    └──────────┘    └──────────┘    └────┘│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Status: ● Calibrated  /  ○ Not calibrated                     │
│                                                                 │
│  Quick Actions:                                                 │
│  [Load Previous Calibration]  [Start New Calibration]          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### CONFIGURATION PAGE
```
┌─────────────────────────────────────────────────────────────────┐
│  Configuration                                    [Save] [Load] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ▼ Data Paths                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │                                                 │    │   │
│  │  │     Drag & drop folder here                     │    │   │
│  │  │           or click to browse                    │    │   │
│  │  │                                                 │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  │  Data Directory:    [________________________] [Browse]  │   │
│  │  Output Directory:  [________________________] [Browse]  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ▼ Wavelength Settings                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Range (nm):  Min [====○========] Max   400 - 1000 nm   │   │
│  │  Reference:   [633.0] nm                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ▼ Acquisition                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Angular Positions: [96]                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Note: Second retarder (FP2) is auto-detected from files.      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### CALIBRATION PAGE
```
┌─────────────────────────────────────────────────────────────────┐
│  Calibration                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ▼ Calibration Files                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  [Discover Files]                                        │   │
│  │                                                          │   │
│  │  ✓ Dark:     dark.bin                                   │   │
│  │  ✓ Air:      air.bin                                    │   │
│  │  ✓ Pol 0°:   pol_0deg.bin                               │   │
│  │  ✓ Pol 45°:  pol_45deg.bin                              │   │
│  │  ✓ Ret 90°:  ret_90deg.bin (FP1)                        │   │
│  │  ✓ Ret 45°:  ret_45deg.bin (FP2) [Auto-detected]        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Run Calibration]                                              │
│                                                                 │
│  ▼ Progress                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ████████████████████░░░░░░░░░░  75%                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ▼ Quality Summary                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Wavelengths calibrated: 245  (400 - 1000 nm)           │   │
│  │  Mean eigenvalue ratio: 1.2e-5                           │   │
│  │                                                          │   │
│  │  Quality Breakdown:                                      │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ Excellent (<1e-4)  ████████████████░░  180 (73%) │    │   │
│  │  │ Good (<1e-3)       ████░░░░░░░░░░░░░░   45 (18%) │    │   │
│  │  │ Acceptable (<1e-2) ██░░░░░░░░░░░░░░░░   15 (6%)  │    │   │
│  │  │ Marginal (<0.1)    █░░░░░░░░░░░░░░░░░    5 (2%)  │    │   │
│  │  │ Poor (≥0.1)        ░░░░░░░░░░░░░░░░░░    0 (0%)  │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  │  [Save Calibration]  [Load Calibration]                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ▼ Diagnostic Plots (Interactive)                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  [Eigenvalue Ratio] [W Matrix] [A Matrix] [Air Valid.]  │   │
│  │                                                          │   │
│  │         [INTERACTIVE PLOTLY FIGURE]                      │   │
│  │         - Hover for values                               │   │
│  │         - Zoom/pan enabled                               │   │
│  │         - Export button in corner                        │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### SAMPLE PROCESSING PAGE
```
┌─────────────────────────────────────────────────────────────────┐
│  Sample Processing                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Status: ● Calibrated (loaded from: calibration_20240115.npz)  │
│          [Load Different Calibration]                           │
│                                                                 │
│  ▼ Sample Selection                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │     Drag & drop sample folder here              │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  │  Sample Directory: [________________________] [Browse]   │   │
│  │  [Discover Samples]                                      │   │
│  │                                                          │   │
│  │  Available Samples:                                      │   │
│  │  [✓] QWP_0deg                                           │   │
│  │  [✓] QWP_45deg                                          │   │
│  │  [ ] HWP_0deg                                            │   │
│  │  [ ] Unknown_sample                                      │   │
│  │                                                          │   │
│  │  [Select All] [Deselect All]                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Process Selected Samples]                                     │
│  ████████████████████████████████████  100%                     │
│                                                                 │
│  ▼ Results: QWP_0deg                            [Sample ▼]     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │  View: [4×4 Matrix] [Select Elements]                    │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │                                                 │    │   │
│  │  │    [INTERACTIVE PLOTLY 4×4 MUELLER MATRIX]      │    │   │
│  │  │              (NORMALIZED)                       │    │   │
│  │  │                                                 │    │   │
│  │  │    - Hover shows mᵢⱼ value at wavelength       │    │   │
│  │  │    - Each subplot is zoomable                   │    │   │
│  │  │                                                 │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  │  [Save Results (.npz)] [Export Plot (.png)]              │   │
│  │  [Export Data (.csv)]                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### MUELLER ELEMENT SELECTOR (Pop-up/Modal)
```
┌─────────────────────────────────────────────────────────────────┐
│  Select Mueller Matrix Elements                          [X]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Click to select elements to overlay:                           │
│                                                                 │
│     ┌─────┬─────┬─────┬─────┐                                  │
│     │[✓]  │[ ]  │[ ]  │[ ]  │                                  │
│     │m₁₁  │m₁₂  │m₁₃  │m₁₄  │                                  │
│     ├─────┼─────┼─────┼─────┤                                  │
│     │[ ]  │[✓]  │[ ]  │[ ]  │                                  │
│     │m₂₁  │m₂₂  │m₂₃  │m₂₄  │                                  │
│     ├─────┼─────┼─────┼─────┤                                  │
│     │[ ]  │[ ]  │[✓]  │[ ]  │                                  │
│     │m₃₁  │m₃₂  │m₃₃  │m₃₄  │                                  │
│     ├─────┼─────┼─────┼─────┤                                  │
│     │[ ]  │[ ]  │[ ]  │[✓]  │                                  │
│     │m₄₁  │m₄₂  │m₄₃  │m₄₄  │                                  │
│     └─────┴─────┴─────┴─────┘                                  │
│                                                                 │
│  Quick Select: [Show Diagonal] [Show Isotropic] [Show Anisotropic] │
│                                                                 │
│  [Apply Selection]  [Cancel]                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### POST-PROCESSING PAGE (Lu-Chipman)
```
┌─────────────────────────────────────────────────────────────────┐
│  Lu-Chipman Decomposition                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Sample: [QWP_0deg ▼]    [Load from File]                       │
│                                                                 │
│  [Run Decomposition]                                            │
│                                                                 │
│  ▼ Summary Statistics                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Parameter          │  Mean ± Std        │  Range       │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  Diattenuation (D)  │  0.0023 ± 0.0012   │ 0.001-0.005  │   │
│  │  Retardance (R)     │  89.7° ± 2.1°      │ 85° - 95°    │   │
│  │  Depol. Index (DI)  │  0.9987 ± 0.0005   │ 0.997-1.000  │   │
│  │  Fast-axis (ψ)      │  0.2° ± 0.5°       │ -1° - 1°     │   │
│  │  Ellipticity (χ)    │  0.1° ± 0.3°       │ -0.5° - 0.5° │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ▼ Parameter Plots (Interactive)                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  [DI] [Retardance] [Diattenuation] [Axis Angles]        │   │
│  │                                                          │   │
│  │         [INTERACTIVE PLOTLY FIGURE]                      │   │
│  │         - Hover for exact values                         │   │
│  │         - Toggle curves with legend clicks               │   │
│  │         - Reference lines (QWP=90°, HWP=180°)           │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ▼ Decomposed Matrices (Normalized)                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  [M_D (Diattenuator)] [M_R (Retarder)] [M_Δ (Depol.)]   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Save Decomposition (.npz)]                                    │
│  [Export Plots (.png)]  [Export Data (.csv)]                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. CODE STYLE REQUIREMENTS

### 5.1 General Principles - RESEARCHER-FRIENDLY CODE

```python
# ============================================================================
# GOOD: Clear, explicit, easy to understand and modify
# ============================================================================

def run_calibration(config, progress_callback=None):
    """
    Run ECM calibration with the given configuration.

    This function orchestrates the complete calibration workflow.

    Parameters
    ----------
    config : ECMConfig
        Configuration object with all calibration parameters.
    progress_callback : callable, optional
        Function to update progress bar: callback(fraction)
        where fraction is between 0.0 and 1.0.

    Returns
    -------
    result : CalibrationResult
        Calibration matrices (W, A) and parameters.
    diagnostics : CalibrationDiagnostics
        Quality metrics and intermediate data.

    Example
    -------
    >>> config = ECMConfig()
    >>> config.paths.data_dir = Path("/my/data")
    >>> result, diagnostics = run_calibration(config)
    """
    # -------------------------------------------------
    # Step 1: Validate that we have a data directory
    # -------------------------------------------------
    if config.paths.data_dir is None:
        raise ValueError("Data directory must be specified in config")

    # -------------------------------------------------
    # Step 2: Run the actual calibration
    # -------------------------------------------------
    result, diagnostics = calibrate_transmission(config, progress_callback)

    return result, diagnostics


# ============================================================================
# BAD: Overly clever, hard to understand or modify
# ============================================================================

def run_cal(c, cb=None):
    return calibrate_transmission(c, cb) if c.paths.data_dir else None
```

### 5.2 Streamlit-Specific Guidelines

```python
# ============================================================================
# Session State: Use clear, consistent keys
# ============================================================================

# Initialize session state at the top of each page
if 'calibration_result' not in st.session_state:
    st.session_state.calibration_result = None

if 'is_calibrated' not in st.session_state:
    st.session_state.is_calibrated = False


# ============================================================================
# Caching: Use for expensive operations
# ============================================================================

@st.cache_data
def load_wavelengths(filepath):
    """
    Load and cache wavelength calibration data.

    Cached to avoid reloading on every page refresh.
    """
    return np.loadtxt(filepath)


# ============================================================================
# Layout: Use columns and expanders for organization
# ============================================================================

# Two-column layout for side-by-side inputs
col1, col2 = st.columns(2)
with col1:
    wl_min = st.number_input("Min Wavelength (nm)", value=400.0)
with col2:
    wl_max = st.number_input("Max Wavelength (nm)", value=1000.0)

# Expanders for optional/advanced sections
with st.expander("Wavelength Settings", expanded=True):
    # ... wavelength inputs ...
    pass


# ============================================================================
# Progress Bars: Simple and clean
# ============================================================================

# Create progress bar
progress_bar = st.progress(0)

# Update during processing (just the bar, no text)
for i, wavelength in enumerate(wavelengths):
    # ... processing ...
    progress_bar.progress((i + 1) / len(wavelengths))

# Clear when done
progress_bar.empty()


# ============================================================================
# Plotly Plots: Interactive and informative
# ============================================================================

import plotly.graph_objects as go

def create_interactive_plot(wavelengths, data, title):
    """
    Create an interactive Plotly plot.

    Features:
    - Hover shows exact values
    - Zoom and pan enabled
    - Export button in corner
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=wavelengths,
        y=data,
        mode='lines',
        name='Data',
        hovertemplate='λ = %{x:.1f} nm<br>Value = %{y:.4f}<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        xaxis_title='Wavelength (nm)',
        yaxis_title='Value',
        hovermode='x unified'
    )

    return fig

# Display in Streamlit
st.plotly_chart(fig, use_container_width=True)
```

### 5.3 File Organization Template

```python
"""
Page Name - Brief description of what this page does.

This page handles [main functionality]. Users can:
- [Action 1]
- [Action 2]
- [Action 3]

Author: Daniel Vala
"""

import streamlit as st
import numpy as np
from pathlib import Path

# Local imports
from components.plots_plotly import create_mueller_plot
from utils.session_state import get_calibration, is_calibrated


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="ECM - Page Name",
    page_icon="📊",
    layout="wide"
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def helper_function():
    """Brief description of what this helper does."""
    pass


# ============================================================================
# MAIN PAGE CONTENT
# ============================================================================

def main():
    """Main page content."""

    st.title("Page Title")

    # -------------------------------------------------
    # Section 1: Description
    # -------------------------------------------------
    st.write("Brief explanation of this section...")

    # -------------------------------------------------
    # Section 2: Another section
    # -------------------------------------------------
    with st.expander("Section Title", expanded=True):
        # ... content ...
        pass


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
```

---

## 6. PHASE INSTRUCTIONS

### For Each Phase, Claude Code Should:

1. **Read this prompt** and understand the current phase requirements
2. **Ask clarifying questions** if anything is ambiguous
3. **Implement only the current phase** - do not jump ahead
4. **Test the implementation** before completing
5. **Report what was done** with a summary of changes
6. **Wait for user approval** before proceeding to next phase

### Phase Completion Checklist

Before marking a phase complete, verify:

- [ ] All tasks in the phase are done
- [ ] Code follows style guidelines (clear, commented, researcher-friendly)
- [ ] App runs without errors (`streamlit run app.py`)
- [ ] Interactive Plotly plots work (hover, zoom, etc.)
- [ ] Core library tests still pass (`pytest` - if applicable)
- [ ] No changes to physics/math logic unless explicitly requested
- [ ] All Mueller matrices are shown NORMALIZED

---

## 7. TECHNICAL NOTES

### 7.1 Session State Keys

Use these consistent keys for session state:

```python
st.session_state.config              # ECMConfig object
st.session_state.is_calibrated       # Boolean: True if calibration loaded
st.session_state.calibration_result  # CalibrationResult object
st.session_state.calibration_diag    # CalibrationDiagnostics object
st.session_state.processed_samples   # Dict[sample_name, MuellerMatrixResult]
st.session_state.lu_chipman_results  # Dict[sample_name, LuChipmanResult]
st.session_state.current_sample      # Currently selected sample name
st.session_state.selected_elements   # List of (i,j) tuples for MM elements
```

### 7.2 Required Dependencies

**requirements-gui.txt:**
```
streamlit>=1.30.0
plotly>=5.18.0
streamlit-file-browser>=0.2.0
pandas>=2.0.0
watchdog>=3.0.0
kaleido>=0.2.1          # For Plotly static image export
openpyxl>=3.1.0         # For Excel export (optional)
```

### 7.3 Running the App

```bash
# From project root
cd streamlit_app
streamlit run app.py

# Or with specific port
streamlit run app.py --server.port 8502

# For development (auto-reload)
streamlit run app.py --server.runOnSave true
```

### 7.4 Export Functions

```python
# PNG Export for Plotly figures
import plotly.io as pio

def export_figure_png(fig, filename):
    """Export Plotly figure to PNG file."""
    fig.write_image(filename, scale=2)  # scale=2 for high resolution
    return filename

# CSV Export for data
import pandas as pd

def export_mueller_csv(M_normalized, wavelengths, filename):
    """
    Export normalized Mueller matrix data to CSV.

    Format: wavelength, m11, m12, m13, m14, m21, ..., m44
    """
    n_wl = len(wavelengths)

    # Flatten Mueller matrix for each wavelength
    data = {'wavelength_nm': wavelengths}
    for i in range(4):
        for j in range(4):
            col_name = f'm{i+1}{j+1}'
            data[col_name] = M_normalized[i, j, :]

    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    return filename
```

### 7.5 Plotly Interactive Features

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_mueller_matrix_plot(M_normalized, wavelengths, title="Mueller Matrix"):
    """
    Create interactive 4×4 Mueller matrix plot.

    Features:
    - Hover shows element name and value
    - Each subplot zoomable independently
    - Synchronized x-axis (wavelength)
    """
    fig = make_subplots(
        rows=4, cols=4,
        subplot_titles=[f'm{i+1}{j+1}' for i in range(4) for j in range(4)],
        shared_xaxes=True,
        vertical_spacing=0.05,
        horizontal_spacing=0.05
    )

    for i in range(4):
        for j in range(4):
            fig.add_trace(
                go.Scatter(
                    x=wavelengths,
                    y=M_normalized[i, j, :],
                    mode='lines',
                    name=f'm{i+1}{j+1}',
                    hovertemplate=f'm{i+1}{j+1}<br>λ=%{{x:.1f}} nm<br>Value=%{{y:.4f}}<extra></extra>',
                    showlegend=False
                ),
                row=i+1, col=j+1
            )

    fig.update_layout(
        title=title,
        height=800,
        hovermode='x unified'
    )

    # Set y-limits for normalized matrix
    for i in range(4):
        for j in range(4):
            if i == 0 and j == 0:
                fig.update_yaxes(range=[0.95, 1.05], row=i+1, col=j+1)
            else:
                fig.update_yaxes(range=[-1.1, 1.1], row=i+1, col=j+1)

    return fig
```

### 7.6 Drag-and-Drop Implementation

```python
import streamlit as st
from streamlit_file_browser import st_file_browser

def directory_selector(label, key):
    """
    Create a directory selector with drag-drop and browse options.
    """
    st.write(f"**{label}**")

    # Option 1: Text input
    path = st.text_input(
        "Enter path or use browser below:",
        key=f"{key}_text",
        placeholder="/path/to/directory"
    )

    # Option 2: File browser
    with st.expander("Browse files"):
        selected = st_file_browser(
            path=path or ".",
            key=f"{key}_browser",
            show_choose_button=True
        )
        if selected:
            path = selected.get('path', path)

    # Validate path
    if path:
        p = Path(path)
        if p.exists() and p.is_dir():
            st.success(f"✓ Valid directory: {len(list(p.glob('*.bin')))} .bin files found")
        else:
            st.error("✗ Directory not found")

    return path
```

---

## APPENDIX: Quick Reference

### Key Imports

```python
# Streamlit
import streamlit as st

# Plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# ECM Core
from ecm.config import ECMConfig
from ecm.core import calibrate_transmission
from ecm.core.sample_processing import process_sample
from ecm.postprocessing import lu_chipman_decomposition

# ECM I/O
from ecm.io import save_calibration, load_calibration, discover_sample_files
from ecm.utils.io import load_spectral_data

# Standard
import numpy as np
import pandas as pd
from pathlib import Path
```

### Main Workflow Code

```python
# 1. Configuration
cfg = ECMConfig()
cfg.paths.data_dir = Path("/path/to/data")
cfg.paths.calibration_output_dir = Path.cwd() / "output"

# 2. Calibration
result, diagnostics = calibrate_transmission(cfg)
save_calibration(result, diagnostics, cfg)

# 3. Sample Processing
sample_data, _ = load_spectral_data(sample_path, cfg)
sample_data = sample_data[:, result.wl_indices] - diagnostics.I_dark
mueller_result = process_sample(sample_data, result.A, result.W, result.inv_W_mod)
M_normalized = mueller_result.M_normalized  # ALWAYS USE NORMALIZED

# 4. Post-processing
lu_result = lu_chipman_decomposition(M_normalized)
```

---

**END OF PROMPT**

*This document is designed to be used with Claude Code. Phase 0 contains the debugging instructions. Work through phases sequentially, getting user approval after each phase.*
