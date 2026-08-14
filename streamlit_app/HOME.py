"""
ECM Polarimetry GUI - Home Page

Main entry point for the Streamlit GUI application.
Provides workflow overview and quick navigation.

Author: Daniel Vala
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent directory to path for ECM imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

# Local imports
from components.sidebar import render_sidebar
from utils.session_state import initialize_session_state
from utils.theme import sync_theme, palette, is_dark, rgba
from utils.styling import inject_custom_css, soft_divider


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="MMForge - Home",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
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
# MAIN CONTENT
# ============================================================================

def main():
    """Render home page content."""

    # -------------------------------------------------
    # Header with Logo and Title
    # -------------------------------------------------
    # The dark theme gets its own file. Simply making the background
    # transparent would not be enough: the anvil and the MM-FORGE wordmark are
    # drawn in the slate #2D3E50, which sits at contrast 1.71 on the dark
    # background, so they would vanish and leave the magenta squares floating
    # by themselves. The variant repaints that ink; see tools/build_icons.py,
    # which generates it. Falls back to the light logo if it is missing.
    assets_dir = Path(__file__).parent / "assets"
    logo_path = assets_dir / ("MMForge_v1_dark.png" if is_dark()
                              else "MMForge_v1.png")
    if not logo_path.exists():
        logo_path = assets_dir / "MMForge_v1.png"

    col1, col2 = st.columns([1, 3])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
    with col2:
        st.markdown("## Your Mueller Matrix Workbench")

    st.markdown("""
    Welcome to **MMForge** — crafted to streamline your polarimetric measurements and analysis.

    This application provides an intuitive workflow for:

    - **Calibrating** the Mueller matrix spectroscopic polarimeter(*) using the Eigenvalue Calibration Method (ECM), in **transmission** or **reflection** mode
    - **Processing** sample measurements to extract Mueller matrices and related ellipsometric and polarimetric parameters
    - **Analyzing** results through Mueller-matrix decompositions: **Lu-Chipman polar, Cloude spectral, Differential (Minkowski space); and Purity Space analysis**


    Navigate through the steps using the :blue-background[sidebar]. Get started with :blue-background[CONFIGURATION] — set your paths and parameters, and you are ready to go!
    If you are a newcomer to this app, read more about the workflow below.

                """)

    # -------------------------------------------------
    # Workflow Overview
    # -------------------------------------------------
    soft_divider()
    st.subheader("Workflow tutorial")

    # CSS for enhanced workflow cards with left border accent and hover effects.
    # Colours come from the active palette: the card is a raised surface, so
    # in light mode it is a shade *lighter* than the page and in dark mode a
    # shade lighter than the (much darker) page — the gradient runs panel →
    # background either way. The tab underline has no palette token of its
    # own; light keeps the softer magenta it has always used and dark takes
    # the primary-hover tint, which plays the same "lighter accent" role.
    p = palette()
    tab_underline = '#FF6B9D' if not is_dark() else p['primary_hover']
    st.markdown(f"""
    <style>
    .workflow-card {{
        background: linear-gradient(135deg, {p['panel']} 0%, {p['bg']} 100%);
        border: 1px solid {p['border']};
        border-left: 4px solid {p['structural']};
        border-radius: 8px;
        padding: 20px 16px;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .workflow-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 6px 16px {rgba(p['structural'], 0.15)};
    }}
    .workflow-card .step-number {{
        font-size: 1.8em;
        font-weight: 700;
        color: {p['primary']};
        margin-bottom: 4px;
        line-height: 1;
    }}
    .workflow-card .step-title {{
        font-size: 1.05em;
        font-weight: 600;
        color: {p['structural']};
        margin-bottom: 6px;
    }}
    .workflow-card .step-desc {{
        font-size: 0.85em;
        color: {p['text_dim']};
        margin: 0;
    }}
    /* Tab styling for gentle color coding and full width distribution */
    .stTabs [data-baseweb="tabs"] [aria-selected="true"] {{
        border-bottom-color: {tab_underline} !important;
    }}
    .stTabs [data-baseweb="tabs"] {{
        width: 100%;
    }}
    .stTabs [data-baseweb="tabs"] button[role="tab"] {{
        flex: 1;
        text-align: center;
    }}
    </style>
    """, unsafe_allow_html=True)

    # Visual workflow diagram using columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
            <div class="workflow-card">
                <div class="step-number">1</div>
                <div class="step-title">Configure</div>
                <p class="step-desc">Set paths and parameters</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <div class="workflow-card">
                <div class="step-number">2</div>
                <div class="step-title">Calibrate</div>
                <p class="step-desc">Run ECM calibration</p>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
            <div class="workflow-card">
                <div class="step-number">3</div>
                <div class="step-title">Process</div>
                <p class="step-desc">Analyze sample measurements</p>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
            <div class="workflow-card">
                <div class="step-number">4</div>
                <div class="step-title">Parameters</div>
                <p class="step-desc">Extract physical parameters</p>
            </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------
    # Information
    # -------------------------------------------------
    st.space(size="small")

    # Use tabs for workflow sections
    tab1, tab2, tab3, tab4 = st.tabs(["CONFIGURE", "2. CALIBRATE", "3. PROCESS", "4. PARAMETERS"])

    with tab1:
        st.markdown("**Begin by configuring the application to suit your experimental setup.**")

        st.markdown("**Select Calibration Mode**")
        st.markdown("""
