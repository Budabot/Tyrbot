@echo off

pip install -U -r requirements.txt

:start
python ./bootstrap.py
if %errorlevel% == 0 goto end
timeout /t 5
goto :start

:end
pause
exit
