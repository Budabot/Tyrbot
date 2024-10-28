@echo off

SET PYTHON_BIN=.\win32\Python3.12.7\python.exe

IF EXIST .\venv\ GOTO install
%PYTHON_BIN% -m pip install virtualenv
%PYTHON_BIN% -m virtualenv --python=%PYTHON_BIN% venv

:install
IF [%1] == [--skip-install] GOTO run
.\venv\Scripts\pip.exe install -r requirements.txt

:run
.\venv\Scripts\python.exe .\bootstrap.py

REM The bot uses non-zero exit codes to signal state.
REM The bot will restart until it returns an exit code of zero.
if %errorlevel% == 0 goto end

if %errorlevel% == 2 goto restart

timeout /t 10
goto :install

:restart
timeout /t 5
goto :install

:end
pause
exit
