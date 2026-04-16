import MetaTrader5 as mt5
import json
import sys
from datetime import datetime
from symbol_utils import resolve_symbol
from gold_trade_logger import update_trade

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

WORKSPACE_FILE = 'C:/Users/Administrator/.openclaw/workspace/gold_data.json'


def now_vn():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S GMT+7')


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def close_position(ticket):
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return {'ok': False, 'error': f'Không tìm thấy lệnh ticket {ticket}'}

    pos = positions[0]
    symbol = pos.symbol
    volume = pos.volume
    order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {'ok': False, 'error': f'Không lấy được tick cho {symbol}'}

    price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

    symbol_info = mt5.symbol_info(symbol)
    fill_candidates = [
        ('FOK', mt5.ORDER_FILLING_FOK),
        ('IOC', mt5.ORDER_FILLING_IOC),
        ('RETURN', mt5.ORDER_FILLING_RETURN),
    ]

    result = None
    last_error = None
    for filling_name, filling in fill_candidates:
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': volume,
            'type': order_type,
            'position': ticket,
            'price': price,
            'deviation': 20,
            'magic': 234000,
            'comment': 'GoldBot Close',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': filling,
        }
        res = mt5.order_send(request)
        if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
            result = res
            break
        last_error = res.comment if res else str(mt5.last_error())

    if result is None:
        return {'ok': False, 'error': last_error}

    profit = pos.profit
    update_trade(ticket, {
        'status': 'closed',
        'closed_at': now_vn(),
        'close_price': price,
        'profit': profit
    })

    return {
        'ok': True,
        'ticket': ticket,
        'symbol': symbol,
        'volume': volume,
        'close_price': price,
        'profit': round(profit, 2)
    }


def close_partial(ticket, volume):
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return {'ok': False, 'error': f'Không tìm thấy lệnh ticket {ticket}'}

    pos = positions[0]
    symbol = pos.symbol
    order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {'ok': False, 'error': f'Không lấy được tick cho {symbol}'}

    price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

    fill_candidates = [
        ('FOK', mt5.ORDER_FILLING_FOK),
        ('IOC', mt5.ORDER_FILLING_IOC),
        ('RETURN', mt5.ORDER_FILLING_RETURN),
    ]

    result = None
    last_error = None
    for filling_name, filling in fill_candidates:
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': round(volume, 2),
            'type': order_type,
            'position': ticket,
            'price': price,
            'deviation': 20,
            'magic': 234000,
            'comment': 'GoldBot Partial Close',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': filling,
        }
        res = mt5.order_send(request)
        if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
            result = res
            break
        last_error = res.comment if res else str(mt5.last_error())

    if result is None:
        return {'ok': False, 'error': last_error}

    return {
        'ok': True,
        'ticket': ticket,
        'symbol': symbol,
        'closed_volume': round(volume, 2),
        'close_price': price
    }


if not mt5.initialize():
    print('❌ Không kết nối được MT5')
    sys.exit(1)

# Đọc lệnh từ gold_data.json
try:
    data = load_json(WORKSPACE_FILE)
    close_cmd = data.get('close_command', {})
except Exception:
    close_cmd = {}

if not close_cmd:
    print('❌ Không có close_command trong gold_data.json')
    mt5.shutdown()
    sys.exit(1)

action = close_cmd.get('action')
ticket = close_cmd.get('ticket')
volume = close_cmd.get('volume')

if action == 'close_all':
    positions = mt5.positions_get()
    if not positions:
        print('ℹ️ Không có lệnh nào đang mở')
    else:
        for pos in positions:
            res = close_position(pos.ticket)
            if res['ok']:
                print(f"✅ Đóng {res['symbol']} ticket {res['ticket']} | Giá: {res['close_price']} | PnL: ${res['profit']}")
            else:
                print(f"❌ Lỗi đóng ticket {pos.ticket}: {res['error']}")

elif action == 'close' and ticket:
    res = close_position(int(ticket))
    if res['ok']:
        print(f"✅ Đóng {res['symbol']} ticket {res['ticket']} | Giá: {res['close_price']} | PnL: ${res['profit']}")
    else:
        print(f"❌ Lỗi: {res['error']}")

elif action == 'close_partial' and ticket and volume:
    res = close_partial(int(ticket), float(volume))
    if res['ok']:
        print(f"✅ Chốt {res['closed_volume']} lot {res['symbol']} ticket {res['ticket']} | Giá: {res['close_price']}")
    else:
        print(f"❌ Lỗi: {res['error']}")

else:
    print(f'❌ Lệnh không hợp lệ: {close_cmd}')

# Xóa close_command sau khi xử lý
try:
    data.pop('close_command', None)
    save_json(WORKSPACE_FILE, data)
except Exception:
    pass

mt5.shutdown()