@echo off
REM One-click MT5 sync for TradeEdge Journal
title TradeEdge — Sync from MT5
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Create it first:
  echo   python -m venv .venv
  echo   .venv\Scripts\pip install -r requirements.txt
  echo   .venv\Scripts\pip install MetaTrader5
  pause
  exit /b 1
)

echo.
echo ========================================
echo   TradeEdge Journal — MT5 Sync
echo ========================================
echo Keep Exness MetaTrader 5 open and logged in.
echo.

".venv\Scripts\python.exe" scripts\sync_mt5.py
set ERR=%ERRORLEVEL%

echo.
if %ERR%==0 (
  echo Sync finished successfully.
) else (
  echo Sync finished with errors. Check the message above.
)
echo.
pause
exit /b %ERR%
