; ClipVault Professional Setup Script

[Setup]
AppId={{C6C26553-6E7B-4F7F-9C8E-3F258E2E5D5C}
AppName=ClipVault
AppVersion=1.0
AppPublisher=Botow
DefaultDirName={autopf}\ClipVault
DefaultGroupName=ClipVault
DisableProgramGroupPage=yes
; Output path for the Setup.exe
OutputDir=c:\Users\botow\_python\ClipVault\Output
OutputBaseFilename=ClipVaultSetup
SetupIconFile=c:\Users\botow\_python\ClipVault\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
; These are the files from your 'dist' folder after running PyInstaller
Source: "c:\Users\botow\_python\ClipVault\dist\.env"; DestDir: "{app}"; Flags: ignoreversion
Source: "c:\Users\botow\_python\ClipVault\dist\client_secrets.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "c:\Users\botow\_python\ClipVault\dist\ClipVault.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "c:\Users\botow\_python\ClipVault\dist\ClipVaultWatcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "c:\Users\botow\_python\ClipVault\dist\ClipVaultStatus.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ClipVault"; Filename: "{app}\ClipVault.exe"
Name: "{userstartup}\ClipVaultStatus"; Filename: "{app}\ClipVaultStatus.exe"
Name: "{autodesktop}\ClipVault"; Filename: "{app}\ClipVault.exe"
; This ensures the Watcher starts automatically when the user logs into Windows
Name: "{userstartup}\ClipVaultWatcher"; Filename: "{app}\ClipVaultWatcher.exe"

[Run]
; Launch the components immediately after installation
Filename: "{app}\ClipVaultStatus.exe"; Description: "Start Status Monitor"; Flags: nowait postinstall skipifsilent
Filename: "{app}\ClipVaultWatcher.exe"; Description: "Start Watcher Service"; Flags: nowait postinstall skipifsilent
Filename: "{app}\ClipVault.exe"; Description: "Launch ClipVault Dashboard"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; CRITICAL: Kill the processes before uninstallation starts to unlock the files
Filename: "taskkill"; Parameters: "/F /IM ClipVault.exe /T"; Flags: runhidden
Filename: "taskkill"; Parameters: "/F /IM ClipVaultWatcher.exe /T"; Flags: runhidden
Filename: "taskkill"; Parameters: "/F /IM ClipVaultStatus.exe /T"; Flags: runhidden

[UninstallDelete]
; Clean up logs and persistent session data created during runtime
Type: filesandordirs; Name: "{localappdata}\ClipVault"
Type: files; Name: "{app}\watcher.log"
Type: files; Name: "{app}\clipvault_debug.log"