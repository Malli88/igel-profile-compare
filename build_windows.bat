@echo off
echo Building IGEL Profile Compare Tool...
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name "IGEL-Profile-Compare" src/main.py
echo.
echo Build complete! Executable in dist/IGEL-Profile-Compare.exe
pause
