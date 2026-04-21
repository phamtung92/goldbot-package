import MetaTrader5 as mt5
import json
import sys
from datetime import datetime
from symbol_utils import resolve_symbol

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BROKER_CONFIG_FILE = 'C:/GoldBot/broker_config.json'

BASE_PAIRS = {
    'XAUUSD': ['XAUUSD', 'GOLD'],
    'EURUSD': ['EURUSD'],
    'GBPUSD': ['GBPUSD'],
    'USDJPY': ['USDJPY'],
    'BTCUSD': ['BTCUSD', 'BTCUSDT', 'XBTUSD'],
    'UKOIL': ['UKOUSDft', 'UKOUSD', 'UKOIL', 'BCO', 'BRENT'],
    'XAGUSD': ['XAGUSD', 'SILVER', 'XAG'],
}


def get_symbol_info(real_symbol):
    info = mt5.symbol_info(real_symbol)
    if info is None:
        return None
    return {
        'real_symbol': real_symbol,
        'tick_value': round(info.trade_tick_value, 6),
        'tick_size': round(info.trade_tick_size, 6),
        'contract_size': info.trade_contract_size,
        'volume_step': info.volume_step,
        'volume_min': info.volume_min,
    }


if not mt5.initialize():
    print('❌ Không kết nối được MT5')
    sys.exit(1)

terminal_info = mt5.terminal_info()
broker_name = terminal_info.company if terminal_info else 'Unknown'

symbols = {}
errors = []

for base, aliases in BASE_PAIRS.items():
    real = resolve_symbol(base)
    if real is None:
        errors.append(f'❌ Không tìm được symbol cho {base}')
        continue
    info = get_symbol_info(real)
    if info is None:
        errors.append(f'❌ Không lấy được info cho {real}')
        continue
    symbols[base] = info
    print(f'✅ {base} → {real} (tick_value={info["tick_value"]}, tick_size={info["tick_size"]})')

config = {
    'broker': broker_name,
    'detected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'symbols': symbols,
}

with open(BROKER_CONFIG_FILE, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print(f'\n✅ Đã lưu broker_config.json — Broker: {broker_name}')
if errors:
    for e in errors:
        print(e)

mt5.shutdown()