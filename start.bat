@echo off

pip install -U -r requirements.txt

:start
python ./bootstrap.py

REM The bot uses non-zero exit codes to signal state.
REM Should be restarted until it returns an exit code of zero.
if %errorlevel% == 0 goto end

timeout /t 1
goto :start

:end
pause
exit
