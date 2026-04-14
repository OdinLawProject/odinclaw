; ODIN Windows Installer — Inno Setup 6
; Compile from the repo root:
;   "C:\Users\owner\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\odinclaw_setup.iss
;
; What this .exe does when run on any Windows PC:
;   1. Copies bundled source for both packages to {app}\src\
;   2. Runs setup.ps1 which:
;        - Downloads and installs Python 3.12 silently if not present
;        - Downloads and installs Ollama silently if not present
;        - Binds Ollama to 127.0.0.1 (security)
;        - Creates a Python venv and pip installs both packages
;        - Starts a background pull of llama3.2:3b
;        - Writes an odin.bat launcher
;   3. Creates Start Menu + optional desktop shortcut

#define MyAppName      "ODIN"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "OdinLawProject"
#define MyAppURL       "https://github.com/OdinLawProject/odinclaw-app"

[Setup]
AppId={{B7C3D4E5-5F6A-4B1C-8D2E-9F0A1B2C3D4E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

DefaultDirName={localappdata}\ODIN
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

OutputDir=Output
OutputBaseFilename=ODINSetup-{#MyAppVersion}

Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

WizardStyle=modern
DisableProgramGroupPage=yes

UninstallDisplayName={#MyAppName}
CreateUninstallRegKey=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Setup script — wires up Python, Ollama, venv, packages
Source: "setup.ps1"; DestDir: "{app}"; Flags: ignoreversion

; ODIN substrate source (OdinClaw-main / odinclaw package)
Source: "..\odinclaw\*";      DestDir: "{app}\src\odinclaw\odinclaw"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc"
Source: "..\pyproject.toml";  DestDir: "{app}\src\odinclaw";          Flags: ignoreversion
Source: "..\README.md";       DestDir: "{app}\src\odinclaw";          Flags: ignoreversion
Source: "..\LICENSE";         DestDir: "{app}\src\odinclaw";          Flags: ignoreversion

; ODIN governed interpreter source (odinclaw-app)
; Assumes sibling repo structure: Desktop\OdinClaw-main and Desktop\odinclaw-app
Source: "..\..\odinclaw-app\interpreter\*";  DestDir: "{app}\src\odin-app\interpreter"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc"
Source: "..\..\odinclaw-app\pyproject.toml"; DestDir: "{app}\src\odin-app";             Flags: ignoreversion
Source: "..\..\odinclaw-app\README.md";      DestDir: "{app}\src\odin-app";             Flags: ignoreversion
Source: "..\..\odinclaw-app\LICENSE";        DestDir: "{app}\src\odin-app";             Flags: ignoreversion

[Icons]
Name: "{group}\ODIN";              Filename: "{app}\odin.bat"; WorkingDir: "{app}"
Name: "{group}\ODIN Status";       Filename: "{app}\odin.bat"; Parameters: "status"; WorkingDir: "{app}"
Name: "{group}\Uninstall ODIN";    Filename: "{uninstallexe}"
Name: "{autodesktop}\ODIN";        Filename: "{app}\odin.bat"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; \
    Parameters: "-ExecutionPolicy Bypass -WindowStyle Normal -File ""{app}\setup.ps1"" ""{app}"""; \
    StatusMsg: "Installing ODIN — downloading Python and Ollama if needed, setting up packages..."; \
    Flags: waituntilterminated

Filename: "{app}\odin.bat"; \
    Parameters: "status"; \
    Description: "Run ODIN status check now"; \
    Flags: nowait postinstall skipifsilent shellexec

[UninstallRun]
Filename: "powershell.exe"; \
    Parameters: "-Command ""Remove-Item -Recurse -Force '{app}\.venv' -ErrorAction SilentlyContinue"""; \
    Flags: runhidden waituntilterminated
