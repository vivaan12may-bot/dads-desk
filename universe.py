"""
Dad's Desk V2 — stock universe.
Expandable: built-in index lists + NSE constituent CSVs + the old universe.txt.
Returns a de-duplicated list of (yahoo_symbol, friendly_name).
"""
import os, csv
import config

# ---- built-in NIFTY 50 (Yahoo symbols) ----
NIFTY50 = [
 "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS","SBIN.NS",
 "BHARTIARTL.NS","ITC.NS","LT.NS","HINDUNILVR.NS","AXISBANK.NS","KOTAKBANK.NS",
 "TATAMOTORS.NS","MARUTI.NS","SUNPHARMA.NS","TITAN.NS","WIPRO.NS","ULTRACEMCO.NS",
 "BAJFINANCE.NS","ASIANPAINT.NS","NTPC.NS","POWERGRID.NS","TATASTEEL.NS",
 "ADANIENT.NS","JSWSTEEL.NS","HCLTECH.NS","COALINDIA.NS","ONGC.NS","M&M.NS",
 "TECHM.NS","NESTLEIND.NS","BAJAJFINSV.NS","GRASIM.NS","HDFCLIFE.NS","SBILIFE.NS",
 "DRREDDY.NS","CIPLA.NS","BRITANNIA.NS","EICHERMOT.NS","HEROMOTOCO.NS","DIVISLAB.NS",
 "APOLLOHOSP.NS","TATACONSUM.NS","BAJAJ-AUTO.NS","INDUSINDBK.NS","ADANIPORTS.NS",
 "HINDALCO.NS","BPCL.NS","SHRIRAMFIN.NS","LTIM.NS",
]

BUILTIN = {"nifty50": NIFTY50}

# NIFTY Next 50 tier (liquid large/mid caps). Add the official NSE CSV to
# indices/ for the full Nifty 500 — this built-in just gives a bigger default.
NIFTY_NEXT50 = [
 "DMART.NS","PIDILITIND.NS","DABUR.NS","GODREJCP.NS","HAVELLS.NS","SIEMENS.NS",
 "ABB.NS","BOSCHLTD.NS","BERGEPAINT.NS","MARICO.NS","COLPAL.NS","GAIL.NS","IOC.NS",
 "VEDL.NS","DLF.NS","GODREJPROP.NS","AMBUJACEM.NS","ACC.NS","BANKBARODA.NS","PNB.NS",
 "CANBK.NS","IDFCFIRSTB.NS","AUBANK.NS","CHOLAFIN.NS","ICICIPRULI.NS","ICICIGI.NS",
 "MUTHOOTFIN.NS","PFC.NS","RECLTD.NS","TATAPOWER.NS","ADANIGREEN.NS","ADANIPOWER.NS",
 "TORNTPHARM.NS","LUPIN.NS","AUROPHARMA.NS","ZYDUSLIFE.NS","ALKEM.NS","TRENT.NS",
 "NAUKRI.NS","PAYTM.NS","POLICYBZR.NS","IRCTC.NS","INDIGO.NS","INDHOTEL.NS",
 "JINDALSTEL.NS","SAIL.NS","NMDC.NS","JUBLFOOD.NS","PAGEIND.NS","MCDOWELL-N.NS",
 "BIOCON.NS","SRF.NS","UPL.NS","PIIND.NS","DIXON.NS","LTTS.NS","PERSISTENT.NS",
 "COFORGE.NS","MPHASIS.NS","TATAELXSI.NS","MOTHERSON.NS","BHARATFORG.NS","BEL.NS",
 "HAL.NS","CONCOR.NS","IRFC.NS","TVSMOTOR.NS","BALKRISIND.NS","ASHOKLEY.NS",
]
# sample mid / small caps — for full coverage drop the official NSE
# midcap150 / smallcap250 CSVs into indices/ (tagged via config.INDEX_CSV_FILES).
MIDCAP = [
 "POLYCAB.NS","SUPREMEIND.NS","ASTRAL.NS","CUMMINSIND.NS","OBEROIRLTY.NS","PRESTIGE.NS",
 "MRF.NS","APLAPOLLO.NS","FEDERALBNK.NS","BANDHANBNK.NS","INDUSTOWER.NS","ESCORTS.NS",
 "MFSL.NS","DEEPAKNTR.NS","TATACOMM.NS","PATANJALI.NS","PHOENIXLTD.NS","COROMANDEL.NS",
 "AARTIIND.NS","CROMPTON.NS","VOLTAS.NS","BATAINDIA.NS","GLENMARK.NS","IPCALAB.NS",
 "LAURUSLABS.NS","LALPATHLAB.NS","METROPOLIS.NS","GODREJIND.NS","SUNDARMFIN.NS",
]
SMALLCAP = [
 "IRCON.NS","RAILTEL.NS","HUDCO.NS","NBCC.NS","ENGINERSIN.NS","KEC.NS","CESC.NS",
 "CDSL.NS","BSE.NS","ANGELONE.NS","IEX.NS","MCX.NS","KFINTECH.NS","HAPPSTMNDS.NS",
 "MASTEK.NS","BIRLASOFT.NS","SONATSOFTW.NS","CYIENT.NS","JBCHEPHARM.NS","GRANULES.NS",
 "GUJGASLTD.NS","BALRAMCHIN.NS","RELAXO.NS","FINPIPE.NS","SUNTECK.NS",
]
BUILTIN["nifty100"] = NIFTY50 + NIFTY_NEXT50
BUILTIN["midcap"]   = MIDCAP
BUILTIN["smallcap"] = SMALLCAP

