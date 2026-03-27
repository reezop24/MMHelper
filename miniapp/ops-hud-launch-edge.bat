@echo off
setlocal

set "HUD_URL=https://YOUR-HUD-DOMAIN.vercel.app/ops-hud.html"
set "EDGE_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

if not exist "%EDGE_PATH%" set "EDGE_PATH=C:\Program Files\Microsoft\Edge\Application\msedge.exe"

if not exist "%EDGE_PATH%" (
  echo Edge browser not found.
  pause
  exit /b 1
)

start "" "%EDGE_PATH%" --new-window --start-fullscreen "%HUD_URL%"
exit /b 0
