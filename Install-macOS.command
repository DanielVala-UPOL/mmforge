#!/bin/bash
# ===================================================================
#  MMForge installer (macOS)
#
#  Run this once after downloading MMForge. It creates a private
#  Python environment inside the MMForge folder and installs
#  everything the application needs.
#
#  Safe to run again at any time - re-running it is the standard fix
#  when something stops working.
#
#  If macOS refuses to open this file ("unidentified developer"),
#  right-click it in Finder, choose Open, then confirm with Open.
#  That warning appears only for files that arrived in a downloaded
#  ZIP; it does not appear when MMForge is cloned with git.
#
#  Optional switches:
#    ./Install-macOS.command --recreate      rebuild the environment
#    ./Install-macOS.command --no-shortcut   skip the Applications icon
# ===================================================================

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

pause_then_exit() {
    echo ""
    printf "Press Enter to close this window... "
    read -r _
    exit "$1"
}

# --- 0) Make sure both launchers are executable ---------------------
# A downloaded ZIP sometimes loses the executable flag, which makes the
# .command files un-double-clickable. Restoring it here means the user
# never has to run chmod by hand.
chmod +x "$ROOT/MMForge.command" 2>/dev/null
chmod +x "$ROOT/Install-macOS.command" 2>/dev/null
chmod +x "$ROOT/tools/create_macos_app.sh" 2>/dev/null

if [ ! -f "$ROOT/tools/setup_env.py" ]; then
    echo ""
    echo "==================================================================="
    echo "  ERROR: this does not look like a complete MMForge folder."
    echo "==================================================================="
    echo ""
    echo "  Expected to find:"
    echo "      $ROOT/tools/setup_env.py"
    echo ""
    echo "  Download MMForge again and unpack the whole folder, then run"
    echo "  this installer from inside it."
    pause_then_exit 1
fi

# --- 1) Find a usable Python ----------------------------------------
# Newest first. /usr/bin/python3 is last on purpose: on a Mac without
# the Xcode Command Line Tools it is only a placeholder that opens an
# installation dialog.
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
            PYTHON="$(command -v "$candidate")"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo ""
    echo "==================================================================="
    echo "  ERROR: no suitable Python was found on this Mac."
    echo "==================================================================="
    echo ""
    echo "  MMForge needs Python 3.10 or newer."
    echo ""
    echo "  1. Download Python 3.12 from:"
    echo "       https://www.python.org/downloads/macos/"
    echo "  2. Open the downloaded .pkg and follow the installer."
    echo "  3. Run this installer again."
    pause_then_exit 1
fi

echo ""
echo "  Using Python: $PYTHON"
echo ""

# --- 2) Hand over to the shared installer ---------------------------
"$PYTHON" "$ROOT/tools/setup_env.py" "$@"
STATUS=$?

if [ "$STATUS" -ne 0 ]; then
    echo ""
    echo "  Setup did not finish. The reason is printed above."
fi

pause_then_exit "$STATUS"
