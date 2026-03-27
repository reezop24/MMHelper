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

  const upstream = process.env.OPS_HUD_UPSTREAM_URL || "";
  if (!upstream) {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.status(503).json({ ok: false, error: "missing_upstream_url" });
    return;
  }

  try {
    const response = await fetch(upstream, { cache: "no-store" });
    const text = await response.text();
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Cache-Control", "no-store, max-age=0");
    res.status(response.status);
    try {
      res.json(JSON.parse(text));
    } catch {
      res.json({ ok: false, error: "invalid_upstream_payload", raw: text.slice(0, 500) });
    }
  } catch (err) {
    res.status(503).json({ ok: false, error: "upstream_unreachable", detail: String(err) });
  }
}
