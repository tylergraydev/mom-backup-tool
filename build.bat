@echo off
echo Installing dependencies...
pip install psutil pyinstaller

echo.
echo Building executable...
pyinstaller --onefile --windowed --name "Mom's Backup Tool" --icon=NONE main.py

echo.
echo Done! Your executable is in the "dist" folder.
pause
