@echo off
REM ============================================================
REM  Omura launcher — starts backend + frontend, then opens
REM  Omura in its own app window (no browser tabs / address bar).
REM  Double-click this, or run the desktop shortcut.
REM ============================================================
title Omura
cd /d "%~dp0"

echo.
echo   Starting Omura...
echo.

REM --- Backend (SQLite-backed local API on :8003, auto-restarts) ---
start "Omura Backend" /min cmd /c "python -m backend.serve_local"

REM --- Frontend (Next.js dev server on :3001, self-healing supervisor) ---
if not exist "%~dp0frontend\node_modules" (
  echo   First run: installing frontend dependencies ^(one time^)...
  cd /d "%~dp0frontend"
  call npm install
  cd /d "%~dp0"
)
REM  serve_frontend.py runs `npm run dev` AND watches it: if the UI ever wedges
REM  on a corrupted .next cache (white screen / HTTP 500), it wipes the cache and
REM  restarts automatically — so you never get stuck on a blank window again.
start "Omura Frontend" /min cmd /c "python serve_frontend.py"

REM --- Wait for the frontend to answer on :3001 (curl; open anyway after ~2 min) ---
echo   Waiting for Omura to come online...
set /a _tries=0
:waitloop
curl.exe -sf -o nul http://localhost:3001
if not errorlevel 1 goto ready
set /a _tries+=1
if %_tries% geq 60 goto ready
ping -n 3 127.0.0.1 >nul
goto waitloop
:ready

REM --- Open in an app window (Edge preferred, then Chrome) ---
set "URL=http://localhost:3001"
set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
set "EDGE64=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
set "CHROMEX=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"

if exist "%EDGE%"    goto useedge
if exist "%EDGE64%"  goto useedge64
if exist "%CHROME%"  goto usechrome
if exist "%CHROMEX%" goto usechromex
start "" "%URL%"
goto done

:useedge
start "" "%EDGE%" --app=%URL%
goto done
:useedge64
start "" "%EDGE64%" --app=%URL%
goto done
:usechrome
start "" "%CHROME%" --app=%URL%
goto done
:usechromex
start "" "%CHROMEX%" --app=%URL%
goto done

:done
echo.
echo   Omura is running. You can close this window.
echo   ^(Backend + frontend keep running in their minimized windows.^)
echo.
timeout /t 4 >nul
