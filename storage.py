"""
Dad's Desk V2 — SQLite history.
Stores every scan and every recommendation so we can show history, spot
"new today" picks, and (Phase 7) backtest and measure real hit-rates.
"""
import sqlite3, json, datetime as dt
import config

def _conn():
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS scans(
            run_id   TEXT PRIMARY KEY,
            ts       TEXT,
            market   TEXT,
            n_scanned INTEGER,
            n_reco    INTEGER
        );
        CREATE TABLE IF NOT EXISTS picks(
            run_id     TEXT,
            ts         TEXT,
            symbol     TEXT,
            name       TEXT,
            price      REAL,
            change     REAL,
            score      REAL,
            confidence INTEGER,
            risk       TEXT,
            status     TEXT,
            target_ref REAL,
            stop_ref   REAL,
            holding    TEXT,
            strategies TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_picks_symbol ON picks(symbol);
        CREATE INDEX IF NOT EXISTS ix_picks_run    ON picks(run_id);
        """)

def save_run(market, n_scanned, recos):
    init()
    run_id = dt.datetime.now(config.IST).strftime("%Y%m%d-%H%M%S")
    ts = dt.datetime.now(config.IST).isoformat()
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO scans VALUES(?,?,?,?,?)",
                  (run_id, ts, market, n_scanned, len(recos)))
        for s in recos:
            c.execute("""INSERT INTO picks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                run_id, ts, s["symbol"], s["name"], s["price"], s["change"],
                s["score"], s["confidence"], s["risk"], s["status"],
                s["target_ref"], s["stop_ref"], s["holding"],
                json.dumps(s.get("reasons", [])),
            ))
    return run_id

def previous_symbols():
    """Symbols recommended in the run before the latest — to flag what's NEW."""
    init()
    with _conn() as c:
        runs = [r["run_id"] for r in c.execute(
            "SELECT run_id FROM scans ORDER BY run_id DESC LIMIT 2")]
        if len(runs) < 2: return set()
        prev = runs[1]
        return {r["symbol"] for r in c.execute(
            "SELECT symbol FROM picks WHERE run_id=? AND status='RECOMMENDED'", (prev,))}

def history(symbol, limit=30):
    init()
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT ts,score,confidence,price,status FROM picks WHERE symbol=? "
            "ORDER BY ts DESC LIMIT ?", (symbol, limit))]
