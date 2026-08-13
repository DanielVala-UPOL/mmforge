#!/usr/bin/env python3
"""
Start the MMForge Streamlit application.

This script is the shared core of both platform launchers
(``MMForge.bat`` on Windows, ``MMForge.command`` on macOS). Those two files
only locate the project folder and the virtual environment; everything that
follows happens here, so the behaviour is identical on both systems.

It is normally run by the virtual environment's own Python, for example::

    .venv/bin/python tools/launch_mmforge.py            (macOS / Linux)
    .venv\\Scripts\\python.exe tools\\launch_mmforge.py    (Windows)

Running it directly is also fine, as long as the interpreter you use has the
MMForge dependencies installed.

Author: Daniel Vala
"""

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


# Print every line as soon as it is produced. Without this, Python buffers our
# messages while Streamlit (a separate process) writes straight to the console,
# so the user sees Streamlit's output first and ours only at the very end - or
# not at all if the window is closed.
sys.stdout.reconfigure(line_buffering=True)


# ============================================================================
# CONSTANTS
# ============================================================================

# tools/launch_mmforge.py  ->  parent is tools/  ->  parent.parent is the root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_ENTRY_POINT = PROJECT_ROOT / "streamlit_app" / "HOME.py"

# Streamlit's usual port. If it is taken (a second MMForge window, or some
# other program), we walk upwards until we find a free one.
FIRST_PORT = 8501
LAST_PORT = 8520

# Bind to the loopback address only. Two reasons:
#   1. Windows Defender Firewall does not prompt for permission, because the
#      server never listens on a network-visible interface.
#   2. The app is not exposed to anyone else on the lab network.
# To reach MMForge from another computer, change this to "0.0.0.0" and expect
# a firewall prompt on the first run.
SERVER_ADDRESS = "127.0.0.1"

# How long to wait for the server to answer before opening the browser.
STARTUP_TIMEOUT_SECONDS = 90
STARTUP_POLL_SECONDS = 0.5

# Package import name -> name shown to the user if it is missing.
REQUIRED_PACKAGES = [
    ("streamlit", "streamlit"),
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("plotly", "plotly"),
    ("pandas", "pandas"),
    ("matplotlib", "matplotlib"),
    ("yaml", "pyyaml"),
    ("tqdm", "tqdm"),
]


# ============================================================================
# HELPERS
# ============================================================================

def print_error(title, lines):
    """Print an error block in a shape that is easy to read in a console."""
    print("")
    print("=" * 68)
    print("  " + title)
    print("=" * 68)
    for line in lines:
        print("  " + line)
    print("")


def check_running_inside_virtual_environment():
    """
    Warn (but do not stop) if this is not a virtual environment's Python.

    A virtual environment has ``sys.prefix`` pointing at the environment while
    ``sys.base_prefix`` still points at the original Python installation. When
    the two are equal, we are running against a system-wide Python.
    """
    if sys.prefix == sys.base_prefix:
        print("  Note: not running inside the MMForge virtual environment.")
        print("        This usually still works, but the installer creates")
        print("        a .venv folder that is meant to be used instead.")
        print("")


def check_required_packages():
    """
    Import every dependency and report the missing ones by name.

    Returns True if everything is present.
    """
    missing = []
    for import_name, install_name in REQUIRED_PACKAGES:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(install_name)

    if not missing:
        return True

    print_error(
        "MMForge is not fully installed",
        [
            "These Python packages are missing:",
            "",
        ]
        + ["    - " + name for name in missing]
        + [
            "",
            "Fix: run the installer once more.",
            "     Windows:  Install-Windows.bat",
            "     macOS:    Install-macOS.command",
        ],
    )
    return False


