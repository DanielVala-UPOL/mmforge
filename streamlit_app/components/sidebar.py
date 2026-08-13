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

from utils.session_state import is_calibrated, is_reflection_calibrated
from utils.styling import soft_divider


# ============================================================================
# CALIBRATION-STATUS TIERS
# ============================================================================
#
# The eigenvalue-ratio tiers from `calculate_quality_breakdown` are:
#   excellent: ratio < 1e-4
#   good     : 1e-4 ≤ ratio < 1e-3
#   acceptable: 1e-3 ≤ ratio < 1e-2
#   marginal : 1e-2 ≤ ratio < 0.1
#   poor     : ratio ≥ 0.1
#
# A summary status combining the per-tier fractions follows the rules
# below. Rules are evaluated worst → best; the first match wins. Both
# transmission and reflection use the same logic.
#
#   1. poor ≥ 50%                                → Unusable    🔴
#   2. poor ≥ 33%                                → Poor        🟡
#   3. marginal + poor ≥ 50%                     → Marginal    🟡
#   4. excellent + good ≥ 50% AND m+p < 25%      → Calibrated  🟢
#   5. excellent+good+acceptable ≥ 50% AND m+p < 25%
#                                                → Sub-optimal 🟢
#   6. fallback                                  → Marginal    🟡


def _summarise_calibration_status(eigenvalue_ratio: np.ndarray):
    """Return (label, color_emoji) for the calibration's per-tier mix.

    Parameters
    ----------
    eigenvalue_ratio : ndarray, shape (n_wavelengths,)

    Returns
    -------
    (label, icon) : (str, str)
        label is the human-readable status; icon is one of '🟢', '🟡', '🔴'.
    """
    n = len(eigenvalue_ratio)
    if n == 0:
        return ('Calibrated', '🟡')  # degenerate, treat as unknown-but-loaded

    r = eigenvalue_ratio
    e = float(np.sum(r < 1e-4) / n)
    g = float(np.sum((r >= 1e-4) & (r < 1e-3)) / n)
    a = float(np.sum((r >= 1e-3) & (r < 1e-2)) / n)
    m = float(np.sum((r >= 1e-2) & (r < 0.1)) / n)
    p = float(np.sum(r >= 0.1) / n)

    cum_eg = e + g                  # everything < 1e-3
    cum_ega = cum_eg + a            # everything < 1e-2
    cum_bad = m + p                 # everything ≥ 1e-2

    # Rules evaluated worst → best; first match wins.
    if p >= 0.50:
        return ('Unusable Calibration', '🔴')
    if p >= 0.33:
        return ('Poor Calibration', '🟡')
    if cum_bad >= 0.50:
        return ('Marginal Calibration', '🟡')
    if cum_eg >= 0.50 and cum_bad < 0.25:
        return ('Calibrated', '🟢')
    if cum_ega >= 0.50 and cum_bad < 0.25:
        return ('Sub-optimal Calibration', '🟢')
    # Fallback: bad fraction in 25–50% AND ≥Acceptable below half
    return ('Marginal Calibration', '🟡')


# ============================================================================
# SIDEBAR RENDERING
# ============================================================================

def _render_status_row(label: str, calibrated: bool, diagnostics) -> None:
    """Render one status row in the sidebar (Transmission or Reflection)."""
    if not calibrated:
        st.markdown(f"🔴 **{label}**: Not calibrated")
        return

    if diagnostics is None or not hasattr(diagnostics, 'eigenvalue_ratio'):
        st.markdown(f"🟡 **{label}**: Calibrated (no diagnostics)")
        return

    status, icon = _summarise_calibration_status(diagnostics.eigenvalue_ratio)
    st.markdown(f"{icon} **{label}**: {status}")


def render_sidebar():
    """
    Render the sidebar with calibration status.

    The navigation is handled automatically by Streamlit's pages/ directory,
    so this function focuses on the status indicator and additional info.

    Status indicator (visual only — internal state remains
    "calibrated"). See ``_summarise_calibration_status`` for the
    full rule table. Summary:

    - 🔴 Unusable Calibration — Poor ≥ 50%
    - 🟡 Poor Calibration     — Poor ≥ 33%
    - 🟡 Marginal Calibration — Marginal + Poor ≥ 50% (or fallback)
    - 🟢 Calibrated           — Excellent + Good ≥ 50% and bad < 25%
    - 🟢 Sub-optimal Calibration — Excellent + Good + Acceptable ≥ 50%
                                  and bad < 25%
    - 🔴 Not calibrated       — no calibration loaded
    """
    with st.sidebar:
        # Logo is now injected via CSS in utils/styling.py above the navigation

        # -------------------------------------------------
        # Calibration Status Indicator
        # -------------------------------------------------
        st.markdown("### Status")

        mode = st.session_state.get('calibration_mode', 'Transmission')
        st.caption(f"Mode: **{mode}**")

        _render_status_row(
            'Transmission',
            is_calibrated(),
            st.session_state.get('calibration_diag'),
        )
        _render_status_row(
            'Reflection',
            is_reflection_calibrated(),
            st.session_state.get('refl_calibration_diag'),
        )

        if not is_calibrated() and not is_reflection_calibrated():
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
                    # Only clear keys we explicitly manage. Widget-bound
                    # keys (buttons, internal checkbox keys, etc.) are left
                    # alone — deleting them mid-flow triggers Streamlit's
                    # widget-state-machine errors. Streamlit will clean
                    # them up naturally on the next rerun.
                    from utils.session_state import SESSION_KEYS
                    for key in list(SESSION_KEYS.keys()):
                        if key in st.session_state:
                            del st.session_state[key]
                    st.session_state['_confirm_reset'] = False
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
                <strong>MMForge v2.1.0</strong><br>
                ECM-Calibration v8.0.0<br>
                © 2026 Daniel Vala
            </div>
            """,
            unsafe_allow_html=True
        )
