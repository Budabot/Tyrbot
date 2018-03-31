@echo off
:start
python ./bootstrap.py
if %errorlevel% neq 0 goto start
pause