def port_is_free(port):
    """Return True if we can bind to the given port on the loopback address."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((SERVER_ADDRESS, port))
        return True
    except OSError:
        # Already in use, or blocked by the operating system.
        return False
    finally:
        probe.close()


def find_free_port():
    """
    Return the first free port in the configured range, or None if all taken.

    Streamlit can pick a port by itself, but it prints a confusing message when
    the default is busy. Choosing the port here lets us tell the user plainly
    that MMForge may already be running.
    """
    for port in range(FIRST_PORT, LAST_PORT + 1):
        if port_is_free(port):
            return port
    return None


def server_is_answering(port):
    """Ask Streamlit's own health endpoint whether it is ready to serve."""
    health_url = "http://{0}:{1}/_stcore/health".format(SERVER_ADDRESS, port)
    try:
        response = urllib.request.urlopen(health_url, timeout=2)
        try:
            return response.status == 200
        finally:
            response.close()
    except (urllib.error.URLError, OSError):
        return False


def wait_for_server(process, port):
    """
    Wait until the server responds, then return True.

    Returns False if the server process stopped on its own (a crash, a port
    conflict Streamlit noticed before we did) or if it never came up in time.
    """
    deadline = time.time() + STARTUP_TIMEOUT_SECONDS
    while time.time() < deadline:
        if process.poll() is not None:
            return False
        if server_is_answering(port):
            return True
        time.sleep(STARTUP_POLL_SECONDS)
    return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("")
    print("  MMForge - starting...")
    print("  Project folder: " + str(PROJECT_ROOT))
    print("")

    # --- 1) The project must actually be here -------------------------------
    if not APP_ENTRY_POINT.is_file():
        print_error(
            "MMForge files not found",
            [
                "Expected to find:",
                "    " + str(APP_ENTRY_POINT),
                "",
                "The launcher must stay inside the MMForge folder.",
                "If you moved or renamed the folder, run the installer again.",
            ],
        )
        return 1

    # --- 2) The dependencies must be importable -----------------------------
    check_running_inside_virtual_environment()
    if not check_required_packages():
        return 1

    # --- 3) Pick a port -----------------------------------------------------
    port = find_free_port()
    if port is None:
        print_error(
            "No free port available",
            [
                "Ports {0} to {1} are all in use.".format(FIRST_PORT, LAST_PORT),
                "",
                "MMForge is most likely already running. Look for an open",
                "MMForge window, or for a browser tab at http://localhost:8501",
            ],
        )
        return 1

    if port != FIRST_PORT:
        print("  Port {0} was busy, using {1} instead.".format(FIRST_PORT, port))
        print("  (MMForge may already be running in another window.)")
        print("")

    url = "http://localhost:{0}".format(port)
    print("  MMForge will open in your web browser at:")
    print("      " + url)
    print("")
    print("  Keep this window open while you work.")
    print("  To stop MMForge: close this window, or press Ctrl+C.")
    print("")
    print("  Starting the server, please wait...")

    # --- 4) Start Streamlit -------------------------------------------------
    # A subprocess is used rather than importing Streamlit's command-line entry
    # point, because it keeps Ctrl+C and window-closing behaviour predictable
    # on both Windows and macOS.
    #
    # server.headless=true matters more than it looks. On a computer where
    # Streamlit has never run before, non-headless mode stops and asks for an
    # e-mail address on the very first start, and waits there forever. Headless
    # mode skips that prompt - but it also means Streamlit will not open the
    # browser, so we do it ourselves once the server actually answers.
    command = [
        sys.executable,
        "-m", "streamlit", "run", str(APP_ENTRY_POINT),
        "--server.port", str(port),
        "--server.address", SERVER_ADDRESS,
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]

    process = subprocess.Popen(command, cwd=str(PROJECT_ROOT))

    try:
        if wait_for_server(process, port):
            print("  Server is ready - opening your browser.")
            print("")
            webbrowser.open(url)
        elif process.poll() is None:
            # Still running, just slow. Not worth failing over.
            print("")
            print("  The server is taking longer than usual to start.")
            print("  Open this address in your browser manually: " + url)
            print("")

        return process.wait()

    except KeyboardInterrupt:
        # Ctrl+C reaches the Streamlit process too, so it is usually already
        # shutting down. Give it a moment, then insist.
        print("")
        print("  Stopping MMForge...")
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate()
        print("  MMForge stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
