"""Save a game's scratch-pad sketch next to its results: sketch.json (the final pad and
every change to it, with who and when) and sketch.png (the final pad, as players saw it).

    python3 -m orgsim.sketch_record results/            # backfill every game under a folder
"""
from __future__ import annotations

import json
import os
import sys


def final_strokes(history: list) -> list:
    """Replay the pad's history the way the engine applies it."""
    pad: list = []
    for h in history:
        if h.get("cleared"):
            pad = []
        pad = (pad + list(h.get("strokes") or []))[-60:]
    return pad


def record(run_dir: str, log: dict | None = None) -> str | None:
    if log is None:
        p = os.path.join(run_dir, "log.json")
        if not os.path.exists(p):
            return None
        log = json.load(open(p))
    sp = log.get("scratchpad") or {}
    history = sp.get("history") or []
    final = sp.get("final") or final_strokes(history)
    if not history and not final:
        return None
    reg = (log.get("regions") or [{}])[0]
    size = (reg.get("x1", 30) - reg.get("x0", 0), reg.get("y1", 20) - reg.get("y0", 0)) if isinstance(reg, dict) else (30, 20)
    json.dump({"final": final, "history": history}, open(os.path.join(run_dir, "sketch.json"), "w"), indent=1)
    from .render import sketch_png
    out = os.path.join(run_dir, "sketch.png")
    sketch_png(final, out, size)
    return out


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "results"
    n = 0
    for dirpath, _, files in os.walk(root):
        if "log.json" in files and "summary.json" in files:
            try:
                if record(dirpath):
                    n += 1
            except Exception as e:     # an old log format: skip it, say so
                print(f"skipped {dirpath}: {e}")
    print(f"recorded sketches for {n} games")
