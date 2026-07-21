# Dad's Desk — LIVE multi-strategy NSE/BSE scanner

Runs during market hours, checks a broad battery of real technical strategies on
every stock in your list, and refreshes **dads-desk.html** for your dad to keep
open. Each pick shows exactly which strategies fired, a plain-English reason
(Gemini), the latest news (Tavily), and real risk/levels.

It surfaces strong setups with real reasons. It does **not** invent how many
shares to buy or the exact day to sell — nothing can know those, and a made-up
number is the one thing that would hurt your dad. Those stay his call.

## Strategies it checks (7 families)
- **Trend:** price above 20/50/200 averages, golden cross, Supertrend, ADX+DI
- **Momentum:** RSI, MACD, Stochastic, Rate-of-Change
- **Breakout / volatility:** 20-day breakout, Bollinger breakout, squeeze firing
- **Volume:** volume surge, OBV rising, above intraday VWAP
- **Mean-reversion:** oversold bounce, lower-band bounce
- **Candlestick patterns:** bullish engulfing, hammer
- **Relative strength:** beating the Nifty over 20 days

A stock only shows up when it clears a strength score **and** several families
agree — that "confluence" is what separates a real setup from noise.

## Setup
```bash
pip install -r requirements.txt
export GEMINI_API_KEY="..."     # Windows: setx GEMINI_API_KEY "..."
export TAVILY_API_KEY="..."     # Windows: setx TAVILY_API_KEY "..."
```

## Run it
```bash
python scan.py --demo    # offline demo, see the layout (no keys/internet)
python scan.py --once    # one real scan now
python scan.py --live    # LIVE: loops every 10 min during 09:15–15:30 IST
```
In **--live** mode dad just keeps dads-desk.html open — the page auto-refreshes
itself during market hours and shows a green "Market OPEN" badge with the time.

## Tuning (top of scan.py)
- `MIN_SCORE` / `MIN_FAMILIES` — stricter = fewer, stronger picks
- `REFRESH_MIN` — how often it re-scans while live
- `TOP_N` — how many get full news + AI explanation
- `universe.txt` — your stock list (`.NS` = NSE, `.BO` = BSE)
- `DADSDESK_LANG=hi` — Hindi explanations

## Honest limits — read these
1. **The machine must stay on.** "Live during hours" means this program keeps
   running on a computer that's on during the trading day (dad's PC, or a cheap
   always-on box/cloud). When it's off, the page just stops updating.
2. **Free data is slightly delayed.** yfinance gives near-real-time, not
   tick-by-tick. For true real-time you'd plug in a broker feed (e.g. Zerodha
   Kite Connect) — the data layer (`fetch()`) is written so that's a small swap.
   Tell me when you want it and I'll wire Kite in.
3. **It can be wrong.** It's a very good filter, not a fortune teller. The size
   of each bet and the exit are human decisions. Never risk money the family
   can't afford to lose; if a stock hits its safety line, sell.
