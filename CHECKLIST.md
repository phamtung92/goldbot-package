# CHECKLIST DEPLOY GOLDBOT VPS

## Việc cần làm thủ công sau khi chạy INSTALL.bat

1. Đăng nhập MT5 bằng tài khoản mới trên VPS
   - Mở MetaTrader 5
   - Login đúng account / password / server
   - Kiểm tra đã thấy giá realtime

2. Bật AutoTrading trên MT5
   - Nhấn nút AutoTrading
   - Đảm bảo EA được phép chạy

3. Tạo Telegram bot mới qua BotFather
   - Vào Telegram
   - Nhắn `@BotFather`
   - Dùng lệnh `/newbot`
   - Lưu lại bot token

4. Điền token Telegram vào OpenClaw
   - Mở file config OpenClaw
   - Thêm bot token mới
   - Kiểm tra channel Telegram hoạt động

5. Kiểm tra Python package
   - MetaTrader5
   - pandas
   - numpy
   - pytz

6. Kiểm tra OpenClaw
   - Chạy `openclaw status`
   - Chạy `openclaw gateway status`

7. Kiểm tra đường dẫn file
   - `C:\GoldBot\gold_analysis.py`
   - `C:\GoldBot\execute_trade.py`
   - `C:\Users\Administrator\.openclaw\workspace\SOUL.md`
   - `C:\Users\Administrator\.openclaw\workspace\HEARTBEAT.md`

8. Test thủ công sau deploy
   - Chạy `python C:\GoldBot\gold_analysis.py`
   - Kiểm tra có tạo/update JSON không
   - Test tín hiệu vàng / BTC / Forex

9. Kiểm tra Task Scheduler
   - Task `GoldBot_GoldAnalysis`
   - Task `GoldBot_OpenClawHeartbeat`

10. Kiểm tra MT5 symbol availability
   - XAUUSD
   - BTCUSD
   - EURUSD
   - GBPUSD
   - USDJPY
