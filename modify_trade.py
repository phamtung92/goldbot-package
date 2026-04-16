import MetaTrader5 as mt5
import json
import sys
from datetime import datetime

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


def modify_position(ticket, sl=None, tp=None):
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return {'ok': False, 'error': f'Không tìm thấy lệnh ticket {ticket}'}

    pos = positions[0]
    new_sl = float(sl) if sl is not None else pos.sl
    new_tp = float(tp) if tp is not None else pos.tp

    request = {
        'action': mt5.TRADE_ACTION_SLTP,
        'symbol': pos.symbol,
        'position': ticket,
        'sl': new_sl,
        'tp': new_tp,
    }

    res = mt5.order_send(request)
    if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
        error = res.comment if res else str(mt5.last_error())
        return {'ok': False, 'error': error}

    return {
        'ok': True,
        'ticket': ticket,
        'symbol': pos.symbol,
        'new_sl': new_sl,
        'new_tp': new_tp
    }


def breakeven(ticket):
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return {'ok': False, 'error': f'Không tìm thấy lệnh ticket {ticket}'}

    pos = positions[0]
    entry = pos.price_open
    symbol_info = mt5.symbol_info(pos.symbol)
    spread = symbol_info.spread * symbol_info.point if symbol_info else 0

    # SL về hòa vốn = entry + spread nhỏ để cover phí
    if pos.type == mt5.ORDER_TYPE_BUY:
        new_sl = round(entry + spread, symbol_info.digits if symbol_info else 3)
    else:
        new_sl = round(entry - spread, symbol_info.digits if symbol_info else 3)

    return modify_position(ticket, sl=new_sl)


if not mt5.initialize():
    print('❌ Không kết nối được MT5')
    sys.exit(1)

try:
    data = load_json(WORKSPACE_FILE)
    modify_cmd = data.get('modify_command', {})
except Exception:
    modify_cmd = {}

if not modify_cmd:
    print('❌ Không có modify_command trong gold_data.json')
    mt5.shutdown()
    sys.exit(1)

action = modify_cmd.get('action')
ticket = modify_cmd.get('ticket')
sl = modify_cmd.get('sl')
tp = modify_cmd.get('tp')

if action == 'breakeven' and ticket:
    res = breakeven(int(ticket))
    if res['ok']:
        print(f"✅ Dời SL về hòa vốn {res['symbol']} ticket {res['ticket']} | SL mới: {res['new_sl']}")
    else:
        print(f"❌ Lỗi: {res['error']}")

elif action == 'modify_sl' and ticket and sl:
    res = modify_position(int(ticket), sl=sl)
    if res['ok']:
        print(f"✅ Dời SL {res['symbol']} ticket {res['ticket']} | SL mới: {res['new_sl']}")
    else:
        print(f"❌ Lỗi: {res['error']}")

elif action == 'modify_tp' and ticket and tp:
    res = modify_position(int(ticket), tp=tp)
    if res['ok']:
        print(f"✅ Dời TP {res['symbol']} ticket {res['ticket']} | TP mới: {res['new_tp']}")
    else:
        print(f"❌ Lỗi: {res['error']}")

elif action == 'modify_sltp' and ticket:
    res = modify_position(int(ticket), sl=sl, tp=tp)
    if res['ok']:
        print(f"✅ Sửa SL/TP {res['symbol']} ticket {res['ticket']} | SL: {res['new_sl']} | TP: {res['new_tp']}")
    else:
        print(f"❌ Lỗi: {res['error']}")

else:
    print(f'❌ Lệnh không hợp lệ: {modify_cmd}')

try:
    data.pop('modify_command', None)
    save_json(WORKSPACE_FILE, data)
except Exception:
    pass

mt5.shutdown()