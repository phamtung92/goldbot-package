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
    return round(ema, 6)


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
    return round(sum(trs[-period:]) / period, 6) if trs else 0


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


def build_timeframe_profile_btc(symbol, timeframe_name, timeframe_mt5, h1_trend, h4_trend, bars=120):
    """Profile riêng cho BTC: lookback dài hơn, ngưỡng ADX cao hơn"""
    candles = get_candles(symbol, timeframe_mt5, bars)
    if len(candles) < 20:
        return {
            'ema34': 0, 'ema89': 0, 'rsi': 0, 'atr': 0, 'adx': 0,
            'swing_high': 0, 'swing_low': 0,
            'trend_h1': h1_trend, 'trend_h4': h4_trend,
            'trend': 'UNKNOWN', 'volume_ratio': 1.0,
            'error': 'NOT_ENOUGH_DATA'
        }

    closes = [c['close'] for c in candles]
    ema34 = calc_ema(closes, 34)
    ema89 = calc_ema(closes, 89)
    # BTC dùng lookback 25 nến thay vì 10 để tránh noise
    swing_high = find_swing_high(candles, 25)
    swing_low = find_swing_low(candles, 25)
    current_close = closes[-1]
    trend = 'UPTREND' if ema34 > ema89 else 'DOWNTREND'

    price_range = swing_high - swing_low
    price_from_low = (current_close - swing_low) / price_range if price_range > 0 else 0.5

    in_pullback_sell = trend == 'DOWNTREND' and price_from_low > 0.6
    in_pullback_buy = trend == 'UPTREND' and price_from_low < 0.4

    adx = calc_adx(candles, 14)
    # BTC cần ADX > 25 mới đủ trend mạnh
    btc_adx_weak = adx < 25

    return {
        'ema34': ema34,
        'ema89': ema89,
        'rsi': calc_rsi(closes),
        'atr': calc_atr(candles, 14),
        'adx': adx,
        'swing_high': swing_high,
        'swing_low': swing_low,
        'trend_h1': h1_trend,
        'trend_h4': h4_trend,
        'trend': trend,
        'volume_ratio': calc_volume_ratio(candles),
        'price_from_low': round(price_from_low, 2),
        'in_pullback_sell': in_pullback_sell,
        'in_pullback_buy': in_pullback_buy,
        'btc_adx_weak': btc_adx_weak,
    }

from symbol_utils import resolve_symbol


def calc_volume_ratio(candles, period=20):
    """Tỷ lệ volume nến hiện tại so với trung bình — phát hiện breakout có volume"""
    if len(candles) < period + 1:
        return 1.0
    volumes = [c['tick_volume'] for c in candles]
    avg_vol = sum(volumes[-period-1:-1]) / period
    current_vol = volumes[-1]
    if avg_vol == 0:
        return 1.0
    return round(current_vol / avg_vol, 2)


