@echo off
chcp 65001 >nul
echo ========================================
echo 黑色圆圈检测与裁剪工具 - Windows 7 打包脚本
echo ========================================
echo.

echo [1/3] 检查PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller未安装，正在安装兼容Windows 7的版本...
    pip install pyinstaller==4.10
) else (
    echo PyInstaller已安装
    for /f "tokens=2 delims=:" %%a in ('pip show pyinstaller ^| findstr "Version"') do set version=%%a
    echo 当前版本:%version%
)

echo.
echo [2/3] 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist BlackCircleRemover.spec del /q BlackCircleRemover.spec

echo.
echo [3/3] 开始打包（多文件模式，兼容Windows 7）...
pyinstaller --name=BlackCircleRemover ^
    --windowed ^
    --icon=NONE ^
    --add-data "README_黑圈处理.txt;." ^
    --hidden-import=PIL ^
    --hidden-import=numpy ^
    --exclude-module=tkinter ^
    --exclude-module=test ^
    BlackCircleRemover.py

if errorlevel 0 (
    echo.
    echo ========================================
    echo 打包成功！
    echo 可执行文件位置: dist\BlackCircleRemover\BlackCircleRemover.exe
    echo ========================================
    echo.
    echo 注意：
    echo 1. 请将整个BlackCircleRemover文件夹复制到目标机器
    echo 2. 需要确保目标机器已安装Visual C++运行库
    echo 3. 首次运行可能需要管理员权限
) else (
    echo.
    echo ========================================
    echo 打包失败！请检查错误信息
    echo ========================================
)

pause
