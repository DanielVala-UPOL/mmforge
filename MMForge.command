#!/bin/bash
# ===================================================================
#  MMForge launcher (macOS)
#
#  Double-click this file to start MMForge, or use the MMForge app
#  that Install-macOS.command puts in your Applications folder.
#
#  The Terminal window that opens is the MMForge server. Keep it open
#  while you work; closing it stops the application.
#
#  Nothing in this file needs to be edited. It finds the project and
#  the Python environment on its own.
# ===================================================================

set -u

# --- 1) The project folder is the folder this file lives in ---------
# BASH_SOURCE is used rather than $0 because it is correct whether the
# file is run or sourced. A Finder alias resolves to the original file
# before running, so aliases work without any extra handling.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- 2) Fallback: this file was copied out of the project -----------
# Install-macOS.command records where MMForge lives. Using the app in
# your Applications folder is the better way to launch from elsewhere,
# but a copied .command should not simply fail.
RECORD="$HOME/Library/Application Support/MMForge/install_path"
if [ ! -f "$ROOT/streamlit_app/HOME.py" ] && [ -f "$RECORD" ]; then
    ROOT="$(cat "$RECORD")"
fi

pause_then_exit() {
    echo ""
    printf "Press Enter to close this window... "
    read -r _
    exit "$1"
}

if [ ! -f "$ROOT/streamlit_app/HOME.py" ]; then
    echo ""
    echo "==================================================================="
    echo "  ERROR: the MMForge folder could not be found."
    echo "==================================================================="
    echo ""
    echo "  This launcher looks for MMForge in its own folder:"
    echo "      $ROOT"
    echo ""
    echo "  Keep MMForge.command inside the MMForge folder. To start"
    echo "  MMForge from elsewhere, use the MMForge app in your"
    echo "  Applications folder instead of copying this file."
    pause_then_exit 1
fi

# --- 3) The virtual environment must exist --------------------------
# Note there is no "activate" step. Calling the environment's own
# python directly does exactly the same job and cannot pick up the
# wrong Python.
VENV_PYTHON="$ROOT/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    echo ""
    echo "==================================================================="
    echo "  ERROR: the MMForge Python environment is missing."
    echo "==================================================================="
    echo ""
    echo "  Expected to find:"
    echo "      $VENV_PYTHON"
    echo ""
    echo "  Fix: run Install-macOS.command once, then try again."
    pause_then_exit 1
fi

# --- 4) Start MMForge -----------------------------------------------
cd "$ROOT" || pause_then_exit 1
"$VENV_PYTHON" "$ROOT/tools/launch_mmforge.py"
STATUS=$?

if [ "$STATUS" -ne 0 ]; then
    echo ""
    echo "  MMForge stopped with an error (code $STATUS)."
    echo "  The reason should be printed above."
    pause_then_exit "$STATUS"
fi

echo ""
echo "  MMForge has stopped."
