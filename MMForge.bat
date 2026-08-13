@echo off
REM ===================================================================
REM  MMForge launcher (Windows)
REM
REM  Double-click this file to start MMForge, or use the Desktop
REM  shortcut created by Install-Windows.bat.
REM
REM  This window is the MMForge server. Keep it open while you work;
REM  closing it stops the application.
REM
REM  Nothing in this file needs to be edited. It finds the project and
REM  the Python environment on its own.
REM ===================================================================

setlocal EnableExtensions
title MMForge - server (keep this window open)

REM --- 1) The project folder is the folder this file lives in --------
REM %~dp0 is the directory of this script, with a trailing backslash.
set "ROOT=%~dp0"
if exist "%ROOT%streamlit_app\HOME.py" goto :have_root

REM --- 2) Fallback: this file was copied out of the project ----------
REM Install-Windows.bat records where MMForge lives. Using a Desktop
REM shortcut is the better way to launch from elsewhere, but a copied
REM .bat should not simply fail.
if not exist "%LOCALAPPDATA%\MMForge\install_path.txt" goto :no_project
set /p ROOT=<"%LOCALAPPDATA%\MMForge\install_path.txt"
if not defined ROOT goto :no_project
if not "%ROOT:~-1%"=="\" set "ROOT=%ROOT%\"
if not exist "%ROOT%streamlit_app\HOME.py" goto :no_project

:have_root
REM --- 3) The virtual environment must exist -------------------------
REM Note there is no "activate" step. Calling the environment's own
REM python.exe directly does exactly the same job and cannot pick up
REM the wrong Python.
if not exist "%ROOT%.venv\Scripts\python.exe" goto :no_venv

REM --- 4) Start MMForge ----------------------------------------------
REM pushd is used instead of "cd /d" because it also copes with network
REM paths such as \\server\share\MMForge.
pushd "%ROOT%"
"%ROOT%.venv\Scripts\python.exe" "%ROOT%tools\launch_mmforge.py"
set "EXITCODE=%ERRORLEVEL%"
popd

if not "%EXITCODE%"=="0" goto :crashed
echo.
echo   MMForge has stopped.
goto :end

:crashed
echo.
echo   MMForge stopped with an error (code %EXITCODE%).
echo   The reason should be printed above.
goto :end

:no_venv
echo.
echo ===================================================================
echo   ERROR: the MMForge Python environment is missing.
echo ===================================================================
echo.
echo   Expected to find:
echo     %ROOT%.venv\Scripts\python.exe
echo.
echo   Fix: run Install-Windows.bat once, then try again.
echo.
goto :end

:no_project
echo.
echo ===================================================================
echo   ERROR: the MMForge folder could not be found.
echo ===================================================================
echo.
echo   This launcher looks for MMForge in its own folder:
echo     %~dp0
echo.
echo   Keep MMForge.bat inside the MMForge folder. To start MMForge
echo   from your Desktop, use the shortcut that Install-Windows.bat
echo   creates instead of copying this file.
echo.

:end
echo.
pause
endlocal
