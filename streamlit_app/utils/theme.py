"""
Theme palettes - the single source of truth for every colour in the GUI.

MMForge ships two themes. Both are defined here, as plain dictionaries, so
that the Plotly helpers (``components/plots_plotly.py``), the injected CSS
(``utils/styling.py``) and the inline HTML blocks on the pages all read the
same values instead of each carrying its own hex literals.

Two palettes, not one
---------------------
The dark theme deliberately uses **two** colour families:

- **Chrome** (``bg``, ``panel``, ``text``, ``structural``, ...) is slate,
  drawn from the navy in the MMForge logo, so the app keeps its identity.
- **Charts** (``chart_*``, ``traces``, ``quality``) sit on a near-black
  ``#121212`` panel with more saturated traces.

The chart panel is therefore *one shade darker* than the app around it.
That is intentional: the figure reads as a recessed panel and the data
stands out. Do not "harmonise" the two. The governing rule is **chrome
recedes, data stays legible** - the app overlays up to 16 sample curves,
and desaturating those along with the UI would be an accessibility
regression, not a style choice.

In light mode, elevation is expressed with *darker* colours. In dark mode
this inverts: elevated surfaces are *lighter* than the background. That is
why ``structural`` is not the same hex in both palettes - it is the same
slate hue, lightened to sit above the background rather than below it.

How the active theme is detected
--------------------------------
``current_theme_name()`` resolves in three steps:

1. the ``MMFORGE_FORCE_THEME`` environment variable, if it is ``light`` or
   ``dark``;
2. ``st.context.theme.type``, which Streamlit infers from the background
   colour the browser reports;
3. ``"light"`` on anything unexpected.

**Measured behaviour under ``streamlit.testing.v1.AppTest`` (Streamlit
1.61.1):** ``st.context.theme`` does *not* raise - it returns the mapping
``{'type': None}``, i.e. the attribute exists and its value is ``None``.
The same is true when the module is imported outside a script run. So the
headless fallback is reached via the "unrecognised value" branch, not via
an exception, and the dark code path is unreachable in tests *unless*
``MMFORGE_FORCE_THEME=dark`` is set. That variable exists for exactly this
reason (and for a user who wants to pin a theme); it is not a second
toggle and it gets no UI. The user-facing switch is Streamlit's own, in
the toolbar menu under Settings -> Appearance.

Known caveat (Streamlit issue #11920): ``st.context.theme.type`` is
inferred from the browser-reported background colour and may be stale on
the first run of a session and on the run immediately after the user flips
the theme. ``sync_theme()`` absorbs the second case by rerunning once when
it sees the value change. A one-frame lag on charts is accepted; a second,
custom toggle that could disagree with Streamlit's own would be worse.

Author: Daniel Vala
"""

import os
from typing import Dict, List, Optional

import streamlit as st

# ============================================================================
# PALETTES
# ============================================================================

# The light values are the ones MMForge has always shipped, lifted verbatim
# from ``utils/styling.py`` and ``components/plots_plotly.py``. They are a
# regression baseline, not a design surface: the light theme must not change
# by a single pixel in the v2.2.0 release.
LIGHT: Dict[str, object] = {
    # chrome
    'bg':               '#FFFFFF',
    'panel':            '#F8F9FA',
    'panel_raised':     '#E9ECEF',
    'text':             '#333333',
    'text_dim':         '#666666',
    'border':           '#E0E0E0',
    'primary':          '#FF1F5B',
    'primary_hover':    '#D91A4E',
    'on_primary':       '#FFFFFF',
    'structural':       '#2D3E50',   # expanders, sidebar highlights
    'structural_hover': '#3D5166',
    'success':          '#56D39A',
    'warning':          '#E8C34A',
    'info':             '#0C8AB3',
    'error':            '#C22026',
    # charts
    'chart_bg':         '#FFFFFF',
    'chart_panel':      '#FFFFFF',
    'chart_grid':       '#E8E8E8',
    'chart_axis':       '#000000',
    'chart_text':       '#333333',
    'chart_tick':       '#666666',
    'quality': {'excellent': '#0C8AB3', 'good': '#56D39A',
                'acceptable': '#E8C34A', 'marginal': '#FF1F5B',
                'poor': '#C22026'},
    'traces': ['#0C8AB3', '#FF1F5B', '#56D39A', '#E8C34A',
               '#EC3CF9', '#9467BD', '#8C564B', '#7F7F7F',
               '#20C9E7', '#A6B840', '#1AFF00', '#F6FF00',
               '#0015FF', '#FF7B00', '#FF0000', '#000000'],
}

