@echo off
SETLOCAL

SET /P UV_VERSION=<"%~dp0..\UV_VERSION"
SET UV_EXE=%~dp0uv.exe
SET TMP_ZIP=%TEMP%\uv-windows.zip
SET URL=https://github.com/astral-sh/uv/releases/download/%UV_VERSION%/uv-x86_64-pc-windows-msvc.zip

IF EXIST "%UV_EXE%" (
    echo uv %UV_VERSION% already present.
    EXIT /B 0
)

echo Downloading uv %UV_VERSION%...
curl -L -o "%TMP_ZIP%" "%URL%"
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Download failed.
    EXIT /B 1
)

echo Downloading checksum...
curl -L -o "%TMP_ZIP%.sha256" "%URL%.sha256"
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Checksum download failed.
    EXIT /B 1
)

echo Verifying checksum...
certutil -hashfile "%TMP_ZIP%" SHA256 | findstr /v "hash" > "%TMP_ZIP%.hash"
set /p ACTUAL_HASH=<"%TMP_ZIP%.hash"
set ACTUAL_HASH=%ACTUAL_HASH: =%
for /f "tokens=1" %%a in ('type "%TMP_ZIP%.sha256"') do set EXPECTED_HASH=%%a

if /I not "%ACTUAL_HASH%"=="%EXPECTED_HASH%" (
    echo ERROR: Checksum mismatch.
    echo Expected: %EXPECTED_HASH%
    echo Actual:   %ACTUAL_HASH%
    DEL "%TMP_ZIP%"
    DEL "%TMP_ZIP%.sha256"
    DEL "%TMP_ZIP%.hash"
    EXIT /B 1
)
DEL "%TMP_ZIP%.sha256"
DEL "%TMP_ZIP%.hash"

echo Extracting uv.exe...
tar -xf "%TMP_ZIP%" -C "%TEMP%" uv.exe
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Extraction failed.
    DEL "%TMP_ZIP%"
    EXIT /B 1
)

MOVE "%TEMP%\uv.exe" "%UV_EXE%"

DEL "%TMP_ZIP%"
echo Done. uv %UV_VERSION% installed to %UV_EXE%
ENDLOCAL
