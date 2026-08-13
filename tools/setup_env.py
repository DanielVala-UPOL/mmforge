#!/usr/bin/env python3
"""
One-time setup for MMForge: create the virtual environment and install
everything MMForge needs.

This script is the shared core of both platform installers
(``Install-Windows.bat`` and ``Install-macOS.command``). It is safe to run
again at any time - re-running it is the standard fix when something stops
working.

Usage::

    python tools/setup_env.py                 normal install / repair
    python tools/setup_env.py --recreate      delete .venv and build it again
    python tools/setup_env.py --no-shortcut   skip the desktop icon step

Deliberately written with no f-strings and no type annotations, so that an
ancient Python still parses the file and can print the "your Python is too
old" message instead of crashing with a syntax error.

Author: Daniel Vala
"""

import os
import platform
import shutil
import subprocess
import sys


# ============================================================================
# CONSTANTS
# ============================================================================

MINIMUM_PYTHON = (3, 10)

# tools/setup_env.py -> tools/ -> project root
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TOOLS_DIR)

VENV_DIR = os.path.join(PROJECT_ROOT, ".venv")
REQUIREMENTS_FILE = os.path.join(PROJECT_ROOT, "requirements.txt")
APP_ENTRY_POINT = os.path.join(PROJECT_ROOT, "streamlit_app", "HOME.py")

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"

SELF_CHECK_IMPORTS = "import streamlit, numpy, scipy, plotly, pandas, matplotlib, yaml, tqdm"


# ============================================================================
# SMALL HELPERS
# ============================================================================

def heading(text):
    print("")
    print("=" * 68)
    print("  " + text)
    print("=" * 68)
    print("")


def step(number, total, text):
    print("")
    print("  [{0}/{1}] {2}".format(number, total, text))
    print("  " + "-" * 60)


def fail(title, lines):
    """
    Print an error block and return False.

    Every caller does ``return fail(...)``, so a failed check simply reports
    itself and hands a False back up to main(), which stops the install.
    """
    print("")
    print("=" * 68)
    print("  ERROR: " + title)
    print("=" * 68)
    for line in lines:
        print("  " + line)
    print("")
    return False


def run(command, description):
    """
    Run a command, streaming its output. Returns True on success.

    Output is intentionally not captured: when pip fails (a proxy, no network,
    a missing wheel) the real reason is in its own message, and hiding it would
    leave the user with a useless "installation failed".
    """
    print("  > " + " ".join(command))
    print("")
    try:
        result = subprocess.run(command)
    except OSError as error:
        print("")
        print("  Could not run " + description + ": " + str(error))
        return False
    print("")
    return result.returncode == 0


def venv_python_path():
    """Full path to the Python executable inside the virtual environment."""
    if IS_WINDOWS:
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def install_record_path():
    """
    Where to remember the MMForge location.

    The launchers normally find the project through their own file path. This
    record is only a fallback, used when someone copies the launcher out of
    the project folder instead of making a shortcut.
    """
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "MMForge", "install_path.txt")
    if IS_MACOS:
        base = os.path.expanduser("~/Library/Application Support")
        return os.path.join(base, "MMForge", "install_path")
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "MMForge", "install_path")


def ask_yes_no(question, default_yes=True):
    """Ask a yes/no question. Falls back to the default if there is no input."""
    suffix = " [Y/n] " if default_yes else " [y/N] "
    try:
        answer = input(question + suffix).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("")
        return default_yes
    if answer == "":
        return default_yes
    return answer.startswith("y")


# ============================================================================
# CHECKS
# ============================================================================

def check_python_version():
    if sys.version_info >= MINIMUM_PYTHON:
        return True
    return fail(
        "This Python is too old for MMForge",
        [
            "Found:    Python {0}.{1}".format(sys.version_info[0], sys.version_info[1]),
            "Required: Python {0}.{1} or newer".format(MINIMUM_PYTHON[0], MINIMUM_PYTHON[1]),
            "",
            "Install Python 3.12 from https://www.python.org/downloads/",
            "and then run this installer again.",
        ],
    )


