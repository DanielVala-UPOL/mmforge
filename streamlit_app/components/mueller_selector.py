"""
Mueller Element Selector Component - 4x4 checkbox grid for element selection.

Provides:
- 4x4 grid of checkboxes for Mueller element selection
- Quick select buttons (diagonal, clear, all)
- Returns list of selected (i, j) tuples

Author: Daniel Vala
"""

import streamlit as st
from typing import List, Tuple


# ============================================================================
# MUELLER ELEMENT SELECTOR
# ============================================================================

def mueller_element_selector(
    key: str = "mueller_selector",
    default_selection: List[Tuple[int, int]] = None
) -> List[Tuple[int, int]]:
    """
    Create a 4x4 checkbox grid for Mueller element selection.

    Parameters
    ----------
    key : str
        Unique key for session state.
    default_selection : list of (i, j) tuples
        Default selected elements.

    Returns
    -------
    selected : list of (i, j) tuples
        Selected element indices (0-indexed).
    """
    st.markdown("**Select Mueller Elements**")
    st.caption("Select elements to overlay on a single plot")

    # Initialize selection in session state if needed
    if f"{key}_selection" not in st.session_state:
        st.session_state[f"{key}_selection"] = default_selection or []

    selected = []

    # Create 4x4 grid of checkboxes
    for i in range(4):
        cols = st.columns(4)
        for j in range(4):
            with cols[j]:
                is_selected = (i, j) in st.session_state[f"{key}_selection"]
                label = f"m{i+1}{j+1}"

                if st.checkbox(label, value=is_selected, key=f"{key}_{i}_{j}"):
                    selected.append((i, j))

    # Update session state
    st.session_state[f"{key}_selection"] = selected

    # Quick select buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Diagonal", key=f"{key}_diagonal"):
            st.session_state[f"{key}_selection"] = [(i, i) for i in range(4)]
            st.rerun()

    with col2:
        if st.button("Clear All", key=f"{key}_clear"):
            st.session_state[f"{key}_selection"] = []
            st.rerun()

    with col3:
        if st.button("Select All", key=f"{key}_all"):
            st.session_state[f"{key}_selection"] = [(i, j) for i in range(4) for j in range(4)]
            st.rerun()

    return selected


def mueller_element_selector_compact(
    key: str = "mueller_selector_compact",
) -> List[Tuple[int, int]]:
    """
    Create a compact Mueller element selector using multiselect.

    Parameters
    ----------
    key : str
        Unique key for session state.

    Returns
    -------
    selected : list of (i, j) tuples
        Selected element indices (0-indexed).
    """
    # Build options list
    options = [f"m{i+1}{j+1}" for i in range(4) for j in range(4)]

    selected_labels = st.multiselect(
        "Select Mueller elements",
        options=options,
        default=["m11"],
        key=f"{key}_multiselect"
    )

    # Convert labels back to (i, j) tuples
    selected = []
    for label in selected_labels:
        i = int(label[1]) - 1
        j = int(label[2]) - 1
        selected.append((i, j))

    return selected
