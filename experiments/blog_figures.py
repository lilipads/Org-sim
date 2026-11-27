"""Figures for blog/01-overstaffing.md (Sonnet overstaffing run, 8 games per table size).

    python3 experiments/blog_figures.py
"""
from __future__ import annotations

import glob
import json
import os
import statistics as st
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ROOT = "results/staffing_sonnet"
OUT = "blog/img"
INK, INK2, GRID = "#191919", "#666666", "#e6e6e6"
SIZE_COLOR = {1: "#257de0", 4: "#f47230", 10: "#00b894"}   # categorical slots 1-3 (validated)
GRAY = "#b8b8b8"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": INK2,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 13,
                     "axes.titleweight": "bold", "axes.titlecolor": INK, "figure.dpi": 100})


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    fig.savefig(os.path.join(OUT, name), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def by_size():
    d = json.load(open(os.path.join(ROOT, "staffing.json")))
    return d["by_size"], d["games"]


def fig_talk_vs_output(agg):
    sizes = ["1", "4", "10"]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    panels = [("Words spoken per game", "words_total", "{:,.0f}"),
              ("Dominoes laid per person", "laid_per_person", "{:.0f}"),
              ("Time anyone's hands were busy", "share_hands_busy", "{:.0%}")]
    for ax, (title, key, fmt) in zip(axes, panels):
        vals = [agg[s][key] for s in sizes]
        bars = ax.bar([f"{s} {'person' if s == '1' else 'people'}" for s in sizes], vals,
                      color=[SIZE_COLOR[int(s)] for s in sizes], width=0.6, edgecolor="white", linewidth=2)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), fmt.format(v), ha="center", va="bottom",
                    color=INK, fontsize=11, fontweight="bold")
        ax.set_title(title, loc="left")
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        ax.set_ylim(0, max(vals) * 1.18)
    fig.suptitle("More people: much more talk, much less building each", x=0.01, ha="left", y=1.06,
                 fontsize=15, fontweight="bold", color=INK)
    save(fig, "talk_vs_output.png")


def fig_progress():
    curves = {1: [], 4: [], 10: []}
    for p in sorted(glob.glob(os.path.join(ROOT, "t*/log.json"))):
        size = int(os.path.basename(os.path.dirname(p)).split("_")[0][1:])
        turns = json.load(open(p))["turns"]
        final = {d[0] for d in turns[-1]["snapshot"] if d[4] == "up"}
        if not final:
            continue
        pts = [(t["time"], sum(1 for d in t["snapshot"] if d[0] in final) / len(final)) for t in turns]
        grid = []
        for s in range(0, 601, 15):
            prev = [v for tt, v in pts if tt <= s]
            grid.append(prev[-1] if prev else 0.0)
        curves[size].append(grid)
    xs = [s / 60 for s in range(0, 601, 15)]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    for size, gs in curves.items():
        mean = [st.mean(col) for col in zip(*gs)]
        ax.plot(xs, mean, color=SIZE_COLOR[size], linewidth=2.2)
        label = f"{size} {'person' if size == 1 else 'people'}"
        x, dy, va = {4: (2.6, 0.03, "bottom"), 10: (5.2, -0.04, "top"), 1: (7.9, -0.04, "top")}[size]
        i = int(round(x * 4))
        ax.text(x, mean[i] + dy, label, color=INK, fontsize=11, fontweight="bold", va=va,
                ha="right" if size == 4 else "left")
    ax.axhline(0.9, color=GRID, linewidth=1, zorder=0)
    ax.text(0.1, 0.915, "90% of the final picture laid", color=INK2, fontsize=9)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Minutes into the game")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_title("Four people finished first; ten people were a minute behind", loc="left")
    ax.text(0, -0.2, "Share of each table's final picture already laid, averaged over 8 games per table size.",
            transform=ax.transAxes, color=INK2, fontsize=9)
    save(fig, "progress.png")


def fig_who_did_what(games, game="t10_s101"):
    g = next(x for x in games if x["game"] == game)
    pp = sorted(g["per_person"].items(), key=lambda kv: -kv[1]["laid"])
    names = [n for n, _ in pp]
    laid = [v["laid"] for _, v in pp]
    words = [v["words"] for _, v in pp]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    cols = ["#257de0" if x >= 10 else GRAY for x in laid]
    axes[0].barh(names, laid, color=cols, edgecolor="white", linewidth=2, height=0.7)
    axes[0].invert_yaxis()
    axes[0].set_title("Dominoes laid", loc="left")
    axes[1].barh(names, words, color=GRAY, edgecolor="white", linewidth=2, height=0.7)
    axes[1].set_title("Words spoken", loc="left")
    for ax, vals in ((axes[0], laid), (axes[1], words)):
        for i, v in enumerate(vals):
            ax.text(v + max(vals) * 0.01, i, str(v), va="center", color=INK, fontsize=10)
        ax.set_xticks([])
        ax.spines["bottom"].set_visible(False)
    top_talker = max(range(len(words)), key=lambda i: words[i])
    axes[1].text(words[top_talker] * 0.5, top_talker, "drew the plan, split the work", va="center",
                 ha="center", color="white", fontsize=9, fontweight="bold")
    fig.suptitle("One ten-person table: four people built the fish", x=0.01, ha="left", y=1.04,
                 fontsize=15, fontweight="bold", color=INK)
    fig.text(0.01, -0.04, "Blue: laid at least 10 dominoes. Four builders laid 151 of 158; the other six laid 7.",
             color=INK2, fontsize=9)
    save(fig, "who_did_what.png")