def check_not_microsoft_store_stub():
    """
    Refuse the Microsoft Store placeholder for Python.

    Windows ships a fake python.exe in WindowsApps that only opens the Store.
    It reports a version but cannot create a usable virtual environment, so
    catching it here saves a very confusing failure later.
    """
    if not IS_WINDOWS:
        return True
    if "WindowsApps" not in sys.executable:
        return True
    return fail(
        "This is the Microsoft Store placeholder, not a real Python",
        [
            "Found: " + sys.executable,
            "",
            "Install Python 3.12 from https://www.python.org/downloads/",
            'and tick "Add python.exe to PATH" during the installation.',
            "Then run this installer again.",
        ],
    )


def check_project_layout():
    if os.path.isfile(APP_ENTRY_POINT) and os.path.isfile(REQUIREMENTS_FILE):
        return True
    return fail(
        "This does not look like a complete MMForge folder",
        [
            "Expected to find:",
            "    " + APP_ENTRY_POINT,
            "    " + REQUIREMENTS_FILE,
            "",
            "Download MMForge again and unpack the whole folder.",
        ],
    )


def warn_about_synced_folder():
    """
    Cloud-synced folders make a poor home for a virtual environment.

    A .venv holds thousands of small files. OneDrive and iCloud will try to
    sync every one of them, which is slow and can lock files mid-install.
    """
    lowered = PROJECT_ROOT.lower()
    for marker in ("onedrive", "icloud", "dropbox", "google drive"):
        if marker in lowered:
            print("")
            print("  WARNING: MMForge is inside a cloud-synced folder.")
            print("           " + PROJECT_ROOT)
            print("")
            print("           Syncing can lock files and slow the install down a lot.")
            print("           A local folder such as " + os.path.join(os.path.expanduser("~"), "MMForge"))
            print("           is a better place for it.")
            print("")
            return


# ============================================================================
# INSTALL STEPS
# ============================================================================

def create_virtual_environment(recreate):
    """
    Create .venv inside the project folder.

    A virtual environment is a private copy of Python that belongs to this one
    project. Packages installed into it cannot disturb anything else on the
    computer, and deleting the MMForge folder removes them completely.
    """
    if os.path.isdir(VENV_DIR) and recreate:
        print("  Removing the existing environment (--recreate)...")
        shutil.rmtree(VENV_DIR, ignore_errors=True)

    if os.path.isdir(VENV_DIR) and os.path.isfile(venv_python_path()):
        print("  An environment already exists and will be reused:")
        print("      " + VENV_DIR)
        print("  (Run this installer with --recreate to rebuild it from scratch.)")
        return True

    # A half-built environment from an interrupted run must go.
    if os.path.isdir(VENV_DIR):
        print("  Found an incomplete environment, removing it...")
        shutil.rmtree(VENV_DIR, ignore_errors=True)

    print("  Creating a private Python environment in:")
    print("      " + VENV_DIR)
    print("")
    ok = run([sys.executable, "-m", "venv", VENV_DIR], "python -m venv")
    if not ok or not os.path.isfile(venv_python_path()):
        return fail(
            "Could not create the Python environment",
            [
                "The command 'python -m venv' failed.",
                "",
                "On Windows and macOS this normally means the Python",
                "installation is incomplete - reinstall Python 3.12 from",
                "https://www.python.org/downloads/ and try again.",
                "",
                "On Linux, install the venv package first, for example:",
                "    sudo apt install python3-venv",
            ],
        )
    return True


