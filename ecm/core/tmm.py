"""
Transfer Matrix Method (TMM) for Multilayer Thin-Film Reflectance

Computes ellipsometric parameters (psi, Delta) and reflectances (Rs, Rp)
for a multilayer dielectric/absorbing stack using the 2×2 transfer matrix
formalism. Designed for the Air/SiO2/Interlayer/Si reflector geometry
used in ECM reflection-mode calibration.

Physics
-------
The transfer matrix method propagates electromagnetic fields through a
planar multilayer structure. For each polarization (s and p), a 2×2
system matrix S relates the incoming and outgoing field amplitudes.
The stack reflection coefficient is r = S[1,0] / S[0,0].

Sign convention: Delta = -arg(rp/rs), matching the Woollam ellipsometer
(exp(+iwt) time convention). Our TMM naturally produces rho in the
exp(-iwt) convention, so we negate the phase.

References
----------
[1] Compain et al., Appl. Opt. 38, 3490-3502 (1999)
[2] Azzam & Bashara, "Ellipsometry and Polarized Light", North-Holland (1977)
[3] Born & Wolf, "Principles of Optics", 7th ed., Cambridge (1999)
"""

from pathlib import Path
from typing import Tuple

import numpy as np
from numpy import ndarray


def tmm_reflectance(
    wavelengths: ndarray,
    d_layers: list,
    n_layers: list,
    k_layers: list,
    aoi_deg: float,
) -> Tuple[ndarray, ndarray, ndarray, ndarray]:
    """
    Compute psi, Delta, Rs, Rp for a multilayer stack using TMM.

    Fully vectorized over wavelengths — no Python loop.

    Parameters
    ----------
    wavelengths : ndarray, shape (n_wl,)
        Vacuum wavelengths in nm.
    d_layers : list of float
        Thicknesses of FINITE layers only [nm].
        For our stack: [d_SiO2, d_interlayer].
        Ambient and substrate are semi-infinite (no thickness).
    n_layers : list of ndarray, each shape (n_wl,)
        Refractive index (real part) for ALL layers including ambient
        and substrate. Order: [n_ambient, n_SiO2, n_interlayer, n_Si].
    k_layers : list of ndarray, each shape (n_wl,)
        Extinction coefficient for ALL layers.
        Order: [k_ambient, k_SiO2, k_interlayer, k_Si].
    aoi_deg : float
        Angle of incidence in degrees.

    Returns
    -------
    psi : ndarray, shape (n_wl,) [radians]
        Ellipsometric angle psi = arctan(|rp/rs|).
    delta : ndarray, shape (n_wl,) [radians]
        Ellipsometric phase Delta = -arg(rp/rs) (Woollam convention).
    Rs : ndarray, shape (n_wl,)
        s-polarization reflectance |rs|^2.
    Rp : ndarray, shape (n_wl,)
        p-polarization reflectance |rp|^2.
    """
    n_wl = len(wavelengths)
    n_total_layers = len(n_layers)  # ambient + finite layers + substrate
    n_finite = len(d_layers)        # number of finite (non-semi-infinite) layers

    # Validate input dimensions
    assert n_total_layers == n_finite + 2, (
        f"Expected {n_finite + 2} layers (ambient + {n_finite} finite + substrate), "
        f"got {n_total_layers}"
    )

    # -------------------------------------------------------------------------
    # Complex refractive indices: N_j = n_j + i*k_j
    # (optics convention: positive k for absorbing media)
    # -------------------------------------------------------------------------
    N = [np.asarray(n_layers[j], dtype=np.complex128)
         + 1j * np.asarray(k_layers[j], dtype=np.complex128)
         for j in range(n_total_layers)]

    # -------------------------------------------------------------------------
    # Snell's law: N_0 * sin(theta_0) = N_j * sin(theta_j)
    # cos_theta_j = sqrt(1 - (N_0 * sin(theta_0) / N_j)^2)
    # Choose root with Re(cos_theta_j) > 0 (forward-propagating wave)
    # -------------------------------------------------------------------------
    theta_0 = np.radians(aoi_deg)
    sin_theta_0 = np.sin(theta_0)
    snell_factor = N[0] * sin_theta_0  # shape (n_wl,) — N_0 * sin(theta_0)

    cos_theta = []
    for j in range(n_total_layers):
        cos_j = np.sqrt(1.0 - (snell_factor / N[j])**2)
        # Enforce forward-propagating root: Re(cos_theta) > 0
        cos_j = np.where(cos_j.real < 0, -cos_j, cos_j)
        cos_theta.append(cos_j)

    # -------------------------------------------------------------------------
    # Compute Fresnel coefficients and build system matrix for s and p
    # separately, using vectorized 2x2 element operations.
    #
    # System matrix: S = I_{0,1} @ L_1 @ I_{1,2} @ L_2 @ ... @ I_{N-1,N}
    #
    # Interface matrix I_{j,j+1} = (1/t_{j,j+1}) * [[1, r_{j,j+1}],
    #                                                  [r_{j,j+1}, 1]]
    #
    # Layer matrix L_j = [[exp(-i*beta_j), 0],
    #                      [0, exp(i*beta_j)]]
    # -------------------------------------------------------------------------

    for pol in ('s', 'p'):
        # Start with identity matrix (vectorized 2x2)
        S00 = np.ones(n_wl, dtype=np.complex128)
        S01 = np.zeros(n_wl, dtype=np.complex128)
        S10 = np.zeros(n_wl, dtype=np.complex128)
        S11 = np.ones(n_wl, dtype=np.complex128)

        for j in range(n_total_layers - 1):
            # -----------------------------------------------------------------
            # Fresnel coefficients at interface j -> j+1
            # -----------------------------------------------------------------
            if pol == 's':
                # r_s = (N_j cos_j - N_{j+1} cos_{j+1}) /
                #       (N_j cos_j + N_{j+1} cos_{j+1})
                numer_r = N[j] * cos_theta[j] - N[j+1] * cos_theta[j+1]
                denom = N[j] * cos_theta[j] + N[j+1] * cos_theta[j+1]
                # t_s = 2 N_j cos_j / (N_j cos_j + N_{j+1} cos_{j+1})
                numer_t = 2.0 * N[j] * cos_theta[j]
            else:  # pol == 'p'
                # r_p = (N_{j+1} cos_j - N_j cos_{j+1}) /
                #       (N_{j+1} cos_j + N_j cos_{j+1})
                numer_r = N[j+1] * cos_theta[j] - N[j] * cos_theta[j+1]
                denom = N[j+1] * cos_theta[j] + N[j] * cos_theta[j+1]
                # t_p = 2 N_j cos_j / (N_{j+1} cos_j + N_j cos_{j+1})
                numer_t = 2.0 * N[j] * cos_theta[j]

            r_jk = numer_r / denom
            t_jk = numer_t / denom

            # -----------------------------------------------------------------
            # Interface matrix: I = (1/t) * [[1, r], [r, 1]]
            # Multiply S = S @ I (right-multiply)
            # -----------------------------------------------------------------
            inv_t = 1.0 / t_jk
            # New S = old_S @ I
            new_S00 = (S00 + S01 * r_jk) * inv_t
            new_S01 = (S00 * r_jk + S01) * inv_t
            new_S10 = (S10 + S11 * r_jk) * inv_t
            new_S11 = (S10 * r_jk + S11) * inv_t
            S00, S01, S10, S11 = new_S00, new_S01, new_S10, new_S11

            # -----------------------------------------------------------------
            # Layer matrix for finite layer j+1 (if not the substrate)
            # L = [[exp(-i*beta), 0], [0, exp(i*beta)]]
            # -----------------------------------------------------------------
            finite_layer_idx = j + 1 - 1  # index into d_layers (0-based)
            if 0 <= finite_layer_idx < n_finite:
                d_j = d_layers[finite_layer_idx]
                # Phase thickness: beta = (2*pi/lambda) * N_{j+1} * cos(theta_{j+1}) * d
                beta = (2.0 * np.pi / wavelengths) * N[j+1] * cos_theta[j+1] * d_j
                exp_neg = np.exp(-1j * beta)
                exp_pos = np.exp(1j * beta)
                # S = S @ L
                new_S00 = S00 * exp_neg
                new_S01 = S01 * exp_pos
                new_S10 = S10 * exp_neg
                new_S11 = S11 * exp_pos
                S00, S01, S10, S11 = new_S00, new_S01, new_S10, new_S11

        # Reflection coefficient: r = S[1,0] / S[0,0]
        r_total = S10 / S00

        if pol == 's':
            rs = r_total
        else:
            rp = r_total

    # -------------------------------------------------------------------------
    # Ellipsometric parameters
    # -------------------------------------------------------------------------
    rho = rp / rs                           # Complex ratio
    psi = np.arctan(np.abs(rho))            # psi = arctan(|rp/rs|)
    delta = -np.angle(rho)                  # Woollam convention: Delta = -arg(rho)
    Rs = np.abs(rs)**2                      # s-reflectance
    Rp = np.abs(rp)**2                      # p-reflectance

    return psi, delta, Rs, Rp


