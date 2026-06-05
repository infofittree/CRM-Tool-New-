@echo off
setlocal
title Migrate CRM data to Aiven Cloud MySQL
cd /d "%~dp0sales_lead_system"

echo ============================================================
echo   Migrate local CRM data  -^>  Aiven Cloud MySQL
echo   (your local database is NOT changed or deleted)
echo ============================================================
echo.
set /p CLOUDPW=Paste your Aiven MySQL password, then press Enter:
echo.

if exist ".venv_codex\Scripts\python.exe" (
    set "PY=.venv_codex\Scripts\python.exe"
) else (
    set "PY=python"
)

"%PY%" tools\migrate_to_cloud_mysql.py ^
  --host mysql-3ea9af81-crm-system-1.i.aivencloud.com ^
  --port 14527 ^
  --user avnadmin ^
  --database defaultdb ^
  --ssl ^
  --password "%CLOUDPW%"

echo.
echo Done. Review the row counts above.
pause