def install_dependencies():
    python = venv_python_path()

    print("  Updating pip...")
    print("")
    run([python, "-m", "pip", "install", "--upgrade", "pip"], "pip upgrade")

    print("  Installing MMForge dependencies (this can take a few minutes)...")
    print("")
    ok = run(
        [python, "-m", "pip", "install", "-r", REQUIREMENTS_FILE],
        "pip install",
    )
    if not ok:
        return fail(
            "Could not install the dependencies",
            [
                "pip printed the reason just above this message.",
                "",
                "The two usual causes are:",
                "  - no internet connection, or a company proxy blocking pypi.org",
                "  - not enough free disk space",
                "",
                "Fix the cause and run this installer again.",
            ],
        )
    return True


def verify_installation():
    python = venv_python_path()
    print("  Checking that every package imports correctly...")
    print("")
    ok = run([python, "-c", SELF_CHECK_IMPORTS], "self-check")
    if not ok:
        return fail(
            "The installation finished but the packages do not load",
            [
                "The import error is printed above.",
                "",
                "Try a clean rebuild:",
                "    python tools/setup_env.py --recreate",
            ],
        )
    print("  All packages import correctly.")
    return True


def record_install_location():
    path = install_record_path()
    try:
        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        handle = open(path, "w")
        try:
            handle.write(PROJECT_ROOT)
        finally:
            handle.close()
        print("  Remembered this location for the launchers:")
        print("      " + path)
    except OSError as error:
        # Not fatal: the launchers find the project by their own path anyway.
        print("  Note: could not write the location record (" + str(error) + ").")
        print("        The launchers will still work from inside this folder.")


def create_desktop_entry():
    """Create the desktop shortcut (Windows) or the app bundle (macOS)."""
    if IS_WINDOWS:
        script = os.path.join(TOOLS_DIR, "create_windows_shortcut.ps1")
        if not os.path.isfile(script):
            print("  Skipped: " + script + " is missing.")
            return
        run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", script, "-ProjectRoot", PROJECT_ROOT],
            "shortcut creation",
        )
        return

    if IS_MACOS:
        script = os.path.join(TOOLS_DIR, "create_macos_app.sh")
        if not os.path.isfile(script):
            print("  Skipped: " + script + " is missing.")
            return
        run(["bash", script, PROJECT_ROOT], "app bundle creation")
        return

    print("  Skipped: desktop shortcuts are only created on Windows and macOS.")
    print("  Start MMForge with:")
    print("      " + venv_python_path() + " " + os.path.join(TOOLS_DIR, "launch_mmforge.py"))


# ============================================================================
# MAIN
# ============================================================================

def main(argv):
    recreate = "--recreate" in argv
    no_shortcut = "--no-shortcut" in argv

    heading("MMForge - setup")
    print("  Project folder: " + PROJECT_ROOT)
    print("  Python:         " + sys.executable)
    print("  Version:        " + sys.version.split()[0])

    total = 6

    step(1, total, "Checking prerequisites")
    if not check_python_version():
        return 1
    if not check_not_microsoft_store_stub():
        return 1
    if not check_project_layout():
        return 1
    warn_about_synced_folder()
    print("  Prerequisites are fine.")

    step(2, total, "Creating the Python environment")
    if not create_virtual_environment(recreate):
        return 1

    step(3, total, "Installing dependencies")
    if not install_dependencies():
        return 1

    step(4, total, "Verifying the installation")
    if not verify_installation():
        return 1

    step(5, total, "Remembering where MMForge lives")
    record_install_location()

    step(6, total, "Desktop shortcut")
    if no_shortcut:
        print("  Skipped (--no-shortcut).")
    elif ask_yes_no("  Create a desktop shortcut for MMForge?"):
        create_desktop_entry()
    else:
        print("  Skipped. You can start MMForge from the project folder instead.")

    heading("Setup complete")
    if IS_WINDOWS:
        print("  Start MMForge by double-clicking:  MMForge.bat")
    elif IS_MACOS:
        print("  Start MMForge by double-clicking:  MMForge.command")
    else:
        print("  Start MMForge with:")
        print("      " + venv_python_path() + " tools/launch_mmforge.py")
    print("")
    print("  If anything stops working later, run this installer again.")
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
