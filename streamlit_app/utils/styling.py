"""
Shared styling utilities for MMForge.

This module consolidates all CSS styling into a single source of truth,
reducing duplication across page files and making style changes easier.

Color Strategy
--------------
The colours come from the active theme's palette (``utils/theme.py``);
nothing here is a hardcoded hex any more. The CSS string is *built* per
script run, because the palette that should feed it is only known then.

- PRIMARY: brand magenta - buttons, sliders, checkboxes, links
- STRUCTURAL: the MMForge slate - expanders, sidebar highlights
- Status colours: success / warning / info

Why the CSS has to be theme-aware at all: it is injected with
``!important`` and therefore *overrides* whatever theme Streamlit itself
picked. Left as literals, the expander headers would keep forcing a light
grey body with #333333 text onto a dark page, which is unreadable.

The roles below are the reason this is a table rather than an f-string
with palette lookups inline. Most roles are the same token in both themes,
but a few genuinely differ:

- table headers take the *elevated surface* in dark, not the slate, and
  their text has to follow (dark text on #2A3542 would be invisible);
- the slider's inactive track has no palette token - light mode has always
  used a bare ``#ddd``, so that literal is kept and dark gets the elevated
  surface, which plays the same "muted track" role.

Expander headers and secondary buttons also take the elevated surface in
dark rather than the lightened slate. That is a deliberate departure from
the plan's section 2.3, made on review: the slate at #899DB3 turned every
expander header into a bright bar and added a fourth blue to a palette
that already had three, which read as neither elegant nor legible. The
elevated surface keeps the elevation logic 2.3 is really about - raised
things are lighter than the page in dark mode - without introducing
another hue. Buttons get a slate *border* so they stay instantly
recognisable as controls.

Every light value below is exactly the literal this file shipped before
the theme work, so the light appearance is unchanged.

Author: Daniel Vala
"""

from typing import Dict

import streamlit as st

from utils.theme import palette, is_dark, rgba


# ============================================================================
# CSS COLOR ROLES
# ============================================================================

def _overlay(color: str, alpha: float) -> str:
    """A translucent wash painted *on top of* an element's own background.

    Setting ``background-color`` to an rgba would replace the surface and
    composite against the page behind it, which on a dark raised surface
    makes the hover state come out *darker* than the resting state. A flat
    one-colour gradient paints over the existing background instead, so the
    surface still lifts. Used only in dark mode: the palette has no solid
    surface above ``panel_raised`` to hover into, whereas light mode has
    always hovered by swapping to a lighter solid.
    """
    wash = rgba(color, alpha)
    return f'linear-gradient({wash}, {wash})'


def _roles() -> Dict[str, str]:
    """Resolve every colour the stylesheet needs for the active theme."""
    p = palette()
    dark = is_dark()

    return {
        'primary':        p['primary'],
        'primary_hover':  p['primary_hover'],
        'on_primary':     p['on_primary'],
        'panel':          p['panel'],
        'panel_raised':   p['panel_raised'],
        'text':           p['text'],
        'text_dim':       p['text_dim'],
        'border':         p['border'],
        'structural':     p['structural'],
        'structural_hover': p['structural_hover'],
        'success':        p['success'],
        'warning':        p['warning'],
        'info':           p['info'],

        # Translucent washes.
        'success_wash':   rgba(p['success'], 0.1),
        'warning_wash':   rgba(p['warning'], 0.1),
        'info_wash':      rgba(p['info'], 0.1),
        'structural_wash':      rgba(p['structural'], 0.1),
        'structural_focus':     rgba(p['structural'], 0.2),

        # Table row hover. The 5% wash was tuned for a dark slate over
        # white; the same 5% of a *light* slate over a near-black row is
        # invisible, so dark gets a stronger wash to land in the same place
        # perceptually.
        'row_hover': rgba(p['structural'], 0.05 if not dark else 0.15),

        # Roles that are not the same token in both themes - see the module
        # docstring for why.
        'track':          '#ddd' if not dark else p['panel_raised'],
        'table_head_bg':  p['structural'] if not dark else p['panel_raised'],
        'table_head_fg':  p['on_primary'] if not dark else p['text'],
        'expander_bg':    p['structural'] if not dark else p['panel_raised'],
        'expander_fg':    p['on_primary'] if not dark else p['text'],
        'expander_hover_bg': p['structural_hover'] if not dark else p['panel_raised'],
        'button_bg':      p['panel'] if not dark else p['panel_raised'],
        'button_border':  p['border'] if not dark else p['structural'],
        'button_hover_bg': p['panel_raised'],
    }


