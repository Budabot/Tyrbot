@echo off
REM Switch to the Tyrbot root directory
cd /d "%~dp0.."

set /p aoPath= Enter the full path to AO (ex: C:\Funcom\Anarchy Online): 
set aoPath=%aoPath:"=%

echo Building tyrbot Docker image...
docker build -t tyrbot -f Dockerfile .

echo.
echo Running items extractor in container...
docker run --rm -u root -v "%aoPath%:/ao:ro" -v "%CD%:/app" -w /app/items_extractor tyrbot python extract.py -d /ao

echo.
pause
