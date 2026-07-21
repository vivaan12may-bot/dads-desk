"""
Dad's Desk V2 — pure technical indicators (no I/O, no state).
Every function takes real price data and returns a real, checkable value.
"""
import numpy as np
import pandas as pd

def ema(s, n): return s.ewm(span=n, adjust=False).mean()
def sma(s, n): return s.rolling(n).mean()

def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return (100 - 100/(1 + up/dn.replace(0, np.nan))).fillna(50)

def macd(c):
    line = ema(c, 12) - ema(c, 26)
    return line, ema(line, 9)

def stoch(df, n=14, d=3):
    ll = df["low"].rolling(n).min(); hh = df["high"].rolling(n).max()
    k = (100*(df["close"]-ll)/(hh-ll).replace(0, np.nan)).fillna(50)
    return k, k.rolling(d).mean()

def roc(c, n=10): return (c/c.shift(n) - 1) * 100

def atr(df, n=14):
    h, l, c = df["high"], df["low"], df["close"]; pc = c.shift()
    tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()

def adx_di(df, n=14):
    h, l, c = df["high"], df["low"], df["close"]
    up = h.diff(); dn = -l.diff()
    plus  = np.where((up>dn)&(up>0), up, 0.0)
    minus = np.where((dn>up)&(dn>0), dn, 0.0)
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    a = pd.Series(tr).ewm(alpha=1/n, adjust=False).mean()
    pdi = 100*pd.Series(plus,  index=df.index).ewm(alpha=1/n, adjust=False).mean()/a
    ndi = 100*pd.Series(minus, index=df.index).ewm(alpha=1/n, adjust=False).mean()/a
    dx = (100*(pdi-ndi).abs()/(pdi+ndi).replace(0, np.nan)).fillna(0)
    return dx.ewm(alpha=1/n, adjust=False).mean(), pdi, ndi

def bollinger(c, n=20, k=2):
    m = sma(c, n); s = c.rolling(n).std()
    return m + k*s, m, m - k*s, (2*k*s/m*100)

def obv(df):
    dirn = np.sign(df["close"].diff()).fillna(0)
    return (dirn*df["volume"]).cumsum()

def supertrend(df, n=10, mult=3.0):
    a = atr(df, n); hl2 = (df["high"]+df["low"])/2
    upper = hl2 + mult*a; lower = hl2 - mult*a
    st = pd.Series(index=df.index, dtype=float); trend = pd.Series(index=df.index, dtype=float)
    st.iloc[0] = upper.iloc[0]; trend.iloc[0] = 1
    for i in range(1, len(df)):
        c = df["close"].iloc[i]
        if   c > st.iloc[i-1]: trend.iloc[i] = 1
        elif c < st.iloc[i-1]: trend.iloc[i] = -1
        else:                  trend.iloc[i] = trend.iloc[i-1]
        if trend.iloc[i] == 1:
            st.iloc[i] = max(lower.iloc[i], st.iloc[i-1] if trend.iloc[i-1]==1 else lower.iloc[i])
        else:
            st.iloc[i] = min(upper.iloc[i], st.iloc[i-1] if trend.iloc[i-1]==-1 else upper.iloc[i])
    return trend

def vwap(df):
    tp = (df["high"]+df["low"]+df["close"])/3
    return (tp*df["volume"]).cumsum()/df["volume"].cumsum().replace(0, np.nan)

# ---- candlestick patterns (last candles) ----
def bullish_engulfing(df):
    o1, c1 = df["open"].iloc[-2], df["close"].iloc[-2]
    o2, c2 = df["open"].iloc[-1], df["close"].iloc[-1]
    return (c1 < o1) and (c2 > o2) and (c2 >= o1) and (o2 <= c1)

def hammer(df):
    o, h, l, c = (df["open"].iloc[-1], df["high"].iloc[-1],
                  df["low"].iloc[-1], df["close"].iloc[-1])
    body = abs(c-o); rng = h-l+1e-9; lower = min(o, c)-l
    return body/rng < 0.4 and lower/rng > 0.5 and c >= o

# ---- simple support / resistance from recent swing points ----
def support_resistance(df, lookback=40):
    seg = df.tail(lookback)
    return round(float(seg["low"].min()), 1), round(float(seg["high"].max()), 1)

def gap_pct(df):
    if len(df) < 2: return 0.0
    prev_close = float(df["close"].iloc[-2]); today_open = float(df["open"].iloc[-1])
    return round((today_open/prev_close - 1)*100, 2) if prev_close else 0.0

