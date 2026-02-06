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

    with st.expander("1: Configure", expanded=False):
        st.markdown("""
        **Begin by configuring the application to suit your experimental setup.**

        **Define :blue-background[**Data Paths]**
        - Specify the data directory containing calibration and sample measurements.
        - The directory *must* contain all calibration samples and measurements.

        **Specify :blue-background[Wavelength Settings]**
        - Set the wavelength range. The maximum range is determined by the source lamp.
        - Both calibration and sample processing will use this range.

        **Adjust :blue-background[Acquisition Settings]**
        - Define the number of discrete steps per one rotation cycle of the compensator in the Polarization State Generator (PSG).
        - This **must** match the hardware settings used during measurements.
        - The default value (96 positions) provides good accuracy while maintaining reasonable measurement time; however, any value >16 can be used.
    """)

    with st.expander("2: Calibrate", expanded=False):
        st.markdown("""
        **Continue with calibrating the polarimeter using the ECM.**
        - Ensure all required calibration samples are present by clicking the :blue-background[Discover Files] button. The application automatically searches for required samples by filename patterns.

        **The following calibration samples and label patterns(*) are required:**
        - Background (closed shutter): :blue-background[\\_DARK_ECM\\_]
        - Air (empty straight-through measurement): :blue-background[\\_ST_ECM\\_]
        - Linear polarizer at 0°: :blue-background[\\_P0_ECM\\_]
        - Linear polarizer at 45°: :blue-background[\\_P45_ECM\\_]
        - Fresnel prism FP1 at 90°: :blue-background[\\_RET90_FP1_ECM\\_]
        - Fresnel prism FP2 at 45° (*recommended, not required*): :blue-background[\\_RET45_FP2_ECM\\_]
        - (*) Before and after the underscore delimiters can be any string (e.g., sample ID, date, etc.); labels are case-sensitive.

        **Hit :red-background[Run Calibration]**
        - The application will process the calibration data and display eigenvalue metrics to assess the calibration quality.
        - You may save the calibration results for future use *(not required)*.

        **Tips:**
        - You can check the calibration status in the :blue-background[sidebar].
        - You may rerun the calibration at any time (e.g., after changing configuration settings) by hitting :red-background[Run Calibration] again.
        - If you have previously saved calibration results, you may load them by specifying the data directory and clicking :blue-background[Load Saved Calibration] at the bottom of the page.
    """)

    with st.expander("3: Process", expanded=False):
        st.markdown("""
        **Now you are ready to process the samples and obtain their Mueller matrices.**
        - Ensure all sample data files are within the specified directory (the same directory as the calibration samples).

        **Hit :blue-background[Discover Samples]**
        - The application will search for sample measurement files.
        - You can select which samples to process by checking the boxes next to their names.
        - Once you have selected the samples, click :red-background[Process Selected] to start processing.
        - The application will process the selected samples and display the results.
        - You can save the processed results for future use *(not required)*.

        **Tips:**
        - You can process samples multiple times by selecting them and hitting :red-background[Process Selected] again.
        - The Mueller matrix plots offer a good degree of interactivity — hover over elements to see values, drag to zoom in, or toggle visibility of individual elements by clicking on the legend items.
        - You can also select which elements to display using the checkboxes next to the plots.
        - Selected samples can be compared side by side in the overlay figures.
    """)

    with st.expander("4: Parameter Extraction", expanded=False):
        st.markdown("""
        **The raw Mueller matrices of the samples can be converted to fundamental polarization quantities.**
        - Here, you can select which samples you want to post-process.

        **Hit :red-background[Run Decomposition]**
        - The application will perform the Lu–Chipman decomposition on the selected samples and display the extracted parameters.
        - The parameters include diattenuation, retardance, depolarization, and eigenmode characteristics.

        **Caution: The Lu–Chipman decomposition is useful for general analysis, but be aware of its limitations:**
        - It assumes transmission geometry and may not be suitable for reflection-mode measurements.
        - It assumes the sample can be represented as a specific sequence of ideal optical elements, which may not hold for all samples.
        - It may not accurately capture complex interactions in highly scattering or anisotropic samples.
        - Breakdowns can occur for samples with extreme polarimetric properties (e.g., near-perfect polarizers or retarders).
        - Extracted parameters should be interpreted with caution, especially when the sample deviates significantly from the model assumptions.
        - Always interpret the results within the context of your specific experimental setup and sample characteristics.

        **Tips:**
        - Explore the :blue-background[Summary Table] in the :red-background[Single Wavelengths] section for a quick comparison of key parameters across samples.
        - You can run the decomposition multiple times by selecting samples and hitting :red-background[Run Decomposition] again.
        - The parameter plots offer interactivity similar to the Mueller matrix plots.
        - You may export the results.
    """)


# ============================================================================
# RUN PAGE
# ============================================================================

if __name__ == "__main__":
    main()
else:
    main()
