@echo off
chcp 65001 >nul
cd /d "c:\Users\parse\Projects\statusbot"

set PY=
REM Full path first - Windows Store stub intercepts "python" command
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if "%PY%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if "%PY%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if "%PY%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if "%PY%"=="" for /d %%i in ("%LOCALAPPDATA%\Programs\Python\Python*") do if exist "%%i\python.exe" set PY="%%i\python.exe"
if "%PY%"=="" where py >nul 2>nul && set PY=py -3
if "%PY%"=="" where python >nul 2>nul && set PY=python

if "%PY%"=="" (
    echo ERROR: Python not found!
    echo Install from https://www.python.org/downloads/
    echo Check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Using: %PY%
%PY% --version
echo.

echo Installing dependencies...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Installation failed. Try running install.bat first.
) else (
    echo Dependencies OK
)
echo.

echo Starting bot...
echo.
set PYTHONUNBUFFERED=1
%PY% run.py
echo.
pause
