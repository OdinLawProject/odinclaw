<#
.SYNOPSIS
    ODIN post-install setup script.
    Called by the Inno Setup installer with -InstallDir, -Model, -AutoStart.
    Also callable standalone for dev/testing.

.PARAMETER InstallDir
    Root directory where ODIN is installed. Default: current directory.

.PARAMETER Model
    Ollama model tag to configure. Default: qwen2.5:7b-instruct-q8_0

.PARAMETER AutoStart
    'true' to register ODIN tray in Windows startup. Default: 'false'
#>
param(
    [string]$InstallDir = $PSScriptRoot,
    [string]$Model      = "qwen2.5:7b-instruct-q8_0",
    [string]$AutoStart  = "false"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference    = "SilentlyContinue"

$DataDir    = "$env:USERPROFILE\.odinclaw"
$VenvDir    = Join-Path $InstallDir ".venv"
$SrcDir     = Join-Path $InstallDir "src\odinclaw"
$VenvPython = "$VenvDir\Scripts\python.exe"

# ── Helpers ───────────────────────────────────────────────────────────────────

function Step([string]$msg) {
    Write-Host ""
    Write-Host "  [ ODIN ]  $msg" -ForegroundColor Cyan
}

function OK([string]$msg) {
    Write-Host "            $msg" -ForegroundColor Green
}

function Warn([string]$msg) {
    Write-Host "            $msg" -ForegroundColor Yellow
}

function Fail([string]$msg) {
    Write-Host ""
    Write-Host "  [ERROR]   $msg" -ForegroundColor Red
    Write-Host ""
    exit 1
}

function WingetInstall([string]$id, [string]$name) {
    Write-Host "            Installing $name via winget..." -ForegroundColor DarkCyan
    try {
        & winget install --id $id -e --silent `
            --accept-source-agreements --accept-package-agreements 2>&1 | Out-Null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function DownloadAndRun([string]$url, [string]$dest, [string[]]$runArgs) {
    Write-Host "            Downloading $([System.IO.Path]::GetFileName($url))..." -ForegroundColor DarkCyan
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
    & $dest @runArgs | Out-Null
    Remove-Item $dest -Force -ErrorAction SilentlyContinue
}

function RefreshPath {
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") +
                ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")
}

# ── Banner ────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor DarkCyan
Write-Host "    ODIN  -  Governed AI  |  Setup" -ForegroundColor Cyan
Write-Host "    Model: $Model" -ForegroundColor DarkCyan
Write-Host "    Dir:   $InstallDir" -ForegroundColor DarkCyan
Write-Host "  ============================================================" -ForegroundColor DarkCyan

# ── 1. Python ─────────────────────────────────────────────────────────────────

Step "Checking Python 3.12+..."

$PythonExe = $null

try {
    $ver = & python -c "import sys; print(sys.version_info >= (3,12))" 2>$null
    if ($ver -eq "True") {
        $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    }
} catch {}

if (-not $PythonExe) {
    Warn "Python 3.12+ not found. Installing..."

    $installed = $false
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        $installed = WingetInstall "Python.Python.3.12" "Python 3.12"
    }

    if (-not $installed) {
        DownloadAndRun `
            "https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe" `
            "$env:TEMP\python_installer.exe" `
            @("/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0")
        Start-Sleep -Seconds 3
    }

    RefreshPath

    foreach ($c in @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:ProgramFiles\Python312\python.exe"
    )) {
        if (Test-Path $c) { $PythonExe = $c; break }
    }

    if (-not $PythonExe) {
        $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    }

    if (-not $PythonExe) {
        Fail "Python installation could not be located. Install Python 3.12 from https://python.org and re-run setup."
    }
    OK "Python installed: $PythonExe"
} else {
    OK "Python ready: $PythonExe"
}

# ── 2. Ollama ─────────────────────────────────────────────────────────────────

Step "Checking Ollama..."

