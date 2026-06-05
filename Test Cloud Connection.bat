@echo off
setlocal
title Test Aiven Cloud MySQL connection
cd /d "%~dp0sales_lead_system"

echo ============================================================
echo   Test connection to Aiven Cloud MySQL
echo ============================================================
echo.
set /p CLOUDPW=Paste your Aiven MySQL password, then press Enter:
echo.

if exist ".venv_codex\Scripts\python.exe" (
    set "PY=.venv_codex\Scripts\python.exe"
) else (
    set "PY=python"
)

"%PY%" tools\test_cloud_connection.py ^
  --host mysql-3ea9af81-crm-system-1.i.aivencloud.com ^
  --port 14527 ^
  --user avnadmin ^
  --database defaultdb ^
  --ssl ^
  --password "%CLOUDPW%"

echo.
pause
