import MetaTrader5 as mt5
import pandas as pd
import json
import sys
import os
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

WORKSPACE_FILE = 'C:/Users/Administrator/.openclaw/workspace/gold_data.json'
RISK_FILE = 'C:/Users/Administrator/.openclaw/workspace/trading_risk_config.json'
NEWS_FILE = 'C:/Users/Administrator/.openclaw/workspace/news_filter.json'


TIMEFRAME_CONFIG = {
    'M1': mt5.TIMEFRAME_M1,
    'M5': mt5.TIMEFRAME_M5,
    'M15': mt5.TIMEFRAME_M15,
}


def now_vn():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S GMT+7')


def load_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def calc_rsi(closes, period=14):
    if len(closes) <= period:
        return 0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def get_candles(symbol, timeframe, n=10):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    if rates is None or len(rates) == 0:
        return []
    df = pd.DataFrame(rates)
    df.columns = [c.lower() for c in df.columns]
    df['time'] = pd.to_datetime(df['time'], unit='s').astype(str)
    return df[['time', 'open', 'high', 'low', 'close', 'tick_volume']].to_dict('records')


def get_open_positions(symbol):
    positions = mt5.positions_get(symbol=symbol)
    return len(positions) if positions else 0


def get_daily_pnl():
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(today, datetime.now())
    if deals is None:
        return 0
    return sum(d.profit for d in deals)


def news_blocked():
    return False, None


def calc_ema(closes, period):
    if not closes:
        return 0
    k = 2 / (period + 1)
    ema = closes[0]
    for price in closes[1:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 3)


def calc_atr(candles, period=14):
    if len(candles) <= period:
        return 0
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]['high']
        l = candles[i]['low']
        pc = candles[i - 1]['close']
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    return round(sum(trs[-period:]) / period, 3) if trs else 0


def calc_adx(candles, period=14):
    if len(candles) <= period:
        return 0
    plus_dm = []
    minus_dm = []
    for i in range(1, len(candles)):
        h_diff = candles[i]['high'] - candles[i - 1]['high']
        l_diff = candles[i - 1]['low'] - candles[i]['low']
        plus_dm.append(h_diff if h_diff > l_diff and h_diff > 0 else 0)
        minus_dm.append(l_diff if l_diff > h_diff and l_diff > 0 else 0)
    atr_val = calc_atr(candles, period)
    if atr_val == 0:
        return 0
    plus_di = 100 * (sum(plus_dm[-period:]) / period) / atr_val
    minus_di = 100 * (sum(minus_dm[-period:]) / period) / atr_val
    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
    return round(dx, 2)


def find_swing_high(candles, lookback=10):
    highs = [c['high'] for c in candles[-lookback:]]
    return round(max(highs), 3) if highs else 0


def find_swing_low(candles, lookback=10):
    lows = [c['low'] for c in candles[-lookback:]]
    return round(min(lows), 3) if lows else 0


def resolve_symbol(base_symbol):
    candidates = [base_symbol, f'{base_symbol}.s', f'{base_symbol}m', f'{base_symbol}.a', f'{base_symbol}.r']
    for candidate in candidates:
        info = mt5.symbol_info(candidate)
        if info and mt5.symbol_select(candidate, True):
            return candidate
    return base_symbol


def build_timeframe_profile(symbol, timeframe_name, timeframe_mt5, h1_trend, h4_trend, bars=120):
    candles = get_candles(symbol, timeframe_mt5, bars)
    if len(candles) < 20:
        return {
            'ema34': 0,
            'ema89': 0,
            'rsi': 0,
            'atr': 0,
            'adx': 0,
            'swing_high': 0,
            'swing_low': 0,
            'trend_h1': h1_trend,
            'trend_h4': h4_trend,
            'trend': 'UNKNOWN',
            'error': 'NOT_ENOUGH_DATA'
        }

    closes = [c['close'] for c in candles]
    ema34 = calc_ema(closes, 34)
    ema89 = calc_ema(closes, 89)
    return {
        'ema34': ema34,
        'ema89': ema89,
        'rsi': calc_rsi(closes),
        'atr': calc_atr(candles, 14),
        'adx': calc_adx(candles, 14),
        'swing_high': find_swing_high(candles, 10),
        'swing_low': find_swing_low(candles, 10),
        'trend_h1': h1_trend,
        'trend_h4': h4_trend,
        'trend': 'UPTREND' if ema34 > ema89 else 'DOWNTREND'
    }