def get_key_levels(symbol):
    """Lấy daily/weekly high-low làm key levels cho TP target"""
    try:
        daily = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 10)
        if daily is None or len(daily) < 2:
            return {}
        today_high = round(float(daily[-1]['high']), 5)
        today_low = round(float(daily[-1]['low']), 5)
        prev_day_high = round(float(daily[-2]['high']), 5)
        prev_day_low = round(float(daily[-2]['low']), 5)

        weekly = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_W1, 0, 4)
        if weekly is None or len(weekly) < 2:
            prev_week_high = prev_week_low = 0
        else:
            prev_week_high = round(float(weekly[-2]['high']), 5)
            prev_week_low = round(float(weekly[-2]['low']), 5)

        return {
            'today_high': today_high,
            'today_low': today_low,
            'prev_day_high': prev_day_high,
            'prev_day_low': prev_day_low,
            'prev_week_high': prev_week_high,
            'prev_week_low': prev_week_low,
        }
    except Exception:
        return {}


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
            'volume_ratio': 1.0,
            'error': 'NOT_ENOUGH_DATA'
        }

    closes = [c['close'] for c in candles]
    ema34 = calc_ema(closes, 34)
    ema89 = calc_ema(closes, 89)
    swing_high = find_swing_high(candles, 10)
    swing_low = find_swing_low(candles, 10)
    current_close = closes[-1]
    trend = 'UPTREND' if ema34 > ema89 else 'DOWNTREND'

    # Phát hiện sóng hồi — cả 2 chiều
    price_range = swing_high - swing_low
    price_from_low = (current_close - swing_low) / price_range if price_range > 0 else 0.5

    # DOWNTREND nhưng giá hồi lên cao → sóng hồi tăng, không nên SELL
    in_pullback_sell = trend == 'DOWNTREND' and price_from_low > 0.6

    # UPTREND nhưng giá hồi xuống thấp → sóng hồi giảm, không nên BUY
    in_pullback_buy = trend == 'UPTREND' and price_from_low < 0.4

    # Phát hiện overextended — giá chạy quá xa EMA34 (> 1.5x ATR)
    atr_val = calc_atr(candles, 14)
    dist_from_ema34 = abs(current_close - ema34)
    overextended_threshold = 1.5 * atr_val if atr_val > 0 else 0
    overextended_buy = (current_close < ema34 and dist_from_ema34 > overextended_threshold)
    overextended_sell = (current_close > ema34 and dist_from_ema34 > overextended_threshold)

    return {
        'ema34': ema34,
        'ema89': ema89,
        'rsi': calc_rsi(closes),
        'atr': atr_val,
        'adx': calc_adx(candles, 14),
        'swing_high': swing_high,
        'swing_low': swing_low,
        'trend_h1': h1_trend,
        'trend_h4': h4_trend,
        'trend': trend,
        'volume_ratio': calc_volume_ratio(candles),
        'price_from_low': round(price_from_low, 2),
        'in_pullback_sell': in_pullback_sell,
        'in_pullback_buy': in_pullback_buy,
        'overextended_buy': overextended_buy,
        'overextended_sell': overextended_sell,
    }


def build_symbol_package(base_symbol, output_name=None):
    resolved = resolve_symbol(base_symbol)
    if resolved:
        mt5.symbol_select(resolved, True)
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

    # RSI H1 divergence — so sánh RSI 3 nến H1 gần nhất vs xu hướng giá
    rsi_h1_divergence = None
    if len(h1_closes) >= 20:
        rsi_h1_c = calc_rsi(h1_closes)           # nến hiện tại
        rsi_h1_p1 = calc_rsi(h1_closes[:-1])     # 1 nến trước
        rsi_h1_p2 = calc_rsi(h1_closes[:-2])     # 2 nến trước
        rsi_h1_rising = rsi_h1_c > rsi_h1_p1 > rsi_h1_p2
        rsi_h1_falling = rsi_h1_c < rsi_h1_p1 < rsi_h1_p2
        # Bearish divergence: giá H1 tăng nhưng RSI H1 giảm
        if h1_trend == 'UPTREND' and rsi_h1_falling:
            rsi_h1_divergence = 'BEARISH'
        # Bullish divergence: giá H1 giảm nhưng RSI H1 tăng
        elif h1_trend == 'DOWNTREND' and rsi_h1_rising:
            rsi_h1_divergence = 'BULLISH'

    package = {
        'symbol': resolved,
        'bid': round(tick.bid, 5) if abs(tick.bid) < 1000 else round(tick.bid, 3),
        'ask': round(tick.ask, 5) if abs(tick.ask) < 1000 else round(tick.ask, 3),
        'key_levels': get_key_levels(resolved),
        'rsi_h1_divergence': rsi_h1_divergence,
    }

    for timeframe_name, timeframe_mt5 in TIMEFRAME_CONFIG.items():
        # BTC dùng hàm riêng với lookback dài hơn và ngưỡng ADX cao hơn
        if 'BTC' in base_symbol.upper():
            package[timeframe_name] = build_timeframe_profile_btc(resolved, timeframe_name, timeframe_mt5, h1_trend, h4_trend)
        else:
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
ukoil_package = build_symbol_package('UKOIL')
xagusd_package = build_symbol_package('XAGUSD')

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
    'BTC': btc_package,
    'UKOIL': ukoil_package,
    'XAGUSD': xagusd_package,
}

daily_pnl = get_daily_pnl()
open_pos = get_open_positions(symbol)
if blocked:
    result['auto_trade'] = f'❌ DỪNG — Gần tin mạnh: {event_name}'
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