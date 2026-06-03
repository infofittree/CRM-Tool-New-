@echo off
setlocal

title Sales Lead System

cd /d "%~dp0sales_lead_system"

if not exist "app\dashboard.py" (
    echo Could not find app\dashboard.py.
    echo Please keep this batch file inside:
    echo %~dp0
    pause
    exit /b 1
)

echo Starting Sales Lead System...
echo.

if exist ".venv_codex\Scripts\python.exe" (
    ".venv_codex\Scripts\python.exe" -m streamlit run app\dashboard.py
    goto after_run
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run app\dashboard.py
    goto after_run
)

python -m streamlit run app\dashboard.py

:after_run

if errorlevel 1 (
    echo.
    echo The system could not start. Please check that Python and Streamlit are installed.
    pause
)