$OllamaExe = (Get-Command ollama -ErrorAction SilentlyContinue).Source
if (-not $OllamaExe) {
    $known = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (Test-Path $known) { $OllamaExe = $known }
}

if ($OllamaExe) {
    OK "Ollama ready: $OllamaExe"
} else {
    Warn "Ollama not found. Installing..."

    $installed = $false
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        $installed = WingetInstall "Ollama.Ollama" "Ollama"
    }

    if (-not $installed) {
        DownloadAndRun `
            "https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe" `
            "$env:TEMP\OllamaSetup.exe" `
            @("/S")
        Start-Sleep -Seconds 5
    }

    RefreshPath

    $OllamaExe = (Get-Command ollama -ErrorAction SilentlyContinue).Source
    if (-not $OllamaExe) {
        $known = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
        if (Test-Path $known) { $OllamaExe = $known }
    }

    if (-not $OllamaExe) {
        Fail "Ollama could not be located after install. Install from https://ollama.com and re-run."
    }
    OK "Ollama installed: $OllamaExe"
}

# Lock Ollama to localhost — security
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "127.0.0.1", "User")

# ── 3. Virtual environment ────────────────────────────────────────────────────

Step "Creating Python environment..."

if (-not (Test-Path $VenvPython)) {
    & $PythonExe -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Fail "Could not create virtual environment at $VenvDir" }
}
OK "Environment: $VenvDir"

# ── 4. Install ODIN package ───────────────────────────────────────────────────

Step "Installing ODIN and dependencies..."

& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -e $SrcDir --quiet
if ($LASTEXITCODE -ne 0) { Fail "Package installation failed." }
OK "All packages installed."

# ── 5. Write config.json ──────────────────────────────────────────────────────

Step "Writing configuration..."

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

@{
    model             = $Model
    model_provider    = "ollama"
    api_base          = "http://localhost:11434"
    ollama_exe        = $OllamaExe
    data_dir          = $DataDir
    session_name      = "odin-session"
    installed_at      = (Get-Date -Format "o")
    installer_version = "1.0.0"
} | ConvertTo-Json -Depth 3 | Set-Content "$DataDir\config.json" -Encoding UTF8

OK "Config: $DataDir\config.json"

# ── 6. Write ODIN.bat launcher ────────────────────────────────────────────────

Step "Writing launcher..."

@"
@echo off
title ODIN - Governed AI
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set OLLAMA_HOST=127.0.0.1
"$VenvPython" -m odinclaw.launcher
if errorlevel 1 pause
"@ | Set-Content "$InstallDir\ODIN.bat" -Encoding ASCII

OK "Launcher: $InstallDir\ODIN.bat"

# ── 7. Background model download ──────────────────────────────────────────────

Step "Starting model download in background..."
Write-Host "            $Model" -ForegroundColor DarkCyan
Write-Host "            This continues after the installer closes." -ForegroundColor DarkCyan

try {
    Start-Process -FilePath $OllamaExe -ArgumentList "serve" `
        -WindowStyle Hidden -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Start-Process -FilePath $OllamaExe -ArgumentList "pull", $Model `
        -WindowStyle Hidden -ErrorAction SilentlyContinue
    OK "Download started."
} catch {
    Warn "Could not start background download. ODIN will pull the model on first launch."
}

# ── 8. Auto-start (optional task) ────────────────────────────────────────────

if ($AutoStart -eq "true") {
    Step "Registering startup entry..."
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    Set-ItemProperty -Path $regPath -Name "ODINClaw" `
        -Value "cmd /c start `"`" /min `"$InstallDir\ODIN.bat`""
    OK "ODIN will start with Windows."
}

# ── Done ──────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor DarkCyan
Write-Host "    Setup complete." -ForegroundColor Green
Write-Host "    Double-click the ODIN shortcut on your desktop to launch." -ForegroundColor White
Write-Host "    Your AI model is downloading in the background." -ForegroundColor DarkCyan
Write-Host "  ============================================================" -ForegroundColor DarkCyan
Write-Host ""
