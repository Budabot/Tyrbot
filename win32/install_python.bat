SET PYTHON_VERSION=3.12.7
SET INSTALL_BINARY=python-%PYTHON_VERSION%-amd64.exe

%INSTALL_BINARY% /quiet InstallAllUsers=0 TargetDir=%cd%\Python%PYTHON_VERSION% Shortcuts=0 Include_doc=0 Include_dev=0 Include_launcher=0 Include_lib=1 Include_pip=1 Include_tcltk=0 Include_test=0 Include_tools=0 PrependPath=1 Include_test=0

rmdir /S /Q ..\venv

pause