- **Transmission** — straight-through configuration. Calibration uses air (ST), two linear polarizers, and one or two Fresnel-prism retarders.
- **Reflection** — oblique-incidence configuration. Calibration uses two reference wafers (25 nm and 10 nm SiO₂ / Si) plus two polarizer-bearing measurements. Default angle of incidence is 65°.
- **Tutorial Data** — bundled transmission example so you can learn the workflow without your own data.
        """)

        st.markdown("**Define Data Paths**")
        st.markdown("""
- **Transmission** and **Reflection** both ask for a single data directory holding all calibration files and sample measurements (the same set of file patterns described in the CALIBRATE tab below).
- An output directory is shared between modes for saving calibrations and exports.
- The :red-background[data directory **must** contain] all required calibration files (see the CALIBRATE tab for keyword patterns).
- The application auto-discovers files based on these patterns; no manual file selection is needed.
        """)

        st.markdown("**Specify Wavelength Settings**")
        st.markdown("""
- Set the wavelength range. The maximum range is determined by the source lamp.
- Both calibration and sample processing will use this range.
        """)

        st.info("""
**Tutorial Data:**
- You may select **Tutorial Data** in **Calibration Mode** to learn the workflow without needing your own measurements.
- This option loads example transmission calibration data and a sample measurement to demonstrate the application's features.
- The Data Directory is automatically prefilled. Saving is not enabled.
- You may still select the wavelength range.
- Caution! The bundled tutorial data is designed for demonstration purposes and may not reflect real experimental conditions. Use it to familiarize yourself with the workflow, but always validate with your own measurements for actual analysis.
- Caution! The tutorial data is for transmission mode only; the reflection mode features will not be demonstrated with this dataset.
                """)

    with tab2:
        st.markdown("**Continue with calibrating the polarimeter using the ECM.**")
        st.markdown("Ensure all required calibration files are present by clicking the :blue-background[Discover Files] button. The application searches for required files by filename patterns. The pattern set depends on the calibration mode you selected on the CONFIGURATION page.")

        st.markdown("**Transmission mode — required label patterns:**")
        st.markdown("""
| Sample | Label Pattern* | Status |
|--------|---------------|--------|
| Background (closed shutter) | :orange-background[\\_DARK_ECM\\_] | **Required** |
| Air (empty straight-through measurement) | :orange-background[\\_ST_ECM\\_] | **Required** |
| Linear polarizer at 0° | :orange-background[\\_P0_ECM\\_] | **Required** |
| Linear polarizer at 45° | :orange-background[\\_P45_ECM\\_] | **Required** |
| Fresnel prism FP1 at 90° | :orange-background[\\_RET90_FP1_ECM\\_] | **Required** |
| Fresnel prism FP2 at 45° | :orange-background[\\_RET45_FP2_ECM\\_] | Optional** |
        """)

        st.markdown("**Reflection mode — required label patterns:**")
        st.markdown("""
| Sample | Label Pattern* | Status |
|--------|---------------|--------|
| Background (closed shutter) | :orange-background[\\_DARK_ECM\\_] | **Required** |
| Wafer 25 nm (bare) | :orange-background[\\_WAFER25NM_ECM\\_] | **Required** |
| Wafer 25 nm + Pol BEFORE sample | :orange-background[\\_WAFER25NM_POL_BEFORE_ECM\\_] | **Required** |
| Wafer 25 nm + Pol AFTER sample | :orange-background[\\_WAFER25NM_POL_AFTER_ECM\\_] | **Required** |
| Wafer 10 nm (bare) | :orange-background[\\_WAFER10NM_ECM\\_] | **Required** |
        """)

        st.caption("*Before and after the underscore delimiters can be any string (e.g., sample ID, date, etc.); labels are case-sensitive.")
        st.caption("**Not required for transmission, but recommended for best results.")

        st.markdown("**Hit :red-background[Run Calibration]**")
        st.markdown("""
- The application will process the calibration data and display eigenvalue metrics to assess the calibration quality.
- In reflection mode, the calibration also runs a per-wavelength wafer optimization and (optionally) a TMM physics-informed thickness fit; results are shown in the *Reflection Quality Details* expander.
- You may save the calibration results for future use *(not required)*. Save files are mode-aware — the same .npz format covers both transmission and reflection calibrations.
        """)

        st.info("""
