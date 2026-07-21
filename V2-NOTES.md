# Dad's Desk V2 — what changed & how to run

V1 was one big `scan.py`. V2 is the same idea, rebuilt into clean modules so it
can grow (500+ stocks, database, alerts, backtesting) without becoming a mess.
**Everything from V1 still works** — same commands, same PWA, same data.json.

## New structure
| File | Job |
|------|-----|
| `config.py` | All settings: thresholds, market hours, universe choice, feature flags |
| `universe.py` | Expandable stock list: built-in NIFTY 50 + index CSVs + universe.txt |
| `indicators.py` | Pure technical math (RSI, MACD, ADX, Bollinger, Supertrend, S/R, gaps…) |
| `engine.py` | Runs the strategy battery + builds the **honest recommendation card** |
| `data.py` | Robust yfinance fetch + offline demo data |
| `brain.py` | Tavily news + Gemini plain-language explanation (graceful fallback) |
| `storage.py` | SQLite history of every scan & recommendation |
| `scan.py` | Orchestrator + CLI + market clock + live loop + publishes data.json/HTML |

## Run it (Windows 11, Python 3.13)
```
pip install -r requirements.txt
python scan.py --demo     # fake data, see it work offline
python scan.py --once      # one real scan (needs internet)
python scan.py --live      # loops during market hours
```
Optional keys for news + AI wording (prices/signals work without them):
```
setx GEMINI_API_KEY "..."
setx TAVILY_API_KEY "..."
```

## The recommendation card (honest version of your spec)
Each pick now carries: **Score**, **Confidence** (= how many strategies agree, not a
promise), **Risk**, **Reference level up**, **Safety line**, **Holding range**,
**Movement context**, **Reasons**, **Status** (RECOMMENDED / WATCH / NOT), and a
**NEW** badge when it wasn't in the previous scan. All of it stored in SQLite.

## Expand the universe
Put an NSE CSV (e.g. `ind_nifty500list.csv`) in `indices/`, add its name to
`INDEX_CSV_FILES` in `config.py`. Done — now it scans 500 stocks.

## What's next (phases queued)
- **P2** parallel fetch + caching for the big universe
- **P3** market breadth, sector strength, delivery % (real "institutional" proxy)
- **P4** news sentiment scoring (pos/neg/neutral)
- **P5** Telegram alerts on threshold crossings
- **P6** FastAPI/Supabase + richer app (watchlists, portfolio, dark mode)
- **P7** backtesting → turns "confidence / target / holding" into MEASURED numbers

---

# Advanced upgrade (scale + deeper analysis)

## Bigger universe
- Default is now **NIFTY 100** (~120 liquid names), scanned **concurrently**.
- For **NIFTY 500**: drop the official NSE `ind_nifty500list.csv` into `indices/`,
  add it to `INDEX_CSV_FILES` in `config.py`, done.
- `MAX_STOCKS` (config) caps each scan. `FETCH_WORKERS` sets concurrency.

## Honest scale ceiling (please read)
Free Yahoo data rate-limits, so there is a real ceiling:
- **~300–500 liquid stocks / every 15 min** → fine (this is effectively the whole
  tradeable market; the illiquid tail is noise).
- **~1,000–2,000** → only as a **once-daily EOD** run, ideally chunked. Set the
  GitHub schedule to once after 3:30 PM and raise `MAX_STOCKS`.
- **True thousands, real-time** → not possible on free data. Needs a paid feed
  (Zerodha Kite or a data vendor). `data.fetch()` is built for a drop-in swap.

"5,000 stocks live and free" is not achievable — anyone promising it is hiding
the rate-limit wall. 500 liquid names covers what you'd actually trade.

## Deeper analysis (all real, all computed)
Per stock, on top of the original battery:
- **Money Flow Index (MFI)**, **Chaikin Money Flow (CMF)** — volume/flow strength
- **Keltner breakout**, **Ichimoku cloud**, **52-week high position & distance**
- **Beta vs Nifty**, **classic pivot levels**
Plus **cross-universe context** computed after every stock is scored:
- **Market breadth** — % of the universe in a healthy uptrend (shown in the header)
- **Relative-strength ranking** — each stock's percentile vs the whole universe;
  top 20% earns a real bonus point.

All of it shows in the tap-to-open popup. Still honest: "confidence" = signal
agreement, targets/stops/holding are references, and size + exit stay human.

---

# Multi-screen upgrade (tabs)

The app now has three control rows at the top:
- **View:** ⭐ Top · Buy · Early climb · Sell / weak
- **Timeframe:** Daily (2–3 wks) · Weekly (2–3 mo) · Monthly (2–3 yr)
- **Cap:** All · Large · Mid · Small

**⭐ Top** = the highest-conviction Buy setups (the "best of the best" — sorted by
signal agreement). **Early climb** = stocks forming a bullish reversal *before*
they've run (hammer / bullish engulfing / morning star / oversold or lower-band
bounce, still near their base) — higher risk, clearly labelled "not yet
confirmed." **Sell / weak** = stocks flashing weakness (below key averages, death
cross, breakdown, bearish patterns, money-flow out) — useful for deciding what to
trim or avoid; it is NOT advice to short.

Market cap is tagged from index membership (Nifty 100 = large; built-in mid/small
samples included). For full mid/small coverage, drop the official NSE
midcap150 / smallcap250 CSVs into `indices/` and tag them in `config.py`:
`INDEX_CSV_FILES = [["ind_niftymidcap150list.csv","mid"], ["ind_niftysmallcap250list.csv","small"]]`.

Still honest: "Top"/"Strong Buy" and the % mean signal strength, "Early" means an
unconfirmed setup that often fails, "Sell" means weakness — none are guarantees,
and size + exit stay a human's call.
