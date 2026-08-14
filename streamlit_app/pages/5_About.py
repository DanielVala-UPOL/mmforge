"""
About the application and code.

Author: Daniel Vala
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.sidebar import render_sidebar
from utils.session_state import initialize_session_state
from utils.theme import sync_theme
from utils.styling import inject_custom_css


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="MMForge - About",
    page_icon=None,
    layout="wide"
)

# Inject consolidated MMForge styling
inject_custom_css()


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

initialize_session_state()

# Notice a theme switch and rerun once, so the Plotly figures are
# rebuilt with the new palette. Note this fires on the next rerun
# after the switch, not at the moment of switching — Streamlit does
# not re-run the script when the theme changes. Must run after
# initialize_session_state(), which creates the key it compares to.
sync_theme()


# ============================================================================
# SIDEBAR
# ============================================================================

render_sidebar()


# ============================================================================
# MAIN PAGE CONTENT
# ============================================================================

def main():
    st.title("About MMForge 2.1")

    st.space(size="small")

    st.markdown("""
    This cross-platform, browser-based application was built with Streamlit and is powered by the ECM calibration Python package developed by the author.
    MMForge supports Mueller matrix spectroscopic ellipsometry in both **transmission** and **reflection** modes,
    with ellipsometric parameter extraction (Ψ, Δ, pseudo-dielectric function, pseudo n/k) and four Mueller-matrix decompositions
    (Lu-Chipman, differential, Cloude spectral, purity space).

    This is MMForge 2.1.0, released in August 2026, on top of ECM-Calibration v8.0.0. Due to specific requirements of the ECM algorithm,
    correct operation of the application requires a particular instrument design. This version is intended for exclusive use
    with the custom-built Mueller matrix spectroscopic ellipsometer at the Department of Optics, Palacký University Olomouc, and may
    not be compatible with other instruments without modification. Future versions will aim to support a wider range of instrument configurations.
    """)

    st.space(size="small")

    with st.expander("About ECM", expanded=False):
        st.markdown("""
        The **Eigenvalue Calibration Method (ECM)** is a self-consistent approach for
        calibrating Mueller matrix spectroscopic ellipsometers with an arbitrary design of the Polarization State Generator (PSG) and Polarization State Analyzer (PSA).

        **Key features:**
        - Self-consistent calibration using eigenvalue analysis
        - Automatic extraction of instrument matrices (W, A)
        - Quality metrics via eigenvalue ratio analysis
        - **Transmission** mode (straight-through)
        - **Reflection** mode (oblique incidence) with per-wavelength wafer optimization and TMM physics-informed thickness fitting
        - Four Mueller-matrix decompositions: Lu-Chipman polar, differential (Minkowski), Cloude spectral, purity space
        - Ellipsometric parameter extraction (Ψ, Δ, ⟨ε⟩, ⟨n⟩, ⟨k⟩) for reflection samples

        **Main references:**
        - Compain et al., "General and self-consistent method for the calibration of polarization modulators, polarimeters, and Mueller-matrix ellipsometers", *Appl. Opt.* **38**, 3490–3502 (1999)
        - Rosales et al., "Extended eigenvalue calibration method for overdetermined Mueller matrix polarimeters", *Opt. Lett.* **49**, 1165–1168 (2024)
        - Lu & Chipman, "Interpretation of Mueller matrices based on polar decomposition", *J. Opt. Soc. Am. A* **13**, 1106–1113 (1996)
        - Gil & Ossikovski, *Polarized Light and the Mueller Matrix Approach*, 2nd ed., CRC Press (2022)
        """)

    with st.expander("Changelog", expanded=False):
        st.markdown("""
                
        ## v2.1.0 (August 2026)

        **New:**
        - **One-click launchers.** `MMForge.bat` on Windows and `MMForge.command`
          on macOS start the application without a terminal or an IDE. The
          Windows installer adds a Desktop shortcut with the MMForge icon; the
          macOS installer builds an MMForge app in your Applications folder.
        - **One-time installers** (`Install-Windows.bat`, `Install-macOS.command`)
          that create the Python environment and install everything needed.
          Safe to re-run: that is the standard repair step.
        - **README** with separate, self-contained step-by-step instructions for
          Windows and macOS.

        **Fixed:**
        - Results were saved into the current working directory, which scattered
          `.npz` and `.csv` files among the program files. MMForge now suggests
          `MMForge_output` in your home folder, and a blank Output Directory box
          falls back to that instead of writing next to the source code.
        - The Streamlit requirement was too loose (`>=1.30`); the Calibration
          page needs 1.37 or newer. All dependencies now have tested upper
          bounds so a fresh installation cannot pull in a breaking release.

        **Changes:**
        - Removed the bundled `plans/` folder and the `data/test/` measurement
          set (31 MB). Tutorial data and runtime assets are unaffected.
        - Usage telemetry is switched off.
        - Added a LICENSE file.

        ---

        ## v2.0.1 (August 2026)

        **Changes:**
        - Minor text updates and clarifications.

        ---

        ## v2.0 (May 2026)

        **New Features:**
        - **Reflection mode** end-to-end: calibration wafers required (25 nm / 10 nm), transfer matrix method thickness fitting, angle of incidence misalignment correction
        - **Ellipsometric parameter extraction** after reflection processing — Ψ, Δ, N/C/S, ⟨ε⟩, ⟨n⟩/⟨k⟩
        - Three new Mueller-matrix decompositions (along with Lu-Chipman) on page 4:
          - **Differential** (Minkowski) — L_m / L_u / M_m / M_u
          - **Cloude spectral** — coherency matrix eigendecomposition
          - **Purity space** — P_P / P_S / P_Δ indices with the (P_S, P_P) diagram
        - Auto-detection of angular positions from binary file dimensions
        - Dual-mode sidebar status indicator
        - Mode-aware save/load (single calibration file format covers both modes)

        **Changes:**
        - "Combined" mode removed
        - WAFER25NM / WAFER10NM terminology replaces "reflector 1" / "reflector 2"
        - ECM library updated to v8.0.0 (was v6.5.5, v7 is internal only and was skipped for this release)

        ---

        ## v1.2 (February 2026)

        **New Features:**
        - Tutorial Data mode with bundled example calibration and sample data
        - Learn the workflow without needing your own measurement data

        **Changes:**
        - Saving/loading disabled in Tutorial mode
        - Auto-configured data paths in Tutorial mode

        ---

        ## v1.1 (February 2026)

        **New Features:**
        - Auto-detect rotator steps from calibration file dimensions
        - Calibration Mode selector (Transmission / Reflection / Combined)

        **Changes:**
        - Removed manual "Angular Positions" input
        - File discovery validates dimension consistency
        - HOME page visual updates and cleanup

        ---

        ## v1.0 (February 2026)

        **Initial Release:**
        - ECM calibration for Mueller matrix spectroscopic polarimetry
        - Transmission mode support
        - Lu-Chipman polar decomposition
        - Interactive Plotly visualizations
        """)


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
