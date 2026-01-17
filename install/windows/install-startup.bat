@echo off
REM Install Locopycat Client to Windows Startup
REM This script creates a shortcut in the Windows Startup folder

echo Installing Locopycat Client to Windows Startup...

REM Get the directory of this script
set "INSTALL_DIR=%~dp0"
REM Remove trailing backslash
set "INSTALL_DIR=%INSTALL_DIR:~0,-1%

REM Get the Windows Startup folder
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

REM Create a shortcut using VBScript
set "VBS_SCRIPT=%TEMP%\create_shortcut.vbs"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\Locopycat Client.lnk"

echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo Set Shortcut = WshShell.CreateShortcut("%SHORTCUT_PATH%") >> "%VBS_SCRIPT%"
echo Shortcut.TargetPath = "%INSTALL_DIR%\start-locopycat.bat" >> "%VBS_SCRIPT%"
echo Shortcut.WorkingDirectory = "%INSTALL_DIR%" >> "%VBS_SCRIPT%"
echo Shortcut.Description = "Locopycat Client" >> "%VBS_SCRIPT%"
echo Shortcut.Save >> "%VBS_SCRIPT%"

cscript //nologo "%VBS_SCRIPT%"
del "%VBS_SCRIPT%"

if exist "%SHORTCUT_PATH%" (
    echo SUCCESS: Locopycat Client has been added to Windows Startup
    echo Shortcuts are located at:
    echo   %SHORTCUT_PATH%
    echo.
    echo The client will automatically start when you log into Windows.
    echo You can also run start-locopycat.bat manually to start it now.
) else (
    echo ERROR: Failed to create shortcut
    echo You may need to run this script as Administrator
)

pause
