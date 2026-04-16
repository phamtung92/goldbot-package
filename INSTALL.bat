@echo off
echo === GoldBot Auto Setup ===

REM 1. Config git
git config --global user.name "phamtung92"
git config --global user.email "phamtung92@gmail.com"

REM 2. Copy files vào đúng vị trí
copy /Y "C:\GoldBot\SOUL.md" "C:\Users\Administrator\.openclaw\workspace\SOUL.md"
copy /Y "C:\GoldBot\gold_analysis.py" "C:\Users\Administrator\gold_analysis.py"
copy /Y "C:\GoldBot\execute_trade.py" "C:\Users\Administrator\execute_trade.py"
copy /Y "C:\GoldBot\symbol_utils.py" "C:\Users\Administrator\symbol_utils.py"
copy /Y "C:\GoldBot\detect_symbols.py" "C:\Users\Administrator\detect_symbols.py"
copy /Y "C:\GoldBot\gold_trade_logger.py" "C:\Users\Administrator\gold_trade_logger.py"

REM 3. Patch openclaw.json - thêm exec permission (không đụng token/apikey)
powershell -Command "$p='C:\Users\Administrator\.openclaw\openclaw.json'; $c=[IO.File]::ReadAllText($p); if($c -notmatch 'exec'){$c=$c.Replace('\"profile\": \"coding\"','\"profile\": \"coding\",' + \"`r`n    \" + '\"exec\": {\"host\": \"gateway\"}'); [IO.File]::WriteAllText($p,$c); Write-Host 'Patched OK'} else {Write-Host 'exec da co san'}"

echo === Xong! Restart OpenClaw roi test: keo M15 vang ===
pause