**Tips:**
- Check the dual calibration status (Transmission / Reflection) in the sidebar
- Rerun anytime after changing settings
- Load saved calibration results at the bottom; the loader auto-detects the mode from the file
        """)

    with tab3:
        st.markdown("**Now you are ready to process the samples and obtain their Mueller matrices.**")
        st.markdown("Ensure all sample data files are within the specified directory (the same directory as the calibration files).")

        st.markdown("**Hit :blue-background[Discover Samples]**")
        st.markdown("""
- The application will search for sample measurement files (any `.bin` file that is **not** a calibration file).
- You can select which samples to process by checking the boxes next to their names.
- Once you have selected the samples, click :red-background[Process Selected] to start processing.
- The application will process the selected samples and display the results.
- You can save the processed results for future use *(not required)*.
        """)

        st.markdown("**Reflection mode**")
        st.markdown("""
- After Mueller-matrix extraction, the application automatically computes ellipsometric parameters using the configured AOI:
  - Ellipsometric angles Ψ and Δ (in degrees)
  - NCS parametrization: N = cos(2Ψ), C = sin(2Ψ)·cos(Δ), S = sin(2Ψ)·sin(Δ)
  - ⟨ε⟩ (pseudo-dielectric function, complex)
  - ⟨n⟩, ⟨k⟩ (refractive index and extinction coefficient derived from ⟨ε⟩)
- Both are displayed in the *Ellipsometric Parameters* expander beneath the Mueller matrix block, and are included in CSV / NPZ exports.
        """)

        st.info("""
**Tips:**
- Process samples multiple times
- Hover over plots to see values
- Drag to zoom in on specific areas
- Compare samples side by side
        """)

    with tab4:
        st.markdown("**The raw Mueller matrices of the samples can be converted to fundamental polarization quantities through four complementary decompositions.**")
        st.markdown("All four methods accept Mueller matrices from either transmission or reflection mode. Each method has its own tab on the PARAMETERS page.")

        st.markdown("**1. Lu–Chipman polar decomposition** *(M = M<sub>Δ</sub> · M<sub>R</sub> · M<sub>D</sub>)*", unsafe_allow_html=True)
        st.markdown("""
- Extracts **diattenuation (D)**, **retardance (R)**, and **depolarization (Δ, DI)** as separate Mueller matrices.
- Reports eigenmode characteristics: fast-axis orientation **ν** and ellipticity **χ**.
- Best suited for samples that can be approximated as a sequence of ideal optical elements (e.g., a retarder followed by a diattenuator), but may not capture complex interactions or strong scattering.
        """)

        st.markdown("**2. Differential decomposition** *(log-space, Minkowski metric)*")
        st.markdown("""
- Decomposes **L = ln(M)** into a polarization part **L<sub>m</sub>** (mean nondepolarizing properties) and a depolarization part **L<sub>u</sub>**.
- Their matrix exponentials give the component matrices **M<sub>m</sub>** and **M<sub>u</sub>**.
- Best suited for samples with significant depolarization and scattering, where the log-space decomposition can better capture changes in polarization properties.
        """, unsafe_allow_html=True)

        st.markdown("**3. Cloude spectral decomposition** *(coherency matrix H)*")
        st.markdown("""
- Builds the 4×4 Hermitian coherency matrix **H** and diagonalizes it into four eigenvalues λ₀ ≥ λ₁ ≥ λ₂ ≥ λ₃ and four component Mueller matrices.
- The Mueller matrix related to thedominant component (λ₀) captures the deterministic and non-depolarizing properties; the rest represent noise.
- Tab shows the eigenvalue spectrum, each component matrix, and selected |H<sub>ij</sub>| traces.
- Best suited for samples with low depolarization and high SNR, where the dominant eigenvalue is significantly larger than the others.
        """, unsafe_allow_html=True)

        st.markdown("**4. Purity space analysis**")
        st.markdown("""
- Computes the three purity indices **P<sub>P</sub>** (polarimetric purity), **P<sub>S</sub>** (spherical purity), and **P<sub>Δ</sub>** (overall purity).
- The **(P<sub>S</sub>, P<sub>P</sub>) purity space diagram** marks each wavelength on a 2-D plot bounded by physical realizability curves (Gil & Ossikovski, 2022).
- Quick visual diagnostic: is the sample mostly a retarder, a diattenuator, a depolarizer; what is the source of depolarization; how does purity evolve with wavelength?
        """, unsafe_allow_html=True)

        st.warning("""
**⚠️  Notes on decomposition results:**
- Decompositions are mathematical tools that can provide insights into the sample's polarization properties, but they are not unique physical models. 
- Different decompositions may yield different interpretations of the same Mueller matrix. Some or all decomposition may be not suitable for a given sample at all!
- Always interpret results within your experimental context.
        """)

        st.info("""
**Tips:**
- Rerun any decomposition anytime; each tab keeps its own result cache
- Plots offer interactive features (hover, zoom, pan, legend toggling)
- Export results from each tab as .npz or .csv for external analysis
        """)


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
