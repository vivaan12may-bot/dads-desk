Drop NSE index constituent CSVs here to expand the universe beyond NIFTY 50.

1. Download from NSE, e.g. "ind_nifty500list.csv" (has a "Symbol" column).
2. Put the file in this folder.
3. In config.py add its filename to INDEX_CSV_FILES, e.g.:
       INDEX_CSV_FILES = ["ind_nifty500list.csv"]
4. Run: python scan.py --once

The loader also still reads universe.txt, so your old custom list keeps working.
