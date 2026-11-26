"""Storyboard frames for presenting a run (slides, blog posts).

For chosen moments of a live run, render the table as people around it would see
it: each person's dominoes in their colour, what was built since the previous
moment highlighted, each person at a seat around the table with a line to where
their hands are working (or a pointing mark), and a summary of what was said and
built in between.

    python3 -m orgsim.storyboard results/pilot/<run>/log.json out_dir [--moments 8]
"""
from __future__ import annotations

import argparse
import json
import math
import os

PALETTE = {0: (47, 111, 176), 1: (192, 86, 58), 2: (63, 143, 90), 3: (138, 91, 181),
           4: (194, 138, 31), 5: (42, 154, 154), 6: (180, 79, 132), 7: (107, 125, 47),
           8: (93, 107, 196), 9: (160, 97, 47)}


def colours(names: list) -> dict:
    return {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(names)}


def seats(names: list, W: float, H: float) -> dict:
    """Seats around the table edge, in table coordinates (outside the table)."""
    spots = [(-4, H * 0.35), (W * 0.35, -4), (W + 4, H * 0.55), (W * 0.6, H + 4),
             (-4, H * 0.75), (W * 0.75, -4), (W + 4, H * 0.2), (W * 0.2, H + 4),
             (W * 0.55, -4), (W * 0.85, H + 4)]
    return {n: spots[i % len(spots)] for i, n in enumerate(names)}


def _font(size: int):
    from PIL import ImageFont
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def crop_bounds(log: dict, W: float = 60, H: float = 40, pad: float = 4.0, aspect: float = 1.45) -> tuple:
    """One view for the whole run: the area any domino ever occupied, padded, at a
    fixed aspect ratio, kept inside the table."""
    xs, ys = [], []
    for rec in log["turns"]:
        for r in rec["snapshot"]:
            xs.append(r[1])
            ys.append(r[2])
    if not xs:
        return 0, 0, W, H
    x0, x1 = max(0, min(xs) - pad), min(W, max(xs) + pad)
    y0, y1 = max(0, min(ys) - pad), min(H, max(ys) + pad)
    w, h = x1 - x0, y1 - y0
    if w / h < aspect:
        grow = h * aspect - w
        x0, x1 = x0 - grow / 2, x1 + grow / 2
    else:
        grow = w / aspect - h
        y0, y1 = y0 - grow / 2, y1 + grow / 2
    dx = max(0, -x0) - max(0, x1 - W)
    dy = max(0, -y0) - max(0, y1 - H)
    x0, x1, y0, y1 = x0 + dx, x1 + dx, y0 + dy, y1 + dy
    return max(0, x0), max(0, y0), min(W, x1), min(H, y1)


def render_frame(snapshot: list, prev_ids: set, names: list, hands: dict, pointing: dict,
                 path: str, bounds: tuple = (0, 0, 60, 40), width_px: int = 1500) -> str:
    """snapshot rows: [id, x, y, angle, state, builder, start]."""
    from PIL import Image, ImageDraw
    col = colours(names)
    bx0, by0, bx1, by1 = bounds
    W, H = bx1 - bx0, by1 - by0
    m = 0.14 * max(W, H)                           # room for seats around the view
    scale = width_px / (W + 2 * m)
    seat = {n: (x + bx0, y + by0) for n, (x, y) in seats(names, W, H).items()}
    seat = {n: (min(max(x, bx0 - m * 0.55), bx1 + m * 0.55), min(max(y, by0 - m * 0.55), by1 + m * 0.55))
            for n, (x, y) in seat.items()}
    PW, PH = int((W + 2 * m) * scale), int((H + 2 * m) * scale)
    img = Image.new("RGB", (PW, PH), (251, 249, 244))
    dr = ImageDraw.Draw(img)
    f_name, f_small = _font(30), _font(24)
    lw = max(4, int(scale * 0.22))

    def px(x, y):
        return ((x - bx0 + m) * scale, (y - by0 + m) * scale)

    dr.rounded_rectangle([px(bx0, by0), px(bx1, by1)], radius=18, fill=(239, 230, 212),
                         outline=(196, 180, 150), width=3)
    for row in snapshot:
        did, x, y, a, state, builder, start = row
        c = col.get(builder, (90, 90, 90))
        new = did not in prev_ids
        rad = math.radians(a)
        ux, uy = math.cos(rad), math.sin(rad)
        if state == "down":
            dr.line([px(x, y), px(x + 0.9 * ux, y + 0.9 * uy)], fill=(205, 70, 60), width=lw)
            continue
        hx, hy = -uy * 0.32, ux * 0.32
        if new:
            dr.ellipse([px(x - 0.48, y - 0.48), px(x + 0.48, y + 0.48)], fill=(255, 222, 110))
        dr.line([px(x - hx, y - hy), px(x + hx, y + hy)], fill=c, width=lw)
        if start:
            cx, cy = px(x, y)
            r = 0.9 * scale
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(30, 140, 70), width=4)
    for n in names:
        sx, sy = px(*seat[n])
        c = col[n]
        target = hands.get(n)
        if target:
            tx, ty = px(*target)
            dr.line([sx, sy, tx, ty], fill=c, width=4)
            dr.ellipse([tx - 12, ty - 12, tx + 12, ty + 12], outline=c, width=5)
        if n in pointing:
            qx, qy = px(*pointing[n])
            dr.line([sx, sy, qx, qy], fill=c, width=2)
            dr.polygon([(qx, qy - 12), (qx - 9, qy + 6), (qx + 9, qy + 6)], fill=c)
        r = 34
        dr.ellipse([sx - r, sy - r, sx + r, sy + r], fill=c)
        dr.text((sx, sy), n[0], fill=(255, 255, 255), font=f_name, anchor="mm")
        label_y = sy - r - 18 if sy > PH - 90 else sy + r + 18
        dr.text((sx, label_y), n, fill=c, font=f_small, anchor="mm")
    img.save(path)
    return path


