# Deploy Dad's Desk to Firebase (full PWA)

Firebase Hosting serves the app (the `pwa/` folder) on a fast, free, HTTPS URL
your dad can install like a real app. The Python engine still does the scanning
and writes `pwa/data.json`; Firebase just serves it.

Two halves:
- **App** → Firebase Hosting (this guide).
- **Fresh data** → either you run `deploy.bat` when you want, or the included
  GitHub Action scans + deploys automatically during market hours.

---

## A. First deploy (about 15 min, Windows 11)

1. **Make a Firebase project** — go to https://console.firebase.google.com →
   *Add project* → name it (e.g. `dads-desk`) → you can skip Analytics.
   Note the **Project ID** it gives you (e.g. `dads-desk-1a2b3`).

2. **Put your Project ID in `.firebaserc`** — open the file and replace
   `YOUR_FIREBASE_PROJECT_ID` with it. Save.

3. **Install the tools** (needs Node.js from https://nodejs.org):
   ```
   npm install -g firebase-tools
   ```

4. **Log in:**
   ```
   firebase login
   ```
   (opens a browser, sign in with the same Google account).

5. **Generate data + deploy** — from inside the `dads-desk-engine` folder:
   ```
   pip install -r requirements.txt
   python scan.py --once
   firebase deploy --only hosting
   ```
   It prints a **Hosting URL** like `https://dads-desk-1a2b3.web.app`. That's your
   live app.

6. **Install on dad's phone** — open that URL in Chrome (Android) or Safari
   (iPhone) → menu → **Add to Home Screen**. Done — real app icon.

From now on, to refresh the data + app in one step just double-click **`deploy.bat`**
(it runs the scan, then deploys).

---

## B. Make it update itself during market hours (no PC on)

Use the included GitHub Action so GitHub scans + deploys for you.

1. Put this project in a **GitHub repo** (public or private).
2. Get a deploy token — on your PC run:
   ```
   firebase login:ci
   ```
   Copy the long token it prints.
3. In the repo: **Settings → Secrets and variables → Actions → New secret**
   - `FIREBASE_TOKEN` = that token
   - `GEMINI_API_KEY`, `TAVILY_API_KEY` = your keys (optional)
4. **Actions** tab → enable → run **"Dad's Desk — scan & deploy to Firebase"**
   once to test. After that it runs every 15 min during market hours, scans, and
   redeploys with fresh data. Your dad's installed app just updates itself.

> Modern alternative to the token: a Firebase **service account** JSON with the
> `FirebaseExtended/action-hosting-deploy` action. The token method above is the
> simplest to start; ask me and I'll switch it to the service-account flow.

---

## Notes
- The service worker is set so the app **always updates** — no more stale
  "undefined stocks" screens. If you ever see an old version, close and reopen
  the app (or pull-to-refresh) and it fetches the latest.
- Free tier is plenty: Firebase Hosting gives 10 GB storage + 360 MB/day transfer
  free — this app is tiny.
- Data is Yahoo's, ~15 min delayed (shown on screen). Real-time needs a paid feed.
- Everything else (universe, timeframes, tabs, cap filters) works exactly as in
  V2-NOTES.md.
