@echo off
chcp 65001 >nul
echo ========================================
echo   DailyReport Win7 Build Tool
echo ========================================
echo.

echo [Check] PyInstaller version...
python -m pip show pyinstaller | findstr "Version: 4.10" >nul
if not errorlevel 1 goto :pyinstaller_ok

echo [Install] Installing PyInstaller 4.10...
python -m pip uninstall pyinstaller -y
python -m pip install pyinstaller==4.10 -i https://mirrors.aliyun.com/pypi/simple
if errorlevel 1 goto :pip_error
echo [Done] PyInstaller 4.10 installed
echo.
goto :pyinstaller_ok

:pyinstaller_ok
echo [OK] PyInstaller 4.10 ready
echo.

echo [Check] openpyxl...
python -m pip show openpyxl >nul
if not errorlevel 1 goto :openpyxl_ok

echo [Install] Installing openpyxl...
python -m pip install openpyxl -i https://mirrors.aliyun.com/pypi/simple
if errorlevel 1 goto :pip_error2
echo [Done] openpyxl installed
echo.
goto :openpyxl_ok

:openpyxl_ok
echo [OK] openpyxl ready
echo.

REM Clean old build files
if exist build\DailyReport (
    echo [Clean] Removing old build...
    rmdir /s /q build\DailyReport
)
if exist dist\DailyReport (
    echo [Clean] Removing old dist folder...
    rmdir /s /q dist\DailyReport
)
if exist dist\DailyReport.exe (
    del /q dist\DailyReport.exe
)
if exist DailyReport.spec (
    del /q DailyReport.spec
)

echo [Build] Starting PyInstaller for DailyReport...
echo.

python -m PyInstaller --name=DailyReport ^
    --windowed ^
    --onefile ^
    --clean ^
    --noconfirm ^
    --hidden-import=PyQt5 ^
    --hidden-import=PyQt5.QtWidgets ^
    --hidden-import=PyQt5.QtCore ^
    --hidden-import=PyQt5.QtGui ^
    --hidden-import=openpyxl ^
    --hidden-import=daily_report_data ^
    DailyReport.py

if errorlevel 1 goto :build_error

echo.
if not exist dist\DailyReport.exe goto :no_exe

echo ========================================
echo   Build Success! (Win7 Compatible)
echo ========================================
echo.
echo Output: dist\DailyReport.exe
for %%A in ("dist\DailyReport.exe") do echo Size: %%~zA bytes
echo.
echo Compatible with Windows 7 SP1 and above
echo No Python environment required
echo.
explorer dist
goto :done

:no_exe
echo [FAIL] exe not found, check errors above
goto :done

:pip_error
echo.
echo [ERROR] PyInstaller 4.10 install failed!
goto :done

:pip_error2
echo.
echo [ERROR] openpyxl install failed!
goto :done

:build_error
echo.
echo [ERROR] Build failed! Check errors above.
goto :done

:done
echo.
pause
