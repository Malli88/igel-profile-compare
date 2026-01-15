@echo off
echo ============================================
echo IGEL Profile Compare - Windows Build
echo ============================================
echo.

echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo Building executable...
pyinstaller --onefile --windowed --name "IGEL-Profile-Compare" --paths src src\main.py

echo.
echo ============================================
if exist dist\IGEL-Profile-Compare.exe (
    echo BUILD SUCCESSFUL!
    echo Executable: dist\IGEL-Profile-Compare.exe
) else (
    echo BUILD FAILED - Check errors above
)
echo ============================================
pause
