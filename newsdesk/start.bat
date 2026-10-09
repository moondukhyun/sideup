@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Somnia Forest NewsDesk

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js is not installed. Install the LTS version from https://nodejs.org and run again.
  pause
  exit /b 1
)

if exist ".apikey" (
  set /p ANTHROPIC_API_KEY=<".apikey"
)
if not defined ANTHROPIC_API_KEY (
  echo Enter your Anthropic API key. It is saved only on this PC in newsdesk\.apikey
  set /p ANTHROPIC_API_KEY=API key: 
  >".apikey" echo %ANTHROPIC_API_KEY%
)

set /p COUNT=How many drafts? (default 3): 
if "%COUNT%"=="" set COUNT=3

echo.
echo Collecting topics and writing drafts...
node run.mjs %COUNT%
if errorlevel 1 (
  echo.
  echo [ERROR] Failed. Check the message above.
  pause
  exit /b 1
)

if exist "out" start "" "out"
echo.
echo Done. Review every draft by hand before recording or uploading.
pause
