#!/usr/bin/env python3
"""Generate self-contained SVG UI mockups for the README.

The frontend is a dark-theme dashboard (Next.js + Tailwind `neutral` palette).
These SVGs reproduce that look faithfully so the README can show the system
without committing binary screenshots — matching the project convention of
hand-drawn SVG assets (see frontend/components/manual/Diagrams.tsx).

Run: python3 docs/images/_generate.py
"""
import random
from pathlib import Path

# --- shared palette (Tailwind neutral dark theme) ---------------------------
BG = "#0a0a0a"        # neutral-950 page
PANEL = "#171717"     # neutral-900 panel
PANEL2 = "#1c1c1f"    # slightly lighter inner
BORDER = "#262626"    # neutral-800
TXT = "#e5e5e5"       # neutral-200
MUT = "#a1a1aa"       # neutral-400
DIM = "#71717a"       # neutral-500
INDIGO = "#4f46e5"
GREEN = "#16a34a"
GREEN_T = "#22c55e"
RED = "#ef4444"
BLUE = "#2563eb"
PURPLE = "#9333ea"
AMBER = "#d97706"
FONT = 'font-family="Segoe UI, Helvetica, Arial, sans-serif"'

OUT = Path(__file__).parent


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def panel(x, y, w, h, fill=PANEL):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{BORDER}"/>'


def chip(x, y, label, fill, w=None, tcol="#ffffff", fs=12):
    w = w if w else 16 + len(label) * 7
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="22" rx="5" fill="{fill}"/>'
        f'<text x="{x + w/2}" y="{y + 15}" text-anchor="middle" fill="{tcol}" font-size="{fs}" {FONT}>{esc(label)}</text>'
    )


def text(x, y, s, fill=TXT, fs=13, anchor="start", weight="normal"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" font-size="{fs}" font-weight="{weight}" {FONT}>{esc(s)}</text>'


def input_box(x, y, w, label, fill=PANEL2):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="24" rx="5" fill="{fill}" stroke="{BORDER}"/>'
        + text(x + 8, y + 16, label, MUT, 12)
    )


# --- candlestick chart ------------------------------------------------------
def candles(x, y, w, h, n=26, seed=7):
    rnd = random.Random(seed)
    price = 100.0
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#09090b"/>']
    # gridlines
    for i in range(1, 4):
        gy = y + h * i / 4
        out.append(f'<line x1="{x}" y1="{gy:.1f}" x2="{x+w}" y2="{gy:.1f}" stroke="{BORDER}" stroke-width="0.5"/>')
    series = []
    for _ in range(n):
        o = price
        price += rnd.uniform(-4, 4.4)
        c = price
        hi = max(o, c) + rnd.uniform(0.4, 3)
        lo = min(o, c) - rnd.uniform(0.4, 3)
        series.append((o, c, hi, lo))
    lows = min(s[3] for s in series)
    highs = max(s[2] for s in series)
    rng = highs - lows or 1
    cw = w / n
    bodyw = cw * 0.55

    def py(v):
        return y + h - (v - lows) / rng * (h - 12) - 6
    for i, (o, c, hi, lo) in enumerate(series):
        cx = x + cw * (i + 0.5)
        col = GREEN_T if c >= o else RED
        out.append(f'<line x1="{cx:.1f}" y1="{py(hi):.1f}" x2="{cx:.1f}" y2="{py(lo):.1f}" stroke="{col}" stroke-width="1"/>')
        top = py(max(o, c))
        bot = py(min(o, c))
        out.append(f'<rect x="{cx - bodyw/2:.1f}" y="{top:.1f}" width="{bodyw:.1f}" height="{max(bot-top,1):.1f}" fill="{col}"/>')
    return "\n".join(out)


def equity_path(x, y, w, h, seed=3, up=True):
    rnd = random.Random(seed)
    n = 40
    v = 0.0
    pts = []
    for _ in range(n):
        v += rnd.uniform(-1, 1.6 if up else 0.6)
        pts.append(v)
    lo, hi = min(pts), max(pts)
    rng = hi - lo or 1
    d = []
    for i, p in enumerate(pts):
        px = x + i / (n - 1) * w
        ppy = y + h - (p - lo) / rng * h
        d.append(f'{"M" if i==0 else "L"}{px:.1f},{ppy:.1f}')
    col = GREEN_T if pts[-1] >= pts[0] else RED
    return f'<path d="{" ".join(d)}" fill="none" stroke="{col}" stroke-width="1.5"/>'