# ============================================================
# Advanced battery — more real, price-derived measures
# ============================================================
def mfi(df, n=14):
    tp = (df["high"]+df["low"]+df["close"])/3
    mf = tp*df["volume"]
    pos = mf.where(tp > tp.shift(), 0.0).rolling(n).sum()
    neg = mf.where(tp < tp.shift(), 0.0).rolling(n).sum()
    return (100 - 100/(1 + pos/neg.replace(0, np.nan))).fillna(50)

def cmf(df, n=20):
    hl = (df["high"]-df["low"]).replace(0, np.nan)
    mfm = ((df["close"]-df["low"]) - (df["high"]-df["close"]))/hl
    mfv = (mfm*df["volume"]).fillna(0)
    return (mfv.rolling(n).sum()/df["volume"].rolling(n).sum().replace(0, np.nan)).fillna(0)

def keltner(df, n=20, mult=2.0):
    mid = ema(df["close"], n); rng = atr(df, n)
    return mid + mult*rng, mid, mid - mult*rng

def ichimoku_bull(df):
    high, low, c = df["high"], df["low"], df["close"]
    tenkan = (high.rolling(9).max() + low.rolling(9).min())/2
    kijun  = (high.rolling(26).max() + low.rolling(26).min())/2
    span_a = ((tenkan + kijun)/2)
    span_b = (high.rolling(52).max() + low.rolling(52).min())/2
    last = float(c.iloc[-1])
    cloud_top = max(float(span_a.iloc[-1]), float(span_b.iloc[-1]))
    return last > cloud_top and float(tenkan.iloc[-1]) > float(kijun.iloc[-1])

def pivots(df):
    """Classic pivot from the last completed bar — reference levels only."""
    h, l, c = float(df["high"].iloc[-2]), float(df["low"].iloc[-2]), float(df["close"].iloc[-2])
    p = (h+l+c)/3
    return round(2*p-l, 1), round(2*p-h, 1)   # R1, S1

def week52(df):
    seg = df.tail(252)
    hi = float(seg["high"].max()); lo = float(seg["low"].min()); last = float(df["close"].iloc[-1])
    pos = (last-lo)/(hi-lo)*100 if hi > lo else 50
    dist = (hi-last)/hi*100 if hi else 0
    return round(pos, 0), round(dist, 1), round(hi, 1)   # % of 52w range, % below 52w high, 52w high

def beta(stock_close, index_close, n=120):
    a = stock_close.pct_change()
    b = index_close.pct_change()
    df = pd.concat([a, b], axis=1, keys=["s", "i"]).dropna().tail(n)
    if len(df) < 30: return 1.0
    var = float(df["i"].var())
    if not var: return 1.0
    cov = float(df["s"].cov(df["i"]))
    return round(cov/var, 2)

# ---- more reversal patterns (bullish + bearish) ----
def morning_star(df):
    if len(df) < 3: return False
    o1,c1 = df["open"].iloc[-3], df["close"].iloc[-3]
    o2,c2 = df["open"].iloc[-2], df["close"].iloc[-2]
    o3,c3 = df["open"].iloc[-1], df["close"].iloc[-1]
    b1,b3 = abs(c1-o1), abs(c3-o3)
    return (c1 < o1) and (abs(c2-o2) < b1*0.5) and (c3 > o3) and (c3 > (o1+c1)/2) and b3 > b1*0.5

def evening_star(df):
    if len(df) < 3: return False
    o1,c1 = df["open"].iloc[-3], df["close"].iloc[-3]
    o2,c2 = df["open"].iloc[-2], df["close"].iloc[-2]
    o3,c3 = df["open"].iloc[-1], df["close"].iloc[-1]
    b1 = abs(c1-o1)
    return (c1 > o1) and (abs(c2-o2) < b1*0.5) and (c3 < o3) and (c3 < (o1+c1)/2)

def bearish_engulfing(df):
    o1,c1 = df["open"].iloc[-2], df["close"].iloc[-2]
    o2,c2 = df["open"].iloc[-1], df["close"].iloc[-1]
    return (c1 > o1) and (c2 < o2) and (o2 >= c1) and (c2 <= o1)

def shooting_star(df):
    o,h,l,c = (df["open"].iloc[-1], df["high"].iloc[-1], df["low"].iloc[-1], df["close"].iloc[-1])
    body = abs(c-o); rng = h-l+1e-9; upper = h-max(o,c)
    return body/rng < 0.4 and upper/rng > 0.5 and c <= o
