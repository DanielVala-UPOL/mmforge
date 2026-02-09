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
from utils.styling import soft_divider


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
        # Logo is now injected via CSS in utils/styling.py above the navigation

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
        # Session Section
        # -------------------------------------------------
        soft_divider()
        st.markdown("### Session")

        if st.button("Reset Session", use_container_width=True, type="secondary"):
            st.session_state['_confirm_reset'] = True

        if st.session_state.get('_confirm_reset', False):
            st.warning("Clear all and start over?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Confirm", type="primary", use_container_width=True, key="sidebar_confirm_reset"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
            with col2:
                if st.button("Cancel", use_container_width=True, key="sidebar_cancel_reset"):
                    st.session_state['_confirm_reset'] = False
                    st.rerun()

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
                font-size: 0.7em;
                border-top: 1px solid #ddd;
            }
            </style>
            <div class="sidebar-version">
                <strong>MMForge v1.2</strong><br>
                ECM-Calibration v6.5.5<br>
                © 2026 Daniel Vala
            </div>
            """,
            unsafe_allow_html=True
        )
