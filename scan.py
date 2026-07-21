#!/usr/bin/env python3
"""
Dad's Desk V2 — orchestrator.

Modes:
    python scan.py --demo    # offline synthetic data (no internet/keys)
    python scan.py --once     # one real scan now, publish, exit
    python scan.py --live     # loop during market hours (09:15-15:30 IST)

Pipeline: universe -> data -> engine(evaluate+recommend) -> brain(news+AI)
          -> storage(SQLite) -> data.json (+ HTML) for the PWA.

Honest by design: it surfaces strong candidates with real reasons, real
reference levels and real risk. It never invents an exact expected return,
an exact sell date, or "institutional buying". Size and exit stay human.
"""
import os, sys, json, time
import datetime as dt

import config, universe, data, engine, brain, storage

DEMO = "--demo" in sys.argv
LIVE = "--live" in sys.argv

# ---------------- market clock ----------------
def now_ist(): return dt.datetime.now(config.IST)

def market_open(t=None):
    t = t or now_ist()
    if t.weekday() >= 5: return False
    if t.strftime("%Y-%m-%d") in config.HOLIDAYS: return False
    mins = t.hour*60 + t.minute
    return config.MARKET_OPEN_MIN <= mins <= config.MARKET_CLOSE_MIN

# ---------------- one scan ----------------
def scan_once():
    uni = universe.load()[:config.MAX_STOCKS]
    if DEMO:
        nd = data.synth("^NSEI")
    else:
        nd = data.fetch("^NSEI", "1d", config.DATA_PERIOD_DAILY)
    ndc = nd["close"] if nd is not None else None
    nwc = data.to_weekly(nd)["close"] if nd is not None else None
    nmc = data.to_monthly(nd)["close"] if nd is not None else None

    print(f"[{now_ist():%H:%M}] scanning {len(uni)} stocks x 3 timeframes ({'DEMO' if DEMO else 'LIVE'})...")
    symbols = [s for s, _, _ in uni]
    name_of = {s: n for s, n, _ in uni}
    cap_of  = {s: c for s, _, c in uni}
    frames = data.fetch_many(symbols, demo=DEMO)

    daily, weekly, monthly = [], [], []
    for sym in symbols:
        d = frames.get(sym)
        if d is None: continue
        nm, tv, cap = name_of[sym], universe.tv_symbol(sym), cap_of[sym]
        try:
            intra = data.synth(sym, "15m") if DEMO else (
                data.fetch(sym, config.DATA_INTERVAL_INTRADAY, "5d") if LIVE else None)
            de = engine.evaluate(sym, nm, tv, d, intra, ndc); de["cap"] = cap; daily.append(de)
            w = data.to_weekly(d)
            if len(w) >= 45:
                we = engine.evaluate(sym, nm, tv, w, None, nwc); we["cap"] = cap; weekly.append(we)
            m = data.to_monthly(d)
            if len(m) >= 30:
                me = engine.evaluate(sym, nm, tv, m, None, nmc); me["cap"] = cap; monthly.append(me)
        except Exception as ex:
            print(f"  ! {sym}: {ex}")

    cols = {}
    for key, evals, hold in (("daily", daily, "about 2–3 weeks"),
                             ("weekly", weekly, "about 2–3 months"),
                             ("monthly", monthly, "about 2–3 years")):
        evals, breadth = engine.finalize(evals)
        for e in evals:
            engine.recommend(e)
            if e["kind"] == "buy":
                e["holding"] = hold
        # keep a balanced set so every screen (buy/early/sell) has picks
        by = {"buy": [], "early": [], "sell": []}
        for e in evals:
            if e["kind"] in by: by[e["kind"]].append(e)
        for kk in by:
            by[kk].sort(key=lambda x: -x["confidence"])
        pub = by["buy"][:config.BUY_N] + by["early"][:config.EARLY_N] + by["sell"][:config.SELL_N]
        cols[key] = {"stocks": pub, "breadth": breadth}
        print(f"  {key:8}: buy {len(by['buy'][:config.BUY_N])} · early {len(by['early'][:config.EARLY_N])} · sell {len(by['sell'][:config.SELL_N])}  (breadth {breadth}%)")

    # enrich the daily BUY leaders with live news + AI (quota-friendly)
    prev = storage.previous_symbols()
    for key in cols:
        enriched = 0
        for s in cols[key]["stocks"]:
            s["is_new"] = (s["symbol"] not in prev) if key == "daily" else False
            if key == "daily" and s["kind"] == "buy" and enriched < config.ENRICH_N:
                n = brain.news(s["name"], demo=DEMO); s["news"] = n
                s["explain"] = brain.explain(s, n, demo=DEMO); enriched += 1
            else:
                s["news"] = None
                s["explain"] = brain.explain(s, None, demo=True)

    status = "OPEN" if market_open() else "CLOSED"
    try:
        storage.save_run(status, len(daily), cols["daily"]["stocks"])
    except Exception as ex:
        print("  ! storage:", ex)

    publish(cols, status, len(daily))
    print("  published data.json + dads-desk.html")
    return sum(len(c["stocks"]) for c in cols.values())

