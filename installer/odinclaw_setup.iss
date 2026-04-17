; ============================================================
;  ODIN — Governed AI  |  Windows Installer
;  Inno Setup 6.3+
;
;  Build:
;    1. python installer\make_images.py        (generate branding)
;    2. "C:\...\Inno Setup 6\ISCC.exe" installer\odinclaw_setup.iss
;
;  Result: installer\Output\ODINSetup-1.0.0.exe
;  Single .exe, no prerequisites, works on any Windows 10/11 machine.
; ============================================================

#define MyAppName      "ODIN"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "OdinLawProject"
#define MyAppURL       "https://github.com/OdinLawProject"
#define MyAppExeName   "ODIN.bat"

; ── Build config ─────────────────────────────────────────────────────────────
[Setup]
AppId={{B7C3D4E5-5F6A-4B1C-8D2E-9F0A1B2C3D4E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) 2025 OdinLawProject

; Install to user's local app data — no admin rights needed
DefaultDirName={localappdata}\ODIN
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Output
OutputDir=Output
OutputBaseFilename=ODINSetup-{#MyAppVersion}
SetupIconFile=

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Visual
WizardStyle=modern
WizardSizePercent=120
WizardImageFile=wizard_sidebar.bmp
WizardSmallImageFile=wizard_header.bmp
DisableProgramGroupPage=yes
DisableReadyMemo=no
DisableWelcomePage=no
ShowLanguageDialog=no

; Uninstall
UninstallDisplayName={#MyAppName} — Governed AI
UninstallDisplayIcon={app}\{#MyAppExeName}
CreateUninstallRegKey=yes

; ── Languages ─────────────────────────────────────────────────────────────────
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ── Custom messages ───────────────────────────────────────────────────────────
[CustomMessages]
WelcomeLabel1=Welcome to ODIN%nGoverned AI
WelcomeLabel2=ODIN is a provably safe AI substrate that runs entirely on your machine.%n%nEvery action is governed, receipted, and explainable.%n%nThis wizard will install ODIN and all required components — including the AI runtime and your chosen model.%n%nNo data ever leaves your machine.
FinishedLabel=ODIN is installed and ready.%n%nDouble-click the ODIN shortcut on your desktop to start.%n%nYour first launch will download the AI model (~2–5 GB depending on your choice). This happens once and runs in the background.
FinishedHeadingLabel=Installation complete

; ── Installer tasks ───────────────────────────────────────────────────────────
[Tasks]
Name: "desktopicon";  Description: "Create a desktop shortcut";      Flags: checked
Name: "autostart";    Description: "Start ODIN tray icon with Windows"; Flags: unchecked

; ── Bundled files ─────────────────────────────────────────────────────────────
[Files]
; PowerShell setup script
Source: "setup.ps1";            DestDir: "{app}";                    Flags: ignoreversion

; ODIN source package
Source: "..\odinclaw\*";        DestDir: "{app}\src\odinclaw\odinclaw"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc,.egg-info"
Source: "..\pyproject.toml";    DestDir: "{app}\src\odinclaw";       Flags: ignoreversion
Source: "..\README.md";         DestDir: "{app}\src\odinclaw";       Flags: ignoreversion
Source: "..\LICENSE";           DestDir: "{app}\src\odinclaw";       Flags: ignoreversion

; ── Shortcuts ─────────────────────────────────────────────────────────────────
[Icons]
Name: "{group}\ODIN";             Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Start ODIN Governed AI"
Name: "{group}\ODIN Status";      Filename: "powershell.exe";        Parameters: "-Command odinclaw status"; WorkingDir: "{app}"; Comment: "Check ODIN substrate status"
Name: "{group}\Uninstall ODIN";   Filename: "{uninstallexe}"
Name: "{autodesktop}\ODIN";       Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon; Comment: "Start ODIN Governed AI"

; ── Run setup script during install ──────────────────────────────────────────
[Run]
Filename: "powershell.exe"; \
    Parameters: "-ExecutionPolicy Bypass -WindowStyle Normal -File ""{app}\setup.ps1"" -InstallDir ""{app}"" -Model ""{code:GetSelectedModel}"" -AutoStart ""{code:GetAutoStart}"""; \
    StatusMsg: "Setting up ODIN — this may take a few minutes..."; \
    Flags: waituntilterminated

; Offer to launch after install
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch ODIN now"; \
    Flags: nowait postinstall skipifsilent shellexec

; ── Uninstall cleanup ─────────────────────────────────────────────────────────
[UninstallRun]
Filename: "powershell.exe"; \
    Parameters: "-NoProfile -Command ""Remove-Item -Recurse -Force '{app}\.venv' -ErrorAction SilentlyContinue; Remove-Item -Force '{app}\ODIN.bat' -ErrorAction SilentlyContinue"""; \
    Flags: runhidden waituntilterminated

; ── Pascal scripting — model selection wizard page ───────────────────────────
[Code]

var
  ModelPage:    TInputOptionWizardPage;
  HardwarePage: TInputOptionWizardPage;

{ Model IDs matching page order }
function ModelId(idx: Integer): String;
begin
  case idx of
    0: Result := 'qwen2.5:7b-instruct-q8_0';
    1: Result := 'llama3.2:3b';
    2: Result := 'mistral:7b';
    3: Result := 'phi3:mini';
    4: Result := 'llama3.1:8b';
  else
    Result := 'qwen2.5:7b-instruct-q8_0';
  end;
end;

function GetSelectedModel(param: String): String;
begin
  Result := ModelId(ModelPage.SelectedValueIndex);
end;

function GetAutoStart(param: String): String;
begin
  if IsTaskSelected('autostart') then
    Result := 'true'
  else
    Result := 'false';
end;

procedure InitializeWizard;
begin
  { ── Hardware profile page ── }
  HardwarePage := CreateInputOptionPage(wpWelcome,
    'Your Hardware',
    'Help ODIN choose the right model for your machine.',
    'Select the option that best describes your computer. ' +
    'ODIN will recommend a model on the next page.',
    True, False);
  HardwarePage.Add('High-end   — 16 GB+ RAM, dedicated GPU');
  HardwarePage.Add('Mid-range  — 12–16 GB RAM, no GPU or integrated GPU');
  HardwarePage.Add('Standard   — 8–12 GB RAM');
  HardwarePage.Add('Minimum    — less than 8 GB RAM');
  HardwarePage.SelectedValueIndex := 1;

  { ── Model selection page ── }
  ModelPage := CreateInputOptionPage(HardwarePage.ID,
    'Choose Your AI Model',
    'Select the model ODIN will use. You can change this later.',
    'All models run 100% locally on your machine. ' +
    'The model will be downloaded on first launch.',
    True, False);

  ModelPage.Add(
    'Qwen 2.5 7B  (Recommended)' + #13#10 +
    '  ~5 GB download  |  8 GB RAM recommended  |  Fast, capable, best all-rounder');
  ModelPage.Add(
    'Llama 3.2 3B  (Lightweight)' + #13#10 +
    '  ~2 GB download  |  6 GB RAM minimum  |  Great for lower-end machines');
  ModelPage.Add(
    'Mistral 7B  (Reasoning)' + #13#10 +
    '  ~4 GB download  |  8 GB RAM recommended  |  Strong analytical reasoning');
  ModelPage.Add(
    'Phi-3 Mini  (Compact)' + #13#10 +
    '  ~2 GB download  |  6 GB RAM minimum  |  Microsoft research model, very efficient');
  ModelPage.Add(
    'Llama 3.1 8B  (Advanced)' + #13#10 +
    '  ~5 GB download  |  10 GB RAM recommended  |  Meta''s latest, excellent quality');
  ModelPage.SelectedValueIndex := 0;
end;

{ Auto-select recommended model based on hardware choice }
procedure HardwarePage_Activate(Sender: TWizardPage);
begin
  { nothing — user manually selects on next page }
end;

function HardwarePage_NextButtonClick(Sender: TWizardPage): Boolean;
var
  hw: Integer;
begin
  hw := HardwarePage.SelectedValueIndex;
  case hw of
    0: ModelPage.SelectedValueIndex := 4; { Llama 3.1 8B }
    1: ModelPage.SelectedValueIndex := 0; { Qwen 2.5 7B  }
    2: ModelPage.SelectedValueIndex := 0; { Qwen 2.5 7B  }
    3: ModelPage.SelectedValueIndex := 1; { Llama 3.2 3B }
  end;
  Result := True;
end;

{ Wire up the hardware page NextButton event }
procedure InitializeWizardExtra;
begin
  HardwarePage.OnNextButtonClick := @HardwarePage_NextButtonClick;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = HardwarePage.ID then
    HardwarePage_NextButtonClick(HardwarePage);
end;

{ Summary shown on Ready page }
function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo,
  MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  s: String;
begin
  s := '';
  s := s + 'Installation directory:' + NewLine;
  s := s + Space + ExpandConstant('{app}') + NewLine + NewLine;
  s := s + 'AI Model:' + NewLine;
  s := s + Space + GetSelectedModel('') + NewLine + NewLine;
  s := s + 'Components:' + NewLine;
  s := s + Space + 'ODIN governance substrate' + NewLine;
  s := s + Space + 'Python 3.12 (if not already installed)' + NewLine;
  s := s + Space + 'Ollama AI runtime (if not already installed)' + NewLine;
  s := s + Space + 'rich, pystray, pillow (Python packages)' + NewLine + NewLine;
  if MemoTasksInfo <> '' then begin
    s := s + 'Additional tasks:' + NewLine;
    s := s + MemoTasksInfo + NewLine;
  end;
  Result := s;
end;
