@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

set "APP_NAME=FrameExtractor"
set "ENTRY_FILE=Frame Extractor.py"
set "ICON_FILE=Images\icon.ico"
set "VERSION_FILE=version_info.txt"
set "APP_VERSION=2.1.1"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

for /f "tokens=3 delims= " %%V in ('findstr /b /c:"APP_VERSION = " "%ENTRY_FILE%"') do (
    set "APP_VERSION=%%~V"
)

set "DIST_APP_DIR=dist\%APP_NAME%"
set "RELEASE_ZIP=dist\%APP_NAME%-%APP_VERSION%.zip"

echo.
echo =============================================
echo   Building Frame Extractor - Folder Release
echo =============================================
echo.
echo Version: %APP_VERSION%
echo Python:  %PYTHON%
echo Output:  %DIST_APP_DIR%
echo.

if not exist "%ENTRY_FILE%" goto missing_entry
if not exist "%ICON_FILE%" goto missing_icon
if not exist "%VERSION_FILE%" goto missing_version

"%PYTHON%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 goto missing_pyinstaller

"%PYTHON%" -m PyInstaller ^
    --noconfirm ^
    --noconsole ^
    --onedir ^
    --clean ^
    --name "%APP_NAME%" ^
    --icon="%ICON_FILE%" ^
    --version-file "%VERSION_FILE%" ^
    --add-data "Images;Images" ^
    --add-data "licenses;licenses" ^
    --add-data "Source;Source" ^
    --collect-data qfluentwidgets ^
    --collect-data imageio_ffmpeg ^
    --copy-metadata imageio ^
    --copy-metadata imageio-ffmpeg ^
    --copy-metadata moviepy ^
    --copy-metadata pillow ^
    --copy-metadata proglog ^
    --copy-metadata PySide6-Fluent-Widgets ^
    --copy-metadata PySideSix-Frameless-Window ^
    "%ENTRY_FILE%"

if errorlevel 1 goto build_failed

if exist "%RELEASE_ZIP%" del /q "%RELEASE_ZIP%" >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -LiteralPath '%CD%\%DIST_APP_DIR%' -DestinationPath '%CD%\%RELEASE_ZIP%' -Force"
if errorlevel 1 goto zip_failed

echo.
echo =============================================
echo               BUILD SUCCESSFUL
echo =============================================
echo.
echo App folder:
echo   %DIST_APP_DIR%
echo.
echo Release zip:
echo   %RELEASE_ZIP%
echo.
echo Upload the zip to GitHub releases for the in-app updater.
echo.
goto done

:missing_entry
echo.
echo BUILD FAILED: Could not find "%ENTRY_FILE%".
goto fail_common

:missing_icon
echo.
echo BUILD FAILED: Could not find "%ICON_FILE%".
goto fail_common

:missing_version
echo.
echo BUILD FAILED: Could not find "%VERSION_FILE%".
goto fail_common

:missing_pyinstaller
echo.
echo BUILD FAILED: PyInstaller is not installed for %PYTHON%.
echo Run:
echo   %PYTHON% -m pip install -r requirements.txt
goto fail_common

:build_failed
echo.
echo =============================================
echo               BUILD FAILED
echo =============================================
echo.
echo Check the PyInstaller output above. Common causes:
echo   - Missing packages in the virtual environment
echo   - Missing Images, licenses, or Source folders
echo   - Import errors in "%ENTRY_FILE%"
echo   - Antivirus or permissions blocking dist/build output
echo.
goto done

:zip_failed
echo.
echo =============================================
echo           BUILD SUCCEEDED, ZIP FAILED
echo =============================================
echo.
echo App folder was built:
echo   %DIST_APP_DIR%
echo.
echo Could not create:
echo   %RELEASE_ZIP%
echo.
echo Make sure PowerShell Compress-Archive is available and dist is writable.
echo.
goto done

:fail_common
echo.
echo Make sure this script is being run from the Frame Extractor project folder.
echo.

:done
echo Press any key to close...
pause >nul
endlocal
