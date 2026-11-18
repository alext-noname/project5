#define AppName "Homework"
#define AppVersion "1.3.0"

[Setup]
AppId={{5623482E-5AEE-4E62-8FA5-B5828FBF9410}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\app.py
OutputDir=installer_output
OutputBaseFilename=HomeworkTrackerSetup
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=homework.ico

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Dirs]
Name: "{app}\data"; Flags: uninsneveruninstall

[Files]
Source: "app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "models.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "storage.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "i18n.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "homework.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "run_app.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\run_app.bat"; WorkingDir: "{app}"; IconFilename: "{app}\homework.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\run_app.bat"; WorkingDir: "{app}"; IconFilename: "{app}\homework.ico"
