#!/usr/bin/env python3
"""Export candlestick chart HTML from SQLite candles.db."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, UTC
from pathlib import Path


def load_rows(db_path: Path, timeframe: str, limit: int) -> list[dict[str, float | str]]:
    con = sqlite3.connect(db_path)
    try:
        cur = con.execute(
            """
            SELECT ts, open, high, low, close
            FROM candles
            WHERE timeframe = ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (timeframe, limit),
        )
        rows = cur.fetchall()
    finally:
        con.close()

    rows.reverse()
    out: list[dict[str, float | int]] = []
    for ts, op, hi, lo, cl in rows:
        dt = datetime.strptime(str(ts), "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        out.append(
            {
                "time": int(dt.timestamp()),
                "open": float(op),
                "high": float(hi),
                "low": float(lo),
                "close": float(cl),
            }
        )
    return out


def build_html(title: str, candles: list[dict[str, float | str]]) -> str:
    data_json = json.dumps(candles, ensure_ascii=True)
    return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <style>
    body {{ margin: 0; background: #0b1220; color: #e5e7eb; font-family: Arial, sans-serif; }}
    .wrap {{ max-width: 1100px; margin: 24px auto; padding: 0 12px; }}
    #chart-wrap {{ height: 620px; border: 1px solid #1f2937; border-radius: 10px; overflow: hidden; }}
    #chart {{ width: 100%; height: 100%; display: block; background: #0b1220; }}
    .meta {{ margin-bottom: 10px; font-size: 14px; color: #9ca3af; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h2>{title}</h2>
    <div class=\"meta\">Candles: {len(candles)}</div>
    <div id=\"chart-wrap\"><canvas id=\"chart\"></canvas></div>
  </div>

  <script>
    const data = {data_json};
    const canvas = document.getElementById('chart');
    const wrap = document.getElementById('chart-wrap');
    const ctx = canvas.getContext('2d');

    const theme = {{
      bg: '#0b1220',
      grid: '#1f2937',
      up: '#16a34a',
      down: '#dc2626',
      axis: '#9ca3af'
    }};

    function resizeCanvas() {{
      const dpr = window.devicePixelRatio || 1;
      const w = wrap.clientWidth;
      const h = wrap.clientHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw();
    }}

    function drawGrid(w, h, padL, padR, padT, padB) {{
      ctx.strokeStyle = theme.grid;
      ctx.lineWidth = 1;
      const linesY = 6;
      for (let i = 0; i <= linesY; i++) {{
        const y = padT + ((h - padT - padB) * i / linesY);
        ctx.beginPath();
        ctx.moveTo(padL, y);
        ctx.lineTo(w - padR, y);
        ctx.stroke();
      }}
      const linesX = 8;
      for (let i = 0; i <= linesX; i++) {{
        const x = padL + ((w - padL - padR) * i / linesX);
        ctx.beginPath();
        ctx.moveTo(x, padT);
        ctx.lineTo(x, h - padB);
        ctx.stroke();
      }}
    }}

    function draw() {{
      const w = wrap.clientWidth;
      const h = wrap.clientHeight;
      const padL = 14, padR = 58, padT = 10, padB = 20;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = theme.bg;
      ctx.fillRect(0, 0, w, h);

      if (!data.length) return;
      const lows = data.map(d => d.low);
      const highs = data.map(d => d.high);
      const minP = Math.min(...lows);
      const maxP = Math.max(...highs);
      const priceSpan = Math.max(maxP - minP, 1e-9);

      drawGrid(w, h, padL, padR, padT, padB);

      const cw = (w - padL - padR) / data.length;
      const bodyW = Math.max(1, Math.floor(cw * 0.72));

      const yOf = (p) => padT + ((maxP - p) / priceSpan) * (h - padT - padB);

      for (let i = 0; i < data.length; i++) {{
        const d = data[i];
        const x = padL + i * cw + cw / 2;
        const yH = yOf(d.high), yL = yOf(d.low), yO = yOf(d.open), yC = yOf(d.close);
        const up = d.close >= d.open;
        ctx.strokeStyle = up ? theme.up : theme.down;
        ctx.fillStyle = up ? theme.up : theme.down;

        ctx.beginPath();
        ctx.moveTo(x, yH);
        ctx.lineTo(x, yL);
        ctx.stroke();

        const yTop = Math.min(yO, yC);
        const yBot = Math.max(yO, yC);
        const hBody = Math.max(1, yBot - yTop);
        ctx.fillRect(Math.floor(x - bodyW / 2), Math.floor(yTop), bodyW, Math.floor(hBody));
      }}

      ctx.fillStyle = theme.axis;
      ctx.font = '12px Arial';
      for (let i = 0; i <= 4; i++) {{
        const p = maxP - (priceSpan * i / 4);
        const y = yOf(p);
        ctx.fillText(p.toFixed(2), w - padR + 4, y + 4);
      }}
    }}

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();
  </script>
</body>
</html>
"""


def main() -> None:
    p = argparse.ArgumentParser(description="Export timeframe chart from SQLite")
    p.add_argument("--db", default="/root/mmhelper/db/twelve_data_bot/candles.db")
    p.add_argument("--tf", default="m5", help="timeframe (m5,m15,m30,h1,h4,d1,w1,mn1)")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--out", default="")
    args = p.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    rows = load_rows(db_path, args.tf, args.limit)
    if not rows:
        raise SystemExit(f"No candle data for timeframe: {args.tf}")

    out_path = Path(args.out) if args.out else db_path.parent / f"chart_{args.tf}.html"
    title = f"XAUUSD {args.tf.upper()} Candlestick"
    out_path.write_text(build_html(title, rows), encoding="utf-8")

    print(f"Saved chart: {out_path}")
    print(f"Candles: {len(rows)}")
    print(f"First: {rows[0]['time']}")
    print(f"Last:  {rows[-1]['time']}")


if __name__ == "__main__":
    main()
