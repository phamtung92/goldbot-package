@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ========================================
echo   GOLDBOT VPS INSTALLER - 1 CLICK
echo ========================================

set BASE_DIR=C:\GoldBot
set WORKSPACE_DIR=C:\Users\Administrator\.openclaw\workspace
set PYTHON_EXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe
set PACKAGE_DIR=%~dp0

echo [1/8] Tao thu muc can thiet...
if not exist "%BASE_DIR%" mkdir "%BASE_DIR%"
if not exist "%WORKSPACE_DIR%" mkdir "%WORKSPACE_DIR%"

echo [2/8] Cai Python neu chua co...
where python >nul 2>nul
if errorlevel 1 (
  powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
  start /wait %TEMP%\python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
)

echo [3/8] Cai thu vien Python...
python -m pip install --upgrade pip
python -m pip install MetaTrader5 pandas numpy pytz

echo [4/8] Cai Node.js neu chua co...
where node >nul 2>nul
if errorlevel 1 (
  powershell -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v20.19.0/node-v20.19.0-x64.msi' -OutFile '%TEMP%\node_installer.msi'"
  msiexec /i %TEMP%\node_installer.msi /qn
)

echo [5/8] Cai OpenClaw...
call npm install -g openclaw

echo [6/8] Copy file bot...
copy /Y "%PACKAGE_DIR%gold_analysis.py" "%BASE_DIR%\gold_analysis.py"
copy /Y "%PACKAGE_DIR%execute_trade.py" "%BASE_DIR%\execute_trade.py"
copy /Y "%PACKAGE_DIR%SOUL.md" "%WORKSPACE_DIR%\SOUL.md"
copy /Y "%PACKAGE_DIR%HEARTBEAT.md" "%WORKSPACE_DIR%\HEARTBEAT.md"

echo [7/8] Tao Task Scheduler chay gold_analysis.py moi 5 phut...
schtasks /Create /F /SC MINUTE /MO 5 /TN "GoldBot_GoldAnalysis" /TR "python %BASE_DIR%\gold_analysis.py" /RL HIGHEST

echo [8/8] Tao Task Scheduler chay OpenClaw moi 1 gio...
schtasks /Create /F /SC HOURLY /MO 1 /TN "GoldBot_OpenClawHeartbeat" /TR "openclaw run main" /RL HIGHEST

echo ========================================
echo Cai dat co ban da hoan tat.
echo Xem CHECKLIST.md de lam tiep cac buoc thu cong.
echo ========================================
pause
