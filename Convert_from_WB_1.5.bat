@echo off
setlocal

title WB 1.5 to Modded Mod Converter v1.2.1
cd /d "%~dp0"

echo ======================================================================
echo           WB 1.5 TO MODDED MOD CONVERTER v1.2.1
echo ======================================================================
echo.

if not "%~1"=="" goto :has_args
if exist "input" (
    for /f "delims=" %%A in ('dir /b /a "input\*" 2^>nul ^| findstr /v /i /x ".gitkeep"') do (
        echo [*] Auto-detected files in input/ folder.
        goto :run_default
    )
)

echo Drag and drop your WB 1.5 custom mod folder directly onto this .bat file,
echo or place your mod folder/zip inside the input/ folder.
echo.
pause
exit /b 1

:has_args
python "WB_1.5_to_Modded.py" %*
set "RC=%ERRORLEVEL%"
goto :finish

:run_default
python "WB_1.5_to_Modded.py"
set "RC=%ERRORLEVEL%"
goto :finish

:finish
echo.
echo Press any key to exit...
pause >nul
exit /b %RC%
