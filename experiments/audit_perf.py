"""Forensic audit of the performance-review main run (seeds 402-407): where did the dominoes come from?

For every domino placed, the kind of job that placed it (tracing a plan stroke, re-laying a stroke, a join,
a fix, an extension), by condition; how the plan grew during the game; and paired-by-seed comparisons.

    python3 experiments/audit_perf.py results/perf_review
"""
from __future__ import annotations

import glob
import json
import os
import re
import statistics as st
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from orgsim.render import sketch_points  # noqa: E402

CONDS = ["none", "individual", "team", "manager", "peer", "forced"]


def kind_of(label: str) -> str:
    l = label.lower()
    if "lifting the old stroke" in l:
        return "re-lay"
    if "connecting" in l:
        return "join"
    if "bridging" in l or "nudging" in l:
        return "fix"
    if "extending" in l:
        return "extend"
    if "tracing" in l or "stroke" in l or "start domino" in l:
        return "trace"
    return "other"


def plan_len(strokes) -> float:
    import math
    tot = 0.0
    for s in strokes:
        if s.get("type") == "label":
            continue
        p = sketch_points(s)
        tot += sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))
    return tot


def game(folder: str) -> dict:
    log = json.load(open(os.path.join(folder, "log.json")))
    summ = json.load(open(os.path.join(folder, "summary.json")))
    last = {}
    placed = Counter()
    lifted = 0
    first_build_t = None
    for t in log["turns"]:
        for who, task in (t.get("tasks") or {}).items():
            if "(" in task:
                last[who] = task.split("(", 1)[1].rsplit(")", 1)[0]
        for e in t["events"]:
            if e["type"] == "build":
                if e.get("placed") and first_build_t is None:
                    first_build_t = t["time"]
                placed[kind_of(last.get(e["who"], ""))] += len(e.get("placed", []))
                lifted += len(e.get("lifted", []))
    # how the plan changed: strokes on the pad at first build vs at the end
    pad, at_first, sketches_after = [], None, 0
    for h in (log.get("scratchpad") or {}).get("history") or []:
        if first_build_t is not None and h["t"] > first_build_t:
            if at_first is None:
                at_first = list(pad)
            sketches_after += 1
        if h.get("cleared"):
            pad = []
        pad = (pad + list(h.get("strokes") or []))[-60:]
    if at_first is None:
        at_first = list(pad)
    n = lambda ss: sum(1 for s in ss if s.get("type") != "label")  # noqa: E731
    think = " ".join((d.get("thinking") or "") for t in log["turns"] for d in t["decisions"].values())
    said = " ".join(m["message"] for t in log["turns"] for c in t["conversations"] for m in c["messages"])
    pat = r"\bmy (own )?(count|number|tally|total)\b|\b(count|tally) (is|so far|toward)|\bcounts? toward\b|\bfor my (count|rating)\b|\bmy rating\b|\bpromotion\b|\bbonus\b"
    return {"game": os.path.basename(folder), "cond": summ.get("review"), "seed": int(folder.rsplit("_s", 1)[1]),
            "placed": summ["placed"], "fell": summ["fell"], "completion": summ["completion"],
            "recognition": summ["recognition"], "laid_total": sum(placed.values()), "lifted": lifted,
            "by_kind": dict(placed), "plan_dominoes_first": round(plan_len(at_first) / 0.5),
            "plan_dominoes_final": round(plan_len(pad) / 0.5), "strokes_first": n(at_first), "strokes_final": n(pad),
            "sketches_after_first_build": sketches_after,
            "incentive_thoughts": len(re.findall(pat, think, re.I)), "incentive_said": len(re.findall(pat, said, re.I))}


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "results/perf_review"
    games = [game(f) for f in sorted(glob.glob(os.path.join(root, "*_s40[2-7]")))]
    json.dump(games, open(os.path.join(root, "audit.json"), "w"), indent=1)
    by = defaultdict(list)
    for g in games:
        by[g["cond"]].append(g)
    kinds = ["trace", "re-lay", "join", "fix", "extend", "other"]
    print("| condition | n | laid | trace | re-lay | join | fix | extend | lifted | standing | plan at first build | plan at end | incentive thoughts |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in CONDS:
        gs = by[c]
        m = lambda f: round(st.mean(f(g) for g in gs), 1)  # noqa: E731
        print(f"| {c} | {len(gs)} | {m(lambda g: g['laid_total'])} | " +
              " | ".join(str(m(lambda g, k=k: g['by_kind'].get(k, 0))) for k in kinds[:5]) +
              f" | {m(lambda g: g['lifted'])} | {m(lambda g: g['placed'])} | {m(lambda g: g['plan_dominoes_first'])} | "
              f"{m(lambda g: g['plan_dominoes_final'])} | {m(lambda g: g['incentive_thoughts'])} |")
    print("\nPer game (seed order 402..407):")
    for key in ("placed", "laid_total", "completion", "recognition", "plan_dominoes_final"):
        print(f"  {key}")
        for c in CONDS:
            print(f"    {c:10}", [g[key] for g in sorted(by[c], key=lambda g: g["seed"])])
    print("\nPaired by seed (difference per seed; sign test two-sided p):")
    from math import comb
    def signp(d):
        pos, neg = sum(x > 0 for x in d), sum(x < 0 for x in d)
        nn, k = pos + neg, min(pos, neg)
        return round(min(1.0, 2 * sum(comb(nn, i) for i in range(k + 1)) / 2 ** nn), 3) if nn else 1.0
    seeds = sorted({g["seed"] for g in games})
    val = {(g["cond"], g["seed"]): g for g in games}
    for a, b in (("individual", "team"), ("individual", "none"), ("none", "team"), ("manager", "team"), ("peer", "team"), ("forced", "team")):
        for key in ("placed", "completion"):
            d = [round(val[(a, s)][key] - val[(b, s)][key], 2) for s in seeds if (a, s) in val and (b, s) in val]
            print(f"  {a} - {b}  {key:10} {d}  p={signp(d)}")


if __name__ == "__main__":
    main()
