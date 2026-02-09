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
    logo_path = Path(__file__).parent / "assets" / "MMForge_v1.png"

    col1, col2 = st.columns([1, 3])
    with col1:
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
    with col2:
        st.markdown("## Your Mueller Matrix Workbench")

    st.markdown("""
    Welcome to **MMForge** — crafted to streamline your polarimetric measurements and analysis.

    This application provides an intuitive workflow for:

    - **Calibrating** the Mueller matrix spectroscopic polarimeter(*) using the Eigenvalue Calibration Method (ECM)
    - **Processing** sample measurements to extract Mueller matrices
    - **Analyzing** results to obtain physical polarimetric parameters of your samples


    Navigate through the steps using the :blue-background[sidebar]. Get started with :blue-background[CONFIGURATION] — set your paths and parameters, and you are ready to go!
    If you are a newcomer, read more about the workflow below.

    (*) *Currently supports only a stepwise dual-rotating-compensator polarimeter with specific PSG and PSA retardances.*
                """)

    # -------------------------------------------------
    # Workflow Overview
    # -------------------------------------------------
    soft_divider()
    st.subheader("Workflow tutorial")

    # CSS for enhanced workflow cards with left border accent and hover effects
    st.markdown("""
    <style>
    .workflow-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
        border: 1px solid #E0E0E0;
        border-left: 4px solid #2D3E50;
        border-radius: 8px;
        padding: 20px 16px;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .workflow-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(45, 62, 80, 0.15);
    }
    .workflow-card .step-number {
        font-size: 1.8em;
        font-weight: 700;
        color: #FF1F5B;
        margin-bottom: 4px;
        line-height: 1;
    }
    .workflow-card .step-title {
        font-size: 1.05em;
        font-weight: 600;
        color: #2D3E50;
        margin-bottom: 6px;
    }
    .workflow-card .step-desc {
        font-size: 0.85em;
        color: #666;
        margin: 0;
    }
    /* Tab styling for gentle color coding and full width distribution */
    .stTabs [data-baseweb="tabs"] [aria-selected="true"] {
        border-bottom-color: #FF6B9D !important;
    }
    .stTabs [data-baseweb="tabs"] {
        width: 100%;
    }
    .stTabs [data-baseweb="tabs"] button[role="tab"] {
        flex: 1;
        text-align: center;
    }
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
        
        st.markdown("**Define Data Paths**")
        st.markdown("""
- Specify the data directory containing calibration and sample measurements.
- The :red-background[directory **must** contain] all calibration samples and measurements.
        """)

        st.markdown("**Specify Wavelength Settings**")
        st.markdown("""
- Set the wavelength range. The maximum range is determined by the source lamp.
- Both calibration and sample processing will use this range.
        """)

        st.markdown("**Select Calibration Mode**")
        st.markdown("""
- Choose between Transmission, Reflection, or Combined mode.
- Currently, only Transmission mode is supported; other modes will be available in future releases.
        """)
        st.info("""
**Tutorial Data:**
- You may select **Turorial Data** in **Calibration Mode** to learn the workflow without needing your own measurements.
- This option loads example calibration data and sample measurements to demonstrate the application's features.
- The Data Directory is automatically prefilled. Saving is not enabled.
- You may still select the wavelength range.
                """)

    with tab2:
        st.markdown("**Continue with calibrating the polarimeter using the ECM.**")
        st.markdown("Ensure all required calibration samples are present by clicking the :blue-background[Discover Files] button. The application automatically searches for required samples by filename patterns.")
        
        st.markdown("**The following calibration samples and label patterns are required:**")
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
        
        st.caption("*Before and after the underscore delimiters can be any string (e.g., sample ID, date, etc.); labels are case-sensitive.")
        st.caption("**Not required, but recommended for best results.")
        
        st.markdown("**Hit :red-background[Run Calibration]**")
        st.markdown("""
- The application will process the calibration data and display eigenvalue metrics to assess the calibration quality.
- You may save the calibration results for future use *(not required)*.
        """)
        
        st.info("""
**Tips:**
- Check calibration status in the sidebar
- Rerun anytime after changing settings
- Load saved calibration results at the bottom
        """)

    with tab3:
        st.markdown("**Now you are ready to process the samples and obtain their Mueller matrices.**")
        st.markdown("Ensure all sample data files are within the specified directory (the same directory as the calibration samples).")
        
        st.markdown("**Hit :blue-background[Discover Samples]**")
        st.markdown("""
- The application will search for sample measurement files.
- You can select which samples to process by checking the boxes next to their names.
- Once you have selected the samples, click :red-background[Process Selected] to start processing.
- The application will process the selected samples and display the results.
- You can save the processed results for future use *(not required)*.
        """)
        
        st.info("""
**Tips:**
- Process samples multiple times
- Hover over plots to see values
- Drag to zoom in on specific areas
- Compare samples side by side
        """)

    with tab4:
        st.markdown("**The raw Mueller matrices of the samples can be converted to fundamental polarization quantities.**")
        st.markdown("Here, you can select which samples you want to post-process.")
        
        st.markdown("**Hit :red-background[Run Decomposition]**")
        st.markdown("""
- The application will perform the Lu–Chipman decomposition on the selected samples and display the extracted parameters.
- The parameters include diattenuation, retardance, depolarization, and eigenmode characteristics.
        """)
        
        st.warning("""
**⚠️  Important Limitations of Lu–Chipman Decomposition:**
- Assumes transmission geometry (may not suit reflection-mode measurements)
- Assumes samples can be represented as ideal optical element sequences
- May not capture complex interactions in scattering or anisotropic samples
- Breakdowns can occur for extreme polarimetric properties
- Always interpret results within your experimental context
        """)
        
        st.info("""
**Tips:**
- Use the Summary Table for quick parameter comparisons
- Rerun decomposition anytime
- Plots offer interactive features
- Export results for external analysis
        """)


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
