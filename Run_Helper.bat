@echo off
title Tor Portable Helper - Launcher

:: 1. Automatic Administrator Privileges Elevation
:: ===============================================
NET FILE >nul 2>&1
if '%errorlevel%' == '0' (
    goto :got_admin
)

echo Creating VBS script for UAC elevation...
setlocal
set "batchPath=%~0"
set "batchArgs=%*"
set "vbsScript=%temp%\OElevate.vbs"

:: Create VBS script for elevation
echo Set UAC = CreateObject^("Shell.Application"^) > "%vbsScript%"
echo UAC.ShellExecute "%batchPath%", "%batchArgs%", "", "runas", 1 >> "%vbsScript%"

:: Run VBS script and exit current instance
"%temp%\OElevate.vbs"
endlocal
exit /b

:got_admin
if exist "%temp%\OElevate.vbs" (
    del "%temp%\OElevate.vbs" >nul 2>&1
)

:: ===============================================
:: 2. Change directory to the script's location
cd /d "%~dp0"

:: 3. Check Python installation and version
cls
echo ========================================
echo    Tor Portable Helper - Initialization
echo ========================================
echo.
echo Checking Python installation...
echo.

:: Try different Python commands to find installed version
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python
    goto :found_python
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python3
    goto :found_python
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=py
    goto :found_python
)

:: No Python found
cls
echo [X] ERROR: PYTHON IS NOT INSTALLED OR NOT IN PATH!
echo.
echo Please install Python 3.8 or newer from:
echo https://www.python.org/downloads/
echo.
echo During installation, MAKE SURE to check:
echo [X] Add Python to PATH
echo.
echo Press any key to open Python download page...
pause >nul
start https://www.python.org/downloads/
exit /b

:found_python
echo [✓] Python found: %PY_CMD%
%PY_CMD% --version

:: 4. Install/upgrade pip first
echo.
echo Upgrading pip...
%PY_CMD% -m pip install --upgrade pip >nul 2>&1
if %errorlevel% equ 0 (
    echo [✓] pip upgraded successfully
) else (
    echo [!] Warning: Could not upgrade pip, continuing...
)

:: 5. Install required dependencies
echo.
echo Installing required libraries...
echo (customtkinter, requests, Pillow)...
%PY_CMD% -m pip install customtkinter requests Pillow >nul 2>&1

if %errorlevel% equ 0 (
    echo [✓] All libraries installed successfully
) else (
    echo.
    echo [X] ERROR: Failed to install libraries
    echo.
    echo Trying with timeout and retry...
    %PY_CMD% -m pip install --timeout 30 --retries 3 customtkinter requests Pillow
    if %errorlevel% neq 0 (
        echo.
        echo [X] Still failed. Please check your connection and try again.
        echo.
        pause
        exit /b
    )
)

:: 6. Run the main application
echo.
echo ========================================
echo    Starting Tor Portable Helper...
echo ========================================
echo.
%PY_CMD% "tor_app.py"

:: 7. Check if application started successfully
if %errorlevel% equ 0 (
    echo.
    echo [✓] Program finished successfully.
) else (
    echo.
    echo [!] Program exited with errors.
)

echo.
pause