# ---------------------------------------------------------------------------
def dashboard():
    W, H = 1200, 760
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-size="13">']
    s.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    # header
    s.append(text(24, 40, "AI Trade Flow", TXT, 22, weight="bold"))
    s.append(text(196, 40, "crypto · 台股 (元大) · 美股 (元大複委託 / Firstrade)", DIM, 13))
    s.append(chip(W - 150, 24, "📖 使用說明書", INDIGO, w=126))

    colx, colw = 24, 740
    rx, rw = 784, 392

    # ---- Market panel ----
    my, mh = 64, 300
    s.append(panel(colx, my, colw, mh))
    s.append(text(colx + 16, my + 28, "Market", TXT, 15, weight="bold"))
    s.append(input_box(colx + 92, my + 12, 110, "BTC/USDT"))
    s.append(input_box(colx + 210, my + 12, 56, "1h"))
    s.append(chip(colx + 274, my + 12, "AI Signal", INDIGO, w=78))
    s.append(candles(colx + 16, my + 48, colw - 32, 150))
    # AI signal result box
    ay = my + 212
    s.append(f'<rect x="{colx+16}" y="{ay}" width="{colw-32}" height="72" rx="6" fill="{PANEL2}" stroke="{BORDER}"/>')
    s.append(text(colx + 28, ay + 26, "BUY", GREEN_T, 14, weight="bold"))
    s.append(text(colx + 66, ay + 26, "(confidence 72% · claude)", MUT, 12))
    s.append(text(colx + 28, ay + 50, "MACD 黃金交叉且 RSI 自超賣回升,短線動能轉強;量能放大支持續攻,", MUT, 12))
    s.append(text(colx + 28, ay + 66, "惟接近前高壓力,建議分批進場並設停損。", MUT, 12))

    # ---- Workflow Builder panel ----
    wy, wh = my + mh + 16, 196
    s.append(panel(colx, wy, colw, wh))
    s.append(text(colx + 16, wy + 28, "Workflow Builder", TXT, 15, weight="bold"))
    for i, (lbl, col) in enumerate([("+ data_source", PANEL2), ("+ strategy", PANEL2), ("+ ai_signal", PANEL2), ("+ order", PANEL2), ("+ logger", PANEL2)]):
        s.append(chip(colx + 168 + i * 86, wy + 14, lbl, col, w=82, tcol=MUT, fs=11))
    s.append(chip(colx + colw - 150, wy + 14, "Save", BLUE, w=58))
    s.append(chip(colx + colw - 86, wy + 14, "Run", GREEN, w=54))
    # node graph
    gy = wy + 52
    s.append(f'<rect x="{colx+16}" y="{gy}" width="{colw-32}" height="124" rx="6" fill="#09090b" stroke="{BORDER}"/>')
    nodes = [("data_source", "BTC/USDT · 1h", GREEN), ("strategy", "ma_cross 10/20", PURPLE), ("order", "qty 0.01", AMBER), ("logger", "", DIM)]
    nx = colx + 40
    centers = []
    for i, (t, sub, col) in enumerate(nodes):
        x0 = nx + i * 168
        s.append(f'<rect x="{x0}" y="{gy+34}" width="140" height="54" rx="8" fill="{PANEL2}" stroke="{col}"/>')
        s.append(f'<rect x="{x0}" y="{gy+34}" width="140" height="18" rx="8" fill="{col}" opacity="0.25"/>')
        s.append(text(x0 + 10, gy + 48, t, TXT, 12, weight="bold"))
        if sub:
            s.append(text(x0 + 10, gy + 72, sub, MUT, 11))
        centers.append((x0, x0 + 140, gy + 61))
    for i in range(len(centers) - 1):
        x1 = centers[i][1]
        x2 = centers[i + 1][0]
        yy = centers[i][2]
        s.append(f'<line x1="{x1}" y1="{yy}" x2="{x2}" y2="{yy}" stroke="{DIM}" stroke-width="1.5" marker-end="url(#ar)"/>')

    # ---- Backtest panel ----
    by, bh = wy + wh + 16, 168
    s.append(panel(colx, by, colw, bh))
    s.append(text(colx + 16, by + 28, "Backtest", TXT, 15, weight="bold"))
    s.append(chip(colx + 360, by + 14, "Run", INDIGO, w=50))
    s.append(chip(colx + 416, by + 14, "Compare all", PURPLE, w=92))
    s.append(chip(colx + 514, by + 14, "Optimize", AMBER, w=78))
    s.append(equity_path(colx + 16, by + 44, colw - 32, 46, up=True))
    metrics = [("Return", "+18.42%", GREEN_T), ("Buy & Hold", "+11.07%", GREEN_T), ("Max DD", "-7.85%", RED), ("Trades", "14 (57% win)", TXT)]
    mw = (colw - 32 - 3 * 10) / 4
    for i, (lbl, val, col) in enumerate(metrics):
        x0 = colx + 16 + i * (mw + 10)
        s.append(f'<rect x="{x0}" y="{by+100}" width="{mw}" height="50" rx="6" fill="{PANEL2}"/>')
        s.append(text(x0 + 12, by + 120, lbl, DIM, 11))
        s.append(text(x0 + 12, by + 140, val, col, 14, weight="bold"))

    # ---- Portfolio panel (right) ----
    py0, ph = 64, 286
    s.append(panel(rx, py0, rw, ph))
    s.append(text(rx + 16, py0 + 28, "Portfolio", TXT, 15, weight="bold"))
    s.append(chip(rx + 112, py0 + 12, "PAPER", GREEN, w=58))
    s.append(chip(rx + rw - 96, py0 + 12, "Reset paper", PANEL2, w=80, tcol=MUT, fs=11))
    stats = [("Cash", "8,420.55"), ("Positions", "1,640.00"), ("Equity", "10,060.55")]
    sw = (rw - 32 - 2 * 8) / 3
    for i, (lbl, val) in enumerate(stats):
        x0 = rx + 16 + i * (sw + 8)
        s.append(f'<rect x="{x0}" y="{py0+44}" width="{sw}" height="46" rx="6" fill="{PANEL2}"/>')
        s.append(text(x0 + 10, py0 + 62, lbl, DIM, 11))
        s.append(text(x0 + 10, py0 + 80, val, TXT, 13, weight="bold"))
    # positions table
    s.append(text(rx + 16, py0 + 112, "Symbol      Qty       Avg        Price       uPnL", DIM, 11))
    rows = [("BTC/USDT", "0.020", "61,200", "62,050", "+17.00", GREEN_T), ("ETH/USDT", "0.300", "3,380", "3,300", "-24.00", RED)]
    for i, (sym, qty, avg, pr, pnl, col) in enumerate(rows):
        yy = py0 + 134 + i * 22
        s.append(f'<line x1="{rx+16}" y1="{yy-14}" x2="{rx+rw-16}" y2="{yy-14}" stroke="{BORDER}" stroke-width="0.5"/>')
        s.append(text(rx + 16, yy, sym, TXT, 11))
        s.append(text(rx + 108, yy, qty, MUT, 11))
        s.append(text(rx + 168, yy, avg, MUT, 11))
        s.append(text(rx + 244, yy, pr, MUT, 11))
        s.append(text(rx + 320, yy, pnl, col, 11))
    s.append(text(rx + 16, py0 + 206, "Recent orders", MUT, 12, weight="bold"))
    orders = [("BUY 0.01 BTC/USDT", "@ 61,200", GREEN_T), ("SELL 0.02 ETH/USDT", "@ 3,300", RED), ("BUY 0.30 ETH/USDT", "@ 3,380", GREEN_T)]
    for i, (o, pr, col) in enumerate(orders):
        yy = py0 + 228 + i * 18
        s.append(text(rx + 16, yy, o, col, 11))
        s.append(text(rx + rw - 16, yy, pr, MUT, 11, anchor="end"))

    # ---- Notifications panel (right) ----
    ny, nh = py0 + ph + 16, 380
    s.append(panel(rx, ny, rw, nh))
    s.append(text(rx + 16, ny + 28, "Notifications", TXT, 15, weight="bold"))
    s.append(chip(rx + rw - 70, ny + 12, "3 new", INDIGO, w=54, fs=11))
    notif = [
        ("order", "Filled BUY 0.01 BTC/USDT @ 61,200", GREEN_T, "12:04"),
        ("signal", "AI: BUY BTC/USDT (conf 72%)", INDIGO, "12:03"),
        ("schedule", "Workflow #2 ran — ok", MUT, "12:00"),
        ("signal", "ma_cross: SELL ETH/USDT", RED, "11:48"),
        ("order", "Filled SELL 0.02 ETH/USDT @ 3,300", RED, "11:48"),
        ("risk", "Order blocked: position cap (422)", AMBER, "11:30"),
    ]
    for i, (kind, msg, col, ts) in enumerate(notif):
        yy = ny + 52 + i * 50
        s.append(f'<rect x="{rx+16}" y="{yy}" width="{rw-32}" height="42" rx="6" fill="{PANEL2}" stroke="{BORDER}"/>')
        s.append(chip(rx + 26, yy + 9, kind, "#27272a", w=56, tcol=col, fs=10))
        s.append(text(rx + 92, yy + 18, msg, TXT, 11))
        s.append(text(rx + rw - 26, yy + 18, ts, DIM, 10, anchor="end"))
        s.append(text(rx + 92, yy + 33, "in-app feed · optional webhook", DIM, 9))

    s.append(f'<defs><marker id="ar" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="{DIM}"/></marker></defs>')
    s.append("</svg>")
    (OUT / "dashboard.svg").write_text("\n".join(s))


def main():
    dashboard()
    print("wrote dashboard.svg")


if __name__ == "__main__":
    main()
