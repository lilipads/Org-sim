"""Measurement half of the performance-review study: the same finished games scored by every review system.

For each game folder with reviews_replay_<system>.json (results/perf_review4/replay_reviews.sh), compare each
system's ratings of the four players with the oracle's contribution, and with what else the ratings might track
(words spoken, the share each person claimed for themselves).

    python3 experiments/analyze_measurement.py results/perf_review4
"""
from __future__ import annotations

import glob
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(__file__))
from analyze_perf import spearman  # noqa: E402

SYSTEMS = ["individual", "peer", "manager", "forced"]


def score(system: str, r: dict):
    if r is None:
        return None
    return r.get("dominoes_fell") if system == "individual" else r.get("rating")


def top(d: dict) -> set:
    m = max(d.values())
    return {n for n, v in d.items() if v == m}


def bottom(d: dict) -> set:
    m = min(d.values())
    return {n for n, v in d.items() if v == m}


def load(folder: str) -> dict | None:
    try:
        oracle = json.load(open(os.path.join(folder, "oracle.json")))
        log = json.load(open(os.path.join(folder, "log.json")))
    except FileNotFoundError:
        return None
    names = list(oracle["contribution"])
    words = {n: 0 for n in names}
    for t in log["turns"]:
        for c in t["conversations"]:
            for m in c["messages"]:
                if m["speaker"] in words:
                    words[m["speaker"]] += len(m["message"].split())
    g = {"game": os.path.basename(folder), "names": names, "oracle": oracle["contribution"],
         "oracle_planning": oracle["with_planning"], "words": words, "ratings": {}, "claimed": None}
    for s in SYSTEMS:
        p = os.path.join(folder, f"reviews_replay_{s}.json")
        if not os.path.exists(p):
            continue
        rv = json.load(open(p))
        sc = {n: score(s, (rv.get("ratings") or {}).get(n)) for n in names}
        if all(v is not None for v in sc.values()):
            g["ratings"][s] = sc
        if s == "manager" and rv.get("claimed_share"):
            g["claimed"] = rv["claimed_share"]
    return g


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(st.mean(xs), 2) if xs else None


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "results/perf_review4"
    games = [g for g in (load(f) for f in sorted(glob.glob(os.path.join(root, "*_s4??")))) if g and g["ratings"]]
    out = {"games": games, "summary": {}}
    print(f"{len(games)} games\n")
    print("| system | n | rank agreement with oracle | ... with oracle incl. planning | ... with words spoken | "
          "names the oracle's top person | names the oracle's bottom person | games where everyone got the same rating |")
    print("|---|---|---|---|---|---|---|---|")
    for s in SYSTEMS:
        gs = [g for g in games if s in g["ratings"]]
        v = lambda g: [g["ratings"][s][n] for n in g["names"]]  # noqa: E731
        o = lambda g, k: [g[k][n] for n in g["names"]]          # noqa: E731
        row = {
            "n": len(gs),
            "rho_oracle": mean(spearman(v(g), o(g, "oracle")) for g in gs),
            "rho_oracle_planning": mean(spearman(v(g), o(g, "oracle_planning")) for g in gs),
            "rho_words": mean(spearman(v(g), o(g, "words")) for g in gs),
            # a system "names" the top person if its (possibly tied) top set includes the oracle's top person,
            # weighted by 1/size of the tie so a flat rating gets chance (0.25), not full credit
            "top_hit": mean(len(top(g["ratings"][s]) & top(g["oracle_planning"])) / len(top(g["ratings"][s]))
                            for g in gs),
            "bottom_hit": mean(len(bottom(g["ratings"][s]) & bottom(g["oracle_planning"]))
                               / len(bottom(g["ratings"][s])) for g in gs),
            "flat": sum(1 for g in gs if len(set(v(g))) == 1),
        }
        out["summary"][s] = row
        print(f"| {s} | {row['n']} | {row['rho_oracle']} | {row['rho_oracle_planning']} | {row['rho_words']} | "
              f"{row['top_hit']} | {row['bottom_hit']} | {row['flat']} |")
    cl = [g for g in games if g["claimed"] and all(g["claimed"].get(n) is not None for n in g["names"])]
    if cl:
        tot = [sum(g["claimed"].values()) for g in cl]
        rho = mean(spearman([g["claimed"][n] for n in g["names"]], [g["oracle_planning"][n] for n in g["names"]])
                   for g in cl)
        out["summary"]["self"] = {"n": len(cl), "claimed_total_mean": mean(tot), "rho_oracle_planning": rho}
        print(f"\nSelf-assessments ({len(cl)} games): the four claimed shares add up to {mean(tot)}% on average; "
              f"rank agreement of claimed share with oracle incl. planning {rho}")
    print("\nAgreement between systems (mean rank correlation across games):")
    for i, a in enumerate(SYSTEMS):
        for b in SYSTEMS[i + 1:]:
            gs = [g for g in games if a in g["ratings"] and b in g["ratings"]]
            r = mean(spearman([g["ratings"][a][n] for n in g["names"]], [g["ratings"][b][n] for n in g["names"]])
                     for g in gs)
            out["summary"][f"{a}~{b}"] = r
            print(f"  {a:10} ~ {b:8} {r}")
    json.dump(out, open(os.path.join(root, "measurement.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
