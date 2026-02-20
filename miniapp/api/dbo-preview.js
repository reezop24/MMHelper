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

  const tf = String(req.query.tf || "m5").toLowerCase();
  const limit = String(req.query.limit || "400");
  const base = process.env.DBO_PREVIEW_UPSTREAM_URL || "http://194.233.71.34/api/dbo-preview";
  const upstream = `${base}?tf=${encodeURIComponent(tf)}&limit=${encodeURIComponent(limit)}`;

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
