@echo off

SET UV=.\win32\uv.exe
SET /P PYTHON_VERSION=<"PYTHON_VERSION"
SET UV_PROJECT_ENVIRONMENT=venv
SET UV_LINK_MODE=copy

IF NOT EXIST %UV% (
    CALL win32\download_uv.bat
    IF %ERRORLEVEL% NEQ 0 GOTO end
)

REM Migration: delete legacy non-uv virtual environments
IF EXIST venv\pyvenv.cfg (
    findstr /i "uv" venv\pyvenv.cfg >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        echo Detected legacy venv. Removing old venv...
        rmdir /S /Q venv
    )
)

:install_requirements
IF NOT EXIST venv\pyvenv.cfg (
    echo venv\pyvenv.cfg not found. Creating virtual environment...
    IF EXIST venv rmdir /S /Q venv
    %UV% venv venv --python %PYTHON_VERSION%
)
%UV% pip install --python venv\Scripts\python.exe -r requirements.txt

:run
venv\Scripts\python.exe bootstrap.py
if %errorlevel% == 0 goto end
if %errorlevel% == 2 goto restart
timeout /t 10
goto install_requirements

:restart
timeout /t 5
goto install_requirements

:end
pause
exit
