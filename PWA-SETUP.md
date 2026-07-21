# Dad's Desk — the installable app (PWA)

You now have two halves:

- **The engine** (`scan.py`) — does the scanning, writes `pwa/data.json`.
- **The PWA** (`pwa/` folder) — the app dad installs on his phone. It reads
  `data.json` and shows the picks. Works offline (shows the last list).

The app can't fetch market data or hold your API keys itself (phones block that,
and keys would leak). So the engine produces the data; the app just displays it.

---

## Fastest way to see it work (2 minutes, on your computer)

```bash
python scan.py --demo          # writes a demo pwa/data.json (fake numbers)
cd pwa
python -m http.server 8000
```
Open **http://localhost:8000** in Chrome. You'll see the app with a red DEMO bar.
On your phone (same Wi-Fi) open **http://YOUR-PC-IP:8000** and Chrome will offer
"Add to Home screen" — that installs it like a real app.

For real numbers, run `python scan.py --once` instead of `--demo` first.

---

## The proper way — runs itself, no laptop on (free, ~20 min setup)

This uses GitHub to run the scan on a schedule and to host the app.

1. **Make a free GitHub account** and create a new **public** repository, e.g.
   `dads-desk`. Upload every file from this folder (keep the structure — the
   `pwa/` folder and the `.github/` folder must stay where they are).

2. **Add your keys as secrets** (they stay hidden on GitHub, never in the app):
   repo → **Settings → Secrets and variables → Actions → New repository secret**
   - `GEMINI_API_KEY` = your Gemini key
   - `TAVILY_API_KEY` = your Tavily key
   - (optional) under **Variables**, add `DADSDESK_LANG` = `hi` for Hindi.

3. **Turn on the scheduler:** repo → **Actions** tab → enable workflows →
   open **"Dad's Desk scan"** → **Run workflow** once to test. It scans and
   commits a fresh `pwa/data.json`. After that it runs itself every 15 minutes
   during market hours.

4. **Host the app:** repo → **Settings → Pages** → Source: **Deploy from a
   branch**, Branch: **main / (root)** → Save. After a minute your app is live at:
   ```
   https://YOUR-USERNAME.github.io/dads-desk/pwa/
   ```

5. **Install on dad's phone:** open that link in Chrome (Android) or Safari
   (iPhone) → menu → **Add to Home Screen**. Now he has an app icon. Tapping it
   shows the latest picks; it refreshes itself and works even with patchy signal.

That's it — the scan runs on GitHub's servers on a timer, publishes the list,
and dad's installed app picks it up. Nothing on your side needs to stay running.

---

## Notes
- Data is Yahoo's, roughly **15 minutes delayed** — the app says so on screen.
- Want true real-time? That needs a broker feed (Zerodha Kite). Ask me and I'll
  wire it into `fetch()`; the rest stays the same.
- Change dad's stock list anytime by editing `universe.txt` in the repo.
- Reminder: this is a strong filter, not a fortune teller. It never says how much
  to buy or when exactly to sell — those stay a human's decision.
