@echo off
chcp 65001 >nul
echo ========================================
echo   CheckDPI Windows 7兼容版打包工具
echo ========================================
echo.

REM 检查并安装正确版本的PyInstaller
echo [检查] 正在检查PyInstaller版本...
python -m pip show pyinstaller | findstr "Version: 4.10" >nul
if errorlevel 1 (
    echo [安装] PyInstaller版本不正确，正在安装4.10版本...
    python -m pip uninstall pyinstaller -y
    python -m pip install pyinstaller==4.10 -i https://mirrors.aliyun.com/pypi/simple
    if errorlevel 1 (
        echo [错误] PyInstaller 4.10 安装失败！
        pause
        exit /b 1
    )
    echo [完成] PyInstaller 4.10 安装成功
    echo.
) else (
    echo [OK] PyInstaller 4.10 已安装
    echo.
)

REM 清理旧的构建文件
if exist build (
    echo [清理] 删除旧的构建文件...
    rmdir /s /q build
)

if exist dist (
    echo [清理] 删除旧的分发文件...
    rmdir /s /q dist
)

if exist CheckDPI.spec (
    echo [清理] 删除旧的spec文件...
    del CheckDPI.spec
)

echo [打包] 开始为Windows 7打包 CheckDPI...
echo.

REM 使用PyInstaller 4.10打包（兼容Windows 7）
python -m PyInstaller --name=CheckDPI ^
    --windowed ^
    --onefile ^
    --clean ^
    --noconfirm ^
    --hidden-import=PIL ^
    --hidden-import=PIL.Image ^
    --hidden-import=PyQt5 ^
    CheckDPI.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo.
if exist dist\CheckDPI.exe (
    echo ========================================
    echo   打包完成！（Windows 7兼容版）
    echo ========================================
    echo.
    echo 可执行文件位置: dist\CheckDPI.exe
    for %%A in ("dist\CheckDPI.exe") do echo 文件大小: %%~zA 字节
    echo.
    echo ✓ 此版本完全兼容 Windows 7 SP1 及以上系统
    echo ✓ 已解决 api-ms-win-core-sysinfo-l1-2-0.dll 问题
    echo.
    explorer dist
) else (
    echo [失败] 打包出错，请检查错误信息
)

echo.
pause