DARK: Dict[str, object] = {
    # chrome - palette A, the slate family from the logo
    'bg':               '#161C24',
    'panel':            '#1F2833',
    'panel_raised':     '#2A3542',
    'text':             '#DDE3EA',
    'text_dim':         '#93A1B0',
    'border':           '#2C3845',
    'primary':          '#E87392',
    'primary_hover':    '#F08CA6',
    'on_primary':       '#161C24',
    'structural':       '#899DB3',   # the slate, LIGHTENED - see module docstring
    'structural_hover': '#9DAFC2',
    'success':          '#73D3A7',
    'warning':          '#DEC573',
    'info':             '#69B9D3',
    'error':            '#DE7377',
    # charts - palette B, deliberately darker than the chrome
    'chart_bg':         '#121212',
    'chart_panel':      '#1E1E1E',
    'chart_grid':       '#2E2E2E',
    'chart_axis':       '#5A5A5A',
    'chart_text':       '#E6E6E6',
    'chart_tick':       '#9AA0A6',
    'quality': {'excellent': '#4BB9DD', 'good': '#5AD89F',
                'acceptable': '#E4C358', 'marginal': '#F34977',
                'poor': '#E4585D'},
    # Same 16 entries, same order as the light list, every one of them above
    # contrast 4.5 on '#121212'. Two of the light entries are outright bugs on
    # any dark background and are fixed here: #16 was pure black (contrast
    # 1.12) and #13 pure blue (2.28). Blue hues get a higher lightness floor
    # than the rest because blue-on-black is the hardest combination the eye
    # has to resolve.
    'traces': ['#40CAE7', '#E7406D', '#56D39A', '#E8C34A',
               '#DE4CE9', '#966ABE', '#B47E74', '#949494',
               '#40B2E7', '#B8C860', '#51E740', '#E2E740',
               '#7781EE', '#E79140', '#E74040', '#E8E8E8'],
}

PALETTES: Dict[str, Dict[str, object]] = {'light': LIGHT, 'dark': DARK}

# Heatmaps keep Plasma in both themes. It is perceptually uniform and was
# verified to read correctly on white and on '#121212' alike.
HEATMAP_COLORSCALE = 'Plasma'

#: Environment variable that pins the theme, bypassing browser detection.
FORCE_THEME_ENV = 'MMFORGE_FORCE_THEME'

#: Session-state key holding the theme seen on the previous script run.
#: Registered in ``SESSION_KEYS`` (``utils/session_state.py``) so that
#: ``initialize_session_state()`` creates it and the re-bind loop protects it
#: from Streamlit's page-navigation cleanup.
THEME_STATE_KEY = 'active_theme'


# ============================================================================
# ACTIVE THEME
# ============================================================================

def current_theme_name() -> str:
    """Return the name of the active theme: ``'light'`` or ``'dark'``.

    Resolution order is the environment override, then Streamlit's own
    browser-derived value, then ``'light'``. See the module docstring for
    what each of those actually does headlessly.
    """
    forced = os.environ.get(FORCE_THEME_ENV, '').strip().lower()
    if forced in PALETTES:
        return forced

    try:
        reported = st.context.theme.type
    except Exception:
        return 'light'

    if isinstance(reported, str) and reported.lower() in PALETTES:
        return reported.lower()
    return 'light'


def palette(theme_name: Optional[str] = None) -> Dict[str, object]:
    """Return the palette dict for ``theme_name``, or for the active theme.

    The dict is the module-level one, not a copy - treat it as read-only.
    """
    if theme_name is None:
        theme_name = current_theme_name()
    return PALETTES.get(theme_name, LIGHT)


def is_dark() -> bool:
    """True when the dark theme is active."""
    return current_theme_name() == 'dark'


def trace_colors(theme_name: Optional[str] = None) -> List[str]:
    """Return the 16-entry multi-sample trace colour sequence."""
    return palette(theme_name)['traces']


def quality_colors(theme_name: Optional[str] = None) -> Dict[str, str]:
    """Return the calibration-quality tier colours."""
    return palette(theme_name)['quality']


def rgba(hex_color: str, alpha: float) -> str:
    """Return ``hex_color`` as a CSS/Plotly ``rgba()`` string at ``alpha``.

    Both the injected CSS and the Plotly legend fills need translucent
    versions of palette colours. Deriving them here keeps the source of
    truth in one place instead of spreading pre-computed rgba triplets
    around the codebase.
    """
    h = hex_color.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {alpha})'


def sync_theme() -> str:
    """Detect a theme change and rerun once so every figure catches up.

    Call this near the top of a page, after ``initialize_session_state()``.

    Streamlit repaints its own chrome the instant the user flips the theme,
    but the Plotly figures were already built with the old palette during
    that run. Comparing against the value stored on the previous run and
    triggering a single ``st.rerun()`` rebuilds them with the new one.

    **What this does not do.** Flipping the theme does not itself re-run the
    Python script - Streamlit only restyles the page in the browser - so
    this function cannot fire at that moment. The figures already on screen
    keep the old palette until the next rerun for any reason: changing page,
    pressing a button, moving a widget. Measured on 1.61.1: switching the
    theme while sitting on a page leaves its charts alone, and navigating
    away and back repaints them.

    Closing that gap would mean polling from a fragment on a timer, which is
    not something to add to pages that run calibrations, and a second custom
    toggle is ruled out (see the module docstring). The lag is accepted.

    The first run of a session stores the value without rerunning: there is
    nothing to catch up with yet, and the browser-reported value is least
    trustworthy at exactly that moment.

    Returns the active theme name (only when it has not changed - a rerun
    does not return).
    """
    name = current_theme_name()
    previous = st.session_state[THEME_STATE_KEY] if THEME_STATE_KEY in st.session_state else None

    if previous != name:
        st.session_state[THEME_STATE_KEY] = name
        if previous is not None:
            st.rerun()

    return name
