"""
ECM Post-Processing Module

Provides Lu-Chipman polar decomposition for extracting physical parameters
from Mueller matrices.

Functions
---------
lu_chipman_decomposition(M_norm)
    Decompose normalized Mueller matrix into M = M_Δ · M_R · M_D

Classes
-------
LuChipmanResult
    Dataclass containing decomposition results and extracted parameters

References
----------
[1] Lu & Chipman, J. Opt. Soc. Am. A 13, 1106-1113 (1996)
[2] Chipman et al., "Polarized Light and Optical Systems" (2018)
"""

from ecm.postprocessing.lu_chipman import (
    LuChipmanResult,
    lu_chipman_decomposition,
)

__all__ = [
    'LuChipmanResult',
    'lu_chipman_decomposition',
]
