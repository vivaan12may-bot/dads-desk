"""
Dad's Desk V2 — strategy engine.

evaluate()  : run the full strategy battery on one stock, return raw signals.
recommend() : turn raw signals into an honest recommendation card.

Honesty rules baked in:
  * "confidence" = how many checked strategies AGREE (signal agreement),
    NOT a probability of profit.
  * target / stop / holding are REFERENCE levels from real structure and
    volatility, labelled as references — never promised outcomes.
  * we never fabricate an exact expected % or "institutional buying".
    (Phase 7 backtesting will replace these with measured statistics.)
"""
import numpy as np
import indicators as I
import config


def evaluate(symbol, name, tv, d, intra=None, nifty_close=None):
    c = d["close"]; last = float(c.iloc[-1])
    e20, e50 = I.ema(c, 20), I.ema(c, 50)
    e200 = I.ema(c, 200 if len(c) >= 200 else 100)
    r = I.rsi(c); rl = float(r.iloc[-1])
    ml, ms = I.macd(c); k, dk = I.stoch(d)
    ad, pdi, ndi = I.adx_di(d); adv = float(ad.iloc[-1])
    up, mid, lo, bw = I.bollinger(c); ob = I.obv(d); st = I.supertrend(d)
    a = I.atr(d); atr_v = float(a.iloc[-1]); atr_pct = atr_v/last*100 if last else 0
    vol20 = float(d["volume"].tail(20).mean())
    vs = float(d["volume"].iloc[-1])/vol20 if vol20 else 1.0
    hi20 = float(d["high"].iloc[-21:-1].max())
    sup, res = I.support_resistance(d)
    gap = I.gap_pct(d)
    chg = (last/float(c.iloc[-2]) - 1)*100 if len(c) > 1 else 0

    fired, checked = {}, 0
    def check(name_, fam, cond):
        nonlocal checked
        checked += 1
        if cond: fired[name_] = fam

    # trend
    check("Above 20/50/200 avg", "trend", last > float(e20.iloc[-1]) > float(e50.iloc[-1]) > float(e200.iloc[-1]))
    check("Golden cross", "trend", float(e50.iloc[-2]) <= float(e200.iloc[-2]) and float(e50.iloc[-1]) > float(e200.iloc[-1]))
    check("Supertrend up", "trend", float(st.iloc[-1]) == 1)
    check("Strong trend (ADX)", "trend", adv >= 25 and float(pdi.iloc[-1]) > float(ndi.iloc[-1]))
    # momentum
    check("RSI healthy", "momentum", 50 <= rl <= 70)
    check("MACD rising", "momentum", float(ml.iloc[-1]) > float(ms.iloc[-1]) and float(ml.iloc[-1]) > float(ml.iloc[-2]))
    check("Stochastic up", "momentum", float(k.iloc[-1]) > float(dk.iloc[-1]) and float(k.iloc[-1]) < 80)
    check("Positive ROC", "momentum", float(I.roc(c).iloc[-1]) > 0)
    # breakout / volatility
    check("20-day breakout", "breakout", last >= hi20)
    check("Bollinger breakout", "breakout", last > float(up.iloc[-1]))
    check("Squeeze firing", "breakout", float(bw.iloc[-1]) > float(bw.iloc[-6]) and float(bw.iloc[-6]) < float(bw.tail(60).median()))
    # volume
    check("Volume surge", "volume", vs >= 1.5)
    check("OBV rising", "volume", float(ob.iloc[-1]) > float(ob.iloc[-5]))
    # mean reversion
    check("Oversold bounce", "meanrev", float(r.iloc[-2]) < 32 and rl > float(r.iloc[-2]))
    check("Bounce off lower band", "meanrev", float(d["low"].iloc[-1]) <= float(lo.iloc[-1]) and last > float(lo.iloc[-1]))
    # patterns
    check("Bullish engulfing", "pattern", I.bullish_engulfing(d))
    check("Hammer", "pattern", I.hammer(d))
    # relative strength vs Nifty
    ret20 = None
    if nifty_close is not None and len(nifty_close) >= 21:
        sret = last/float(c.iloc[-21]) - 1
        nret = float(nifty_close.iloc[-1])/float(nifty_close.iloc[-21]) - 1
        ret20 = sret
        check("Beating Nifty (20d)", "relstrength", sret > nret)
    # intraday trigger (live)
    if intra is not None and len(intra) > 5:
        vw = I.vwap(intra)
        check("Above VWAP (intraday)", "volume", float(intra["close"].iloc[-1]) > float(vw.iloc[-1]))

    # --- advanced battery ---
    mfi_v = float(I.mfi(d).iloc[-1]); cmf_v = float(I.cmf(d).iloc[-1])
    ku, kmid, kl = I.keltner(d)
    w52_pos, w52_dist, w52_hi = I.week52(d)
    r1, s1 = I.pivots(d)
    bta = I.beta(c, nifty_close) if nifty_close is not None else 1.0
    check("Money Flow strong", "volume", mfi_v >= 55)
    check("Chaikin inflow", "volume", cmf_v > 0.05)
    check("Keltner breakout", "breakout", last > float(ku.iloc[-1]))
    check("Above Ichimoku cloud", "trend", I.ichimoku_bull(d))
    check("Near 52-week high", "trend", w52_dist <= 5)

    families = set(fired.values())
    score = round(sum(config.FAMILY_W[f] for f in fired.values()), 1)

    # --- bearish battery (for the Sell / weakness screen) ---
    bear = {}
    def bcheck(nm_, cond):
        if cond: bear[nm_] = True
    lo20 = float(d["low"].iloc[-21:-1].min())
    bcheck("Below 20 & 50 avg", last < float(e20.iloc[-1]) and last < float(e50.iloc[-1]))
    bcheck("Death cross", float(e50.iloc[-1]) < float(e200.iloc[-1]))
    bcheck("Supertrend down", float(st.iloc[-1]) == -1)
    bcheck("MACD falling", float(ml.iloc[-1]) < float(ms.iloc[-1]) and float(ml.iloc[-1]) < float(ml.iloc[-2]))
    bcheck("RSI weak", rl < 45)
    bcheck("Breaking support", last <= lo20)
    bcheck("Below lower band", last < float(lo.iloc[-1]))
    bcheck("Money flow out", cmf_v < -0.05 or mfi_v < 40)
    bcheck("Bearish engulfing", I.bearish_engulfing(d))
    bcheck("Evening star", I.evening_star(d))
    bcheck("Shooting star", I.shooting_star(d))
    bear_score = len(bear)

    # --- early bullish reversal (may climb soon, not yet moved) ---
    reversal = []
    if I.hammer(d): reversal.append("Hammer")
    if I.bullish_engulfing(d): reversal.append("Bullish engulfing")
    if I.morning_star(d): reversal.append("Morning star")
    near_low = last <= float(d["low"].tail(40).min()) * 1.06     # still near the base
    not_extended = rl < 58 and last < float(e20.iloc[-1]) * 1.03  # hasn't run up yet
    bull_conf = round(100 * len(fired) / max(1, checked))
    bear_conf = round(100 * bear_score / 11)

    return {
        "symbol": symbol, "name": name, "tv": tv,
        "price": round(last, 1), "change": round(chg, 2),
        "rsi": round(rl, 0), "adx": round(adv, 0), "atr_pct": round(atr_pct, 1),
        "vsurge": round(vs, 1), "gap": gap, "support": sup, "resistance": res,
        "recent_high": round(hi20, 1), "atr_v": atr_v,
        "mfi": round(mfi_v, 0), "cmf": round(cmf_v, 2), "beta": bta,
        "w52_pos": w52_pos, "w52_dist": w52_dist, "w52_high": w52_hi,
        "pivot_r1": r1, "pivot_s1": s1, "ret20": ret20,
        "bear": bear, "bear_score": bear_score, "bear_conf": bear_conf,
        "bull_conf": bull_conf, "reversal": reversal,
        "near_low": near_low, "not_extended": not_extended,
        "fired": fired, "families": len(families), "checked": checked,
        "score": score, "extended": rl > 72,
    }


