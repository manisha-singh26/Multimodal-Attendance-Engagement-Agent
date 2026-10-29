@echo off
echo ======================================================================
echo Launching Multimodal Classroom Intelligence Agent in Production
echo ======================================================================
echo Installing requirements...
python -m pip install -r requirements.txt
echo Running system verification tests...
python -m unittest tests/test_system.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Unit tests failed. Aborting launch.
    pause
    exit /b %ERRORLEVEL%
)
echo Starting Production Server (Waitress)...
python wsgi.py

