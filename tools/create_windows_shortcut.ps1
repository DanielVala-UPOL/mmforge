<#
.SYNOPSIS
    Create a Desktop shortcut for MMForge.

.DESCRIPTION
    Called by tools/setup_env.py at the end of the installation. It can also
    be run on its own if the shortcut is ever lost:

        powershell -ExecutionPolicy Bypass -File tools\create_windows_shortcut.ps1

    The shortcut points at MMForge.bat inside the project folder and carries
    the MMForge icon. Windows cannot put a custom icon on a .bat file itself,
    which is exactly why the Desktop entry is a shortcut (.lnk) rather than a
    copy of the launcher. Keeping the .bat in the project also means it can
    always find the project folder from its own location.

    If the project folder is later moved or renamed, re-run the installer to
    refresh the shortcut.

.PARAMETER ProjectRoot
    The MMForge folder. Defaults to the parent of the folder holding this
    script, which is correct whenever the file sits in tools/.
#>

param(
    [string]$ProjectRoot = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
)

$ErrorActionPreference = "Stop"

$launcher = Join-Path $ProjectRoot "MMForge.bat"
$iconFile = Join-Path $ProjectRoot "tools\mmforge.ico"

if (-not (Test-Path $launcher)) {
    Write-Host "  Could not find $launcher - shortcut not created."
    exit 1
}

# GetFolderPath is used rather than "$env:USERPROFILE\Desktop" because many
# university and company machines redirect the Desktop into OneDrive.
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "MMForge.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcher
$shortcut.WorkingDirectory = $ProjectRoot
$shortcut.Description = "MMForge - Mueller Matrix Workbench"
$shortcut.WindowStyle = 1

if (Test-Path $iconFile) {
    $shortcut.IconLocation = $iconFile
}

$shortcut.Save()

Write-Host "  Desktop shortcut created:"
Write-Host "      $shortcutPath"
if (-not (Test-Path $iconFile)) {
    Write-Host "  (No icon file at $iconFile - the shortcut uses the default icon.)"
}
