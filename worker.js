/**
 * Dad's Desk — refresh trigger (Cloudflare Worker, free tier).
 *
 * The PWA cannot hold a GitHub token (it would be public). This tiny worker
 * holds it as an encrypted secret and triggers the scan workflow on request.
 *
 * Secrets to set in Cloudflare (Settings -> Variables -> Add secret):
 *   GH_TOKEN  = your fine-grained GitHub token (Actions: Read and write)
 *   GH_REPO   = e.g. vivaan12may-bot/dads-desk
 *   GH_FILE   = firebase.yml
 *   GH_REF    = main
 */

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

// simple cooldown so the button can't spam GitHub
let lastRun = 0;
const COOLDOWN_MS = 60 * 1000;

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS });
    }
    if (request.method !== "POST") {
      return json({ ok: false, error: "POST only" }, 405);
    }

    const now = Date.now();
    if (now - lastRun < COOLDOWN_MS) {
      return json({
        ok: true,
        queued: false,
        message: "A scan was just started. Give it a minute.",
      });
    }

    const repo = env.GH_REPO;
    const file = env.GH_FILE || "firebase.yml";
    const ref = env.GH_REF || "main";
    if (!env.GH_TOKEN || !repo) {
      return json({ ok: false, error: "Worker not configured (GH_TOKEN / GH_REPO)" }, 500);
    }

    const url = `https://api.github.com/repos/${repo}/actions/workflows/${file}/dispatches`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": `Bearer ${env.GH_TOKEN}`,
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "dads-desk-worker",
      },
      body: JSON.stringify({ ref }),
    });

    if (res.status === 204) {
      lastRun = now;
      return json({ ok: true, queued: true, message: "Scan started" });
    }
    const text = await res.text();
    return json({ ok: false, status: res.status, error: text.slice(0, 300) }, 502);
  },
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...CORS },
  });
}
