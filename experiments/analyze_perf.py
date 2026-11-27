"""Performance review study: one table per game (people x oracle x ratings x behaviour), then a summary
by condition.

    python3 experiments/analyze_perf.py results/perf_review [game ...]
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orgsim.oracle import _plan_points, compute, on_plan, world_from_rows  # noqa: E402
from orgsim.sketch_record import final_strokes  # noqa: E402


def spearman(xs: list, ys: list) -> float | None:
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = ranks([p[0] for p in pairs]), ranks([p[1] for p in pairs])
    n = len(pairs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 2) if den else None


def game(folder: str) -> dict:
    log = json.load(open(os.path.join(folder, "log.json")))
    summ = json.load(open(os.path.join(folder, "summary.json")))
    rev = json.load(open(os.path.join(folder, "reviews.json"))) if os.path.exists(os.path.join(folder, "reviews.json")) else {}
    orc = compute(log)
    names = [a["name"] for a in log["agents"]]
    plan_pts = _plan_points((log.get("scratchpad") or {}).get("final") or
                            final_strokes((log.get("scratchpad") or {}).get("history") or []))
    words, private, private_words, present_words, absent_words = (defaultdict(int) for _ in range(5))
    laid, inspections = defaultdict(int), defaultdict(int)
    sched = rev.get("manager_schedule") or []
    for t in log["turns"]:
        here = any(a <= t["time"] < b for a, b in sched)
        for c in t["conversations"]:
            for m in c["messages"]:
                w = len(m["message"].split())
                words[m["speaker"]] += w
                (present_words if here else absent_words)[m["speaker"]] += w
        for e in t["events"]:
            if e["type"] == "to_manager":
                private[e["who"]] += 1
                private_words[e["who"]] += len(e["text"].split())
            elif e["type"] == "build":
                laid[e["who"]] += len(e.get("placed", []))
            elif e["type"] == "inspect":
                inspections[e["who"]] += 1
    final = world_from_rows(log["turns"][-1]["snapshot"])
    plan = on_plan(final, plan_pts)
    off_plan = defaultdict(int)
    for i, d in final.dominoes.items():
        if i not in plan:
            off_plan[d.builder] += 1
    ratings = {}
    for n in names:
        r = (rev.get("ratings") or {}).get(n) or {}
        ratings[n] = r.get("rating", r.get("dominoes_fell"))
    people = {}
    for n in names:
        p = orc["people"][n]
        people[n] = {"style": (rev.get("styles") or {}).get(n), "skill": (rev.get("skills") or {}).get(n),
                     "rating": ratings[n], "contribution": orc["contribution"][n],
                     "with_planning": orc["with_planning"][n], **p, "laid": laid[n], "off_plan": off_plan[n],
                     "words": words[n], "words_manager_present": present_words[n],
                     "words_manager_away": absent_words[n], "private_msgs": private[n],
                     "private_words": private_words[n], "inspections": inspections[n]}
    cond = rev.get("condition") or summ.get("review")
    from orgsim.design_check import _strokes_of
    from orgsim.render import sketch_points
    import math as _m
    plan_len = sum(sum(_m.dist(p[i], p[i + 1]) for i in range(len(p) - 1))
                   for p in (sketch_points(st) for st in _strokes_of(
                       (log.get("scratchpad") or {}).get("final") or
                       final_strokes((log.get("scratchpad") or {}).get("history") or []))))
    return {"game": os.path.basename(folder.rstrip("/")), "condition": cond, "intent": summ.get("team_intent"),
            "plan_dominoes": round(plan_len / 0.5),
            "recognition": summ.get("recognition"), "fell": summ.get("fell"), "placed": summ.get("placed"),
            "completion": summ.get("completion"), "people": people,
            "rho_contribution": spearman([ratings[n] for n in names], [orc["contribution"][n] for n in names]),
            "rho_with_planning": spearman([ratings[n] for n in names], [orc["with_planning"][n] for n in names]),
            "rho_words": spearman([ratings[n] for n in names], [words[n] for n in names]),
            "manager_present_share": round(sum(b - a for a, b in sched) / 600, 2) if sched else None}


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "results/perf_review"
    picks = sys.argv[2:] or sorted(d for d in glob.glob(os.path.join(root, "*_s*")) if not os.path.basename(d).startswith("plumb"))
    games = []
    for f in picks:
        if os.path.exists(os.path.join(f, "summary.json")):
            games.append(game(f))
    lines = []
    for g in games:
        lines.append(f"## {g['game']} ({g['condition']}): {g['intent']}, recognition {g['recognition']}, "
                     f"fell {g['fell']}/{g['placed']}, plan needs ~{g['plan_dominoes']} dominoes")
        lines.append(f"rating vs oracle rho {g['rho_contribution']} (with planning {g['rho_with_planning']}); "
                     f"rating vs words rho {g['rho_words']}")
        lines.append("| who | style | rating | oracle | +plan | sound | fixes | breaks | planning | laid | redundant | stray | words | private | inspect |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for n, p in g["people"].items():
            lines.append(f"| {n} | {p['style']} | {p['rating']} | {p['contribution']} | {p['with_planning']} | "
                         f"{p['sound_work']} | {p['fixes']} | {p['open_breaks_owned']} | {p['planning']} | {p['laid']} | {p['redundant']} | "
                         f"{p['off_plan']} | {p['words']} | {p['private_msgs']} | {p['inspections']} |")
        lines.append("")
    # by condition (main run only: seeds >= 402)
    import statistics as st
    by = defaultdict(list)
    for g in games:
        if int(g["game"].rsplit("_s", 1)[1]) >= 402:
            by[g["condition"]].append(g)
    order = ["none", "individual", "team", "manager", "peer", "forced"]
    head = ["| condition | games | recognised | share fell | dominoes placed | plan size | redundant | words | private msgs | rho(rating, oracle) | rho(rating, +planning) | rho(rating, words) | rating spread |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    def mean(v):
        v = [x for x in v if x is not None]
        return round(st.mean(v), 2) if v else None
    for c in order:
        gs = by.get(c, [])
        if not gs:
            continue
        spread = [max(p["rating"] for p in g["people"].values()) - min(p["rating"] for p in g["people"].values())
                  for g in gs if all(p["rating"] is not None for p in g["people"].values())]
        head.append(f"| {c} | {len(gs)} | {sum(g['recognition'] >= 0.5 for g in gs)}/{len(gs)} | "
                    f"{mean([g['completion'] for g in gs])} | {mean([g['placed'] for g in gs])} | "
                    f"{mean([g['plan_dominoes'] for g in gs])} | {mean([sum(p['redundant'] for p in g['people'].values()) for g in gs])} | "
                    f"{mean([sum(p['words'] for p in g['people'].values()) for g in gs])} | "
                    f"{mean([sum(p['private_msgs'] for p in g['people'].values()) for g in gs])} | "
                    f"{mean([g['rho_contribution'] for g in gs])} | {mean([g['rho_with_planning'] for g in gs])} | "
                    f"{mean([g['rho_words'] for g in gs])} | {mean(spread)} |")
    lines = ["# By condition (seeds 402+)", ""] + head + [""] + lines
    out = "\n".join(lines)
    print(out)
    with open(os.path.join(root, "analysis.md"), "w") as f:
        f.write(out + "\n")
    with open(os.path.join(root, "analysis.json"), "w") as f:
        json.dump(games, f, indent=1)


if __name__ == "__main__":
    main()
