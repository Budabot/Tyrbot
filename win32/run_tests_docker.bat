@echo off
REM Switch to the Tyrbot root directory
cd /d "%~dp0.."

echo Building tyrbot-test Docker image...
docker build -t tyrbot-test -f Dockerfile.test .

echo.
echo Running unit tests in container...
docker run --rm -u user -v "%CD%:/app" -v /app/data tyrbot-test python -m unittest discover -p "*_test.py"

echo.

pause