def compute_reflector_properties(
    wavelengths: ndarray,
    d_SiO2: float,
    d_interlayer: float,
    n_k_data: dict,
    aoi_deg: float,
) -> Tuple[ndarray, ndarray, ndarray, ndarray]:
    """
    Compute psi, Delta, Rs, Rp for the Air/SiO2/Interlayer/Si reflector stack.

    Convenience wrapper around tmm_reflectance() for the specific ECM
    reflector geometry.

    Parameters
    ----------
    wavelengths : ndarray, shape (n_wl,)
        Vacuum wavelengths in nm.
    d_SiO2 : float
        SiO2 layer thickness in nm.
    d_interlayer : float
        Interlayer thickness in nm (typically 1.0 nm, fixed).
    n_k_data : dict
        Optical constants: {'Si': (n, k), 'SiO2': (n, k), 'Interlayer': (n, k)}.
        Each n, k is an ndarray of shape (n_wl,).
    aoi_deg : float
        Angle of incidence in degrees.

    Returns
    -------
    psi : ndarray [radians]
    delta : ndarray [radians]
    Rs : ndarray
    Rp : ndarray
    """
    n_wl = len(wavelengths)

    # Assemble layer stack: Air / SiO2 / Interlayer / Si
    n_layers = [
        np.ones(n_wl),                 # Air (ambient)
        n_k_data['SiO2'][0],           # SiO2
        n_k_data['Interlayer'][0],     # Interlayer
        n_k_data['Si'][0],             # Si (substrate)
    ]
    k_layers = [
        np.zeros(n_wl),                # Air
        n_k_data['SiO2'][1],           # SiO2
        n_k_data['Interlayer'][1],     # Interlayer
        n_k_data['Si'][1],             # Si
    ]
    d_layers = [d_SiO2, d_interlayer]  # Finite layer thicknesses

    return tmm_reflectance(wavelengths, d_layers, n_layers, k_layers, aoi_deg)


