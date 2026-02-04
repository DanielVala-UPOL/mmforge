"""
File Browser Component - Simple path input with validation.

Provides editable text inputs for folder and file path selection.
Users can type or paste paths directly.

Author: Daniel Vala
"""

import streamlit as st
from pathlib import Path
from typing import Optional, List


def directory_selector(
    label: str,
    key: str,
    default_path: str = "",
    help_text: str = ""
) -> Optional[str]:
    """
    Create a directory selector with editable text input.

    Parameters
    ----------
    label : str
        Label for the selector.
    key : str
        Unique key for Streamlit session state.
    default_path : str
        Default path to show (only used if no value exists).
    help_text : str
        Help text displayed below input.

    Returns
    -------
    path : str or None
        Selected directory path, or None if invalid/empty.
    """
    st.markdown(f"**{label}**")

    # Session state key for this directory
    state_key = f'{key}_path'

    # Get current value - use existing value if present, otherwise default
    current_value = st.session_state.get(state_key, default_path)

    # Editable text input
    # Using value= instead of relying on key= to avoid Streamlit widget state issues
    new_path = st.text_input(
        "Path",
        value=current_value,
        key=f"{key}_text_input",  # Unique widget key
        placeholder="/path/to/your/data/folder",
        help=help_text if help_text else "Enter or paste the full path to the folder",
        label_visibility="collapsed"
    )

    # Always update session state with current value
    st.session_state[state_key] = new_path

    # Validation
    if new_path and new_path.strip():
        p = Path(new_path)
        if p.exists() and p.is_dir():
            st.success("Valid directory")
            return new_path
        else:
            st.error(f"Directory not found: `{new_path}`. Check that the path exists and you have read permissions.")
            return None

    return None


def directory_selector_compact(
    label: str,
    key: str,
    default_path: str = "",
) -> Optional[str]:
    """
    Create a compact directory selector (for output directories).

    Parameters
    ----------
    label : str
        Label for the selector.
    key : str
        Unique key for Streamlit session state.
    default_path : str
        Default path to show (only used if no value exists).

    Returns
    -------
    path : str or None
        Selected directory path, or None if empty.
    """
    st.markdown(f"**{label}**")

    # Session state key for this directory
    state_key = f'{key}_path'

    # Get current value - use existing value if present, otherwise default
    current_value = st.session_state.get(state_key, default_path)

    # Editable text input
    new_path = st.text_input(
        "Path",
        value=current_value,
        key=f"{key}_text_input",  # Unique widget key
        placeholder="/path/to/output/folder",
        help="Enter or paste the full path to the folder",
        label_visibility="collapsed"
    )

    # Always update session state with current value
    st.session_state[state_key] = new_path

    # Validation
    if new_path and new_path.strip():
        p = Path(new_path)
        if p.exists() and p.is_dir():
            st.success("Valid directory")
            return new_path
        else:
            # For output directory, allow non-existing paths (will be created)
            st.info("Directory will be created if it doesn't exist")
            return new_path

    return None


def file_selector(
    label: str,
    key: str,
    file_types: List[str] = None,
    default_path: str = ""
) -> Optional[str]:
    """
    Create a file selector with editable text input.

    Parameters
    ----------
    label : str
        Label for the selector.
    key : str
        Unique key for session state.
    file_types : list
        List of accepted file extensions (e.g., ['.npz']).
    default_path : str
        Default path to show (only used if no value exists).

    Returns
    -------
    path : str or None
        Selected file path, or None if invalid/empty.
    """
    st.markdown(f"**{label}**")

    # Session state key for this file
    state_key = f'{key}_file'

    # Get current value - use existing value if present, otherwise default
    current_value = st.session_state.get(state_key, default_path)

    # Editable text input
    new_file = st.text_input(
        "File path",
        value=current_value,
        key=f"{key}_text_input",  # Unique widget key
        placeholder="/path/to/file.npz",
        help=f"Enter or paste the full path to the file{' (' + ', '.join(file_types) + ')' if file_types else ''}",
        label_visibility="collapsed"
    )

    # Always update session state with current value
    st.session_state[state_key] = new_file

    # Validation
    if new_file and new_file.strip():
        p = Path(new_file)
        if p.exists() and p.is_file():
            if file_types:
                if p.suffix.lower() in [ft.lower() for ft in file_types]:
                    st.success(f"Valid file: {p.name}")
                    return new_file
                else:
                    st.error(f"Invalid file type: `{p.suffix}`. Expected one of: {', '.join(file_types)}")
                    return None
            st.success(f"Valid file: {p.name}")
            return new_file
        else:
            st.error(f"File not found: `{new_file}`. Check that the file path is correct.")
            return None

    return None
