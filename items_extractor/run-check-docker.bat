@echo off
REM Switch to the Tyrbot root directory
cd /d "%~dp0.."

set /p aoPath= Enter the full path to AO (ex: C:\Funcom\Anarchy Online): 
set aoPath=%aoPath:"=%

echo Building tyrbot Docker image...
docker build -t tyrbot -f Dockerfile .
if errorlevel 1 goto fail

echo.
echo Checking module data in container...
docker run --rm -v "%aoPath%:/ao:ro" -v "%CD%:/app:ro" -w /app/items_extractor tyrbot python check.py -d /ao
if errorlevel 1 goto fail

echo.
echo No problems found.
pause
exit /b 0

:fail
echo.
echo Check failed; see the errors above.
pause
exit /b 1
