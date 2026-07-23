# Make the Refresh button start a REAL scan

By default the Refresh button just re-downloads whatever was last published.
This makes it actually kick off a fresh scan on demand.

**Why a worker?** The app is public, so it can't hold a GitHub token (anyone
could steal it). A tiny Cloudflare Worker holds the token privately and triggers
the scan when the app asks. Free tier is far more than enough.

---

## 1. Create the worker (5 min)

1. Sign up free at **https://dash.cloudflare.com** → **Workers & Pages**
   → **Create application** → **Create Worker**.
2. Name it `dads-desk-refresh` → **Deploy**.
3. Click **Edit code**. Delete everything in the editor and paste the entire
   contents of **`worker.js`** from this project. → **Deploy**.

## 2. Add the secrets

In the worker → **Settings → Variables and Secrets** → add:

| Name | Value | Type |
|---|---|---|
| `GH_TOKEN` | your fine-grained GitHub token (Actions: Read and write) | **Secret** (encrypt) |
| `GH_REPO` | `YOURNAME/dads-desk` | Text |
| `GH_FILE` | `firebase.yml` | Text |
| `GH_REF` | `main` | Text |

Save / redeploy.

## 3. Point the app at it

Copy the worker URL (looks like `https://dads-desk-refresh.YOURNAME.workers.dev`).

Open **`pwa/app-config.js`** and put it in:

```js
window.DADSDESK_TRIGGER_URL = "https://dads-desk-refresh.YOURNAME.workers.dev";
```

Then push and deploy:

```
git add .
git commit -m "refresh trigger"
git push
```

(or run `deploy.bat`)

## 4. Use it

Open the app → press **↻ Refresh**:
- It starts a real scan on GitHub
- The button shows **Scanning…** and the app polls every 20 s
- New picks land in about **1–3 minutes**, then it says "Updated with a fresh scan"

There's a 60-second cooldown built in so repeated taps don't spam GitHub.

---

## Testing the 15-minute schedule outside market hours

The cron is set to market hours only:

```
*/15 3-10 * * 1-5      # 09:15–15:30 IST, Mon–Fri
```

To prove it works **right now** (any time of day), temporarily change the
cron-job.org schedule to:

```
*/15 * * * *
```

Watch the repo's **Actions** tab — a new run should appear every 15 minutes.
Once you've confirmed it, set it back to `*/15 3-10 * * 1-5` so it doesn't
burn runs overnight.

> Note: outside market hours the data won't change much — the point of the test
> is that a new run *appears* every 15 minutes.