def build_symbol_package(base_symbol, output_name=None):
    resolved = resolve_symbol(base_symbol)
    tick = mt5.symbol_info_tick(resolved)
    if tick is None:
        return {
            'symbol': resolved,
            'bid': 0.0,
            'ask': 0.0,
            'M1': {'error': 'NO_TICK'},
            'M5': {'error': 'NO_TICK'},
            'M15': {'error': 'NO_TICK'}
        }

    h1_candles = get_candles(resolved, mt5.TIMEFRAME_H1, 120)
    h4_candles = get_candles(resolved, mt5.TIMEFRAME_H4, 120)
    h1_closes = [c['close'] for c in h1_candles]
    h4_closes = [c['close'] for c in h4_candles]
    ema34_h1 = calc_ema(h1_closes, 34)
    ema89_h1 = calc_ema(h1_closes, 89)
    ema34_h4 = calc_ema(h4_closes, 34)
    ema89_h4 = calc_ema(h4_closes, 89)
    h1_trend = 'UPTREND' if ema34_h1 > ema89_h1 else 'DOWNTREND'
    h4_trend = 'UPTREND' if ema34_h4 > ema89_h4 else 'DOWNTREND'

    package = {
        'symbol': resolved,
        'bid': round(tick.bid, 5) if abs(tick.bid) < 1000 else round(tick.bid, 3),
        'ask': round(tick.ask, 5) if abs(tick.ask) < 1000 else round(tick.ask, 3),
    }

    for timeframe_name, timeframe_mt5 in TIMEFRAME_CONFIG.items():
        package[timeframe_name] = build_timeframe_profile(resolved, timeframe_name, timeframe_mt5, h1_trend, h4_trend)

    return package


# Đọc MT5 config
config_path = os.path.join(os.path.dirname(__file__), 'mt5_config.txt')
mt5_login = None
mt5_password = None
mt5_server = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        for line in f:
            if line.startswith('MT5_LOGIN='):
                mt5_login = int(line.strip().split('=')[1])
            elif line.startswith('MT5_PASSWORD='):
                mt5_password = line.strip().split('=')[1]
            elif line.startswith('MT5_SERVER='):
                mt5_server = line.strip().split('=')[1]

if mt5_login and mt5_password and mt5_server:
    if not mt5.initialize(login=mt5_login, password=mt5_password, server=mt5_server):
        print('ERROR: Không kết nối được MT5')
        raise SystemExit(1)
else:
    if not mt5.initialize():
        print('ERROR: Không kết nối được MT5')
        raise SystemExit(1)

symbol = resolve_symbol('XAUUSD')
mt5.symbol_select(symbol, True)
tick = mt5.symbol_info_tick(symbol)
symbol_info = mt5.symbol_info(symbol)

m5 = get_candles(symbol, mt5.TIMEFRAME_M5, 10)
m15 = get_candles(symbol, mt5.TIMEFRAME_M15, 50)
h1 = get_candles(symbol, mt5.TIMEFRAME_H1, 50)
h4 = get_candles(symbol, mt5.TIMEFRAME_H4, 50)
closes_h1 = [c['close'] for c in h1]
closes_h4 = [c['close'] for c in h4]
closes_m15 = [c['close'] for c in m15]
rsi_h1 = calc_rsi(closes_h1)
rsi_h4 = calc_rsi(closes_h4)
rsi_m15 = calc_rsi(closes_m15)
ma20_h1 = round(sum(closes_h1[-20:]) / 20, 2) if len(closes_h1) >= 20 else 0
ma50_h1 = round(sum(closes_h1[-50:]) / 50, 2) if len(closes_h1) >= 50 else 0
trend = 'UPTREND' if ma20_h1 > ma50_h1 else 'DOWNTREND'

m5_full = get_candles(symbol, mt5.TIMEFRAME_M5, 50)
closes_m5 = [c['close'] for c in m5_full]
rsi_m5 = calc_rsi(closes_m5)
ema34_m5 = calc_ema(closes_m5, 34)
ema89_m5 = calc_ema(closes_m5, 89)
atr_m5 = calc_atr(m5_full, 14)
adx_m5 = calc_adx(m5_full, 14)
swing_high_m5 = find_swing_high(m5_full, 10)
swing_low_m5 = find_swing_low(m5_full, 10)
m5_trend = 'UPTREND' if ema34_m5 > ema89_m5 else 'DOWNTREND'

ema34_m15 = calc_ema(closes_m15, 34)
ema89_m15 = calc_ema(closes_m15, 89)
atr_m15 = calc_atr(m15, 14)
adx_m15 = calc_adx(m15, 14)
swing_high_m15 = find_swing_high(m15, 10)
swing_low_m15 = find_swing_low(m15, 10)
m15_trend = 'UPTREND' if ema34_m15 > ema89_m15 else 'DOWNTREND'

ema34_h1 = calc_ema(closes_h1, 34)
ema89_h1 = calc_ema(closes_h1, 89)
h1_trend = 'UPTREND' if ema34_h1 > ema89_h1 else 'DOWNTREND'

ema34_h4 = calc_ema(closes_h4, 34)
ema89_h4 = calc_ema(closes_h4, 89)
h4_trend = 'UPTREND' if ema34_h4 > ema89_h4 else 'DOWNTREND'

