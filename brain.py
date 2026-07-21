"""
Dad's Desk V2 — news + plain-language brain.
Tavily fetches real news; Gemini explains in simple words and tags sentiment.
Both degrade gracefully: no key / no internet -> built-in template, never crashes.
"""
import os, time, datetime as dt
import config

_CACHE = {}
def _get(key):
    v = _CACHE.get(key)
    if v and (time.time()-v[0]) < config.EXPLAIN_TTL*60: return v[1]
    return None
def _put(key, val): _CACHE[key] = (time.time(), val)

def news(name, demo=False):
    if demo or not config.USE_NEWS:
        return None
    try:
        import requests
        r = requests.post("https://api.tavily.com/search", json={
            "api_key": os.environ["TAVILY_API_KEY"],
            "query": f"{name} share price news India",
            "search_depth": "basic", "max_results": 3, "topic": "news", "days": 3,
        }, timeout=25)
        items = r.json().get("results", [])
        if not items: return None
        top = items[0]
        return {"title": top.get("title",""), "url": top.get("url",""),
                "blurb": (top.get("content","") or "")[:300]}
    except Exception as ex:
        print("  ! Tavily:", ex); return None

def explain(stock, nws, demo=False):
    key = stock["symbol"] + dt.date.today().isoformat()
    cached = _get(key)
    if cached: return cached
    reasons = stock.get("reasons", [])
    if demo or not config.USE_AI:
        out = _template(stock, reasons, nws); _put(key, out); return out
    try:
        import requests
        lang = "simple Hindi" if config.LANG == "hi" else "very simple English"
        nl = f"Latest news: {nws['title']}. {nws['blurb']}" if nws else "No fresh news found."
        prompt = (f"Explain to an older person who does not read charts, in 2 short {lang} "
                  f"sentences, why {stock['name']} looks technically strong now. Strategies "
                  f"firing: {', '.join(reasons)}. Up {stock['change']}% today, RSI {stock['rsi']}, "
                  f"ADX {stock['adx']}. Say plainly what this means and what the news implies. "
                  f"Do NOT predict a price, do NOT say how many shares to buy, do NOT give a "
                  f"sell date. Calm and factual. {nl}")
        r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/"
                          "gemini-1.5-flash:generateContent?key=" + os.environ["GEMINI_API_KEY"],
                          json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=30)
        out = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as ex:
        print("  ! Gemini:", ex); out = _template(stock, reasons, nws)
    _put(key, out); return out

def _template(stock, reasons, nws):
    m = []
    if "Above 20/50/200 avg" in reasons: m.append("its price sits above its main averages")
    if "20-day breakout" in reasons or "Bollinger breakout" in reasons: m.append("it broke past its recent high")
    if "Volume surge" in reasons: m.append("far more people are trading it than usual")
    if "MACD rising" in reasons or "Stochastic up" in reasons: m.append("its momentum is turning up")
    if "Beating Nifty (20d)" in reasons: m.append("it's outperforming the overall market")
    why = ", and ".join(m[:3]) if m else f"{len(reasons)} strategies agree"
    out = (f"{stock['name']} looks strong right now because {why}. It moved "
           f"{stock['change']:+.1f}% and {stock['families']} kinds of signals line up together.")
    if nws: out += f" In the news: {nws['title']}."
    return out