# ---------------- publish (data.json + HTML) ----------------
def publish(cols, status, scanned=0):
    t = now_ist()
    def row(s):
        return {
            "symbol": s["symbol"], "tv": s["tv"], "name": s["name"],
            "price": s["price"], "change": s["change"], "risk": s["risk"],
            "score": s["score"], "confidence": s["confidence"], "families": s["families"],
            "status": s["status"], "tier": s.get("tier","—"), "is_new": s.get("is_new", False),
            "kind": s.get("kind","buy"), "cap": s.get("cap","large"),
            "target_ref": s["target_ref"], "stop_ref": s["stop_ref"],
            "holding": s["holding"], "expected": s["expected"],
            "recent_high": s["recent_high"], "support": s["support"], "resistance": s["resistance"],
            "extended": s["extended"], "reasons": s.get("reasons", []),
            "rsi": s["rsi"], "adx": s["adx"], "mfi": s["mfi"], "cmf": s["cmf"],
            "beta": s["beta"], "w52_pos": s["w52_pos"], "w52_dist": s["w52_dist"],
            "rs_percentile": s.get("rs_percentile"), "atr_pct": s["atr_pct"],
            "explain": s.get("explain", ""), "news": s.get("news"),
            "chart": f"https://www.tradingview.com/chart/?symbol={s['tv']}",
        }
    LABELS = {"daily": ("2–3 weeks", "Daily"), "weekly": ("2–3 months", "Weekly"),
              "monthly": ("2–3 years", "Monthly")}
    payload = {
        "updated": t.isoformat(),
        "updated_h": t.strftime("%a, %d %b %Y · %H:%M IST"),
        "market": status, "demo": DEMO,
        "freshness": "Demo data (fake)" if DEMO else config.DELAYED_NOTE,
        "scanned": scanned,
        "columns": {k: {
            "hold": LABELS[k][0], "tf": LABELS[k][1],
            "breadth": cols[k]["breadth"], "count": len(cols[k]["stocks"]),
            "stocks": [row(s) for s in cols[k]["stocks"]],
        } for k in ("daily", "weekly", "monthly")},
    }
    for folder in (config.HERE, config.PWA_DIR):
        if os.path.isdir(folder):
            with open(os.path.join(folder, "data.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(os.path.join(config.HERE, "dads-desk.html"), "w", encoding="utf-8") as f:
        f.write(_html(payload))

def _esc(x):
    return (str(x).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;"))

def _html(p):
    demobar = ("<div class='demobar'>⚠️ DEMO — FAKE, RANDOM NUMBERS. Run "
               "<b>python scan.py --once</b> for real data.</div>" if p["demo"] else "")
    tcls = lambda t: {"Strong Buy":"sb","Buy":"b","Watch":"w","Emerging":"e","Sell":"s","Strong Sell":"ss"}.get(t,"w")
    def row(s):
        chips = "".join(f"<span class='chip'>{_esc(r)}</span>" for r in s["reasons"][:8])
        newnew = "<span class='new'>NEW</span>" if s["is_new"] else ""
        news = (f"<div class='news'>📰 <a href='{_esc(s['news']['url'])}' target='_blank' rel='noopener'>{_esc(s['news']['title'])}</a></div>"
                if s.get("news") else "")
        return f"""
        <details class="row">
          <summary>
            <span class="dot {s['risk']}"></span>
            <span class="rmain"><span class="rname">{_esc(s['name'])} {newnew}</span>
              <span class="rtk">{_esc(s['tv'])} · ₹{s['price']:,}</span></span>
            <span class="rconf">{s['confidence']}%</span>
            <span class="tier {tcls(s['tier'])}">{_esc(s['tier'])}</span>
          </summary>
          <div class="detail">
            <p class="why">{_esc(s['explain'])}</p>{news}
            <div class="chips">{chips}</div>
            <div class="grid">
              <div><span class="k">Risk</span><span class="v">{s['risk'].upper()}</span></div>
              <div><span class="k">Score</span><span class="v">{s['score']}</span></div>
              <div><span class="k">Reference level up</span><span class="v">₹{s['target_ref']:,}</span></div>
              <div><span class="k">Safety line</span><span class="v">₹{s['stop_ref']:,}</span></div>
              <div><span class="k">Rel. strength</span><span class="v">{('top '+str(100-s['rs_percentile'])+'%') if s.get('rs_percentile') is not None else '—'}</span></div>
              <div><span class="k">52-wk position</span><span class="v">{s['w52_pos']}%</span></div>
            </div>
            <div class="meta"><b>Suggested holding:</b> {_esc(s['holding'])}<br><b>Movement:</b> {_esc(s['expected'])}</div>
            <a class="chart" href="{_esc(s['chart'])}" target="_blank" rel="noopener">See the chart</a>
          </div>
        </details>"""
    sections = ""
    KINDS = [("buy", "Buy"), ("early", "Early climb"), ("sell", "Sell / weakness")]
    for key in ("daily", "weekly", "monthly"):
        col = p["columns"][key]
        sections += (f"<div class='seclabel'><span class='hold'>{col['hold']}</span>"
                     f"<span class='tf'>{col['tf']} chart · {col['count']} picks · breadth {col['breadth']}%</span></div>")
        for kk, klabel in KINDS:
            items = [s for s in col["stocks"] if s.get("kind") == kk]
            if not items: continue
            rows = "".join(row(s) for s in items)
            sections += f"<div class='kindlabel'>{klabel} <span>({len(items)})</span></div><div class='sec'>{rows}</div>"
    return _PAGE.replace("{{DEMOBAR}}", demobar).replace("{{TIME}}", p["updated_h"]) \
        .replace("{{STATUS}}", p["market"]).replace("{{FRESH}}", p["freshness"]) \
        .replace("{{SCANNED}}", str(p.get("scanned", 0))).replace("{{SECTIONS}}", sections)

_PAGE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Dad's Desk</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Mukta:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--paper:#FAF8F3;--card:#fff;--ink:#1F2733;--muted:#6B7280;--line:#E8E3D8;--teal:#0E8A7D;--tealD:#0A6C61;--low:#1E9E6A;--med:#D9922A;--high:#D9534F}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:'Mukta',system-ui,sans-serif;font-size:17px;line-height:1.5}
.wrap{max-width:680px;margin:0 auto;padding:0 14px 60px}
header{padding:20px 4px 6px;display:flex;justify-content:space-between;align-items:flex-end;gap:10px}
h1{font-family:'Poppins';margin:0;font-size:25px}.sub{color:var(--muted);font-size:13px;margin-top:2px}.fresh{font-size:12px;color:var(--muted);margin-top:2px}
.status{font-family:'Poppins';font-weight:600;font-size:12px;padding:5px 11px;border-radius:999px}
.status.OPEN{color:var(--low);background:#E7F5EE}.status.CLOSED{color:var(--muted);background:#EFEAE0}
.demobar{background:#D9534F;color:#fff;text-align:center;font-family:'Poppins';font-weight:700;font-size:13px;padding:11px 14px;border-radius:12px;margin:12px 0 4px}
.banner{background:var(--teal);color:#fff;border-radius:14px;padding:12px 16px;margin:12px 0 12px;font-size:14px}.banner b{font-weight:700}
.hint{font-size:12px;color:var(--muted);margin:0 4px 8px}
.seclabel{display:flex;justify-content:space-between;align-items:baseline;margin:20px 4px 8px}
.seclabel .hold{font-family:'Poppins';font-weight:700;font-size:18px;color:var(--ink)}
.seclabel .tf{font-size:12px;color:var(--muted)}
.sec details.row:first-of-type{border-radius:14px 14px 0 0}.sec details.row:last-of-type{border-radius:0 0 14px 14px}
details.row{background:var(--card);border:1px solid var(--line);list-style:none}
details.row+details.row{border-top:none}
summary{display:flex;align-items:center;gap:11px;padding:13px 14px;cursor:pointer;list-style:none}
summary::-webkit-details-marker{display:none}
.dot{width:11px;height:11px;border-radius:50%;flex:0 0 auto}.dot.low{background:var(--low)}.dot.med{background:var(--med)}.dot.high{background:var(--high)}
.rmain{flex:1;min-width:0;display:flex;flex-direction:column}.rname{font-family:'Poppins';font-weight:600;font-size:16px}.rtk{font-size:12px;color:var(--muted)}
.rconf{font-family:'Poppins';font-weight:700;font-size:16px;color:var(--tealD);min-width:44px;text-align:right}
.tier{font-family:'Poppins';font-weight:600;font-size:11px;padding:5px 9px;border-radius:999px;white-space:nowrap;min-width:78px;text-align:center}
.tier.sb{color:#fff;background:var(--low)}.tier.b{color:var(--tealD);background:#E1F0ED}.tier.w{color:var(--med);background:#FBF1DE}
.tier.ss{color:#fff;background:var(--high)}.tier.s{color:var(--high);background:#FBE7E6}.tier.e{color:var(--med);background:#FBF1DE}
.kindlabel{font-family:'Poppins';font-weight:600;font-size:13px;color:var(--muted);margin:12px 4px 6px}.kindlabel span{color:var(--teal)}
.new{font-size:10px;background:var(--teal);color:#fff;border-radius:5px;padding:1px 5px}
.detail{padding:2px 15px 16px;border-top:1px solid var(--line)}
.why{font-size:16px;margin:12px 0 8px}
.news{font-size:14px;background:var(--paper);border-radius:10px;padding:9px 12px;margin-bottom:8px}.news a{color:var(--tealD);text-decoration:none}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0}.chip{font-size:12px;color:var(--muted);background:var(--paper);border:1px solid var(--line);border-radius:999px;padding:3px 10px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 16px;margin:10px 0 8px}.grid .k{display:block;font-size:11px;color:var(--muted);text-transform:uppercase}.grid .v{display:block;font-weight:700;font-size:16px}
.meta{font-size:14px;color:#4B5563;background:var(--paper);border-radius:10px;padding:10px 12px;margin-bottom:10px}.meta b{color:var(--ink)}
.chart{display:inline-block;background:var(--teal);color:#fff;text-decoration:none;font-family:'Poppins';font-weight:600;font-size:15px;padding:11px 18px;border-radius:12px}
.empty{text-align:center;color:var(--muted);padding:24px 20px;background:var(--card);border:1px dashed var(--line);border-radius:14px}
.foot{margin-top:22px;padding:15px 17px;border-radius:16px;background:#FBF6EC;border:1px solid var(--line);font-size:13px;color:var(--muted);line-height:1.6}.foot b{color:var(--ink)}
</style></head><body><div class="wrap">
{{DEMOBAR}}
<header><div><h1>Dad's Desk</h1><div class="sub">{{TIME}} · {{SCANNED}} stocks · 3 timeframes</div><div class="fresh">{{FRESH}}</div></div><span class="status {{STATUS}}">Market {{STATUS}}</span></header>
<div class="banner"><b>Three timeframes.</b> Daily = short swings (2–3 weeks), Weekly = positions (2–3 months), Monthly = long-term (2–3 years). Tap a row for the plan. "Confidence"/"Strong Buy" = signal strength, not a promise.</div>
{{SECTIONS}}
</div></body></html>"""

# ---------------- entry ----------------
def main():
    if LIVE and not DEMO:
        print(f"LIVE mode — every {config.REFRESH_MIN} min, 09:15-15:30 IST.")
        while True:
            try:
                if market_open(): scan_once()
                else: print(f"[{now_ist():%H:%M}] market closed — idle.")
            except Exception as ex:
                print("cycle error:", ex)
            time.sleep(config.REFRESH_MIN*60 if market_open() else 300)
    else:
        scan_once()

if __name__ == "__main__":
    main()
