@echo off
echo === GoldBot Auto Setup ===

REM 1. Config git
git config --global user.name "phamtung92"
git config --global user.email "phamtung92@gmail.com"

REM 2. Copy files vào đúng vị trí
copy /Y "C:\GoldBot\SOUL.md" "C:\Users\Administrator\.openclaw\agents\main\agent\SOUL.md"
copy /Y "C:\GoldBot\gold_analysis.py" "C:\Users\Administrator\gold_analysis.py"
copy /Y "C:\GoldBot\execute_trade.py" "C:\Users\Administrator\execute_trade.py"
copy /Y "C:\GoldBot\execute_forex_trade.py" "C:\Users\Administrator\execute_forex_trade.py"

echo === Xong! Mo MT5 dang nhap roi test: keo M15 vang ===
pause