def hands_at(rec: dict) -> dict:
    """Where each person's hands were working in a beat, from build events."""
    out = {}
    snap = {r[0]: r for r in rec["snapshot"]}
    for e in rec["events"]:
        if e["type"] == "build":
            ids = [i for i in e["placed"] if i in snap] + [i for i, _ in e.get("restood", []) if i in snap]
            if ids:
                xs = [snap[i][1] for i in ids]
                ys = [snap[i][2] for i in ids]
                out[e["who"]] = (sum(xs) / len(xs), sum(ys) / len(ys))
        elif e["type"] in ("take_down", "inspect") and e.get("area"):
            x0, y0, x1, y1 = e["area"]
            out[e["who"]] = ((x0 + x1) / 2, (y0 + y1) / 2)
    return out


def storyboard(log: dict, out_dir: str, cut_minutes: list) -> list:
    """Frames at the given minutes (end of each window). Returns per-moment summaries."""
    os.makedirs(out_dir, exist_ok=True)
    names = [a["name"] for a in log["agents"]]
    turns = log["turns"]
    tables = [r for r in log.get("regions", []) if r.get("kind") == "table"]
    W = max((r["x1"] for r in tables), default=60)
    H = max((r["y1"] for r in tables), default=40)
    bounds = crop_bounds(log, W, H, pad=max(2.0, W / 15))
    moments = []
    prev_ids: set = {r[0] for r in log["initial"]}
    prev_t = -1.0
    last_hands: dict = {}
    for k, minute in enumerate(cut_minutes):
        t_end = minute * 60
        window = [r for r in turns if prev_t < r["time"] < t_end]
        if not window:
            continue
        last = window[-1]
        said, built, took, bumps, points = [], {}, {}, 0, {}
        for r in window:
            for c in r["conversations"]:
                m = c["messages"][0]
                said.append({"clock": r["clock"], "speaker": m["speaker"], "to": m["to"], "text": m["message"],
                             "pointing": bool(m.get("pointing"))})
            for e in r["events"]:
                if e["type"] == "build":
                    built[e["who"]] = built.get(e["who"], 0) + len(e["placed"]) + len(e.get("restood", []))
                elif e["type"] == "take_down":
                    took[e["who"]] = took.get(e["who"], 0) + len(e["ids"])
                elif e["type"] == "bump":
                    bumps += 1
            last_hands.update(hands_at(r))
        recent_hands = {}
        for r in window[-4:]:
            recent_hands.update(hands_at(r))
        path = os.path.join(out_dir, f"moment{k + 1:02d}.png")
        render_frame(last["snapshot"], prev_ids, names, recent_hands, points, path, bounds)
        moments.append({"file": path, "from": prev_t if prev_t >= 0 else 0, "to": t_end,
                        "clock": last["clock"], "said": said, "built": built, "took_down": took,
                        "bumps": bumps, "dominoes_standing": sum(1 for x in last["snapshot"] if x[4] == "up"),
                        "hands": {n: [round(v, 1) for v in xy] for n, xy in recent_hands.items()}})
        prev_ids = {x[0] for x in last["snapshot"]}
        prev_t = t_end - 1e-9
    return moments


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("out")
    ap.add_argument("--minutes", default="1,3,5,7.5,10,12.5,15,17.5,20")
    args = ap.parse_args()
    log = json.load(open(args.log))
    cuts = [float(x) for x in args.minutes.split(",")]
    moments = storyboard(log, args.out, cuts)
    with open(os.path.join(args.out, "moments.json"), "w") as f:
        json.dump(moments, f, indent=1)
    print(f"{len(moments)} frames in {args.out}")


if __name__ == "__main__":
    main()
