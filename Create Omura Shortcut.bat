@echo off
REM ============================================================
REM  Run this ONCE to put an "Omura" icon on your Desktop.
REM  Double-clicking that icon launches the app like a program.
REM ============================================================
cd /d "%~dp0"
set "TARGET=%~dp0Omura.bat"
set "ICON=%~dp0frontend\public\omura.ico"
set "SHORTCUT=%USERPROFILE%\Desktop\Omura.lnk"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%SHORTCUT%'); ^
   $s.TargetPath = '%TARGET%'; ^
   $s.WorkingDirectory = '%~dp0'; ^
   if (Test-Path '%ICON%') { $s.IconLocation = '%ICON%' }; ^
   $s.WindowStyle = 7; ^
   $s.Description = 'Launch Omura Life Manager'; ^
   $s.Save()"

echo.
echo   Done. An "Omura" icon is now on your Desktop.
echo   Double-click it any time to open the app.
echo.
pause
