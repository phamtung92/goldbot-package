import MetaTrader5 as mt5
import json
import sys
import os
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

WORKSPACE_FILE = 'C:/Users/Administrator/.openclaw/workspace/forex_pending_signals.json'


def now_vn():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S GMT+7')


def load_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {} if default is None else default


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def detect_filling(symbol_info):
    filling_mode = symbol_info.filling_mode
    if filling_mode & mt5.ORDER_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    if filling_mode & mt5.ORDER_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def place_trade(signal):
    symbol = signal['symbol']
    action = signal['action']
    volume = float(signal['lot'])
    sl = float(signal['sl'])
    tp = float(signal['tp'])

    if not mt5.symbol_select(symbol, True):
        return {'ok': False, 'error': f'Không select được symbol {symbol}'}

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {'ok': False, 'error': f'Không lấy được tick cho {symbol}'}

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return {'ok': False, 'error': f'Không lấy được symbol info cho {symbol}'}

    if action == 'BUY':
        price = tick.ask
        order_type = mt5.ORDER_TYPE_BUY
    else:
        price = tick.bid
        order_type = mt5.ORDER_TYPE_SELL

    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': symbol,
        'volume': volume,
        'type': order_type,
        'price': price,
        'sl': sl,
        'tp': tp,
        'deviation': 20,
        'magic': 234001,
        'comment': 'GoldBot',
        'type_time': mt5.ORDER_TIME_GTC,
        'type_filling': detect_filling(symbol_info),
    }

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        return {'ok': False, 'error': result.comment if result else str(mt5.last_error())}

    verified = mt5.positions_get(ticket=result.order)
    return {
        'ok': True,
        'ticket': int(result.order),
        'price': result.price,
        'symbol': symbol,
        'action': action,
        'lot': volume,
        'sl': sl,
        'tp': tp,
        'verified': bool(verified and len(verified) > 0)
    }


if not mt5.initialize():
    print('❌ Không kết nối được MT5')
    sys.exit(1)

pending = load_json(WORKSPACE_FILE, {'signals': []})
signals = pending.get('signals', [])
if not signals:
    print('❌ Không có pending forex signal!')
    mt5.shutdown()
    sys.exit(1)

results = []
remaining = []
for signal in signals:
    if signal.get('confirmed') is True:
        res = place_trade(signal)
        results.append(res)
    else:
        remaining.append(signal)

pending['signals'] = remaining
save_json(WORKSPACE_FILE, pending)

print(json.dumps({'timestamp': now_vn(), 'results': results}, indent=2, ensure_ascii=False))
mt5.shutdown()
