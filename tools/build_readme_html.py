#!/usr/bin/env python3
"""
Turn README.md into a standalone README.html.

Why this exists
---------------
On GitHub, README.md is already rendered as a formatted web page - that is
the normal way people will read it. This script covers the other case: a
user who received MMForge as a folder or a ZIP and has no internet, no
GitHub and no code editor. They can double-click README.html and get the
same document, nicely formatted, in whatever browser they already have.

The output is fully self-contained: the stylesheet is inlined and the logo
is embedded as a data URI, so the single .html file works even if it is
copied somewhere else on its own.

How to regenerate
-----------------
Only needed after editing README.md. Requires one extra package that
MMForge itself does not use::

    python -m pip install markdown
    python tools/build_readme_html.py

Author: Daniel Vala
"""

import base64
import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    print("This script needs the 'markdown' package:")
    print("    python -m pip install markdown")
    sys.exit(1)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE = PROJECT_ROOT / "README.md"
TARGET = PROJECT_ROOT / "README.html"

PRIMARY_COLOR = "#FF1F5B"

# Markdown extensions:
#   extra      - tables, fenced code blocks, and friends
#   md_in_html - lets Markdown inside <details markdown="1"> be converted,
#                which is what the troubleshooting section relies on
#   sane_lists - stops a stray number from restarting a list
EXTENSIONS = ["extra", "md_in_html", "sane_lists"]


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MMForge - Read Me</title>
<style>
  :root {{ --primary: {primary}; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 2.5rem 1.5rem 5rem;
    background: #ffffff;
    color: #24292f;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica,
                 Arial, sans-serif;
    font-size: 16px;
    line-height: 1.65;
  }}
  main {{ max-width: 860px; margin: 0 auto; }}
  h1, h2, h3 {{ line-height: 1.25; margin-top: 2.2rem; }}
  h1 {{ font-size: 2.1rem; border-bottom: 3px solid var(--primary);
        padding-bottom: .4rem; margin-top: 0; }}
  h2 {{ font-size: 1.5rem; border-bottom: 1px solid #e1e4e8;
        padding-bottom: .3rem; }}
  h3 {{ font-size: 1.15rem; color: var(--primary); }}
  a {{ color: #0969da; }}
  img {{ max-width: 100%; height: auto; }}
  hr {{ border: 0; border-top: 1px solid #e1e4e8; margin: 2.5rem 0; }}
  code {{
    background: #f0f1f3; border-radius: 6px; padding: .15em .4em;
    font-family: "SF Mono", Menlo, Consolas, monospace; font-size: .88em;
  }}
  pre {{
    background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 8px;
    padding: 1rem; overflow-x: auto;
  }}
  pre code {{ background: none; padding: 0; font-size: .85em; }}
  blockquote {{
    margin: 1.2rem 0; padding: .6rem 1.1rem; color: #57606a;
    border-left: 4px solid var(--primary); background: #fff5f8;
  }}
  blockquote p {{ margin: .4rem 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1.2rem 0; }}
  th, td {{ border: 1px solid #d0d7de; padding: .55rem .8rem;
            text-align: left; vertical-align: top; }}
  th {{ background: #f6f8fa; }}
  details {{
    border: 1px solid #d0d7de; border-radius: 8px;
    padding: .7rem 1rem; margin: .6rem 0; background: #fbfcfd;
  }}
  details[open] {{ background: #ffffff; }}
  summary {{ cursor: pointer; font-weight: 600; }}
  details > *:not(summary) {{ margin-left: .2rem; }}
  ol, ul {{ padding-left: 1.6rem; }}
  li {{ margin: .25rem 0; }}
  .note {{
    max-width: 860px; margin: 3rem auto 0; padding-top: 1rem;
    border-top: 1px solid #e1e4e8; color: #6e7781; font-size: .85rem;
  }}
</style>
</head>
<body>
<main>
{body}
</main>
<p class="note">
  Generated from README.md. The most recent version is always at
  <a href="https://github.com/DanielVala-UPOL/mmforge">github.com/DanielVala-UPOL/mmforge</a>.
</p>
</body>
</html>
"""


def embed_images(html_text):
    """
    Replace local image paths with base64 data URIs.

    Without this the .html would only show the logo while it sits next to
    the project. Embedding keeps the file useful on its own.
    """
    def replace(match):
        before, source, after = match.group(1), match.group(2), match.group(3)
        if source.startswith(("http://", "https://", "data:")):
            return match.group(0)

        image_path = PROJECT_ROOT / source
        if not image_path.is_file():
            print("  Warning: image not found, left as a link: " + source)
            return match.group(0)

        suffix = image_path.suffix.lower().lstrip(".")
        mime = "image/jpeg" if suffix in ("jpg", "jpeg") else "image/" + suffix
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        print("  Embedded image: " + source)
        return '{0}data:{1};base64,{2}{3}'.format(before, mime, encoded, after)

    return re.sub(r'(<img[^>]*\ssrc=")([^"]+)(")', replace, html_text)


def main():
    if not SOURCE.is_file():
        print("Could not find " + str(SOURCE))
        return 1

    print("Reading  " + str(SOURCE))
    body = markdown.markdown(SOURCE.read_text(encoding="utf-8"),
                             extensions=EXTENSIONS)
    body = embed_images(body)

    page = PAGE_TEMPLATE.format(primary=PRIMARY_COLOR, body=body)
    TARGET.write_text(page, encoding="utf-8")

    print("Written  " + str(TARGET))
    print("Size     {0:.0f} KB".format(TARGET.stat().st_size / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