def finalize(evals):
    """Cross-universe context computed AFTER all stocks are evaluated:
    market breadth and each stock's relative-strength percentile."""
    rets = sorted([e["ret20"] for e in evals if e["ret20"] is not None])
    n = len(rets)
    def pct_rank(x):
        if x is None or n == 0: return None
        below = sum(1 for r in rets if r <= x)
        return round(100*below/n)
    # breadth = share of the scanned universe in a healthy uptrend
    up = sum(1 for e in evals if e["fired"].get("Above 20/50/200 avg") or
             e["fired"].get("Above Ichimoku cloud"))
    breadth = round(100*up/len(evals)) if evals else 0
    for e in evals:
        e["rs_percentile"] = pct_rank(e["ret20"])
        e["market_breadth"] = breadth
        # a strong RS reading adds a real, context-based point to the score
        if e["rs_percentile"] is not None and e["rs_percentile"] >= 80:
            e["fired"]["Top 20% relative strength"] = "relstrength"
            e["score"] = round(e["score"] + config.FAMILY_W["relstrength"], 1)
            e["families"] = len(set(e["fired"].values()))
    return evals, breadth


def recommend(e):
    """Build the honest recommendation card from an evaluation."""
    last = e["price"]; atr_pct = e["atr_pct"]
    risk = "low" if atr_pct < 2 else ("med" if atr_pct < 4 else "high")

    # reference levels (real structure + volatility) — NOT promises
    target_ref = round(max(e["recent_high"], e["resistance"], last*(1 + 2*atr_pct/100)), 1)
    # safety line = volatility-based stop, but never wider than the nearby swing low
    vol_stop = last - 1.5*e["atr_v"]
    stop_ref = round(max(vol_stop, e["support"]) if e["support"] < last else vol_stop, 1)

    # signal agreement, honestly labelled (share of checked strategies that fired)
    confidence = round(100 * len(e["fired"]) / max(1, e["checked"]))

    # holding hint from the dominant setup — a RANGE with a reason, never "5 days"
    fams = set(e["fired"].values())
    if {"breakout", "momentum"} & fams:
        holding = "swing setup — typically plays out over about 3–10 trading days"
    elif "trend" in fams:
        holding = "trend setup — often develops over 2–6 weeks"
    else:
        holding = "short-term setup — usually a few days to two weeks"

    dist = round((target_ref/last - 1)*100, 1) if last else 0
    expected = (f"this stock typically moves about {atr_pct}% a day; "
                f"the reference level is roughly {dist}% away")

    if   e["score"] >= config.MIN_SCORE and e["families"] >= config.MIN_FAMILIES:
        status = "RECOMMENDED"
    elif e["score"] >= config.WATCH_SCORE:
        status = "WATCH"
    else:
        status = "NOT RECOMMENDED"

    # signal-strength tier (a label, not a promise)
    if status == "RECOMMENDED" and (e["score"] >= 12 or confidence >= 65):
        tier = "Strong Buy"
    elif status == "RECOMMENDED":
        tier = "Buy"
    elif status == "WATCH":
        tier = "Watch"
    else:
        tier = "—"

    # --- classify into a screen: sell / early / buy / neutral ---
    bear_score = e["bear_score"]; reversal = e["reversal"]
    if bear_score >= 4 and e["score"] < config.MIN_SCORE:
        kind = "sell"
        confidence = e["bear_conf"]
        reasons = list(e["bear"].keys())
        tier = "Strong Sell" if bear_score >= 6 else "Sell"
        holding = "weakness signals — if you hold this, consider trimming or exiting"
        expected = f"showing {bear_score} signs of weakness; downside support near ₹{e['support']:,}"
    elif e["not_extended"] and e["score"] < 10 and bear_score < 4 and (
            e["reversal"] or "Oversold bounce" in e["fired"] or "Bounce off lower band" in e["fired"]):
        kind = "early"
        early_sig = list(e["reversal"])
        for r in ("Oversold bounce", "Bounce off lower band", "MACD rising", "Hammer"):
            if r in e["fired"] and r not in early_sig: early_sig.append(r)
        confidence = max(confidence, 38 + 11*len(early_sig))
        reasons = early_sig or ["Basing near support"]
        tier = "Emerging"
        holding = "early reversal — may be starting to turn; higher risk, not yet confirmed"
        expected = f"forming a base near ₹{e['support']:,}; watch for follow-through before it runs"
    elif status in ("RECOMMENDED", "WATCH"):
        kind = "buy"
        reasons = list(e["fired"].keys())
    else:
        kind = "neutral"
        reasons = list(e["fired"].keys())

    e.update({
        "risk": risk, "confidence": confidence, "target_ref": target_ref,
        "stop_ref": stop_ref, "holding": holding, "expected": expected,
        "status": status, "tier": tier, "kind": kind, "reasons": reasons,
    })
    return e
