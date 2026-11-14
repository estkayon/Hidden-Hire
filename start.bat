@echo off
title Hidden Hire
cd /d "%~dp0"
set "ENV_NAME=hidden-hire"
set "URL=http://127.0.0.1:8000"

rem Already running: just open the browser.
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing '%URL%/api/sync' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if %errorlevel%==0 (
  start "" "%URL%"
  exit /b 0
)

rem Python environment: project .venv first, then the conda env.
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
) else (
  for %%C in ("%USERPROFILE%\anaconda3" "%USERPROFILE%\miniconda3" "%ProgramData%\anaconda3" "%ProgramData%\miniconda3") do (
    if exist "%%~C\Scripts\activate.bat" (
      call "%%~C\Scripts\activate.bat" %ENV_NAME%
      goto :env_ready
    )
  )
)
:env_ready

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Create the environment first, see README.md.
  pause
  exit /b 1
)

rem Build the dashboard once.
if not exist "web\dist\index.html" (
  echo Building the dashboard, this takes a minute...
  pushd web
  call npm install
  call npm run build
  popd
)

rem Open the browser as soon as the server answers.
start "" /b powershell -NoProfile -Command "for ($i = 0; $i -lt 90; $i++) { try { Invoke-WebRequest -UseBasicParsing '%URL%/api/sync' -TimeoutSec 2 | Out-Null; Start-Process '%URL%'; break } catch { Start-Sleep -Seconds 1 } }"

echo Hidden Hire is running at %URL%. Close this window to stop it.
python -m app.main