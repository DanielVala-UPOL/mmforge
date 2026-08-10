"""Minimal ANSI color utilities for terminal output."""

import sys

# Auto-detect: disable colors if not a TTY (e.g., piped to file)
_USE_COLOR = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

def _wrap(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

def green(text: str) -> str:
    return _wrap("32", text)

def yellow(text: str) -> str:
    return _wrap("33", text)

def red(text: str) -> str:
    return _wrap("31", text)

def bold(text: str) -> str:
    return _wrap("1", text)

def cyan(text: str) -> str:
    return _wrap("36", text)

def dim(text: str) -> str:
    return _wrap("2", text)
