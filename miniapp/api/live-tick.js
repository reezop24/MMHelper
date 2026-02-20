export default async function handler(req, res) {
  if (req.method === "OPTIONS") {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    res.status(204).end();
    return;
  }

  if (req.method !== "GET") {
    res.status(405).json({ ok: false, error: "method_not_allowed" });
    return;
  }

  const upstream =
    process.env.LIVE_TICK_UPSTREAM_URL || "http://194.233.71.34/api/live-tick.json";

  try {
    const response = await fetch(upstream, { cache: "no-store" });
    if (!response.ok) {
      res.status(response.status).json({ ok: false, error: "upstream_http_error" });
      return;
    }
    const payload = await response.json();
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Cache-Control", "no-store, max-age=0");
    res.status(200).json(payload);
  } catch (err) {
    res.status(503).json({ ok: false, error: "upstream_unreachable", detail: String(err) });
  }
}