def fig_gallery():
    picks = [("t1_s101", "Alone: a good plan, but nothing fell"), ("t1_s104", "Alone: 16 dominoes left standing"),
             ("t4_s105", "Four people"), ("t4_s101", "Four people"),
             ("t10_s101", "Ten people"), ("t10_s108", "Ten people: the run stopped early")]
    tiles = []
    for game, caption in picks:
        p = os.path.join(ROOT, game, "before_push.png")
        im = Image.open(p).convert("RGB")
        im.thumbnail((560, 380))
        tiles.append((im, caption))
    W, H = 560, 380 + 44
    sheet = Image.new("RGB", (W * 2 + 30, H * 3 + 20), "white")
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    for i, (im, cap) in enumerate(tiles):
        r, c = divmod(i, 2)
        x, y = 10 + c * (W + 10), 10 + r * H
        sheet.paste(im, (x + (W - im.width) // 2, y))
        ImageDraw.Draw(sheet).text((x + 6, y + 384), cap, fill=INK, font=font)
    sheet.save(os.path.join(OUT, "gallery.png"))


def fig_method(game="t4_s101"):
    """What a player works with: the scratch-pad plan and the table (dark = connected to the start)."""
    a = Image.open(os.path.join(ROOT, game, "sketch.png")).convert("RGB")
    b = Image.open(os.path.join(ROOT, game, "before_push.png")).convert("RGB")
    h = 420
    a = a.resize((int(a.width * h / a.height), h))
    b = b.resize((int(b.width * h / b.height), h))
    sheet = Image.new("RGB", (a.width + b.width + 30, h + 50), "white")
    sheet.paste(a, (10, 10))
    sheet.paste(b, (a.width + 20, 10))
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    d = ImageDraw.Draw(sheet)
    d.text((16, h + 16), "The plan on the shared scratch pad", fill=INK, font=font)
    d.text((a.width + 26, h + 16), "The table before the push", fill=INK, font=font)
    sheet.save(os.path.join(OUT, "plan_and_table.png"))


def main():
    agg, games = by_size()
    fig_talk_vs_output(agg)
    fig_progress()
    fig_who_did_what(games)
    fig_gallery()
    fig_method()
    print("figures in", OUT)


if __name__ == "__main__":
    main()


def fig_timelapse(game="t10_s101", name="timelapse.gif", scale=20):
    """The build, one frame per 15-second beat with what was said, then the push."""
    import tempfile
    import textwrap
    import sys
    sys.path.insert(0, ".")
    from orgsim.dominoes import Domino
    from orgsim.game import table_world
    from orgsim.render import picture_png
    log = json.load(open(os.path.join(ROOT, game, "log.json")))
    tmp = tempfile.mkdtemp()
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 17)
        bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 19)
    except OSError:
        font = bold = ImageFont.load_default()

    def world_of(rows, fallen=frozenset()):
        w = table_world("table", 30, 20, 10000)
        for r in rows:
            d = Domino(r[0], r[1], r[2], r[3], r[5], 0, "table")
            d.state = "down" if (r[0] in fallen or r[4] == "down") else "up"
            d.start = bool(r[6])
            w.dominoes[d.id] = d
        return w

    def frame(w, header, caption, fallen=None):
        p = os.path.join(tmp, "f.png")
        picture_png(w, p, scale=scale, show_standing=True, fallen=fallen)
        im = Image.open(p).convert("RGB")
        cap_lines = textwrap.wrap(caption, 56) if caption else []
        if len(cap_lines) > 3:
            cap_lines = cap_lines[:3]
            cap_lines[-1] = cap_lines[-1].rstrip(" .,") + " …”"
        out = Image.new("RGB", (im.width, im.height + 44 + 24 * 3), "white")
        out.paste(im, (0, 40))
        dr = ImageDraw.Draw(out)
        dr.text((12, 10), header, fill=INK, font=bold)
        for k, line in enumerate(cap_lines):
            dr.text((12, im.height + 50 + 24 * k), line, fill=INK2, font=font)
        return out.convert("P", palette=Image.ADAPTIVE)

    frames, durations = [], []
    last_caption = ""
    for t in log["turns"]:
        msgs = [m for c in t["conversations"] for m in c["messages"] if m["speaker"] != "Facilitator"]
        if msgs:
            m = max(msgs, key=lambda m: len(m["message"]))
            last_caption = f"{m['speaker']}: “{m['message']}”"
        up = sum(1 for r in t["snapshot"] if r[4] == "up")
        frames.append(frame(world_of(t["snapshot"], fallen={r[0] for r in t["snapshot"]}),
                            f"{t['clock']}  ·  {up} dominoes standing",
                            last_caption))
        durations.append(700)
    rows = log["turns"][-1]["snapshot"]
    times = {int(k): v for k, v in log["push"]["times"].items()}
    w = world_of(rows)
    t_end = max(times.values()) if times else 0
    steps = 24
    for k in range(steps + 1):
        tt = t_end * k / steps
        fallen = {i for i, ti in times.items() if ti <= tt}
        frames.append(frame(w, "10:00  ·  the push", f"{len(fallen)} of {len(rows)} dominoes down", fallen=fallen))
        durations.append(80)
    durations[-1] = 2500
    frames[0].save(os.path.join(OUT, name), save_all=True, append_images=frames[1:], duration=durations, loop=0,
                   optimize=True)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "gif":
    fig_timelapse()
