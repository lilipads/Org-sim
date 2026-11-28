"""Mechanics check with no AI: is a supply runner worth it? Four scripted people build the fish from the pad,
with dominoes in boxes by the door (PERF_REVIEW_STUDY.md §14).

  selfish  - everyone fetches a trayful (12) for themselves when they run out
  coop     - whoever runs out fetches a big batch (40) for the shared bin
  runner   - one person only fetches 40 at a time into the shared bin; the other three build

    python3 experiments/check_depot.py [--seeds 8]
"""
from __future__ import annotations

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import check_tracing as ct  # noqa: E402
from orgsim.dominoes import Physics  # noqa: E402
from orgsim.game import table_world  # noqa: E402
from orgsim.live import Decision, LiveConfig, LiveGame  # noqa: E402


class Worker(ct.Tracer):
    def __init__(self, name, jobs, sketcher, mode, runner=False):
        super().__init__(name, jobs, sketcher=sketcher, repair=False, sketch=ct.FISH)
        self.mode, self.runner, self.game = mode, runner, None

    def act(self, obs):
        g = self.game
        if obs["task"].startswith("You're away"):     # at the boxes: nothing to decide until back
            self.k += 1
            return Decision()
        if self.runner and self.k >= 2:
            self.k += 1
            if obs["task"].startswith("You're away"):
                return Decision()
            if g.depot_left() > 0 and g.bin_total() < 30:
                return Decision(fetch={"n": 40, "for": "bin"})
            return Decision()
        if (g is not None and self.k >= 2 and g.tray[self.name] == 0 and g.bin_total() == 0
                and not (self.mode == "runner" and g.depot_left() > 0 and g.t < 60)   # the runner's first trip is coming
                and not obs["task"].startswith("You're away") and g.depot_left() > 0
                and (self.jobs or "Building" in obs["task"])):
            self.k += 1
            if self.mode == "coop":
                return Decision(fetch={"n": 40, "for": "bin"})
            return Decision(fetch={"n": 12, "for": "me"})
        return super().act(obs)


def run(seed: int, mode: str) -> dict:
    rng = random.Random(seed)
    order = list(range(2, len(ct.FISH) + 1))
    rng.shuffle(order)
    order = [1] + order                         # someone always starts with stroke 1 (it lays the start)
    names = ["A", "B", "C", "D"]
    builders = names[:3] if mode == "runner" else names
    jobs = {n: order[i::len(builders)] for i, n in enumerate(builders)}
    agents = [Worker(n, jobs.get(n, []), i == 0, mode, runner=(mode == "runner" and n == "D"))
              for i, n in enumerate(names)]
    skills = {n: {"speed": rng.uniform(0.6, 1.6), "error": rng.uniform(0.5, 2.0)} for n in names}
    w = table_world("table", 30, 20, 250, Physics(pos_sigma=0.025, bump_radius=3.0))
    cfg = LiveConfig(duration=600, seed=seed, seconds_per_domino=3.0, skills=skills, freehand_sigma=0.15,
                     scratchpad_until=600, announce_at=(), idle_quiet=15, max_quiet=15, depot=True)
    g = LiveGame(w, agents, cfg)
    for a in agents:
        a.game = g
    res = g.run()
    turns = g.log["turns"]
    final = {r[0] for r in turns[-1]["snapshot"] if r[4] == "up"}
    t90 = next((t["time"] for t in turns if final and
                sum(1 for r in t["snapshot"] if r[0] in final) >= 0.9 * len(final)), None)
    fetched = sum(e["n"] for t in turns for e in t["events"] if e["type"] == "fetch")
    return {"fell": res["per_table"]["table"]["fell"], "t90": t90, "fetched": fetched}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    args = ap.parse_args()
    for mode in ("selfish", "coop", "runner"):
        rs = [run(s, mode) for s in range(args.seeds)]
        t90 = [r["t90"] for r in rs if r["t90"] is not None] or [0]
        print(f"{mode:8} fell median {sorted(r['fell'] for r in rs)[len(rs) // 2]:4}  "
              f"90% laid at {sum(t90) / len(t90) / 60:.1f} min  fetched {sum(r['fetched'] for r in rs) / len(rs):.0f}  "
              f"all fell {[r['fell'] for r in rs]}")


if __name__ == "__main__":
    main()
