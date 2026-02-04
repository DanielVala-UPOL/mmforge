# ECM Polarimetry GUI - Phase 6 Instructions

**Purpose**: Step-by-step instructions for implementing Phase 6 polish and enhancements
**Phase**: 6 - Polish & Enhancements
**Author**: Daniel Vala
**Date**: February 2026

---

## TABLE OF CONTENTS

1. [Overview](#1-overview)
2. [Priority 1: Essential Polish](#2-priority-1-essential-polish)
3. [Priority 2: Nice to Have](#3-priority-2-nice-to-have)
4. [Priority 3: Optional](#4-priority-3-optional)
5. [Verification Checklist](#5-verification-checklist)

---

## 1. OVERVIEW

### 1.1 Current State

Phase 5 is complete. The app has full functionality:
- Configuration page with path inputs and settings
- Calibration page with ECM integration, quality breakdown, and eigenvalue plot
- Processing page with sample discovery, batch processing, and Mueller matrix visualization
- Parameters page with Lu-Chipman decomposition, parameter plots, and summary table
- Export to .npz and .csv works; PNG export buttons exist but are disabled

### 1.2 Phase 6 Goals

Focus on polish and quality-of-life improvements:
- Enable PNG export (infrastructure already exists)
- Add caching for better performance
- Add reset functionality
- Improve error messages
- Add batch export
- Minor UI improvements

### 1.3 Important Constraints

- **DO NOT** modify physics/math logic in `ecm/` package
- **DO NOT** change existing working functionality
- Keep code simple and well-commented
- Test after each change

---

## 2. PRIORITY 1: ESSENTIAL POLISH

### 2.1 Enable PNG Export Buttons

**Goal**: Connect the disabled "Export Plot (.png)" buttons to working export functionality.

**Files to modify**:
- `streamlit_app/pages/3_Processing.py`
- `streamlit_app/pages/4_Parameters.py`

**Implementation**:

The `export_figure_png()` function already exists in `streamlit_app/utils/export.py`. Use it with `st.download_button`.

**Pattern for Processing page** (add after the plot is created):

```python
from utils.export import export_figure_png

# After creating the figure (e.g., fig = create_mueller_matrix_plot(...))
# Replace the disabled button with:

try:
    png_bytes = export_figure_png(fig, "mueller_matrix.png")
    st.download_button(
        label="Export Plot (.png)",
        data=png_bytes,
        file_name=f"{selected_sample}_mueller_matrix.png",
        mime="image/png",
        use_container_width=True
    )
except Exception as e:
    st.button(
        "Export Plot (.png)",
        disabled=True,
        help=f"Export failed: {e}",
        use_container_width=True
    )
```

**Apply to these plots**:
1. Processing page - Mueller matrix 4x4 grid
2. Processing page - Selected elements overlay
3. Processing page - Sample comparison
4. Parameters page - Decomposed matrices (M_D, M_R, M_Δ)
5. Parameters page - Parameter plots (D, DI, R, ν/χ)

**Note**: Each plot section should have its own export button below the plot.

---

### 2.2 Add Streamlit Caching

**Goal**: Improve performance by caching expensive operations.

**Files to modify**:
- `streamlit_app/components/plots_plotly.py`
- `streamlit_app/pages/2_Calibration.py` (file discovery)
- `streamlit_app/pages/3_Processing.py` (sample discovery)

**Implementation**:

**A. Cache plot generation functions** (plots_plotly.py):

Add `@st.cache_data` decorator to pure functions that don't depend on session state:

```python
import streamlit as st

# For functions that take numpy arrays as input:
@st.cache_data
def create_eigenvalue_plot(
    eigenvalue_ratios: ndarray,
    wavelengths: ndarray,
    title: str = "Eigenvalue Ratio (Calibration Quality)"
) -> go.Figure:
    # ... existing code ...
```

**Functions to cache** (read-only, no session state):
- `create_eigenvalue_plot()`
- `create_quality_breakdown_chart()`
- `create_diattenuation_plot()`
- `create_di_plot()`
- `create_retardance_plot()`
- `create_fast_axis_plot()`

**Functions NOT to cache** (depend on selections or multiple samples):
- `create_mueller_matrix_plot()` - m00 parameter varies
- `create_mueller_comparison_plot()` - sample selection varies
- Comparison plots - selections vary

**B. Cache file discovery** (use carefully):

```python
# In 2_Calibration.py - wrap the discovery call
@st.cache_data(ttl=60)  # Cache for 60 seconds
def cached_discover_files(data_dir: str, n_positions: int, wl_min: float, wl_max: float):
    """Cached file discovery to avoid repeated filesystem scans."""
    from ecm.config import ECMConfig
    from ecm.core.file_discovery import discover_calibration_files

    cfg = ECMConfig(
        data_dir=data_dir,
        n_positions=n_positions,
        wavelength_range=(wl_min, wl_max)
    )
    return discover_calibration_files(cfg)
```

**Note**: Use `ttl` (time-to-live) for file discovery so it refreshes periodically.

---

### 2.3 Add "Reset Session" Button

**Goal**: Allow users to clear all data and start fresh without reloading the app.

**File to modify**: `streamlit_app/app.py`

**Implementation**:

Add a Reset button in the Home page with confirmation dialog:

```python
# Add at the bottom of main() in app.py, before the "About ECM" expander

st.markdown("---")

# Reset Session
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("Reset Session", use_container_width=True, type="secondary"):
        st.session_state['_confirm_reset'] = True

# Confirmation dialog
if st.session_state.get('_confirm_reset', False):
    st.warning("This will clear all calibration data, processed samples, and decomposition results.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Confirm Reset", type="primary", use_container_width=True):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state['_confirm_reset'] = False
            st.rerun()
```

---

## 3. PRIORITY 2: NICE TO HAVE

### 3.1 Improve Error Messages

**Goal**: Make error messages actionable with suggestions.

**Files to modify**:
- `streamlit_app/components/file_browser.py`
- `streamlit_app/pages/2_Calibration.py`
- `streamlit_app/pages/3_Processing.py`

**Pattern**:

```python
# BEFORE (generic error)
st.error("Directory not found")

# AFTER (actionable error)
st.error("Directory not found. Please check that the path exists and is accessible.")
```

**Specific improvements**:

| Location | Current Message | Improved Message |
|----------|-----------------|------------------|
| file_browser.py | "Directory not found" | "Directory not found. Check that the path exists and you have read permissions." |
| file_browser.py | "Path is not a directory" | "Path exists but is not a directory. Please enter a folder path, not a file path." |
| file_browser.py | "Valid directory: X .bin files found" (when X=0) | "Directory exists but contains no .bin files. Check that calibration data files are present." |
| 2_Calibration.py | "Missing: DARK, ST, ..." | "Missing calibration files: DARK, ST. These files are required for ECM calibration." |
| 3_Processing.py | "No samples found" | "No sample files found in the selected directory. Sample files should be .bin format." |

---

### 3.2 Add Batch Export Functionality

**Goal**: Export all data at once as a zip file.

**Files to modify**:
- `streamlit_app/pages/3_Processing.py`
- `streamlit_app/pages/4_Parameters.py`
- `streamlit_app/utils/export.py` (add new function)

**Implementation**:

**A. Add helper function to export.py**:

```python
import io
import zipfile

def create_export_zip(files_dict: dict) -> bytes:
    """
    Create a zip file from a dictionary of filename -> content pairs.

    Parameters
    ----------
    files_dict : dict
        Dictionary mapping filenames to content (str for CSV, bytes for PNG).

    Returns
    -------
    zip_bytes : bytes
        Zip file as bytes for download.
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files_dict.items():
            if isinstance(content, str):
                zf.writestr(filename, content.encode('utf-8'))
            else:
                zf.writestr(filename, content)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()
```

**B. Add "Export All" button to Processing page**:

```python
from utils.export import export_mueller_csv, create_export_zip

# In the Export section of Processing page
if st.button("Export All Data (.zip)", use_container_width=True, disabled=not processed_samples):
    files = {}
    for name, result in processed_samples.items():
        csv_content = export_mueller_csv(result.M_normalized, wavelengths, name)
        files[f"{name}_mueller_matrix.csv"] = csv_content

    zip_bytes = create_export_zip(files)
    st.download_button(
        label="Download All (ZIP)",
        data=zip_bytes,
        file_name="ecm_processed_samples.zip",
        mime="application/zip"
    )
```

---

### 3.3 Persist Comparison Selections

**Goal**: Remember which samples are selected for comparison when switching views.

**Files to modify**:
- `streamlit_app/pages/3_Processing.py`
- `streamlit_app/pages/4_Parameters.py`

**Implementation**:

Store comparison selections in session state with consistent keys:

```python
# Initialize at page load
if 'processing_compare_selection' not in st.session_state:
    st.session_state['processing_compare_selection'] = []

# When user selects samples for comparison, update session state
# Use the session state value as default for checkboxes
```

This ensures selections persist across:
- View mode switches (4x4 Grid → Compare Samples → Selected Elements)
- Tab switches
- Page navigation and return

---

## 4. PRIORITY 3: OPTIONAL

### 4.1 Configuration Validation Warnings

**Goal**: Warn users about unusual configuration values.

**File to modify**: `streamlit_app/pages/1_Configuration.py`

**Implementation**:

Add validation after the wavelength slider:

```python
wl_min, wl_max = wl_range

# Validation warnings (non-blocking)
if wl_min < 300:
    st.warning("Wavelength minimum is below 300 nm. Most polarimeters operate in the visible range (400-800 nm).")
if wl_max > 1500:
    st.warning("Wavelength maximum exceeds 1500 nm. Verify your detector supports this range.")

# Similar for n_positions
typical_positions = [36, 72, 96, 144]
if n_positions not in typical_positions:
    st.info(f"Note: {n_positions} angular positions is atypical. Common values are 36, 72, 96, or 144.")
```

---

### 4.2 UI Micro-Improvements

**Goal**: Small improvements to placeholder text and help tooltips.

**Improvements**:

1. **Empty state messages** - When no data is loaded, show helpful guidance:
```python
# Instead of just st.info("No processed samples")
st.info("No processed samples yet. Go to the Processing page to load and process sample data.")
```

2. **Add missing help tooltips**:
```python
# Example: Add help to buttons that might be confusing
st.button("Clear All", help="Deselect all samples")
```

---

## 5. VERIFICATION CHECKLIST

After implementing Phase 6, verify:

### Priority 1 - Essential

- [ ] PNG export works on Processing page (Mueller matrix plot)
- [ ] PNG export works on Processing page (Selected elements plot)
- [ ] PNG export works on Processing page (Comparison plot)
- [ ] PNG export works on Parameters page (Decomposed matrices)
- [ ] PNG export works on Parameters page (Parameter plots)
- [ ] Caching is applied to appropriate plot functions
- [ ] File discovery caching works (no repeated filesystem scans)
- [ ] Reset Session button appears on Home page
- [ ] Reset Session clears all data after confirmation
- [ ] App still runs without errors: `streamlit run app.py`

### Priority 2 - Nice to Have

- [ ] Error messages include actionable suggestions
- [ ] "Export All" zip download works on Processing page
- [ ] "Export All" zip download works on Parameters page
- [ ] Sample selections persist when switching view modes

### Priority 3 - Optional

- [ ] Wavelength range warnings appear for unusual values
- [ ] Angular position info appears for atypical values
- [ ] Placeholder text is helpful and guides users

---

## IMPLEMENTATION ORDER

Recommended order for implementation:

1. **PNG Export** (highest impact, infrastructure exists)
2. **Reset Session** (simple, high utility)
3. **Caching** (performance improvement)
4. **Error Messages** (quick wins)
5. **Batch Export** (nice to have)
6. **Persist Selections** (nice to have)
7. **Validation Warnings** (optional)
8. **UI Micro-Improvements** (optional)

---

**END OF INSTRUCTIONS**

*Follow these instructions step-by-step. Test after each major change. Report any issues or ambiguities.*
