"""
Sidebar Component - Navigation and calibration status.

Displays:
- Workflow navigation (handled by Streamlit pages)
- Calibration status indicator (green/red dot)
- Loaded calibration info (if available)

Author: Daniel Vala
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.session_state import is_calibrated, get_calibration_info


# ============================================================================
# SIDEBAR RENDERING
# ============================================================================

def render_sidebar():
    """
    Render the sidebar with calibration status.

    The navigation is handled automatically by Streamlit's pages/ directory,
    so this function focuses on the status indicator and additional info.
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
            st.markdown("🟢 **Calibrated**")

            # Show calibration info if available
            cal_info = get_calibration_info()
            if cal_info:
                with st.expander("Calibration Details", expanded=False):
                    st.write(f"**Wavelengths:** {cal_info.get('n_wavelengths', 'N/A')}")
                    wl_min = cal_info.get('wl_min')
                    wl_max = cal_info.get('wl_max')
                    if wl_min is not None and wl_max is not None:
                        st.write(f"**Range:** {wl_min:.0f} - {wl_max:.0f} nm")
                    mean_ratio = cal_info.get('mean_ratio')
                    if mean_ratio is not None:
                        st.write(f"**Mean ratio:** {mean_ratio:.2e}")
                    if cal_info.get('use_ret45'):
                        st.write("**FP2:** Detected")
        else:
            st.markdown("🔴 **Not calibrated**")
            st.caption("Run calibration or load a saved calibration file.")

        # -------------------------------------------------
        # Version info at bottom
        # -------------------------------------------------
        st.markdown("---")
        st.caption("ECM Polarimetry v6.5.5")
