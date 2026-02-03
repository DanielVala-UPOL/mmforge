# ECM Polarimetry GUI - UI/UX Refinement Instructions

**Purpose**: Step-by-step instructions for Claude Code to implement UI/UX improvements
**Phase**: Post Phase 1 (basic layout complete)
**Author**: Daniel Vala
**Date**: February 2026

---

## TABLE OF CONTENTS

1. [Overview](#1-overview)
2. [Required Packages](#2-required-packages)
3. [Global Changes](#3-global-changes)
4. [Page-Specific Changes](#4-page-specific-changes)
5. [New Components](#5-new-components)
6. [Verification Checklist](#6-verification-checklist)

---

## 1. OVERVIEW

### 1.1 Goals

This document describes UI/UX refinements to apply AFTER Phase 1 is complete. The changes focus on:

- Cleaner, icon-free interface
- Sticky header with app navigation
- Modern file/folder browsing (web-based)
- Streamlined page layouts
- Warning messages as tooltips instead of permanent alerts

### 1.2 Design Principles

- **No icons**: Remove all emoji icons unless explicitly requested
- **Minimal clutter**: Remove redundant sections and navigation buttons
- **Modern file handling**: Use `streamlit-file-browser` for folder selection
- **Tooltips over warnings**: Use `help` parameter and hover states

### 1.3 Important Notes

- **DO NOT** use `tkinter` for file dialogs (local-only, won't work in deployed apps)
- **DO** use `streamlit-file-browser` (works in cloud deployments)
- Theme toggle uses Streamlit's built-in settings (hamburger menu → Settings → Theme)

---

## 2. REQUIRED PACKAGES

### 2.1 Add to requirements-gui.txt

```
streamlit>=1.30.0
streamlit-file-browser>=0.2.0
streamlit-antd-components>=0.3.0
plotly>=5.18.0
pandas>=2.0.0
watchdog>=3.0.0
kaleido>=0.2.1
```

### 2.2 Package Purposes

| Package | Purpose |
|---------|---------|
| `streamlit-file-browser` | Web-based folder/file selection (works in cloud) |
| `streamlit-antd-components` | Modern UI components (buttons, alerts, dividers) |

### 2.3 Installation

```bash
pip install streamlit-file-browser streamlit-antd-components
```

---

## 3. GLOBAL CHANGES

### 3.1 Remove All Icons

**Scope**: All pages and components

**Action**: Remove emoji prefixes from:
- Page titles (e.g., `st.title("🔬 ECM Polarimetry")` → `st.title("ECM Polarimetry")`)
- Button labels (e.g., `"💾 Save Config"` → `"Save Config"`)
- Expander labels (e.g., `"📁 Data Paths"` → `"Data Paths"`)
- Subheaders
- Any other UI text

**Exception**: Keep the calibration status indicators in sidebar:
- `🟢` for Calibrated
- `🔴` for Not calibrated

These are functional indicators, not decorative icons.

---

### 3.2 Implement Sticky Header

**Location**: Create new component `streamlit_app/components/header.py`

**Structure**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│  ECM Polarimetry                              [Settings] [Help]         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Left side**: App name "ECM Polarimetry"
**Right side**: Settings button, Help button

**Implementation**:

```python
"""
Sticky Header Component

Provides a fixed header at the top of all pages with:
- App name (left)
- Settings and Help buttons (right)
"""

import streamlit as st


def render_header():
    """
    Render the sticky header.

    Call this at the top of every page, AFTER st.set_page_config().
    """
    # -------------------------------------------------
    # CSS for sticky positioning
    # -------------------------------------------------
    st.markdown("""
    <style>
        /* Sticky header container */
        .sticky-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 60px;
            background-color: white;
            border-bottom: 1px solid #e0e0e0;
            z-index: 999;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            .sticky-header {
                background-color: #0e1117;
                border-bottom-color: #262730;
            }
        }

        .header-title {
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0;
            color: #262730;
        }

        @media (prefers-color-scheme: dark) {
            .header-title {
                color: #fafafa;
            }
        }

        .header-buttons {
            display: flex;
            gap: 10px;
        }

        /* Push main content down to avoid overlap */
        .main .block-container {
            padding-top: 80px !important;
        }

        /* Hide default Streamlit header elements if desired */
        header[data-testid="stHeader"] {
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # Header HTML structure
    # -------------------------------------------------
    # Note: Buttons are rendered via Streamlit below
    st.markdown("""
    <div class="sticky-header">
        <h1 class="header-title">ECM Polarimetry</h1>
        <div class="header-buttons" id="header-buttons-placeholder"></div>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # Settings and Help buttons (using columns trick)
    # -------------------------------------------------
    # Create a container that visually aligns with header
    # This is a workaround since pure HTML buttons can't trigger Streamlit

    col1, col2, col3, col4, col5 = st.columns([6, 1, 1, 0.5, 0.5])

    with col4:
        settings_clicked = st.button("Settings", key="header_settings", help="Open settings")

    with col5:
        help_clicked = st.button("Help", key="header_help", help="Open help")

    # -------------------------------------------------
    # Handle button clicks - open modals
    # -------------------------------------------------
    if settings_clicked:
        st.session_state['show_settings_modal'] = True

    if help_clicked:
        st.session_state['show_help_modal'] = True

    # Render modals if triggered
    _render_settings_modal()
    _render_help_modal()


def _render_settings_modal():
    """Render the settings modal dialog."""
    if st.session_state.get('show_settings_modal', False):
        with st.container():
            st.markdown("---")
            st.subheader("Settings")

            col1, col2 = st.columns([4, 1])
            with col2:
                if st.button("Close", key="close_settings"):
                    st.session_state['show_settings_modal'] = False
                    st.rerun()

            st.markdown("**Theme**")
            st.info(
                "To change the app theme, click the hamburger menu (☰) in the top-right corner, "
                "then go to Settings → Theme. You can choose Light, Dark, or System default."
            )

            st.markdown("**About**")
            st.write("ECM Polarimetry GUI v1.0")
            st.write("Eigenvalue Calibration Method for Mueller Matrix Polarimetry")

            st.markdown("---")


def _render_help_modal():
    """Render the help modal dialog."""
    if st.session_state.get('show_help_modal', False):
        with st.container():
            st.markdown("---")
            st.subheader("Help")

            col1, col2 = st.columns([4, 1])
            with col2:
                if st.button("Close", key="close_help"):
                    st.session_state['show_help_modal'] = False
                    st.rerun()

            st.markdown("""
            **Quick Reference**

            **Workflow:**
            1. **Configure** - Set data paths and wavelength range
            2. **Calibrate** - Run ECM calibration on calibration samples
            3. **Process** - Extract Mueller matrices from sample measurements
            4. **Parameters** - Lu-Chipman decomposition for physical parameters

            **Tips:**
            - Calibration status is shown in the sidebar
            - All Mueller matrices are displayed normalized
            - Use the element selector to overlay specific matrix elements
            - Export plots as PNG, data as CSV

            **References:**
            - Compain et al., "General and self-consistent method for the calibration
              of polarization modulators, polarimeters, and Mueller-matrix ellipsometers",
              *Appl. Opt.* **38**, 3490-3502 (1999)
            """)

            st.markdown("---")
```

**Usage in each page**:
```python
from components.header import render_header

# After st.set_page_config()
render_header()
```

---

### 3.3 Warning Messages as Tooltips

**Current behavior**: Permanent `st.warning()` messages visible on page

**New behavior**: Show warnings as tooltips on hover over the relevant button

**Implementation approach**:

For disabled buttons that need explanation:
```python
# BEFORE (permanent warning)
if st.button("Run Calibration", disabled=True):
    pass
st.warning("Set data directory in Configuration page first")

# AFTER (tooltip on button)
st.button(
    "Run Calibration",
    disabled=True,
    help="Set data directory in Configuration page first"
)
```

**Note**: Streamlit's `help` parameter works on disabled buttons starting from v1.30.

---

## 4. PAGE-SPECIFIC CHANGES

### 4.1 Home Page (app.py)

**Changes**:
1. Remove the title from body (now in sticky header)
2. Remove "Current Status" section entirely
3. Remove "Quick Actions" section entirely
4. Keep: Welcome text, Workflow diagram, About ECM expander

**Resulting structure**:
```
[Sticky Header: ECM Polarimetry    Settings | Help]

Welcome to the Eigenvalue Calibration Method interface...

---
Workflow
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│Configure │→ │Calibrate │→ │ Process  │→ │Parameters│
└──────────┘  └──────────┘  └──────────┘  └──────────┘

▼ About ECM (collapsed expander)
```

**Lines to delete** (approximate, verify in code):
- Title with icon: `st.title("🔬 ECM Polarimetry GUI")`
- Current Status section: lines containing "Current Status", `is_calibrated()` check, metrics
- Quick Actions section: lines with "Quick Actions", button columns

---

### 4.2 Configuration Page (1_Configuration.py)

**Changes**:

| Remove | Keep/Modify |
|--------|-------------|
| Page title icon | Title text "Configuration" |
| "Save Config" button | - |
| "Load Config" button | - |
| Text input for Data Directory | Replace with folder browser |
| Text input for Output Directory | Replace with folder browser |
| Reference Wavelength field | Hardcode 633nm internally |
| FP2 auto-detection note | - |
| Config Summary expander | - |

**New layout**:
```
[Sticky Header]

Configuration
─────────────────────────────────────────────────────────

▼ Data Paths (expanded)
┌─────────────────────────────────────────────────────┐
│  [Drag & drop zone - same as before]                │
│                                                     │
│  Data Directory:    [selected path] [Browse]        │
│  Output Directory:  [selected path] [Browse]        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────┐  ┌─────────────────────────────┐
│ Wavelength Settings         │  │ Acquisition Settings        │
│                             │  │                             │
│ Range (nm):                 │  │ Angular Positions: [96] (?) │
│ [====|----------|====]      │  │                             │
│ 400            1000         │  │                             │
└─────────────────────────────┘  └─────────────────────────────┘
        (side by side using st.columns)
```

**Folder Browser Implementation**:

```python
from streamlit_file_browser import st_file_browser

def folder_selector(label: str, key: str, default_path: str = "") -> str:
    """
    Create a folder selector using streamlit-file-browser.

    Returns the selected folder path.
    """
    st.markdown(f"**{label}**")

    col1, col2 = st.columns([4, 1])

    # Display current path
    current_path = st.session_state.get(f'{key}_path', default_path)

    with col1:
        st.text_input(
            "Path",
            value=current_path,
            key=f"{key}_display",
            disabled=True,
            label_visibility="collapsed"
        )

    with col2:
        browse_clicked = st.button("Browse", key=f"{key}_browse")

    # Show file browser when Browse is clicked
    if browse_clicked or st.session_state.get(f'{key}_browsing', False):
        st.session_state[f'{key}_browsing'] = True

        with st.expander("Select folder", expanded=True):
            selected = st_file_browser(
                path=current_path or ".",
                key=f"{key}_browser",
                show_choose_file=False,
                show_choose_folder=True,
                show_delete_file=False,
                show_download_file=False,
                show_new_folder=False,
                show_upload_file=False,
            )

            if selected and selected.get('target_folder'):
                st.session_state[f'{key}_path'] = selected['target_folder']
                st.session_state[f'{key}_browsing'] = False
                st.rerun()

    return st.session_state.get(f'{key}_path', '')
```

**Wavelength Slider**:
```python
# Use range slider instead of two number inputs
wl_range = st.slider(
    "Wavelength Range (nm)",
    min_value=200,
    max_value=2000,
    value=(400, 1000),
    step=10,
    key="wavelength_range"
)
wl_min, wl_max = wl_range
```

**Angular Positions with Tooltip**:
```python
n_positions = st.number_input(
    "Angular Positions",
    min_value=16,
    max_value=256,
    value=96,
    step=1,
    key="n_positions",
    help="96 positions provides good accuracy while maintaining reasonable measurement time."
)
```

---

### 4.3 Calibration Page (2_Calibration.py)

**Changes**:

| Remove | Modify |
|--------|--------|
| Page title icon | Keep title "Calibration" |
| File path text input (Load Calibration) | Replace with folder browser |

**Save/Load section update**:
```
Save / Load Calibration
─────────────────────────────────────────

Save Current Calibration          Load Saved Calibration
[Save Calibration] (disabled)     [selected file path] [Browse]
                                  [Load Selected]
```

**Implementation for file browser**:
```python
def file_selector_browser(label: str, key: str, file_types: list = None) -> str:
    """
    File selector using streamlit-file-browser.

    Parameters
    ----------
    file_types : list
        List of extensions to filter (e.g., ['.npz'])
    """
    st.markdown(f"**{label}**")

    col1, col2 = st.columns([4, 1])

    current_file = st.session_state.get(f'{key}_file', '')

    with col1:
        st.text_input(
            "File",
            value=current_file,
            disabled=True,
            label_visibility="collapsed",
            key=f"{key}_display"
        )

    with col2:
        browse_clicked = st.button("Browse", key=f"{key}_browse")

    if browse_clicked or st.session_state.get(f'{key}_browsing', False):
        st.session_state[f'{key}_browsing'] = True

        with st.expander("Select file", expanded=True):
            # Determine glob pattern from file_types
            glob_pattern = None
            if file_types:
                extensions = [ext.replace('.', '') for ext in file_types]
                if len(extensions) == 1:
                    glob_pattern = f"*.{extensions[0]}"
                else:
                    glob_pattern = f"*.{{{','.join(extensions)}}}"

            selected = st_file_browser(
                path=".",
                key=f"{key}_browser",
                show_choose_file=True,
                show_choose_folder=False,
                glob_pattern=glob_pattern,
            )

            if selected and selected.get('target_file'):
                st.session_state[f'{key}_file'] = selected['target_file']
                st.session_state[f'{key}_browsing'] = False
                st.rerun()

    return st.session_state.get(f'{key}_file', '')
```

---

### 4.4 Processing Page (3_Processing.py)

**Changes**:

| Remove |
|--------|
| Page title icon |
| "Go to Calibration" button |
| "Go to Configuration" button |

**When not calibrated**, instead of showing navigation buttons:
```python
if not is_calibrated():
    st.warning("Not calibrated. Please run calibration or load a saved calibration first.")
    st.stop()
```

The warning is acceptable here since the user cannot proceed at all without calibration.

---

### 4.5 Lu-Chipman Page → Parameters Extraction (4_Lu_Chipman.py)

**Changes**:

| Change | Details |
|--------|---------|
| Rename file | `4_Lu_Chipman.py` → `4_Parameters.py` |
| Rename page title | "Lu-Chipman Decomposition" → "Parameters Extraction" |
| Rename in page_config | `page_title="ECM - Parameters"` |
| Remove page title icon | Keep "Parameters Extraction" text |
| Remove "Go to Calibration" button | |
| Remove "Go to Processing" button | |

**When prerequisites not met**:
```python
if not is_calibrated():
    st.warning("Not calibrated. Please run calibration first.")
    st.stop()

if not processed_samples:
    st.info("No processed samples available. Process samples first, or load from file.")
    # Keep only the "Load from File" button
    if st.button("Load from File"):
        st.info("File loading will be implemented in Phase 5")
```

---

## 5. NEW COMPONENTS

### 5.1 File Structure Update

After implementing these changes, the components directory should be:

```
streamlit_app/
├── components/
│   ├── __init__.py
│   ├── header.py           # NEW: Sticky header with Settings/Help
│   ├── sidebar.py          # EXISTING: Keep as-is
│   ├── file_browser.py     # UPDATE: Use streamlit-file-browser
│   ├── plots_plotly.py     # EXISTING: Keep as-is
│   └── mueller_selector.py # EXISTING: Keep as-is
```

### 5.2 Updated file_browser.py

Replace the existing `file_browser.py` with implementations using `streamlit-file-browser`:

```python
"""
File Browser Component - Modern folder and file selection.

Uses streamlit-file-browser for web-based browsing that works
in both local and deployed environments.

Author: Daniel Vala
"""

import streamlit as st
from streamlit_file_browser import st_file_browser
from pathlib import Path
from typing import Optional


def directory_selector(
    label: str,
    key: str,
    default_path: str = "",
    help_text: str = ""
) -> Optional[str]:
    """
    Create a directory selector with drag-drop zone and browse button.

    Uses streamlit-file-browser for folder selection.

    Parameters
    ----------
    label : str
        Label for the selector.
    key : str
        Unique key for Streamlit session state.
    default_path : str
        Default path to show.
    help_text : str
        Help text displayed as tooltip on browse button.

    Returns
    -------
    path : str or None
        Selected directory path, or None if not selected.
    """
    st.markdown(f"**{label}**")

    # -------------------------------------------------
    # Drag-and-drop zone (visual)
    # -------------------------------------------------
    st.markdown(
        """
        <div style="
            border: 2px dashed #ccc;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            background-color: #f9f9f9;
            margin-bottom: 10px;
        ">
            <p style="color: #666; margin: 0;">
                Drag and drop folder here<br>
                <small>or use Browse button below</small>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------------------------------
    # Path display and Browse button
    # -------------------------------------------------
    current_path = st.session_state.get(f'{key}_path', default_path)

    col1, col2 = st.columns([4, 1])

    with col1:
        st.text_input(
            "Selected path",
            value=current_path if current_path else "(No folder selected)",
            disabled=True,
            label_visibility="collapsed",
            key=f"{key}_display"
        )

    with col2:
        browse_clicked = st.button(
            "Browse",
            key=f"{key}_browse",
            help=help_text if help_text else "Select a folder"
        )

    # -------------------------------------------------
    # File browser (shown when Browse clicked)
    # -------------------------------------------------
    if browse_clicked:
        st.session_state[f'{key}_browsing'] = True

    if st.session_state.get(f'{key}_browsing', False):
        with st.expander("Select folder", expanded=True):
            start_path = current_path if current_path and Path(current_path).exists() else "."

            browser_result = st_file_browser(
                path=start_path,
                key=f"{key}_browser",
                show_choose_file=False,
                show_choose_folder=True,
                show_delete_file=False,
                show_download_file=False,
                show_new_folder=True,
                show_upload_file=False,
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Select This Folder", key=f"{key}_select"):
                    if browser_result and browser_result.get('current_path'):
                        st.session_state[f'{key}_path'] = browser_result['current_path']
                    st.session_state[f'{key}_browsing'] = False
                    st.rerun()
            with col2:
                if st.button("Cancel", key=f"{key}_cancel"):
                    st.session_state[f'{key}_browsing'] = False
                    st.rerun()

    # -------------------------------------------------
    # Validation
    # -------------------------------------------------
    selected_path = st.session_state.get(f'{key}_path', '')

    if selected_path:
        p = Path(selected_path)
        if p.exists() and p.is_dir():
            bin_files = list(p.glob("*.bin"))
            st.success(f"Valid directory: {len(bin_files)} .bin files found")
            return selected_path
        else:
            st.error("Directory not found")
            return None

    return None


def file_selector(
    label: str,
    key: str,
    file_types: list = None,
    default_path: str = ""
) -> Optional[str]:
    """
    Create a file selector with browse button.

    Uses streamlit-file-browser for file selection.

    Parameters
    ----------
    label : str
        Label for the selector.
    key : str
        Unique key for session state.
    file_types : list
        List of accepted file extensions (e.g., ['.npz']).
    default_path : str
        Default path to show.

    Returns
    -------
    path : str or None
        Selected file path, or None if not selected.
    """
    st.markdown(f"**{label}**")

    current_file = st.session_state.get(f'{key}_file', default_path)

    col1, col2 = st.columns([4, 1])

    with col1:
        st.text_input(
            "Selected file",
            value=current_file if current_file else "(No file selected)",
            disabled=True,
            label_visibility="collapsed",
            key=f"{key}_display"
        )

    with col2:
        browse_clicked = st.button("Browse", key=f"{key}_browse")

    if browse_clicked:
        st.session_state[f'{key}_browsing'] = True

    if st.session_state.get(f'{key}_browsing', False):
        with st.expander("Select file", expanded=True):
            # Build glob pattern
            glob_pattern = None
            if file_types:
                exts = [ext.lstrip('.') for ext in file_types]
                glob_pattern = f"*.{exts[0]}" if len(exts) == 1 else None

            browser_result = st_file_browser(
                path=".",
                key=f"{key}_browser",
                show_choose_file=True,
                show_choose_folder=False,
                show_delete_file=False,
                show_download_file=False,
                glob_pattern=glob_pattern,
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Select File", key=f"{key}_select"):
                    if browser_result and browser_result.get('selected_file'):
                        st.session_state[f'{key}_file'] = browser_result['selected_file']
                    st.session_state[f'{key}_browsing'] = False
                    st.rerun()
            with col2:
                if st.button("Cancel", key=f"{key}_cancel"):
                    st.session_state[f'{key}_browsing'] = False
                    st.rerun()

    # Validation
    selected_file = st.session_state.get(f'{key}_file', '')

    if selected_file:
        p = Path(selected_file)
        if p.exists() and p.is_file():
            if file_types:
                if p.suffix.lower() in [ft.lower() for ft in file_types]:
                    st.success(f"Valid file: {p.name}")
                    return selected_file
                else:
                    st.error(f"Invalid file type. Expected: {', '.join(file_types)}")
                    return None
            st.success(f"Valid file: {p.name}")
            return selected_file
        else:
            st.error("File not found")
            return None

    return None
```

---

## 6. VERIFICATION CHECKLIST

After implementing all changes, verify:

### 6.1 Global

- [ ] No emoji icons anywhere (except sidebar status indicators)
- [ ] Sticky header visible on all pages
- [ ] Settings button opens modal with theme info
- [ ] Help button opens modal with quick reference
- [ ] App runs without errors: `streamlit run app.py`

### 6.2 Home Page

- [ ] No title in body (moved to header)
- [ ] No "Current Status" section
- [ ] No "Quick Actions" section
- [ ] Welcome text present
- [ ] Workflow diagram present
- [ ] "About ECM" expander present

### 6.3 Configuration Page

- [ ] No Save/Load Config buttons
- [ ] Folder browser works for Data Directory
- [ ] Folder browser works for Output Directory
- [ ] No Reference Wavelength field (hardcoded to 633nm)
- [ ] Wavelength range uses slider
- [ ] Wavelength Settings and Acquisition Settings side-by-side
- [ ] Angular Positions has tooltip (not inline info box)
- [ ] No FP2 auto-detection note
- [ ] No Config Summary section

### 6.4 Calibration Page

- [ ] No page title icon
- [ ] File browser for loading calibration files
- [ ] Warnings shown as tooltips on disabled buttons

### 6.5 Processing Page

- [ ] No page title icon
- [ ] No "Go to Calibration" button
- [ ] No "Go to Configuration" button
- [ ] Simple warning + stop when not calibrated

### 6.6 Parameters Extraction Page (formerly Lu-Chipman)

- [ ] File renamed to `4_Parameters.py`
- [ ] Page title is "Parameters Extraction"
- [ ] No page title icon
- [ ] No "Go to Calibration" button
- [ ] No "Go to Processing" button

### 6.7 Packages

- [ ] `streamlit-file-browser` installed and working
- [ ] `streamlit-antd-components` installed (for future use)
- [ ] File browsers work in both local and deployed environments

---

## APPENDIX: Summary of Removed Elements

| Page | Removed Element |
|------|-----------------|
| All | Emoji icons (except sidebar status) |
| All | Title in page body (now in header) |
| Home | "Current Status" section |
| Home | "Quick Actions" section |
| Configuration | Save Config button |
| Configuration | Load Config button |
| Configuration | Reference Wavelength field |
| Configuration | FP2 auto-detection note |
| Configuration | Config Summary expander |
| Processing | "Go to Calibration" button |
| Processing | "Go to Configuration" button |
| Parameters | "Go to Calibration" button |
| Parameters | "Go to Processing" button |

---

**END OF INSTRUCTIONS**

*Follow these instructions step-by-step. Test each section after implementing. Report any issues or ambiguities.*
