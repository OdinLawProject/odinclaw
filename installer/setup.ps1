# ODIN Setup Script — embedded by Inno Setup, run at install time
# Called as: powershell.exe -ExecutionPolicy Bypass -File setup.ps1 <AppDir>
# Compatible with PowerShell 5.1 (Windows built-in)

param([string]$AppDir)

$ErrorActionPreference = "Stop"
$ProgressPreference    = "SilentlyContinue"
$LogFile               = Join-Path $AppDir "install.log"

Add-Type -AssemblyName System.Windows.Forms

function Log([string]$msg) {
    $ts   = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
}

function Die([string]$msg) {
    Log "FATAL: $msg"
    [System.Windows.Forms.MessageBox]::Show(
        $msg, "ODIN Setup Failed",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
    exit 1
}

New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
Log "ODIN setup starting — AppDir: $AppDir"

# ─── 1. Locate or install Python 3.12 ────────────────────────────────────────

Log "Checking for Python 3.10+..."

function Find-Python {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python312\python.exe",
        "C:\Program Files\Python312\python.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) {
            $v = & $p --version 2>&1
            if ($v -match "Python 3\.(\d+)" -and [int]$Matches[1] -ge 10) { return $p }
        }
    }
    # Check PATH
    $fromPath = Get-Command "python" -ErrorAction SilentlyContinue
    if ($fromPath) {
        $v = & $fromPath.Source --version 2>&1
        if ($v -match "Python 3\.(\d+)" -and [int]$Matches[1] -ge 10) { return $fromPath.Source }
    }
    return $null
}

$PythonExe = Find-Python
if (-not $PythonExe) {
    Log "Python 3.10+ not found — downloading Python 3.12.10..."
    $Installer = "$env:TEMP\python-3.12.10-amd64.exe"
    try {
        (New-Object System.Net.WebClient).DownloadFile(
            "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe",
            $Installer
        )
        Log "Running Python installer silently..."
        $p = Start-Process -FilePath $Installer `
            -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0" `
            -Wait -PassThru
        if ($p.ExitCode -ne 0) { Die "Python installer failed (exit code $($p.ExitCode))" }

        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","User") + ";" +
                    [System.Environment]::GetEnvironmentVariable("PATH","Machine")
        $PythonExe = Find-Python
    } catch {
        Die "Could not download Python: $_`n`nInstall Python 3.12 from https://python.org/downloads and re-run ODINSetup.exe"
    }
}
if (-not $PythonExe) { Die "Python 3.10+ not found after install attempt." }
Log "Python: $( & $PythonExe --version 2>&1 ) at $PythonExe"

# ─── 2. Locate or install Ollama ─────────────────────────────────────────────

Log "Checking for Ollama..."

function Find-Ollama {
    $found = Get-Command "ollama" -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "C:\Program Files\Ollama\ollama.exe"
    )
    foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
    return $null
}

$OllamaExe = Find-Ollama
if (-not $OllamaExe) {
    Log "Ollama not found — downloading OllamaSetup.exe..."
    $Installer = "$env:TEMP\OllamaSetup.exe"
    try {
        (New-Object System.Net.WebClient).DownloadFile(
            "https://ollama.com/download/OllamaSetup.exe",
            $Installer
        )
        Log "Running Ollama installer silently..."
        $p = Start-Process -FilePath $Installer -ArgumentList "/S" -Wait -PassThru
        if ($p.ExitCode -ne 0) {
            Log "Warning: Ollama installer returned exit code $($p.ExitCode)"
        }
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","User") + ";" +
                    [System.Environment]::GetEnvironmentVariable("PATH","Machine")
        $OllamaExe = Find-Ollama
    } catch {
        Log "Warning: Ollama download/install failed: $_ — install later from https://ollama.com"
    }
}

if ($OllamaExe) {
    Log "Ollama: $OllamaExe"
    # Security: bind Ollama to localhost only
    [System.Environment]::SetEnvironmentVariable("OLLAMA_HOST",    "127.0.0.1",         "User")
    [System.Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", "http://localhost",   "User")
    Log "OLLAMA_HOST=127.0.0.1 (localhost only)"
} else {
    Log "Warning: Ollama not installed — ODIN will run without a local model until you install Ollama from https://ollama.com"
}

# ─── 3. Create virtual environment ───────────────────────────────────────────

Log "Creating Python virtual environment..."
$VenvDir    = Join-Path $AppDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip    = Join-Path $VenvDir "Scripts\pip.exe"

if (-not (Test-Path $VenvDir)) {
    & $PythonExe -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Die "Failed to create virtual environment." }
}
Log "Upgrading pip..."
& $VenvPython -m pip install --upgrade pip --quiet
Log "Virtual environment ready: $VenvDir"

