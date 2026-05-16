@echo off
REM ============================================================
REM  AIOEPS - Full AI Installer (run AFTER INSTALL.bat works)
REM  Installs: PyTorch, YOLOv8, scikit-learn, audio libs
REM  No CMake required!
REM ============================================================

echo.
echo  Installing Full AI Packages (15-30 min, ~2GB download)...
echo.

cd /d "%~dp0backend"
call venv\Scripts\activate.bat

echo  [1/4] Installing ML packages...
pip install scikit-learn==1.3.2 scipy==1.11.4 pandas==2.1.3 --quiet
pip install matplotlib==3.8.2 seaborn==0.13.2 imutils==0.5.4 --quiet

echo  [2/4] Installing PyTorch (CPU version - smaller download)...
pip install torch==2.1.1 torchvision==0.16.1 --index-url https://download.pytorch.org/whl/cpu --quiet

echo  [3/4] Installing YOLOv8...
pip install ultralytics==8.0.227 --quiet

echo  [4/4] Installing Audio (pyaudio, pyttsx3)...
pip install pyaudio==0.2.14 --quiet 2>nul || echo [WARN] pyaudio skipped
pip install SpeechRecognition==3.10.0 pyttsx3==2.90 --quiet

echo.
echo  =====================================================
echo   Full AI installation complete!
echo   Run INSTALL.bat to start the server.
echo  =====================================================
pause
