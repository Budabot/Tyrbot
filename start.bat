@echo off

:start
win32\python ./bootstrap.py

REM The bot uses non-zero exit codes to signal state.
REM The bot will restart until it returns an exit code of zero.
if %errorlevel% == 0 goto end

timeout /t 1
goto :start

:end
pause
exit
