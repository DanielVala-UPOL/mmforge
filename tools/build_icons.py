#!/usr/bin/env python3
"""
Build the launcher icons from the MMForge logo.

Why this exists
---------------
The Dock on macOS and the Windows Desktop show application icons as filled
rounded squares. Dropping the bare logo in leaves a transparent background,
so MMForge looked like a floating wide sticker next to Word, Excel and the
rest. This script composes the logo onto a proper icon plate.

Inputs and outputs
------------------
    streamlit_app/assets/MMForge_v1.png   the logo (wide, white background)
        -> tools/mmforge.png              1024x1024, source for the macOS .icns
        -> tools/mmforge.ico              multi-size, used by the Windows shortcut

The design: the anvil and spark mark (without the MM-FORGE wordmark, which is
unreadable at 32 px) recoloured white, centred on a dark navy rounded square.
Navy rather than white because the Dock is full of white icons.

How to regenerate
-----------------
Only needed if the logo changes. Requires Pillow, which MMForge itself does
not use::

    python -m pip install pillow
    python tools/build_icons.py

Author: Daniel Vala
"""

import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw
except ImportError:
    print("This script needs Pillow and numpy:")
    print("    python -m pip install pillow numpy")
    sys.exit(1)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGO = PROJECT_ROOT / "streamlit_app" / "assets" / "MMForge_v1.png"
PNG_OUT = PROJECT_ROOT / "tools" / "mmforge.png"
ICO_OUT = PROJECT_ROOT / "tools" / "mmforge.ico"

# MMForge brand navy, sampled from the logo.
NAVY = (45, 62, 80, 255)

CANVAS = 1024
PLATE_RATIO = 0.90       # rounded square as a fraction of the canvas
CORNER_RATIO = 0.225     # corner radius as a fraction of the plate
ART_RATIO = 0.84         # mark width as a fraction of the plate

# Bounding box of the anvil-and-sparks mark inside the logo, excluding the
# MM-FORGE wordmark underneath. Measured from the 1767x876 source.
MARK_BOX = (151, 114, 1606, 564)

ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48),
             (64, 64), (128, 128), (256, 256)]


def drop_white_background(image):
    """
    Turn the logo's opaque white background transparent.

    Alpha is ramped rather than switched, so anti-aliased edges stay smooth
    instead of turning into a jagged outline.
    """
    pixels = np.array(image).astype(np.int16)
    distance_from_white = 255 - pixels[..., :3].min(axis=2)
    alpha = np.clip(distance_from_white * 6, 0, 255)
    pixels[..., 3] = np.minimum(pixels[..., 3], alpha)
    return Image.fromarray(pixels.astype("uint8"), "RGBA")


def recolour_navy_to_white(image):
    """Repaint the dark navy parts white so they read against a navy plate."""
    pixels = np.array(image).astype(np.int16)
    distance = np.abs(pixels[..., :3] - np.array(NAVY[:3])).sum(axis=2)
    is_navy = distance < 200
    pixels[is_navy, 0] = 255
    pixels[is_navy, 1] = 255
    pixels[is_navy, 2] = 255
    return Image.fromarray(pixels.astype("uint8"), "RGBA")


def build_icon():
    logo = Image.open(LOGO).convert("RGBA")
    mark = recolour_navy_to_white(drop_white_background(logo).crop(MARK_BOX))

    plate_size = int(CANVAS * PLATE_RATIO)
    radius = int(plate_size * CORNER_RATIO)

    plate = Image.new("RGBA", (plate_size, plate_size), (0, 0, 0, 0))
    ImageDraw.Draw(plate).rounded_rectangle(
        [0, 0, plate_size - 1, plate_size - 1], radius=radius, fill=NAVY
    )

    icon = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    offset = (CANVAS - plate_size) // 2
    icon.alpha_composite(plate, (offset, offset))

    scale = (plate_size * ART_RATIO) / mark.width
    mark = mark.resize(
        (int(mark.width * scale), int(mark.height * scale)), Image.LANCZOS
    )
    icon.alpha_composite(
        mark, ((CANVAS - mark.width) // 2, (CANVAS - mark.height) // 2)
    )
    return icon


def main():
    if not LOGO.is_file():
        print("Could not find " + str(LOGO))
        return 1

    icon = build_icon()

    # 1024 px so sips and iconutil can produce every Retina size sharply.
    icon.save(PNG_OUT)
    print("Written " + str(PNG_OUT) + "  (1024x1024)")

    icon.save(ICO_OUT, format="ICO", sizes=ICO_SIZES)
    print("Written " + str(ICO_OUT) + "  " + str([s[0] for s in ICO_SIZES]))

    print("")
    print("macOS: re-run the installer (or bash tools/create_macos_app.sh)")
    print("       to rebuild ~/Applications/MMForge.app with the new icon.")
    print("Windows: re-run Install-Windows.bat to refresh the Desktop shortcut.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
