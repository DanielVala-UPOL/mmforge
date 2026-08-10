"""
ECM Post-Processing Module

Four decomposition methods for extracting physical parameters from Mueller matrices.

Decompositions
--------------
Lu-Chipman polar decomposition
    M = M_Delta @ M_R @ M_D — diattenuation, retardance, depolarization.
    Result class: LuChipmanResult

Differential decomposition (Minkowski metric)
    L = ln(M), split into G-antisymmetric (mean properties L_m)
    and G-symmetric (depolarization uncertainties L_u) components.
    Result class: DifferentialDecompositionResult

Cloude spectral decomposition
    Coherency matrix H eigendecomposition into dominant and secondary
    scattering mechanism Mueller matrices.
    Result class: CloudeDecompositionResult

Purity space analysis
    Purity indices P_P (polarizance), P_S (spherical purity),
    P_Delta (overall polarimetric purity) for the purity space diagram.
    Result class: PurityResult

References
----------
[3] Lu & Chipman, J. Opt. Soc. Am. A 13, 1106-1113 (1996)
[4] Gil & Ossikovski, "Polarized Light and the Mueller Matrix Approach"
    (2nd ed.), CRC Press (2022), Sections 9.4.1, 5.3, 6.2
[5] Chipman et al., "Polarized Light and Optical Systems", CRC Press (2018)
"""

from ecm.postprocessing.lu_chipman import (
    LuChipmanResult,
    lu_chipman_decomposition,
)

from ecm.postprocessing.differential_decomposition import (
    DifferentialDecompositionResult,
    differential_decomposition,
)

from ecm.postprocessing.cloude_decomposition import (
    CloudeDecompositionResult,
    cloude_decomposition,
)

from ecm.postprocessing.purity_space import (
    PurityResult,
    purity_analysis,
)

__all__ = [
    'LuChipmanResult',
    'lu_chipman_decomposition',
    'DifferentialDecompositionResult',
    'differential_decomposition',
    'CloudeDecompositionResult',
    'cloude_decomposition',
    'PurityResult',
    'purity_analysis',
]
