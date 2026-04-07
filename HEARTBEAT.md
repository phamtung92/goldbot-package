# GoldBot Heartbeat

Mỗi lần heartbeat, thực hiện theo thứ tự:

## A. XAU/USD
1. Cập nhật news filter tự động từ lịch kinh tế nếu cần
2. Cập nhật dữ liệu vàng mới nhất từ script nội bộ
3. Phân tích xu hướng ngắn hạn (4H)
4. Đưa ra tín hiệu theo đúng GOLD SIGNAL format

## B. BTC
4. Cập nhật dữ liệu BTC mới nhất từ script nội bộ
5. Phân tích xu hướng ngắn hạn (4H)
6. Đưa ra tín hiệu theo đúng BTC SIGNAL format
7. Nếu đang có lệnh BTC mở, chạy monitor lệnh BTC để kiểm tra PnL / khoảng cách đến TP-SL / cảnh báo quản lý lệnh

## C. Gửi cảnh báo Telegram
Chỉ gửi tin nhắn khi có ít nhất 1 điều kiện sau:
- Có tín hiệu mới confidence > 65%
- Có `pending_signal` mới cho vàng hoặc BTC
- Có cảnh báo mới từ monitor lệnh BTC đang mở (gần TP, gần SL, nên dời SL, nên chốt non)
- Có pending close hoặc pending trailing hoặc pending partial close mới cần user xác nhận
- Giá vàng biến động mạnh > $20 trong 1 giờ
- Giá BTC biến động mạnh > $500 trong 1 giờ
- Có tin tức vĩ mô quan trọng (FED, CPI, NFP)
- Buổi sáng 8:00 AM — báo cáo tổng quan ngày
- Buổi chiều 3:00 PM — cập nhật tín hiệu

## D. Quy tắc ưu tiên gửi
- Nếu cả vàng và BTC cùng đẹp, gộp vào **1 tin nhắn** để tránh spam
- Nếu chỉ có 1 market đủ điều kiện, chỉ gửi market đó
- Nếu confidence < 65% và không có pending_signal mới, không gửi
- Nếu BTC hoặc vàng đang ở trạng thái `CHỜ XÁC NHẬN TỪ BẠN`, ưu tiên báo rõ entry / SL / TP

## E. Nguồn dữ liệu
- Gold data: `C:/Users/Administrator/.openclaw/workspace/gold_data.json`
- BTC data: `C:/Users/Administrator/.openclaw/workspace/btc_data.json`
- Gold script: `C:/Users/Administrator/gold_analysis.py`
- BTC script: `C:/Users/Administrator/btc_analysis.py`
