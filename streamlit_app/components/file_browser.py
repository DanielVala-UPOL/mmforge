"""
File Browser Component - Drag-and-drop and directory selection.

Provides a unified interface for:
- Drag-and-drop file/folder upload (visual placeholder)
- Manual path text input
- Path validation

Author: Daniel Vala
"""

import streamlit as st
from pathlib import Path
from typing import Optional


# ============================================================================
# DIRECTORY SELECTOR
# ============================================================================

def directory_selector(
    label: str,
    key: str,
    default_path: str = "",
    help_text: str = ""
) -> Optional[Path]:
    """
    Create a directory selector with drag-drop zone and text input.

    Parameters
    ----------
    label : str
        Label for the selector.
    key : str
        Unique key for Streamlit session state.
    default_path : str
        Default path to show.
    help_text : str
        Help text to display.

    Returns
    -------
    path : Path or None
        Selected directory path, or None if invalid/empty.
    """
    st.markdown(f"**{label}**")

    if help_text:
        st.caption(help_text)

    # -------------------------------------------------
    # Drag-and-drop zone (visual placeholder)
    # -------------------------------------------------
    # Note: Streamlit's native file_uploader doesn't support
    # folder selection. This is a visual placeholder that will be
    # enhanced with streamlit-file-browser in later phases.

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
                📁 Drag and drop folder here<br>
                <small>or enter path below</small>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------------------------------
    # Text input for path
    # -------------------------------------------------
    path_input = st.text_input(
        "Path",
        value=default_path,
        key=f"{key}_path_input",
        label_visibility="collapsed",
        placeholder="Enter directory path..."
    )

    # -------------------------------------------------
    # Validate path
    # -------------------------------------------------
    if path_input:
        p = Path(path_input)
        if p.exists() and p.is_dir():
            # Count .bin files for quick validation
            bin_files = list(p.glob("*.bin"))
            st.success(f"✓ Valid directory: {len(bin_files)} .bin files found")
            return p
        elif p.exists():
            st.error("✗ Path exists but is not a directory")
            return None
        else:
            st.error("✗ Directory not found")
            return None

    return None


def directory_selector_compact(
    label: str,
    key: str,
    default_path: str = "",
) -> Optional[Path]:
    """
    Create a compact directory selector (text input only, no drag-drop).

    Parameters
    ----------
    label : str
        Label for the selector.
    key : str
        Unique key for Streamlit session state.
    default_path : str
        Default path to show.

    Returns
    -------
    path : Path or None
        Selected directory path, or None if invalid/empty.
    """
    path_input = st.text_input(
        label,
        value=default_path,
        key=f"{key}_path_input",
        placeholder="Enter directory path..."
    )

    if path_input:
        p = Path(path_input)
        if p.exists() and p.is_dir():
            return p
        elif p.exists():
            st.error("Path is not a directory")
            return None
        else:
            st.error("Directory not found")
            return None

    return None


# ============================================================================
# FILE SELECTOR (for loading single files like calibration.npz)
# ============================================================================

def file_selector(
    label: str,
    key: str,
    file_types: list = None,
    default_path: str = ""
) -> Optional[Path]:
    """
    Create a file selector for single file selection.

    Parameters
    ----------
    label : str
        Label for the selector.
    key : str
        Unique key for session state.
    file_types : list
        List of accepted file extensions (e.g., ['.npz', '.npy']).
    default_path : str
        Default path to show.

    Returns
    -------
    path : Path or None
        Selected file path, or None if invalid/empty.
    """
    st.markdown(f"**{label}**")

    path_input = st.text_input(
        "File path",
        value=default_path,
        key=f"{key}_file_input",
        label_visibility="collapsed",
        placeholder="Enter file path..."
    )

    if path_input:
        p = Path(path_input)
        if p.exists() and p.is_file():
            if file_types:
                if p.suffix.lower() in file_types:
                    st.success(f"✓ Valid file: {p.name}")
                    return p
                else:
                    st.error(f"✗ Invalid file type. Expected: {', '.join(file_types)}")
                    return None
            else:
                st.success(f"✓ Valid file: {p.name}")
                return p
        elif p.exists():
            st.error("✗ Path is not a file")
            return None
        else:
            st.error("✗ File not found")
            return None

    return None
