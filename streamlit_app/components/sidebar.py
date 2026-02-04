"""
Sidebar Component - Navigation and calibration status.

Displays:
- Workflow navigation (handled by Streamlit pages)
- Calibration status indicator (green/yellow/red dot)
- Loaded calibration info (if available)
- Version info at bottom

Author: Daniel Vala
"""

import streamlit as st
import numpy as np
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.session_state import is_calibrated


# ============================================================================
# SIDEBAR RENDERING
# ============================================================================

def render_sidebar():
    """
    Render the sidebar with calibration status.

    The navigation is handled automatically by Streamlit's pages/ directory,
    so this function focuses on the status indicator and additional info.

    Status indicator logic (visual only - internal state remains "calibrated"):
    - >=Good >= 50%: green circle, "Calibrated"
    - >=Good 25-50%: yellow circle, "Marginal Calibration"
    - >=Good < 25%: yellow circle, "Poor Calibration"
    - Not calibrated: red circle, "Not calibrated"
    """
    with st.sidebar:
        # -------------------------------------------------
        # Divider before status
        # -------------------------------------------------
        st.markdown("---")

        # -------------------------------------------------
        # Calibration Status Indicator
        # -------------------------------------------------
        st.markdown("### Status")

        if is_calibrated():
            diag = st.session_state.get('calibration_diag')

            # Calculate ≥Good percentage (excellent + good, i.e., ratio < 1e-3)
            good_pct = 0
            if diag is not None:
                ratio = diag.eigenvalue_ratio
                good_pct = np.sum(ratio < 1e-3) / len(ratio) * 100

            # Determine status display based on ≥Good percentage
            if good_pct >= 50:
                st.markdown("🟢 **Calibrated**")
            elif good_pct >= 25:
                st.markdown("🟡 **Marginal Calibration**")
            else:
                st.markdown("🟡 **Poor Calibration**")
        else:
            st.markdown("🔴 **Not calibrated**")
            st.caption("Run calibration or load a saved calibration file.")

        # -------------------------------------------------
        # Version info at absolute bottom using CSS
        # -------------------------------------------------
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] > div:first-child {
                display: flex;
                flex-direction: column;
                height: 100vh;
            }
            [data-testid="stSidebarContent"] {
                flex: 1;
                display: flex;
                flex-direction: column;
            }
            .sidebar-version {
                margin-top: auto;
                padding: 20px 0;
                text-align: center;
                color: #666;
                font-size: 0.8em;
                border-top: 1px solid #ddd;
            }
            </style>
            <div class="sidebar-version">
                ECM Polarimetry v6.5.5
            </div>
            """,
            unsafe_allow_html=True
        )
