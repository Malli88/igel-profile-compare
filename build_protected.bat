@echo off
echo ============================================
echo IGEL Profile Compare - Protected Build
echo ============================================
echo.
echo This creates a protected single executable
echo using Nuitka (compiles Python to C code)
echo.

echo [1/3] Installing dependencies...
pip install -r requirements.txt
pip install nuitka ordered-set zstandard

echo.
echo [2/3] Compiling to protected executable...
echo This may take 5-10 minutes...
echo.

python -m nuitka ^
    --onefile ^
    --standalone ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=icon.ico ^
    --include-data-dir=templates=templates ^
    --include-package=core ^
    --include-package=web ^
    --output-filename=IGEL-Profile-Compare.exe ^
    --company-name="IGEL Technology" ^
    --product-name="IGEL Profile Compare" ^
    --file-version=1.0.0 ^
    --product-version=1.0.0 ^
    --remove-output ^
    run_web.py

echo.
echo [3/3] Build complete!
echo.

if exist IGEL-Profile-Compare.exe (
    echo ============================================
    echo SUCCESS! Protected executable created:
    echo   IGEL-Profile-Compare.exe
    echo.
    echo Protection features:
    echo   - Compiled to C code (not bytecode)
    echo   - No .pyc files to decompile
    echo   - Obfuscated control flow
    echo ============================================
) else (
    echo BUILD FAILED - Check errors above
)
pause
