"""
Dad's Desk V2 — data layer.
Real prices via yfinance (robust: retries, rate-limit backoff, MultiIndex fix).
Synthetic prices for --demo so it runs with no internet.
"""
import time, random
import datetime as dt
import numpy as np
import pandas as pd
import config

NEED = ["open", "high", "low", "close", "volume"]

def fetch(symbol, interval="1d", period=None, demo=False, tries=None):
    if demo:
        return synth(symbol, interval)
    period = period or config.DATA_PERIOD_DAILY
    tries  = tries or config.FETCH_TRIES
    import yfinance as yf
    last_err = None
    for attempt in range(tries):
        try:
            df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
            if df is None or df.empty:
                time.sleep(0.6*(attempt+1)); continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.rename(columns=str.lower)
            if not all(c in df.columns for c in NEED):
                return None
            df = df[NEED].dropna()
            return df if len(df) >= 40 else None
        except Exception as ex:
            last_err = ex; time.sleep(0.8*(attempt+1))
    if last_err:
        print(f"  ! {symbol}: fetch failed ({last_err})")
    return None

def fetch_many(symbols, demo=False, workers=None):
    """Fetch many symbols concurrently. Returns {symbol: DataFrame}.
    Concurrency is what makes a few-hundred-stock universe finish in
    reasonable time instead of hours. Yahoo still rate-limits, so keep
    workers modest and the universe liquid."""
    workers = workers or config.FETCH_WORKERS
    out = {}
    if demo:
        for s in symbols:
            out[s] = synth(s, "1d")
        return out
    from concurrent.futures import ThreadPoolExecutor, as_completed
    def one(sym):
        return sym, fetch(sym, "1d", demo=False)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one, s) for s in symbols]
        done = 0
        for f in as_completed(futs):
            try:
                sym, df = f.result()
                if df is not None:
                    out[sym] = df
            except Exception:
                pass
            done += 1
            if done % 50 == 0:
                print(f"    ...fetched {done}/{len(symbols)}")
    return out

def synth(symbol, interval="1d"):
    rng = random.Random((hash(symbol+interval)) & 0xffffffff)
    n = 1300 if interval == "1d" else 120
    price = rng.uniform(200, 3500); drift = rng.uniform(-0.0035, 0.0030)
    vol = rng.uniform(0.008, 0.03); base_v = rng.uniform(5e5, 8e6); regime = rng.random()
    o_, h_, l_, c_, v_ = [], [], [], [], []
    for i in range(n):
        ret = drift + rng.gauss(0, vol)
        if i > n-18 and rng.random() < 0.5:
            ret += vol*rng.uniform(-1.6, 1.7) * (1 if regime > 0.4 else -1)
        o = price; price = max(1.0, price*(1+ret))
        hi = max(o, price)*(1+abs(rng.gauss(0, vol/2)))
        lo = min(o, price)*(1-abs(rng.gauss(0, vol/2)))
        v = base_v*(1+abs(rng.gauss(0, 0.6)))
        if i > n-6 and rng.random() < 0.5: v *= rng.uniform(1.4, 3.0)
        o_.append(o); c_.append(price); h_.append(hi); l_.append(lo); v_.append(v)
    idx = pd.date_range(end=dt.datetime.now(), periods=n, freq="D" if interval=="1d" else "h")
    return pd.DataFrame({"open":o_, "high":h_, "low":l_, "close":c_, "volume":v_}, index=idx)

# ---- timeframe resampling (build weekly & monthly bars from daily) ----
def _resample(df, rule):
    o = df["open"].resample(rule).first()
    h = df["high"].resample(rule).max()
    l = df["low"].resample(rule).min()
    c = df["close"].resample(rule).last()
    v = df["volume"].resample(rule).sum()
    out = pd.concat({"open":o,"high":h,"low":l,"close":c,"volume":v}, axis=1).dropna()
    return out

def to_weekly(df):  return _resample(df, "W")
def to_monthly(df):
    try:    return _resample(df, "ME")   # pandas >= 2.2
    except Exception: return _resample(df, "M")
