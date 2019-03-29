@echo off

goto :install_venv

:start
venv\Scripts\pip install -U -r requirements.txt

venv\Scripts\python ./bootstrap.py

REM The bot uses non-zero exit codes to signal state.
REM The bot will restart until it returns an exit code of zero.
if %errorlevel% == 0 goto end

timeout /t 1
goto :start

:end
pause
exit

:install_venv
.\win32\Python3.6\python.exe -m virtualenv --python=.\win32\Python3.6\python.exe venv
goto :start