def load_nk_data(assets_dir: Path) -> dict:
    """
    Load n,k dispersion data for Si, SiO2, and Interlayer from assets directory.

    Parameters
    ----------
    assets_dir : Path
        Directory containing Si_nk.txt, SiO2_nk.txt, and Interlayer_nk.txt.

    Returns
    -------
    n_k_data : dict
        {'Si': (n, k), 'SiO2': (n, k), 'Interlayer': (n, k), 'wavelengths': wl}
        where each n, k, wl is an ndarray of shape (n_wl,).
    """
    assets_dir = Path(assets_dir)
    n_k_data = {}

    for material, filename in [
        ('Si', 'Si_nk.txt'),
        ('SiO2', 'SiO2_nk.txt'),
        ('Interlayer', 'Interlayer_nk.txt'),
    ]:
        filepath = assets_dir / filename
        data = np.loadtxt(filepath, comments='#')
        wavelengths = data[:, 0]
        n = data[:, 1]
        k = data[:, 2]
        n_k_data[material] = (n, k)
        print(f"  Loaded {material} n,k: {len(wavelengths)} points, "
              f"{wavelengths[0]:.1f}-{wavelengths[-1]:.1f} nm")

    n_k_data['wavelengths'] = wavelengths

    return n_k_data


def trim_nk_data(n_k_data: dict, target_wavelengths: ndarray) -> dict:
    """
    Trim n,k data to match measurement wavelengths by index masking.

    All data files share the same StellarNet BlackComet spectrometer grid.
    The n,k data spans 400-1000 nm (1414 pixels) while measurements may
    use a narrower range (e.g. 450-900 nm, 1039 pixels). This function
    finds the matching indices and extracts the subset — no interpolation.

    Parameters
    ----------
    n_k_data : dict
        From load_nk_data(): {'wavelengths': wl, 'Si': (n, k), ...}.
    target_wavelengths : ndarray, shape (n_target,)
        Measurement wavelengths [nm] — must be a subset of n_k_data['wavelengths'].

    Returns
    -------
    n_k_trimmed : dict
        Same structure, trimmed to target wavelength range.

    Raises
    ------
    ValueError
        If target wavelengths are not a subset of n,k wavelengths.
    """
    source_wl = n_k_data['wavelengths']
    wl_min, wl_max = target_wavelengths[0], target_wavelengths[-1]

    # Find indices of source wavelengths within target range
    mask = (source_wl >= wl_min - 0.01) & (source_wl <= wl_max + 0.01)
    idx = np.where(mask)[0]

    if len(idx) != len(target_wavelengths):
        raise ValueError(
            f"Wavelength grid mismatch: n,k data has {len(idx)} points in "
            f"[{wl_min:.1f}, {wl_max:.1f}] nm, but measurement has "
            f"{len(target_wavelengths)} points. "
            f"Ensure both use the same spectrometer grid."
        )

    # Verify grids match (same BlackCommet pixels)
    max_diff = np.max(np.abs(source_wl[idx] - target_wavelengths))
    if max_diff > 0.01:
        raise ValueError(
            f"Wavelength grids do not align: max difference = {max_diff:.4f} nm. "
            f"Expected identical BlackCommet spectrometer pixels."
        )

    n_k_trimmed = {'wavelengths': source_wl[idx].copy()}
    for material in ('Si', 'SiO2', 'Interlayer'):
        n_raw, k_raw = n_k_data[material]
        n_k_trimmed[material] = (n_raw[idx].copy(), k_raw[idx].copy())

    return n_k_trimmed


