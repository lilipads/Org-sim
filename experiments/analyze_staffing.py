"""Overstaffing experiment: talking vs doing at tables of 1, 4 and 10.

    python3 experiments/analyze_staffing.py results/staffing

Reads every <dir>/*/log.json + summary.json and writes <dir>/staffing.md and
<dir>/staffing.json: per game, then averaged by table size.
"""
from __future__ import annotations

import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict


def state_of(task_text: str) -> str:
    t = task_text.lower()
    if t.startswith("building (waiting"):
        return "waiting"
    if t.startswith("building") or t.startswith("taking") or t.startswith("standing"):
        return "hands busy"
    return "hands free"


def game_metrics(run_dir: str) -> dict:
    log = json.load(open(os.path.join(run_dir, "log.json")))
    summ = json.load(open(os.path.join(run_dir, "summary.json")))
    names = [a["name"] if isinstance(a, dict) else a for a in log["agents"]]
    beat = log["config"].get("beat", 15.0)
    states = defaultdict(Counter)
    spoke_beats = Counter()
    words = Counter()
    placed, lifted, inspects = Counter(), Counter(), Counter()
    lifted_others = 0
    bumps, knocked = 0, 0
    for t in log["turns"]:
        for a, s in t.get("tasks", {}).items():
            states[a][state_of(s)] += 1
        for c in t.get("conversations", []):
            for m in c.get("messages", []):
                if m["speaker"] in names:
                    words[m["speaker"]] += len(m["message"].split())
                    spoke_beats[m["speaker"]] += 1
        for e in t.get("events", []):
            if e["type"] == "build":
                placed[e["who"]] += len(e.get("placed", []))
                for _, owner in e.get("lifted", []):
                    lifted[e["who"]] += 1
                    lifted_others += owner != e["who"]
            elif e["type"] == "bump":
                bumps += 1
                knocked += e.get("knocked", 0)
            elif e["type"] == "inspect":
                inspects[e["who"]] += 1
    n = len(names)
    total_beats = sum(sum(c.values()) for c in states.values()) or 1
    per_person_placed = [placed[a] for a in names]
    top = max(per_person_placed) if per_person_placed else 0
    total_placed = sum(per_person_placed)
    return {
        "game": os.path.basename(run_dir.rstrip("/")),
        "size": n,
        "people": names,
        "recognition": summ["recognition"],
        "recognized": summ["recognition"] >= 0.5,
        "recognition_if_all_fell": summ.get("recognition_if_all_fell"),
        "completion": summ["completion"],
        "standing_at_push": summ["placed"],
        "fell": summ["fell"],
        "first_domino_at": summ.get("first_domino_at"),
        "words_total": sum(words.values()),
        "words_per_person": round(sum(words.values()) / n, 1),
        "messages_total": sum(spoke_beats.values()),
        "share_hands_busy": round(sum(states[a]["hands busy"] for a in names) / total_beats, 3),
        "share_waiting": round(sum(states[a]["waiting"] for a in names) / total_beats, 3),
        "share_hands_free": round(sum(states[a]["hands free"] for a in names) / total_beats, 3),
        "dominoes_laid": total_placed,
        "laid_per_person": round(total_placed / n, 1),
        "top_builder_share": round(top / total_placed, 3) if total_placed else 0.0,
        "people_laying_under_10": sum(1 for x in per_person_placed if x < 10),
        "lifted": sum(lifted.values()),
        "lifted_someone_elses": lifted_others,
        "bumps": bumps,
        "knocked_by_bumps": knocked,
        "inspections": sum(inspects.values()),
        "per_person": {a: {"words": words[a], "laid": placed[a], "lifted": lifted[a],
                           "inspections": inspects[a], "beats": dict(states[a])} for a in names},
        "beat_seconds": beat,
    }


AVG_KEYS = ["recognition", "completion", "standing_at_push", "fell", "words_total", "words_per_person",
            "messages_total", "share_hands_busy", "share_waiting", "share_hands_free", "dominoes_laid",
            "laid_per_person", "top_builder_share", "people_laying_under_10", "lifted", "lifted_someone_elses",
            "bumps", "knocked_by_bumps", "inspections"]


def _secs(clock):
    if not clock:
        return None
    if isinstance(clock, (int, float)):
        return float(clock)
    m, s = str(clock).split(":")
    return int(m) * 60 + int(s)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "results/staffing"
    games = []
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d)
        if os.path.exists(os.path.join(p, "summary.json")) and os.path.exists(os.path.join(p, "log.json")):
            games.append(game_metrics(p))
    by = defaultdict(list)
    for g in games:
        by[g["size"]].append(g)
    agg = {}
    for size, gs in sorted(by.items()):
        a = {k: round(st.mean(g[k] for g in gs), 3) for k in AVG_KEYS}
        a["games"] = len(gs)
        a["recognized"] = f"{sum(g['recognized'] for g in gs)}/{len(gs)}"
        fd = [_secs(g["first_domino_at"]) for g in gs if _secs(g["first_domino_at"]) is not None]
        a["first_domino_at_s"] = round(st.mean(fd), 1) if fd else None
        agg[size] = a
    json.dump({"games": games, "by_size": agg}, open(os.path.join(root, "staffing.json"), "w"), indent=1)

    rows = [("Recognized", "recognized"), ("Mean recognition score", "recognition"),
            ("Share of standing dominoes that fell", "completion"), ("Dominoes that fell", "fell"),
            ("First domino laid (s)", "first_domino_at_s"),
            ("Words spoken, whole table", "words_total"), ("Words spoken per person", "words_per_person"),
            ("Person-time with hands busy", "share_hands_busy"), ("Person-time waiting for the run", "share_waiting"),
            ("Person-time with hands free (talking, looking, idle)", "share_hands_free"),
            ("Dominoes laid", "dominoes_laid"), ("Dominoes laid per person", "laid_per_person"),
            ("Top builder's share of dominoes", "top_builder_share"),
            ("People who laid fewer than 10", "people_laying_under_10"),
            ("Dominoes lifted again (rework)", "lifted"), ("...of them someone else's", "lifted_someone_elses"),
            ("Table bumps", "bumps"), ("Dominoes knocked by bumps", "knocked_by_bumps"),
            ("Close inspections", "inspections")]
    sizes = sorted(agg)
    out = ["# Overstaffing: tables of " + ", ".join(map(str, sizes)), "",
           "Averages per game (" + ", ".join(f"{agg[s]['games']} games at size {s}" for s in sizes) + ").", "",
           "| | " + " | ".join(f"Table of {s}" for s in sizes) + " |",
           "|---|" + "---|" * len(sizes)]
    for label, k in rows:
        out.append(f"| {label} | " + " | ".join(str(agg[s].get(k)) for s in sizes) + " |")
    out += ["", "## Games", "",
            "| Game | Size | Recognition | Fell | Words | Laid | Lifted | Bumps | Busy | Free |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for g in games:
        out.append(f"| {g['game']} | {g['size']} | {g['recognition']} | {g['fell']}/{g['standing_at_push']} | "
                   f"{g['words_total']} | {g['dominoes_laid']} | {g['lifted']} | {g['bumps']} | "
                   f"{g['share_hands_busy']:.0%} | {g['share_hands_free']:.0%} |")
    open(os.path.join(root, "staffing.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
