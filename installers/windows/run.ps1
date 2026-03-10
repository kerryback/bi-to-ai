# BI to AI Development Environment Installer for Windows
# This script installs Python and Claude Code
# Supports both x64 and ARM64 architectures (auto-detected)
# Run this script as Administrator

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"
$ProgressPreference = 'SilentlyContinue'  # Speed up downloads

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Detect architecture
$Arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
$IsArm = $Arch -eq [System.Runtime.InteropServices.Architecture]::Arm64

if ($IsArm) {
    $ArchLabel = "ARM64"
    $PythonUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-arm64.exe"
    $PythonInstaller = "python-3.12.8-arm64.exe"
} else {
    $ArchLabel = "x64"
    $PythonUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    $PythonInstaller = "python-3.12.8-amd64.exe"
}

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  BI to AI Development Environment Installer" -ForegroundColor Cyan
Write-Host "  for Windows ($ArchLabel)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Create temp directory for downloads
$TempDir = "$env:TEMP\bi-to-ai-setup"
if (Test-Path $TempDir) {
    Remove-Item -Recurse -Force $TempDir
}
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

function Write-Status {
    param([string]$Message)
    Write-Host "[*] $Message" -ForegroundColor White
}

function Write-Success {
    param([string]$Message)
    Write-Host "[+] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# Step 1: Install Python 3.12
Write-Status "Installing Python 3.12 ($ArchLabel)..."
$PythonInstalled = (Test-Path "C:\Program Files\Python312\python.exe") -or (Test-Path "C:\Program Files\Python312-arm64\python.exe")
if (-not $PythonInstalled) {
    $PythonPath = "$TempDir\$PythonInstaller"

    Write-Status "  Downloading Python 3.12 $ArchLabel..."
    Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonPath

    Write-Status "  Running Python installer..."
    Start-Process -Wait -FilePath $PythonPath -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0"

    Refresh-Path
    Write-Success "Python 3.12 installed"
} else {
    Write-Success "Python 3.12 already installed"
}

# Step 2: Install Claude Code (native installer)
Write-Status "Installing Claude Code..."
Refresh-Path
$ClaudeInstalled = Test-CommandExists "claude"
if (-not $ClaudeInstalled) {
    Write-Status "  Running native installer..."
    Invoke-Expression (Invoke-RestMethod -Uri "https://claude.ai/install.ps1")
    Refresh-Path
    Write-Success "Claude Code installed"
} else {
    Write-Success "Claude Code already installed"
}

# Step 3: Install Claude skills
Write-Status "Installing Claude skills..."
$SkillsSource = Join-Path $ScriptDir "skills"
$SkillsDest = "$env:USERPROFILE\.claude\skills"
if (Test-Path $SkillsSource) {
    New-Item -ItemType Directory -Force -Path $SkillsDest | Out-Null
    Copy-Item -Recurse -Force "$SkillsSource\*" $SkillsDest
    Write-Success "Claude skills installed to $SkillsDest"
} else {
    Write-Warning "Skills folder not found"
}

# Cleanup
Write-Status "Cleaning up temporary files..."
Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
Write-Success "Cleanup complete"

# Verification
Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  Verifying Installation" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

Refresh-Path
$AllGood = $true

Write-Status "Checking installed versions..."

# Check Python
try {
    $PyVersion = python --version 2>&1
    Write-Success "  Python: $PyVersion"
} catch {
    Write-Warning "  Python: NOT FOUND (may need to restart PowerShell)"
    $AllGood = $false
}

# Check Claude
try {
    $ClaudeVersion = claude --version 2>&1
    Write-Success "  Claude Code: $ClaudeVersion"
} catch {
    Write-Warning "  Claude Code: NOT FOUND"
    $AllGood = $false
}

Write-Host ""
if ($AllGood) {
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host "  Installation Complete!" -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Cyan
} else {
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host "  Installation Complete (with warnings)" -ForegroundColor Yellow
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Some components may not be available until you" -ForegroundColor Yellow
    Write-Host "close and reopen PowerShell." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Close and reopen PowerShell or Command Prompt"
Write-Host "  2. Run 'claude' to start Claude Code and authenticate"
Write-Host ""
Write-Host "Installed software:" -ForegroundColor Yellow
Write-Host "  - Python 3.12 ($ArchLabel)"
Write-Host "  - Claude Code"
Write-Host ""