# ─── 4. Install ODIN substrate (odinclaw) ────────────────────────────────────

Log "Installing ODIN substrate package..."
$SubstrateSrc = Join-Path $AppDir "src\odinclaw"

if (Test-Path (Join-Path $SubstrateSrc "pyproject.toml")) {
    Log "Installing from bundled source: $SubstrateSrc"
    & $VenvPip install -e $SubstrateSrc --quiet
} else {
    Log "Bundled substrate not found — installing from GitHub..."
    & $VenvPip install "git+https://github.com/OdinLawProject/odinclaw.git" --quiet
}
if ($LASTEXITCODE -ne 0) { Die "ODIN substrate install failed. See $LogFile" }
Log "ODIN substrate installed"

# ─── 5. Install ODIN governed interpreter (odinclaw-app) ─────────────────────

Log "Installing ODIN governed interpreter..."
$AppSrc = Join-Path $AppDir "src\odin-app"

if (Test-Path (Join-Path $AppSrc "pyproject.toml")) {
    Log "Installing from bundled source: $AppSrc"
    & $VenvPip install -e $AppSrc --quiet
} else {
    Log "Bundled app source not found — installing from GitHub..."
    & $VenvPip install "git+https://github.com/OdinLawProject/odinclaw-app.git" --quiet
}
if ($LASTEXITCODE -ne 0) { Die "ODIN interpreter install failed. See $LogFile" }
Log "ODIN interpreter installed"

# ─── 6. Write odin.bat launcher ──────────────────────────────────────────────

Log "Writing odin.bat launcher..."
$LauncherPath = Join-Path $AppDir "odin.bat"

$Bat = "@echo off`r`n"
$Bat += "setlocal`r`n"
$Bat += "set ODIN_DIR=$AppDir`r`n"
$Bat += "call `"$VenvDir\Scripts\activate.bat`"`r`n"
$Bat += "`r`n"
$Bat += "if /I `"%1`"==`"status`" (`r`n"
$Bat += "    python -c `"from odinclaw.odin.orchestration.lifecycle import build_lifecycle; print('ODIN substrate: OK')`"`r`n"
$Bat += "    goto :end`r`n"
$Bat += ")`r`n"
$Bat += "if /I `"%1`"==`"pull-model`" (`r`n"
$Bat += "    ollama pull llama3.2:3b`r`n"
$Bat += "    goto :end`r`n"
$Bat += ")`r`n"
$Bat += "if /I `"%1`"==`"pentest`" (`r`n"
$Bat += "    for %%f in (`"$AppSrc\pentest\*.py`") do python `"%%f`"`r`n"
$Bat += "    goto :end`r`n"
$Bat += ")`r`n"
$Bat += "`r`n"
$Bat += "rem Default: launch ODIN governed interpreter`r`n"
$Bat += "python -m interpreter %*`r`n"
$Bat += ":end`r`n"

[System.IO.File]::WriteAllText($LauncherPath, $Bat, [System.Text.Encoding]::ASCII)
Log "Launcher: $LauncherPath"

# ─── 7. Pull default model in background ─────────────────────────────────────

if ($OllamaExe) {
    Log "Starting background pull of llama3.2:3b (continues after installer closes)..."
    Start-Process -FilePath $OllamaExe -ArgumentList "pull", "llama3.2:3b" `
        -WindowStyle Hidden -ErrorAction SilentlyContinue
}

# ─── 8. Smoke test ───────────────────────────────────────────────────────────

Log "Running substrate smoke test..."
$SmokeScript = @"
import tempfile
from pathlib import Path
tmp = Path(tempfile.mkdtemp())
from odinclaw.odin.orchestration.lifecycle import build_lifecycle
lc = build_lifecycle(tmp)
lc.startup()
lc.shutdown()
from odinclaw.odin.audit.receipt_chain import ReceiptChain
ok, msg = ReceiptChain(tmp / 'receipts.jsonl').verify_chain()
assert ok, f'Receipt chain FAILED: {msg}'
print('ODIN substrate smoke test: PASSED')
print('Receipt chain:', msg)
"@

$SmokeFile = "$env:TEMP\odin_smoke.py"
[System.IO.File]::WriteAllText($SmokeFile, $SmokeScript)
$out = & $VenvPython $SmokeFile 2>&1
$out | ForEach-Object { Log $_ }
if ($LASTEXITCODE -ne 0) {
    Log "Warning: smoke test failed — install may still work, check $LogFile"
} else {
    Log "Smoke test passed"
}

# ─── Done ─────────────────────────────────────────────────────────────────────

Log "ODIN setup complete."
Log "Launcher: $LauncherPath"
Log "Log:      $LogFile"
