@echo off
echo ============================================
echo IGEL Profile Compare - Obfuscated Build
echo ============================================
echo.

echo [1/4] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller pyarmor

echo.
echo [2/4] Obfuscating source code...
pyarmor gen -O dist_obf -r src run_web.py

echo.
echo [3/4] Building executable...
cd dist_obf
pyinstaller --onefile --windowed --name "IGEL-Profile-Compare" ^
    --add-data "../templates;templates" ^
    run_web.py
cd ..

echo.
echo [4/4] Cleaning up...
move dist_obf\dist\IGEL-Profile-Compare.exe .
rmdir /s /q dist_obf build dist 2>nul

if exist IGEL-Profile-Compare.exe (
    echo ============================================
    echo SUCCESS! Obfuscated executable created:
    echo   IGEL-Profile-Compare.exe
    echo ============================================
) else (
    echo BUILD FAILED
)
pause
