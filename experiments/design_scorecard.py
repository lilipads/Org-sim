"""Score a design (a scratch-pad sketch) on its own, separate from how well a team builds it.

    python3 experiments/design_scorecard.py experiments/designs/whale.json [--seeds 6]

A designs file is {"animal": "whale", "designs": {"name": [strokes...], ...}}. For each design:
  * buildable: four scripted builders trace it with ordinary hands (no AI); share of runs where 90%+
    of what they laid falls, and the mean share that falls;
  * legible: the best scripted build, with every domino knocked over, shown to 3 blind judges;
  * cost: dominoes it needs, and minutes of laying for four people.
Results go to <file>_scores.json and a picture per design beside it.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import check_tracing as ct  # noqa: E402
from orgsim.agents.llm import CallLog  # noqa: E402
from orgsim.judge import judge_picture  # noqa: E402
from orgsim.render import picture_png, sketch_points  # noqa: E402


def length(strokes: list) -> float:
    tot = 0.0
    for s in strokes:
        pts = sketch_points(s) if s.get("type") != "label" else []
        tot += sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    return tot


def ideal_world(strokes: list):
    """The design built perfectly: dominoes every half unit along every stroke, lying down."""
    from orgsim.dominoes import Domino
    from orgsim.game import table_world
    w = table_world("table", 30, 20, 10000)
    k = 0
    for s in strokes:
        if s.get("type") == "label":
            continue
        pts = sketch_points(s)
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            seg = math.dist(pts[i], pts[i + 1])
            ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
            for t in range(max(1, int(seg / 0.5))):
                f = t * 0.5 / seg if seg else 0
                k += 1
                d = Domino(k, x0 + f * (x1 - x0), y0 + f * (y1 - y0), ang, "ideal", 0, "table")
                d.state = "down"
                w.dominoes[k] = d
    return w


def score(animal: str, strokes: list, out_png: str, seeds: int, log: CallLog) -> dict:
    n = round(length(strokes) / 0.5)
    runs = [ct.run(s, True, strokes, return_world=True) for s in range(seeds)]
    fell = []
    for _, g in runs:                      # share of the design that a scripted team gets to fall
        out = g.log["push"]["per_table"]["table"]
        fell.append(min(1.0, out["fell"] / n) if n else 0.0)
    picture_png(ideal_world(strokes), out_png, scale=28)
    j = judge_picture(out_png, animal, 3, log)
    comps = fell
    return {"strokes": len([s for s in strokes if s.get("type") != "label"]), "dominoes_needed": n,
            "minutes_for_four": round(n * 3.0 / 4 / 60, 1),
            "buildable_90": f"{sum(c >= 0.9 for c in comps)}/{len(comps)}",
            "share_of_design_fell": round(sum(comps) / len(comps), 2),
            "legible": j["recognition"], "judge_guesses": [g["guesses"][:1] for g in j["judges"]],
            "design_score": round(j["recognition"] * sum(comps) / len(comps), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--seeds", type=int, default=6)
    a = ap.parse_args()
    spec = json.load(open(a.file))
    base = os.path.splitext(a.file)[0]
    log = CallLog(base + "_calls.jsonl")
    res = {}
    for name, strokes in spec["designs"].items():
        res[name] = score(spec["animal"], strokes, f"{base}_{name}.png", a.seeds, log)
        print(name, res[name], flush=True)
    json.dump(res, open(base + "_scores.json", "w"), indent=1)


if __name__ == "__main__":
    main()
