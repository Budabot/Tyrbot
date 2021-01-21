@echo off

IF EXIST .\venv\ GOTO install
.\win32\Python3.6\python.exe -m virtualenv --python=.\win32\Python3.6\python.exe venv

:install
IF [%1] == [--skip-install] GOTO run
venv\Scripts\pip install -r requirements.txt

:run
venv\Scripts\python ./bootstrap.py

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
