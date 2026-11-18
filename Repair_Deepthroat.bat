@echo off
setlocal
title Repair Deeproom deepthroat positions
cd /d "%~dp0"
if "%~1"=="" (
    echo Drag your Deeproom custom_wives folder onto this file.
    pause
    exit /b 1
)
set "LIST=%TEMP%\wb_repair_deepthroat.txt"
python Repair_Deepthroat.py "%~1" > "%LIST%"
if errorlevel 1 (
    type "%LIST%"
    pause
    exit /b 1
)
type "%LIST%"
findstr /b /c:"Nothing to fix." "%LIST%" >nul && ( pause & exit /b 0 )
echo.
choice /c YN /m "Apply these fixes (originals are backed up)"
if errorlevel 2 exit /b 0
python Repair_Deepthroat.py "%~1" --apply
pause
