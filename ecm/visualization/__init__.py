"""
ECM Visualization Module

Publication-quality plotting functions for Mueller matrices, polarimetric
parameters, and diagnostic visualizations.

Plotting Functions
------------------
plot_mueller_matrix(M, wavelengths, ...)
    4×4 subplot grid of Mueller matrix elements vs wavelength

plot_polarimetric_parameters(lu_result, wavelengths, ...)
    Lu-Chipman parameters: DI, Retardance (degrees/waves), Diattenuation, axis

plot_decomposed_matrices(decomp, wavelengths, ...)
    Decomposed M_D, M_R, M_Δ matrices

plot_intensity_data(intensity, wavelengths, omega, ...)
    Intensity diagnostics: spectral, angular, heatmap

Utilities
---------
setup_figure(name, ...)
    Create figure with publication-quality defaults

format_axes(ax, xlabel, ylabel, ...)
    Apply consistent formatting to axes

get_publication_colors()
    Return color palette for publication plots

Style Guidelines
----------------
Default styling follows publication standards suitable for
Nature Photonics, Science Advances, and similar journals:

- Font size: 14 pt (labels, ticks, legend), 16 pt (titles)
- Line width: 1.5 pt
- Figure background: white
- Grid: light gray, dashed
- DPI: 300 for saved figures

References
----------
[1] Lu & Chipman, J. Opt. Soc. Am. A 13, 1106-1113 (1996)
"""

from ecm.visualization.figure_utils import (
    setup_figure,
    format_axes,
    get_publication_colors,
    PUBLICATION_RCPARAMS,
)

from ecm.visualization.mueller_plots import (
    plot_mueller_matrix,
    plot_mueller_element,
)

from ecm.visualization.parameter_plots import (
    plot_polarimetric_parameters,
    plot_depolarization_index,
    plot_retardance,
    plot_diattenuation,
    plot_retarder_axis,
)

from ecm.visualization.decomposition_plots import (
    plot_decomposed_matrices,
    plot_decomposed_matrix,
)

from ecm.visualization.intensity_plots import (
    plot_intensity_data,
    plot_intensity_heatmap,
)

__all__ = [
    # Utilities
    'setup_figure',
    'format_axes',
    'get_publication_colors',
    'PUBLICATION_RCPARAMS',
    # Mueller plots
    'plot_mueller_matrix',
    'plot_mueller_element',
    # Parameter plots
    'plot_polarimetric_parameters',
    'plot_depolarization_index',
    'plot_retardance',
    'plot_diattenuation',
    'plot_retarder_axis',
    # Decomposition plots
    'plot_decomposed_matrices',
    'plot_decomposed_matrix',
    # Intensity plots
    'plot_intensity_data',
    'plot_intensity_heatmap',
]
