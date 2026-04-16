import MetaTrader5 as mt5
import json
import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BROKER_CONFIG = 'C:/GoldBot/broker_config.json'

PAIR_MAP = {
    'v': 'XAUUSD',
    'b': 'BTCUSD',
    'eu': 'EURUSD',
    'uj': 'USDJPY',
    'gb': 'GBPUSD',
    'XAUUSD': 'XAUUSD',
    'BTCUSD': 'BTCUSD',
    'EURUSD': 'EURUSD',
    'USDJPY': 'USDJPY',
    'GBPUSD': 'GBPUSD',
}


def load_broker_config():
    with open(BROKER_CONFIG, 'r', encoding='utf-8') as f:
        return json.load(f)


def calc_lot(pair_key, risk_usd, entry, sl):
    config = load_broker_config()
    base = PAIR_MAP.get(pair_key.lower()) or PAIR_MAP.get(pair_key.upper())
    if not base:
        print(f'❌ Không nhận ra cặp: {pair_key}')
        sys.exit(1)

    sym_data = config['symbols'].get(base)
    if not sym_data:
        print(f'❌ Không tìm thấy {base} trong broker_config.json')
        sys.exit(1)

    real_symbol = sym_data['real_symbol']
    tick_value = sym_data['tick_value']
    tick_size = sym_data['tick_size']
    volume_min = sym_data['volume_min']

    if not mt5.initialize():
        print('❌ Không kết nối được MT5')
        sys.exit(1)

    tick = mt5.symbol_info_tick(real_symbol)
    if tick is None:
        print(f'❌ Không lấy được tick cho {real_symbol}')
        mt5.shutdown()
        sys.exit(1)

    spread = round(tick.ask - tick.bid, 6)
    sl_distance = abs(entry - sl)
    sl_distance_real = sl_distance + spread
    sl_ticks = sl_distance_real / tick_size
    risk_per_lot = sl_ticks * tick_value
    lot = risk_usd / risk_per_lot
    lot = max(round(lot - 0.005, 2), volume_min)  # làm tròn xuống
    risk_actual = round(lot * risk_per_lot, 2)

    result = {
        'pair': base,
        'real_symbol': real_symbol,
        'entry': entry,
        'sl': sl,
        'risk_usd': risk_usd,
        'spread': spread,
        'sl_distance': round(sl_distance, 6),
        'sl_distance_real': round(sl_distance_real, 6),
        'sl_ticks': round(sl_ticks, 2),
        'tick_value': tick_value,
        'tick_size': tick_size,
        'risk_per_lot': round(risk_per_lot, 4),
        'lot': lot,
        'risk_actual': risk_actual
    }

    print(json.dumps(result, ensure_ascii=False))
    mt5.shutdown()


# Usage: calc_lot.py <pair> <risk_usd> <entry> <sl>
# Example: calc_lot.py uj 40 158.932 158.869
if len(sys.argv) != 5:
    print('Usage: calc_lot.py <pair> <risk_usd> <entry> <sl>')
    print('Pairs: v, b, eu, uj, gb')
    sys.exit(1)

pair = sys.argv[1]
risk_usd = float(sys.argv[2])
entry = float(sys.argv[3])
sl = float(sys.argv[4])

calc_lot(pair, risk_usd, entry, sl)