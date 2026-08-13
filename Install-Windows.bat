@echo off
REM ===================================================================
REM  MMForge installer (Windows)
REM
REM  Run this once after downloading MMForge. It creates a private
REM  Python environment inside the MMForge folder and installs
REM  everything the application needs.
REM
REM  Safe to run again at any time - re-running it is the standard fix
REM  when something stops working.
REM
REM  Optional switches:
REM    Install-Windows.bat --recreate      rebuild the environment
REM    Install-Windows.bat --no-shortcut   skip the Desktop shortcut
REM ===================================================================

setlocal EnableExtensions
title MMForge - setup

set "ROOT=%~dp0"

if not exist "%ROOT%tools\setup_env.py" goto :no_project

REM --- Find a usable Python -------------------------------------------
REM "py" is the Python launcher that ships with the python.org installer
REM and is the most reliable way to reach a real Python on Windows.
set "PY_CMD="
py -3 -c "import sys" >nul 2>nul && set "PY_CMD=py -3"
if not defined PY_CMD (
  python -c "import sys" >nul 2>nul && set "PY_CMD=python"
)
if not defined PY_CMD goto :no_python

echo.
echo   Using Python command: %PY_CMD%
echo.

%PY_CMD% "%ROOT%tools\setup_env.py" %*
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
  echo.
  echo   Setup did not finish. The reason is printed above.
)
goto :end

:no_python
echo.
echo ===================================================================
echo   ERROR: Python was not found on this computer.
echo ===================================================================
echo.
echo   1. Download Python 3.12 from:
echo        https://www.python.org/downloads/
echo   2. Run the installer.
echo   3. IMPORTANT: tick "Add python.exe to PATH" on the first screen.
echo   4. Restart this installer.
echo.
goto :end

:no_project
echo.
echo ===================================================================
echo   ERROR: this does not look like a complete MMForge folder.
echo ===================================================================
echo.
echo   Expected to find:
echo     %ROOT%tools\setup_env.py
echo.
echo   Download MMForge again and unpack the whole folder, then run
echo   this installer from inside it.
echo.

:end
echo.
pause
endlocal
