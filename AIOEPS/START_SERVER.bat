@echo off
cd /d "%~dp0backend"
call venv\Scripts\activate.bat
echo Starting AIOEPS...
echo Open: http://localhost:5000
echo Admin: admin@aioeps.com / admin123
python app.py
pause
