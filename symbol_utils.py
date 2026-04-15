import MetaTrader5 as mt5

COMMON_SUFFIXES = ["", ".s", "m", ".a", ".r", "_i", ".i", "pro", ".pro"]
BASE_ALIASES = {
    "XAUUSD": ["XAUUSD", "GOLD"],
    "BTCUSD": ["BTCUSD", "BTCUSDT", "XBTUSD"],
    "EURUSD": ["EURUSD"],
    "GBPUSD": ["GBPUSD"],
    "USDJPY": ["USDJPY"],
}


def build_symbol_candidates(base_symbol: str):
    raw = (base_symbol or "").strip()
    if not raw:
        return []
    normalized = raw.upper()
    seeds = []
    for key, aliases in BASE_ALIASES.items():
        if normalized == key or normalized in aliases or normalized.startswith(key):
            seeds.extend(aliases)
            seeds.append(key)
    seeds.append(raw)
    seeds.append(normalized)

    out = []
    seen = set()
    for seed in seeds:
        if not seed:
            continue
        for suffix in COMMON_SUFFIXES:
            candidate = seed if seed.endswith(suffix) and suffix else f"{seed}{suffix}"
            if candidate not in seen:
                seen.add(candidate)
                out.append(candidate)
    return out


def resolve_symbol(base_symbol: str):
    for candidate in build_symbol_candidates(base_symbol):
        try:
            info = mt5.symbol_info(candidate)
            if info and mt5.symbol_select(candidate, True):
                tick = mt5.symbol_info_tick(candidate)
                if tick is not None and (getattr(tick, 'bid', 0) or getattr(tick, 'ask', 0)):
                    return candidate
        except Exception:
            pass
    return None


def broker_safe_stops(symbol: str, entry: float, sl: float, tp: float, side: str):
    info = mt5.symbol_info(symbol)
    if info is None:
        return sl, tp
    point = getattr(info, 'point', 0.0) or 0.0
    stops_level = getattr(info, 'trade_stops_level', 0) or 0
    freeze_level = getattr(info, 'trade_freeze_level', 0) or 0
    min_points = max(stops_level, freeze_level, 10)
    min_distance = point * min_points if point else 0.0
    if min_distance <= 0:
        return sl, tp

    side = side.upper()
    if side == 'BUY':
        if entry - sl < min_distance:
            sl = entry - min_distance
        if tp - entry < min_distance:
            tp = entry + min_distance
    else:
        if sl - entry < min_distance:
            sl = entry + min_distance
        if entry - tp < min_distance:
            tp = entry - min_distance

    digits = getattr(info, 'digits', 3) or 3
    return round(sl, digits), round(tp, digits)
