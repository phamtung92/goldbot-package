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


def now_vn():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S GMT+7')


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def pick_signal(data):
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

symbol = data['symbol']
mt5.symbol_select(symbol, True)
tick = mt5.symbol_info_tick(symbol)
price = tick.ask if action == 'BUY' else tick.bid
order_type = mt5.ORDER_TYPE_BUY if action == 'BUY' else mt5.ORDER_TYPE_SELL

symbol_info = mt5.symbol_info(symbol)
filling_mode = symbol_info.filling_mode
if filling_mode & mt5.ORDER_FILLING_FOK:
    filling = mt5.ORDER_FILLING_FOK
elif filling_mode & mt5.ORDER_FILLING_IOC:
    filling = mt5.ORDER_FILLING_IOC
else:
    filling = mt5.ORDER_FILLING_RETURN

print(f'🔧 Filling mode detected: {filling}')
print(f'📌 Signal source: {source}')

request = {
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
    'type_filling': filling,
}
result = mt5.order_send(request)
if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
    msg = f"❌ Lỗi đặt lệnh: {result.comment if result else mt5.last_error()}"
else:
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