def interpolate_nk_to_wavelengths(n_k_data: dict, target_wavelengths: ndarray) -> dict:
    """
    Interpolate n,k dispersion data to a target wavelength grid.

    Uses linear interpolation (np.interp) for wavelength remapping. This is
    the general-purpose alternative to trim_nk_data(), which requires exact
    grid alignment. Use this when the target grid may not match the source
    grid exactly (e.g., when computing TMM at arbitrary wavelengths).

    Parameters
    ----------
    n_k_data : dict
        From load_nk_data(): {'wavelengths': wl, 'Si': (n, k), 'SiO2': (n, k),
        'Interlayer': (n, k)}.
    target_wavelengths : ndarray, shape (n_target,)
        Target wavelength grid [nm].

    Returns
    -------
    n_k_interp : dict
        Same structure with arrays interpolated to target grid.
        {'Si': (n_interp, k_interp), 'SiO2': ..., 'Interlayer': ...,
         'wavelengths': target_wavelengths}
    """
    source_wl = n_k_data['wavelengths']
    n_k_interp = {'wavelengths': target_wavelengths.copy()}

    for material in ('Si', 'SiO2', 'Interlayer'):
        n_raw, k_raw = n_k_data[material]
        n_interp = np.interp(target_wavelengths, source_wl, n_raw)
        k_interp = np.interp(target_wavelengths, source_wl, k_raw)
        n_k_interp[material] = (n_interp, k_interp)

    return n_k_interp
