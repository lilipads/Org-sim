"""Uniqueness across the tables of one round, and the final ambition score.

    python3 experiments/uniqueness.py results/<folder>/<game> results/<folder>/<game> ...

Uniqueness = 1 / (number of tables in the round with the same animal), so a table whose animal nobody else
built scores 1, two tables sharing an animal score 0.5 each. Final = recognition x ambition x uniqueness.
Writes "uniqueness" and "final_ambition_score" into each game's summary.json.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter


def norm(animal: str) -> str:
    a = " ".join(str(animal or "").lower().replace("-", " ").split())
    for prefix in ("a ", "an ", "the "):
        if a.startswith(prefix):
            a = a[len(prefix):]
    return a[:-1] if a.endswith("s") and not a.endswith("ss") else a


def main(folders: list):
    summaries = {f: json.load(open(os.path.join(f, "summary.json"))) for f in folders}
    counts = Counter(norm(s.get("team_intent")) for s in summaries.values())
    for f, s in summaries.items():
        u = 1.0 / counts[norm(s.get("team_intent"))]
        s["uniqueness"] = round(u, 3)
        if "ambition" in s:
            s["final_ambition_score"] = round(s["recognition"] * s["ambition"] * u, 3)
        json.dump(s, open(os.path.join(f, "summary.json"), "w"), indent=2)
        print(os.path.basename(f.rstrip("/")), s.get("team_intent"), "recognition", s.get("recognition"),
              "ambition", s.get("ambition"), "uniqueness", s["uniqueness"], "final", s.get("final_ambition_score"))


if __name__ == "__main__":
    main(sys.argv[1:])
