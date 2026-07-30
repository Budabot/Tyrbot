@echo off

SET UV=.\win32\uv.exe
SET /P PYTHON_VERSION=<"win32\PYTHON_VERSION"
SET UV_PROJECT_ENVIRONMENT=venv
SET UV_LINK_MODE=copy

IF NOT EXIST %UV% (
    CALL win32\download_uv.bat
    IF %ERRORLEVEL% NEQ 0 GOTO end
)

REM One-time migration: delete old venv if it points to deleted win32\Python3.12.7 directory
IF EXIST venv\pyvenv.cfg (
    findstr /i "Python3.12.7" venv\pyvenv.cfg >nul 2>&1
    IF %ERRORLEVEL% EQU 0 (
        echo Detected legacy venv from Python 3.12.7. Removing old venv...
        rmdir /S /Q venv
    )
)

:install_requirements
IF NOT EXIST venv %UV% venv --python %PYTHON_VERSION% venv
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
