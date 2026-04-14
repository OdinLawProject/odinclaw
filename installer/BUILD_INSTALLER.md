# Building the OdinClaw Windows Installer (.exe)

## Quick setup (no .exe needed)

Run the PowerShell bootstrap from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File Install-OdinClaw.ps1
```

This installs Python (via winget if needed), Ollama, the odinclaw substrate,
and odinclaw-app, then creates a desktop shortcut. No Inno Setup required.

---

## Building a proper .exe installer with Inno Setup

### 1. Install Inno Setup 6

Download from https://jrsoftware.org/isdl.php and install.

### 2. Prepare the installer directory

```
installer/
├── odinclaw_setup.iss      ← the Inno Setup script
├── odinclaw.ico            ← app icon (256×256 .ico)
├── OllamaSetup.exe         ← download from https://ollama.com/download/windows
├── odinclaw-src/           ← copy of OdinClaw-main (the substrate)
│   └── (full repo contents)
├── odinclaw-app-src/       ← copy of odinclaw-app
│   └── (full repo contents, excluding .venv)
└── launch/
    ├── setup_env.ps1       ← env setup script (already here)
    ├── odinclaw.bat        ← launcher (written by setup_env.ps1)
    └── odinclaw.ico        ← copy of icon here too
```

Populate `odinclaw-src/` and `odinclaw-app-src/`:

```bat
xcopy /E /I /Y ".." "installer\odinclaw-src" ^
  /EXCLUDE:installer\xcopy_exclude.txt
xcopy /E /I /Y "..\odinclaw-app" "installer\odinclaw-app-src" ^
  /EXCLUDE:installer\xcopy_exclude.txt
```

Where `xcopy_exclude.txt` contains:
```
.git
.venv
__pycache__
*.pyc
pentest\results
```

### 3. Compile

```bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\odinclaw_setup.iss
```

Output: `installer\Output\OdinClawSetup.exe`

### 4. What the installer does

1. Checks for Python 3.10+ (prompts to download if missing)
2. Runs Ollama's silent installer (`OllamaSetup.exe /S`)
3. Runs `setup_env.ps1` to create a venv and install both packages
4. Creates Start Menu shortcuts and optional desktop icon
5. Registers an uninstaller in Add/Remove Programs

---

## CI: auto-building the installer on release

Add to `.github/workflows/release.yml`:

```yaml
- name: Install Inno Setup
  run: choco install innosetup -y

- name: Prepare installer sources
  run: |
    xcopy /E /I /Y . installer\odinclaw-src /EXCLUDE:installer\xcopy_exclude.txt
    xcopy /E /I /Y ..\odinclaw-app installer\odinclaw-app-src /EXCLUDE:installer\xcopy_exclude.txt

- name: Build installer
  run: |
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\odinclaw_setup.iss

- name: Upload installer artifact
  uses: actions/upload-artifact@v4
  with:
    name: OdinClawSetup
    path: installer/Output/OdinClawSetup.exe
```
