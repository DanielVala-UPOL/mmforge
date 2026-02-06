"""
Export Utilities - Save plots and data to files.

Provides functions for:
- Exporting Plotly figures to PNG
- Exporting Mueller matrix data to CSV
- Exporting decomposition results to CSV

Author: Daniel Vala
"""

import numpy as np
from numpy import ndarray
import pandas as pd


# ============================================================================
# FIGURE EXPORT
# ============================================================================

def export_figure_png(fig, filename: str, scale: float = 2.0) -> bytes:
    """
    Export Plotly figure to PNG bytes.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
        Plotly figure to export.
    filename : str
        Filename (used for download, not saved to disk).
    scale : float
        Resolution scale factor. Default 2.0 for high resolution.

    Returns
    -------
    png_bytes : bytes
        PNG image as bytes (for st.download_button).

    Notes
    -----
    Requires kaleido package for static image export.
    """
    try:
        png_bytes = fig.to_image(format="png", scale=scale)
        return png_bytes
    except Exception as e:
        raise RuntimeError(
            f"Error exporting figure: {e}. "
            f"Make sure kaleido is installed: pip install kaleido"
        )


# ============================================================================
# DATA EXPORT
# ============================================================================

def export_mueller_csv(
    M_normalized: ndarray,
    wavelengths: ndarray,
    sample_name: str = "sample"
) -> str:
    """
    Export normalized Mueller matrix data to CSV string.

    Format: wavelength_nm, m11, m12, m13, m14, ..., m44

    Parameters
    ----------
    M_normalized : ndarray, shape (4, 4, n_wavelengths)
        Normalized Mueller matrices.
    wavelengths : ndarray
        Wavelength values in nm.
    sample_name : str
        Sample name for metadata.

    Returns
    -------
    csv_string : str
        CSV data as string (for st.download_button).
    """
    n_wl = len(wavelengths)

    # Build data dictionary
    data = {'wavelength_nm': wavelengths}

    for i in range(4):
        for j in range(4):
            col_name = f'm{i+1}{j+1}'
            data[col_name] = M_normalized[i, j, :]

    df = pd.DataFrame(data)

    # Add header comment with metadata
    header = f"# ECM Mueller Matrix Export - {sample_name}\n"
    header += f"# Wavelengths: {n_wl}\n"
    header += f"# Range: {wavelengths.min():.1f} - {wavelengths.max():.1f} nm\n"

    csv_string = header + df.to_csv(index=False)

    return csv_string


def export_lu_chipman_csv(
    lu_result,
    wavelengths: ndarray,
    sample_name: str = "sample"
) -> str:
    """
    Export Lu-Chipman decomposition results to CSV string.

    Parameters
    ----------
    lu_result : LuChipmanResult
        Lu-Chipman decomposition result.
    wavelengths : ndarray
        Wavelength values in nm.
    sample_name : str
        Sample name for metadata.

    Returns
    -------
    csv_string : str
        CSV data as string.
    """
    data = {
        'wavelength_nm': wavelengths,
        'DI': lu_result.DI,
        'D': lu_result.D,
        'R_deg': lu_result.R_deg,
        'R_waves': lu_result.R_waves,
        'psi_deg': lu_result.psi_deg,
        'chi_deg': lu_result.chi_deg,
    }

    df = pd.DataFrame(data)

    header = f"# ECM Lu-Chipman Decomposition - {sample_name}\n"
    header += f"# DI: Depolarization Index [0,1]\n"
    header += f"# D: Diattenuation [0,1]\n"
    header += f"# R_deg: Retardance [degrees]\n"
    header += f"# R_waves: Retardance [waves]\n"
    header += f"# psi_deg: Fast-axis azimuth [degrees]\n"
    header += f"# chi_deg: Ellipticity angle [degrees]\n"

    csv_string = header + df.to_csv(index=False)

    return csv_string


def export_calibration_summary_csv(
    calibration_info: dict,
    eigenvalue_ratios: ndarray,
    wavelengths: ndarray
) -> str:
    """
    Export calibration summary to CSV string.

    Parameters
    ----------
    calibration_info : dict
        Calibration summary information.
    eigenvalue_ratios : ndarray
        Eigenvalue ratios at each wavelength.
    wavelengths : ndarray
        Wavelength values in nm.

    Returns
    -------
    csv_string : str
        CSV data as string.
    """
    data = {
        'wavelength_nm': wavelengths,
        'eigenvalue_ratio': eigenvalue_ratios,
    }

    df = pd.DataFrame(data)

    header = f"# ECM Calibration Summary\n"
    header += f"# Wavelengths: {calibration_info.get('n_wavelengths', 'N/A')}\n"
    header += f"# Range: {calibration_info.get('wl_min', 'N/A'):.1f} - {calibration_info.get('wl_max', 'N/A'):.1f} nm\n"
    header += f"# Mean eigenvalue ratio: {calibration_info.get('mean_ratio', 'N/A'):.2e}\n"

    csv_string = header + df.to_csv(index=False)

    return csv_string


# ============================================================================
# BATCH EXPORT
# ============================================================================

def create_export_zip(files_dict: dict) -> bytes:
    """
    Create a zip file from a dictionary of filename -> content pairs.

    Parameters
    ----------
    files_dict : dict
        Dictionary mapping filenames to content (str for CSV, bytes for PNG).

    Returns
    -------
    zip_bytes : bytes
        Zip file as bytes for download.

    Example
    -------
    files = {
        "sample1_mueller.csv": csv_string,
        "sample1_plot.png": png_bytes,
    }
    zip_bytes = create_export_zip(files)
    st.download_button("Download All", data=zip_bytes, file_name="export.zip")
    """
    import io
    import zipfile

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files_dict.items():
            if isinstance(content, str):
                zf.writestr(filename, content.encode('utf-8'))
            else:
                zf.writestr(filename, content)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()
