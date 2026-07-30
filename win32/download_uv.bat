@echo off
SETLOCAL

SET /P UV_VERSION=<"%~dp0UV_VERSION"
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
