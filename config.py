"""
Dad's Desk V2 — central configuration.
Everything tunable lives here so the rest of the code stays clean.
"""
import os
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
PWA_DIR     = os.path.join(HERE, "pwa")
INDICES_DIR = os.path.join(HERE, "indices")
DB_PATH     = os.path.join(HERE, "dadsdesk.db")

# ---- market clock (IST) ----
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
MARKET_OPEN_MIN  = 9*60 + 15     # 09:15
MARKET_CLOSE_MIN = 15*60 + 30    # 15:30
# NSE trading holidays — update once a year from nseindia.com. Weekends are
# handled automatically, so this only needs the special weekday holidays.
HOLIDAYS = set([
    # "YYYY-MM-DD",  add the current year's NSE holiday list here
])

# ---- which universe to scan ----
# Built-in NIFTY 50 always available. Drop NSE constituent CSVs into indices/
# (e.g. ind_nifty500list.csv) and list their filenames here to expand.
UNIVERSE_LISTS   = ["nifty100", "midcap", "smallcap"]   # large + mid + small out of the box
INDEX_CSV_FILES  = []                    # e.g. [["ind_niftymidcap150list.csv","mid"]]
INCLUDE_TXT      = True                  # also read the old universe.txt (back-compat)

# ---- scan thresholds ----
MIN_SCORE    = 6      # min weighted strategy score to be RECOMMENDED
MIN_FAMILIES = 3      # must fire across at least this many strategy families
WATCH_SCORE  = 4      # below RECOMMENDED but worth watching
TOP_N        = 8      # how many recommendations to fully enrich + publish
ENRICH_N     = 8      # how many get live news + AI wording (rest use built-in text)
PUBLISH_N    = 30     # how many rows to show in the app's list (Strong Buy/Buy/Watch)
PUBLISH_PER_TF = 90   # max rows published per timeframe (buy+early+sell, before cap filter)
BUY_N   = 50          # per timeframe: top buys published
EARLY_N = 30          # per timeframe: top early-reversal picks
SELL_N  = 30          # per timeframe: top sell / weakness picks

# ---- live loop ----
REFRESH_MIN  = 10     # minutes between scans while market is open
EXPLAIN_TTL  = 30     # minutes to cache each AI explanation (saves API quota)

# ---- strategy family weights ----
FAMILY_W = {"trend":1.4, "momentum":1.2, "breakout":1.3, "volume":1.0,
            "meanrev":0.7, "pattern":0.8, "relstrength":1.2}

# ---- feature flags (auto-off when keys/data are missing) ----
USE_NEWS = bool(os.environ.get("TAVILY_API_KEY"))
USE_AI   = bool(os.environ.get("GEMINI_API_KEY"))
LANG     = os.environ.get("DADSDESK_LANG", "en")

# ---- data source ----
DATA_PERIOD_DAILY = "5y"   # need long history for monthly timeframe
DATA_INTERVAL_INTRADAY = "15m"
FETCH_TRIES = 3
FETCH_WORKERS = 12       # concurrent fetches (higher = faster but more rate-limit risk)
MAX_STOCKS = 500         # hard cap per scan (free-data ceiling; see V2-NOTES)
DELAYED_NOTE = "Live · ~15 min delayed (Yahoo)"
