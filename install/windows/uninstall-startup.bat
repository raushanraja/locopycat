@echo off
REM Remove Locopycat Client from Windows Startup

echo Removing Locopycat Client from Windows Startup...

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\Locopycat Client.lnk"

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo SUCCESS: Locopycat Client has been removed from Windows Startup
) else (
    echo INFO: Locopycat Client shortcut not found in startup folder
)

pause
