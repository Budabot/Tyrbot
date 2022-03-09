cd ..

rmdir /S /Q ".git"
rmdir /S /Q ".idea"
rmdir /S /Q "venv"
rmdir /S /Q "data\cache"
rmdir /S /Q "data\info"
del /Q "logs\*"
del /Q "data\*"
del "conf\config.py"

FOR /D /R .\ %%X IN (__pycache__) DO RMDIR /S /Q "%%X"

pause