cfg = load_json(RISK_FILE, {'account_balance': 1000, 'gold': {'default_risk_percent': 2, 'fallback_lot': 0.01, 'sl_points_default': 25, 'tp_points_default': 50, 'max_positions': 3, 'max_daily_loss': 50}})
gold_cfg = cfg.get('gold', {})
sl_points = gold_cfg.get('sl_points_default', 25)
tp_points = gold_cfg.get('tp_points_default', 50)
risk_percent = gold_cfg.get('default_risk_percent', cfg.get('default_risk_percent', 2))
fallback_lot = gold_cfg.get('fallback_lot', 0.01)
blocked, event_name = news_blocked()

xau_package = build_symbol_package('XAUUSD')
eurusd_package = build_symbol_package('EURUSD')
gbpusd_package = build_symbol_package('GBPUSD')
usdjpy_package = build_symbol_package('USDJPY')
btc_package = build_symbol_package('BTCUSD')

result = {
    'timestamp': now_vn(),
    'symbol': symbol,
    'bid': tick.bid,
    'ask': tick.ask,
    'spread': round(tick.ask - tick.bid, 2),
    'rsi_h1': rsi_h1,
    'rsi_h4': rsi_h4,
    'ma20_h1': ma20_h1,
    'ma50_h1': ma50_h1,
    'trend': trend,
    'risk_percent': risk_percent,
    'news_blocked': blocked,
    'news_event': event_name,
    'candles': {'m5': m5, 'm15': m15[-10:], 'h1': h1[-10:], 'h4': h4[-10:]},
    'm5': {
        'ema34': ema34_m5,
        'ema89': ema89_m5,
        'rsi': rsi_m5,
        'atr': atr_m5,
        'adx': adx_m5,
        'swing_high': swing_high_m5,
        'swing_low': swing_low_m5,
        'trend': m5_trend
    },
    'm15': {
        'ema34': ema34_m15,
        'ema89': ema89_m15,
        'rsi': rsi_m15,
        'atr': atr_m15,
        'adx': adx_m15,
        'swing_high': swing_high_m15,
        'swing_low': swing_low_m15,
        'trend': m15_trend,
        'h1_ema34': ema34_h1,
        'h1_ema89': ema89_h1,
        'h1_trend': h1_trend,
        'h4_trend': h4_trend
    },
    'XAUUSD': xau_package,
    'EURUSD': eurusd_package,
    'GBPUSD': gbpusd_package,
    'USDJPY': usdjpy_package,
    'BTC': btc_package
}

daily_pnl = get_daily_pnl()
open_pos = get_open_positions(symbol)
if blocked:
    result['auto_trade'] = f'❌ DỪNG — Gần tin mạnh: {event_name}'
elif daily_pnl <= -gold_cfg.get('max_daily_loss', 50):
    result['auto_trade'] = f"❌ DỪNG — Đã thua quá ${gold_cfg.get('max_daily_loss', 50)} hôm nay"
elif open_pos >= gold_cfg.get('max_positions', 3):
    result['auto_trade'] = f'⏸️ CHỜ — Đang có {open_pos} lệnh vàng mở'
else:
    if rsi_h1 > 65 and ma20_h1 < ma50_h1:
        entry = tick.bid
        sl = round(tick.ask + sl_points, 2)
        tp = round(tick.bid - tp_points, 2)
        risk_calc = {'lot': fallback_lot}
        result['suggested_lot'] = risk_calc['lot']
        result['auto_trade'] = '⏳ CHỜ XÁC NHẬN TỪ BẠN'
        result['pending_signal'] = {'action': 'SELL', 'entry': entry, 'sl': sl, 'tp': tp, 'rsi_h1': rsi_h1, 'rsi_h4': rsi_h4, 'trend': trend, 'confidence': '75%', 'lot': risk_calc['lot']}
    elif rsi_h1 < 35 and ma20_h1 > ma50_h1:
        entry = tick.ask
        sl = round(tick.bid - sl_points, 2)
        tp = round(tick.ask + tp_points, 2)
        risk_calc = {'lot': fallback_lot}
        result['suggested_lot'] = risk_calc['lot']
        result['auto_trade'] = '⏳ CHỜ XÁC NHẬN TỪ BẠN'
        result['pending_signal'] = {'action': 'BUY', 'entry': entry, 'sl': sl, 'tp': tp, 'rsi_h1': rsi_h1, 'rsi_h4': rsi_h4, 'trend': trend, 'confidence': '75%', 'lot': risk_calc['lot']}
    else:
        result['suggested_lot'] = fallback_lot
        result['auto_trade'] = f'⏸️ HOLD — RSI H1: {rsi_h1} | Trend: {trend} | Chưa đủ điều kiện'

with open(WORKSPACE_FILE, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(json.dumps(result, indent=2, ensure_ascii=False))
mt5.shutdown()