# which cap each built-in list represents
CAP_BY_LIST = {"nifty50":"large", "nifty100":"large", "midcap":"mid", "smallcap":"small"}

FRIENDLY = {
 "RELIANCE.NS":"Reliance Industries","TCS.NS":"Tata Consultancy Services",
 "HDFCBANK.NS":"HDFC Bank","INFY.NS":"Infosys","ICICIBANK.NS":"ICICI Bank",
 "SBIN.NS":"State Bank of India","BHARTIARTL.NS":"Bharti Airtel","ITC.NS":"ITC",
 "LT.NS":"Larsen & Toubro","HINDUNILVR.NS":"Hindustan Unilever","AXISBANK.NS":"Axis Bank",
 "KOTAKBANK.NS":"Kotak Mahindra Bank","TATAMOTORS.NS":"Tata Motors","MARUTI.NS":"Maruti Suzuki",
 "SUNPHARMA.NS":"Sun Pharma","TITAN.NS":"Titan","WIPRO.NS":"Wipro","ULTRACEMCO.NS":"UltraTech Cement",
 "BAJFINANCE.NS":"Bajaj Finance","ASIANPAINT.NS":"Asian Paints","NTPC.NS":"NTPC",
 "POWERGRID.NS":"Power Grid","TATASTEEL.NS":"Tata Steel","ADANIENT.NS":"Adani Enterprises",
 "JSWSTEEL.NS":"JSW Steel","HCLTECH.NS":"HCL Technologies","COALINDIA.NS":"Coal India",
 "ONGC.NS":"ONGC","M&M.NS":"Mahindra & Mahindra","TECHM.NS":"Tech Mahindra",
 "NESTLEIND.NS":"Nestle India","BAJAJFINSV.NS":"Bajaj Finserv","GRASIM.NS":"Grasim",
 "HDFCLIFE.NS":"HDFC Life","SBILIFE.NS":"SBI Life","DRREDDY.NS":"Dr Reddy's",
 "CIPLA.NS":"Cipla","BRITANNIA.NS":"Britannia","EICHERMOT.NS":"Eicher Motors",
 "HEROMOTOCO.NS":"Hero MotoCorp","DIVISLAB.NS":"Divi's Labs","APOLLOHOSP.NS":"Apollo Hospitals",
 "TATACONSUM.NS":"Tata Consumer","BAJAJ-AUTO.NS":"Bajaj Auto","INDUSINDBK.NS":"IndusInd Bank",
 "ADANIPORTS.NS":"Adani Ports","HINDALCO.NS":"Hindalco","BPCL.NS":"BPCL",
 "SHRIRAMFIN.NS":"Shriram Finance","LTIM.NS":"LTIMindtree",
}

def tv_symbol(y):
    if y.endswith(".NS"): return "NSE:" + y[:-3].replace("&","_")
    if y.endswith(".BO"): return "BSE:" + y[:-3].replace("&","_")
    return y

def name_of(sym):
    return FRIENDLY.get(sym, sym.split(".")[0].replace("&"," & ").title())

def _from_index_csv(path):
    """NSE constituent CSVs have a 'Symbol' column (plain NSE ticker)."""
    out = []
    try:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                s = (row.get("Symbol") or row.get("SYMBOL") or "").strip()
                if s:
                    out.append(s.upper() + ".NS")
    except Exception as e:
        print(f"  ! could not read {os.path.basename(path)}: {e}")
    return out

def load():
    """Return an ordered, de-duplicated list of (symbol, name, cap)."""
    tagged = []   # (symbol, cap)
    for key in config.UNIVERSE_LISTS:
        cap = CAP_BY_LIST.get(key, "large")
        for s in BUILTIN.get(key, []):
            tagged.append((s, cap))
    for entry in config.INDEX_CSV_FILES:
        fn, cap = (entry if isinstance(entry, (list, tuple)) else (entry, "large"))
        for s in _from_index_csv(os.path.join(config.INDICES_DIR, fn)):
            tagged.append((s, cap))
    if config.INCLUDE_TXT:
        txt = os.path.join(config.HERE, "universe.txt")
        if os.path.exists(txt):
            with open(txt) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        tagged.append((line if "." in line else line + ".NS", "large"))

    seen, ordered = set(), []
    for s, cap in tagged:
        s = s.upper()
        if s not in seen:
            seen.add(s); ordered.append((s, name_of(s), cap))
    return ordered
