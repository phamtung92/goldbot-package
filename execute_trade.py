import MetaTrader5 as mt5
import json
import sys
from datetime import datetime
from gold_trade_logger import append_trade

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

WORKSPACE_FILE = 'C:/Users/Administrator/.openclaw/workspace/gold_data.json'
M1_SIGNAL_FILE = 'C:/Users/Administrator/.openclaw/workspace/gold_m1_prompt_signal.json'


from symbol_utils import resolve_symbol, broker_safe_stops


def now_vn():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S GMT+7')


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def pick_signal(data):
    if 'last_confirmed_signal' in data:
        signal = data['last_confirmed_signal']
        if all(k in signal for k in ('action', 'sl', 'tp')):
            if 'lot' not in signal:
                signal['lot'] = 0.01
            signal['_source'] = 'last_confirmed_signal'
            data['pending_signal'] = {
                'action': signal['action'],
                'entry': signal.get('entry'),
                'sl': signal['sl'],
                'tp': signal['tp'],
                'lot': signal.get('lot', 0.01),
                'symbol': signal.get('symbol', data.get('symbol', 'XAUUSD'))
            }
            return signal
    if 'pending_m1_signal' in data:
        signal = data['pending_m1_signal']
        signal['_source'] = 'pending_m1_signal'
        return signal
    if 'pending_signal' in data:
        signal = data['pending_signal']
        signal['_source'] = 'pending_signal'
        return signal
    try:
        m1 = load_json(M1_SIGNAL_FILE)
        if m1.get('order') in ('BUY', 'SELL'):
            signal = {
                'action': m1['order'],
                'entry': m1['entry'],
                'sl': m1['sl'],
                'tp': m1['tp'],
                'lot': 0.01,
                '_source': 'gold_m1_prompt_signal.json'
            }
            return signal
    except Exception:
        pass
    return None


data = load_json(WORKSPACE_FILE)
signal = pick_signal(data)

if not signal:
    print('❌ Không có pending signal!')
    sys.exit(1)

action = signal['action']
sl = signal['sl']
tp = signal['tp']
volume = signal.get('lot', 0.01)
source = signal.get('_source', 'unknown')

if not mt5.initialize():
    print('❌ Không kết nối được MT5')
    sys.exit(1)

raw_symbol = signal.get('symbol')
if not raw_symbol:
    print('❌ last_confirmed_signal thiếu field "symbol"! Không thể đặt lệnh.')
    print(f'   Signal hiện tại: {json.dumps(signal, ensure_ascii=False)}')
    mt5.shutdown()
    sys.exit(1)
symbol = resolve_symbol(raw_symbol)
if not symbol:
    print(f'❌ Không resolve được symbol: {raw_symbol}')
    mt5.shutdown()
    sys.exit(1)

tick = mt5.symbol_info_tick(symbol)
if tick is None:
    print(f'❌ Không lấy được tick cho {symbol}')
    mt5.shutdown()
    sys.exit(1)

price = tick.ask if action == 'BUY' else tick.bid
sl, tp = broker_safe_stops(symbol, price, float(sl), float(tp), action)
order_type = mt5.ORDER_TYPE_BUY if action == 'BUY' else mt5.ORDER_TYPE_SELL

symbol_info = mt5.symbol_info(symbol)
fill_candidates = [
    ('FOK', mt5.ORDER_FILLING_FOK),
    ('IOC', mt5.ORDER_FILLING_IOC),
    ('RETURN', mt5.ORDER_FILLING_RETURN),
]

print(f'📌 Signal source: {source}')

base_request = {
    'action': mt5.TRADE_ACTION_DEAL,
    'symbol': symbol,
    'volume': volume,
    'type': order_type,
    'price': price,
    'sl': sl,
    'tp': tp,
    'deviation': 20,
    'magic': 234000,
    'comment': 'GoldBot',
    'type_time': mt5.ORDER_TIME_GTC,
}

result = None
used_filling_name = None
last_error_msg = None
for filling_name, filling in fill_candidates:
    request = dict(base_request)
    request['type_filling'] = filling
    test_result = mt5.order_send(request)
    if test_result is not None and test_result.retcode == mt5.TRADE_RETCODE_DONE:
        result = test_result
        used_filling_name = filling_name
        break
    last_error_msg = test_result.comment if test_result else str(mt5.last_error())

if result is None:
    msg = f"❌ Lỗi đặt lệnh: {last_error_msg}"
else:
    print(f'🔧 Filling mode dùng thành công: {used_filling_name}')
    msg = f"✅ Đặt lệnh {action} thành công! Ticket: {result.order} | Giá: {price} | SL: {sl} | TP: {tp} | Lot: {volume} | Source: {source}"
    append_trade({
        'ticket': int(result.order),
        'market': 'GOLD',
        'symbol': symbol,
        'action': action,
        'entry': round(price, 2),
        'sl': sl,
        'tp': tp,
        'volume': volume,
        'opened_at': now_vn(),
        'status': 'open',
        'profit': 0,
        'signal_source': source
    })
    if source in data:
        del data[source]
    elif source == 'gold_m1_prompt_signal.json':
        pass
    if source == 'pending_m1_signal' and 'pending_signal' in data:
        data['auto_trade'] = msg + ' | M1 được ưu tiên hơn pending_signal thường'
    else:
        data['auto_trade'] = msg
    save_json(WORKSPACE_FILE, data)
print(msg)
mt5.shutdown()