def build_css() -> str:
    """Return the MMForge stylesheet for the active theme."""
    c = _roles()

    # Hover lift for the surfaces that have nowhere solid left to go in
    # dark. Emitted as an extra declaration only in dark mode, so the light
    # stylesheet stays character-for-character what it always was.
    lift = ''
    if is_dark():
        lift = f"\n        background-image: {_overlay(palette()['structural'], 0.14)};"

    return f"""
<style>
    /* ===== Page Container ===== */
    .stMainBlockContainer {{
        max-width: 70rem;
    }}

    /* ===== Primary Interactive Elements (keep magenta) ===== */
    /* Slider: Only color the selected range, not the full track */
    .stSlider [data-baseweb="slider"] [data-testid="stTickBar"] > div {{
        background-color: {c['track']} !important;
    }}
    .stSlider [data-baseweb="slider"] > div > div[role="slider"] {{
        background-color: {c['primary']} !important;
    }}
    .stSlider [data-baseweb="slider"] > div > div:not([role="slider"]) {{
        background-color: {c['track']} !important;
    }}
    .stProgress > div > div > div > div {{
        background-color: {c['primary']} !important;
    }}
    .stCheckbox > label > div[data-checked="true"] {{
        background-color: {c['primary']} !important;
        border-color: {c['primary']} !important;
    }}

    /* ===== Primary Buttons (keep magenta for brand) ===== */
    .stButton > button[kind="primary"] {{
        background-color: {c['primary']} !important;
        border-color: {c['primary']} !important;
        color: {c['on_primary']} !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        background-color: {c['primary_hover']} !important;
        border-color: {c['primary_hover']} !important;
        color: {c['on_primary']} !important;
    }}

    /* ===== Secondary Buttons ===== */
    .stButton > button:not([kind="primary"]) {{
        background-color: {c['button_bg']} !important;
        border: 1px solid {c['button_border']} !important;
        color: {c['text']} !important;
    }}
    .stButton > button:not([kind="primary"]):hover {{
        background-color: {c['button_hover_bg']} !important;
        border-color: {c['structural']} !important;{lift}
    }}

    /* ===== Message Colors ===== */
    .stSuccess {{
        background-color: {c['success_wash']} !important;
        border-left-color: {c['success']} !important;
    }}
    .stWarning {{
        background-color: {c['warning_wash']} !important;
        border-left-color: {c['warning']} !important;
    }}
    .stInfo {{
        background-color: {c['info_wash']} !important;
        border-left-color: {c['info']} !important;
    }}

    /* ===== Sidebar Active Page (use slate blue) ===== */
    [data-testid="stSidebarNav"] li[aria-selected="true"] {{
        background-color: {c['structural_wash']} !important;
        border-left: 3px solid {c['structural']} !important;
    }}

    /* ===== Expander Headers (use slate blue) ===== */
    [data-testid="stExpander"] > details > summary {{
        background-color: {c['expander_bg']} !important;
        color: {c['expander_fg']} !important;
        border-radius: 4px;
        padding: 0.5rem 1rem;
    }}
    [data-testid="stExpander"] > details > summary:hover {{
        background-color: {c['expander_hover_bg']} !important;{lift}
    }}
    [data-testid="stExpander"] > details > summary svg {{
        fill: {c['expander_fg']} !important;
    }}

    /* ===== Form Input Focus States ===== */
    .stTextInput > div > div > input:focus {{
        border-color: {c['structural']} !important;
        box-shadow: 0 0 0 2px {c['structural_focus']} !important;
    }}
    .stNumberInput > div > div > input:focus {{
        border-color: {c['structural']} !important;
        box-shadow: 0 0 0 2px {c['structural_focus']} !important;
    }}
    .stSelectbox > div > div:focus-within {{
        border-color: {c['structural']} !important;
    }}

    /* ===== Dataframe Styling ===== */
    [data-testid="stDataFrame"] th {{
        background-color: {c['table_head_bg']} !important;
        color: {c['table_head_fg']} !important;
        font-weight: 600;
    }}
    [data-testid="stDataFrame"] tr:hover {{
        background-color: {c['row_hover']} !important;
    }}

    /* ===== Larger Tab Fonts (for decomposed matrix selectors) ===== */
    [data-testid="stTabs"] button {{
        font-size: 1.1rem !important;
        font-weight: 500 !important;
    }}
</style>
"""


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def inject_custom_css():
    """
    Inject MMForge custom CSS into the current page.

    Call this function once at the top of each page, after st.set_page_config().
    This replaces the need for inline <style> blocks in each page file.

    Example:
        st.set_page_config(page_title="MMForge - PAGE", layout="wide")
        inject_custom_css()
    """
    st.html(build_css())


def soft_divider():
    """
    Insert a subtle divider between sections.

    Use instead of st.markdown("---") for a softer visual separation.
    """
    border = palette()['border']
    st.markdown(f"""
    <div style="height: 1px; background: linear-gradient(to right, transparent, {border}, transparent); margin: 1.5rem 0;"></div>
    """, unsafe_allow_html=True)
