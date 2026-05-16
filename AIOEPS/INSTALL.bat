@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  AIOEPS - Smart Windows Installer
REM  Handles dlib WITHOUT needing CMake or Visual Studio!
REM ============================================================

echo.
echo  =====================================================
echo    AIOEPS - AI Proctoring System  ^|  Auto Installer
echo  =====================================================
echo.

REM Check Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] Python not found!
    echo  Download: https://www.python.org/downloads/
    pause & exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo  Python: %PY_VER%

cd /d "%~dp0backend"

echo.
echo  [1/5] Creating virtual environment...
if not exist venv python -m venv venv
call venv\Scripts\activate.bat

echo  [2/5] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo  [3/5] Installing core packages (Flask, OpenCV, MediaPipe)...
pip install -r requirements_minimal.txt --quiet
echo        Done!

echo  [4/5] Installing dlib pre-built wheel (no CMake needed)...
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (set PYMAJ=%%a& set PYMIN=%%b)
pip install https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.1-cp%PYMAJ%%PYMIN%-cp%PYMAJ%%PYMIN%-win_amd64.whl --quiet 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo        Pre-built wheel not found for Python %PY_VER%, trying pip...
    pip install dlib --quiet 2>nul
    IF %ERRORLEVEL% NEQ 0 (
        echo        [OK] dlib skipped - face recognition uses fallback mode
    ) ELSE (
        pip install face-recognition --quiet 2>nul
        echo        face-recognition installed!
    )
) ELSE (
    pip install face-recognition --quiet 2>nul
    echo        dlib + face-recognition installed!
)

echo.
echo  [5/5] Launching server...
echo.
echo  =====================================================
echo    Browser : http://localhost:5000
echo    Admin   : admin@aioeps.com  /  admin123
echo    Ctrl+C to stop
echo  =====================================================
echo.
python app.py
pause
