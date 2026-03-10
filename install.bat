@echo off
chcp 65001 >nul
cd /d "c:\Users\parse\Projects\statusbot"

set PY=
REM Try full path FIRST - Windows Store stub intercepts "python" command
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if "%PY%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if "%PY%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if "%PY%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if "%PY%"=="" for /d %%i in ("%LOCALAPPDATA%\Programs\Python\Python*") do if exist "%%i\python.exe" set PY="%%i\python.exe"
if "%PY%"=="" where py >nul 2>nul && set PY=py -3
if "%PY%"=="" where python >nul 2>nul && set PY=python

if "%PY%"=="" (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

echo Python: %PY%
%PY% --version
echo.

echo Upgrading pip...
%PY% -m pip install --upgrade pip
echo.

echo Installing python-dotenv...
%PY% -m pip install --user --no-cache-dir python-dotenv
if errorlevel 1 goto :error
echo OK
echo.

echo Installing sympy...
%PY% -m pip install --user --no-cache-dir sympy
if errorlevel 1 goto :error
echo OK
echo.

echo Installing python-telegram-bot...
%PY% -m pip install --user --no-cache-dir python-telegram-bot
if errorlevel 1 goto :error
echo Installing certifi (SSL fix for Windows)...
%PY% -m pip install --user --no-cache-dir certifi
if errorlevel 1 goto :error
echo Installing easyocr and pillow (for photo OCR)...
%PY% -m pip install --user --no-cache-dir easyocr pillow
if errorlevel 1 goto :error
echo OK
echo.

echo All packages installed! Run start.bat to launch the bot.
pause
exit /b 0

:error
echo.
echo ========================================
echo INSTALLATION FAILED
echo ========================================
echo.
echo Running pip install again to capture error...
%PY% -m pip install python-dotenv sympy python-telegram-bot certifi easyocr pillow > install_log.txt 2>&1
type install_log.txt
echo.
echo Open install_log.txt and send its contents for help.
pause
exit /b 1
