@echo off
REM MGMT 675 Development Environment Installer Launcher
REM Right-click this file and select "Run as Administrator"

echo ================================================
echo   MGMT 675 Development Environment Installer
echo ================================================
echo.

REM Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This installer must be run as Administrator.
    echo.
    echo Please:
    echo   1. Right-click on INSTALL.bat
    echo   2. Select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Starting installer...
echo.

REM Run the PowerShell installer script with Bypass execution policy
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0run.ps1"

if %errorLevel% neq 0 (
    echo.
    echo ================================================
    echo   Installation Failed
    echo ================================================
    echo.
    echo Please check the error messages above.
    echo See README.md for alternative installation methods.
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Installation Complete
echo ================================================
echo.
echo Please close and reopen PowerShell or Command Prompt
echo to use the newly installed tools.
echo.
pause
