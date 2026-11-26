"""Mechanics check with no AI: four scripted people trace a fish sketch from the pad
in parallel, in shuffled orders, with varied hands. How often does the whole fish fall?

    python3 experiments/check_tracing.py [--seeds 30]
"""
from __future__ import annotations

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orgsim.dominoes import Physics  # noqa: E402
from orgsim.game import table_world  # noqa: E402
from orgsim.live import Decision, LiveAgentBase, LiveConfig, LiveGame  # noqa: E402

FISH = [   # nose at the left; top and belly both start at the nose; tail on the right
    {"type": "curve", "points": [[6, 10], [8.5, 7.8], [11, 6.6], [14, 6], [17, 6.6], [19.5, 8], [21, 10]]},
    {"type": "curve", "points": [[6, 10], [8.5, 12.2], [11, 13.4], [14, 14], [17, 13.4], [19.5, 12], [21, 10]]},
    {"type": "curve", "points": [[21, 10], [23.5, 7.5], [25, 6.8]]},
    {"type": "curve", "points": [[21, 10], [23.5, 12.5], [25, 13.2]]},
]


def find_break(world):
    """A place where the run visibly stops short of more dominoes just ahead."""
    import math
    reach = world.reachable_from_start()
    for i in reach:
        d = world.dominoes[i]
        if world.successors(d):
            continue
        r = math.radians(d.angle)
        for b in world.near(d.x, d.y, 2.0):
            if b.id not in reach and b.state == "up" and (b.x - d.x) * math.cos(r) + (b.y - d.y) * math.sin(r) > 0:
                return (d.x, d.y)
    return None


class Tracer(LiveAgentBase):
    def __init__(self, name, jobs, sketcher=False, repair=False):
        super().__init__(name, "table")
        self.jobs, self.sketcher, self.k = list(jobs), sketcher, 0
        self.repair, self.world = repair, None

    def act(self, obs):
        self.k += 1
        if self.sketcher and self.k == 1:
            return Decision(pad="take", eagerness=9, sketch=[])
        if self.sketcher and self.k == 2:
            return Decision(sketch=FISH, pad="put_down")
        if "nothing" in obs["pad_status"].lower():
            return Decision()
        if obs["task"].startswith("Building"):
            return Decision(do="continue")
        if self.jobs:
            j = self.jobs.pop(0)
            return Decision(do="build", strokes=[{"type": "trace", "stroke": j}])
        if self.repair and self.world is not None:     # free hands: fix a break in the run
            brk = find_break(self.world)
            if brk:
                return Decision(do="build", strokes=[{"type": "fix", "at": list(brk)}])
        return Decision()


def run(seed: int, repair: bool = False) -> float:
    rng = random.Random(seed)
    order = [1, 2, 3, 4]
    rng.shuffle(order)
    names = ["A", "B", "C", "D"]
    agents = [Tracer(n, [order[i]], sketcher=(i == 0), repair=repair) for i, n in enumerate(names)]
    skills = {n: {"speed": rng.uniform(0.6, 1.6), "error": rng.uniform(0.5, 2.0)} for n in names}
    w = table_world("table", 30, 20, 250, Physics(pos_sigma=0.025, bump_radius=3.0))
    cfg = LiveConfig(duration=600, seed=seed, seconds_per_domino=3.0, skills=skills, freehand_sigma=0.15,
                     scratchpad_until=600, announce_at=(), idle_quiet=15, max_quiet=15)
    g = LiveGame(w, agents, cfg)
    for a in agents:
        a.world = w
    res = g.run()
    return res["per_table"]["table"]["completion"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--repair", action="store_true", help="free hands look for breaks and fix them")
    args = ap.parse_args()
    comps = [run(s, args.repair) for s in range(args.seeds)]
    full = sum(c >= 0.9 for c in comps)
    print(f"{full}/{len(comps)} runs with 90%+ falling; mean {sum(comps) / len(comps):.0%}")
    print(" ".join(f"{c:.0%}" for c in comps))


if __name__ == "__main__":
    main()
