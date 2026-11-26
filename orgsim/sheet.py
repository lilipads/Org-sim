"""One-page 'who did what' sheet for a live run: storyboard frames every two
minutes, plus a final 'who built what' picture.

    python3 -m orgsim.sheet results/pilot/<run> "Title for the sheet"
"""
from __future__ import annotations

import json
import os
import sys

from .storyboard import crop_bounds, render_frame, storyboard


def make_sheet(run_dir: str, title: str, minutes: list | None = None) -> tuple:
    from PIL import Image, ImageDraw, ImageFont
    log = json.load(open(os.path.join(run_dir, "log.json")))
    out = os.path.join(run_dir, "storyboard")
    minutes = minutes or [2, 4, 6, 8, 10, 12, 14, 16, 20]
    moments = storyboard(log, out, minutes)
    names = [a["name"] for a in log["agents"]]
    tables = [r for r in log["regions"] if r.get("kind") == "table"]
    W = max(r["x1"] for r in tables)
    H = max(r["y1"] for r in tables)
    snap = log["push"]["before_push"]
    final = os.path.join(out, "who_built_what.png")
    render_frame(snap, {r[0] for r in snap}, names, {}, {}, final, crop_bounds(log, W, H, pad=max(2.0, W / 15)))

    frames = [Image.open(m["file"]) for m in moments]
    w, h = frames[0].size
    tw, cols, head = 600, 3, 64
    th = int(h * tw / w)
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 16, rows * (th + head + 16) + 76), (250, 247, 240))
    dr = ImageDraw.Draw(sheet)
    bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    dr.text((16, 16), title + "  ·  yellow glow = built since the previous frame", fill=(31, 36, 48), font=small)
    prev = "0:00"
    for i, (m, fr) in enumerate(zip(moments, frames)):
        r, c = divmod(i, cols)
        x, y = 16 + c * (tw + 16), 76 + r * (th + head + 16)
        end = f"{int(minutes[i])}:00" if i < len(minutes) else m["clock"]
        built = ", ".join(f"{k} +{v}" for k, v in m["built"].items()) or "nothing built"
        dr.text((x, y), f"{prev}–{end}", fill=(184, 87, 46), font=bold)
        dr.text((x, y + 30), built, fill=(74, 80, 96), font=small)
        sheet.paste(fr.resize((tw, th)), (x, y + head - 8))
        prev = end
    path = os.path.join(out, "who_did_what_sheet.png")
    sheet.save(path)
    return path, final


if __name__ == "__main__":
    print(make_sheet(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Who did what"))
