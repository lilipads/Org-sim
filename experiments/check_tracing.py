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


# Sketches copied from real AI games that failed before the junction fixes.
LEADIN = [  # batch1 sonnet_B_s2: lead-in from the start, split into top and belly, V tail at the back
    {"type": "line", "x0": 3, "y0": 10, "x1": 6, "y1": 10},
    {"type": "curve", "points": [[6, 10], [7.5, 7.3], [10, 5.7], [14.5, 5], [19, 5.7], [21.5, 7.3], [23, 10]]},
    {"type": "curve", "points": [[6, 10], [7.5, 12.7], [10, 14.3], [14.5, 15], [19, 14.3], [21.5, 12.7], [23, 10]]},
    {"type": "line", "x0": 23, "y0": 10, "x1": 27, "y1": 6},
    {"type": "line", "x0": 23, "y0": 10, "x1": 27, "y1": 14},
]
VTAIL = [   # batch1 haiku_A_s1: tail drawn as one V stroke passing through the start
    {"type": "curve", "points": [[8, 10], [10, 7.5], [14, 5.8], [19, 6], [23, 8], [25, 10]]},
    {"type": "curve", "points": [[8, 10], [10, 12.5], [14, 14.2], [19, 14], [23, 12], [25, 10]]},
    {"type": "curve", "points": [[3, 5], [5, 8], [8, 10], [5, 12], [3, 15]]},
]
SKETCHES = {"fish": FISH, "leadin": LEADIN, "vtail": VTAIL}


class Tracer(LiveAgentBase):
    def __init__(self, name, jobs, sketcher=False, repair=False, sketch=None):
        super().__init__(name, "table")
        self.sketch = sketch or FISH
        self.jobs, self.sketcher, self.k = list(jobs), sketcher, 0
        self.repair, self.world = repair, None

    def act(self, obs):
        self.k += 1
        if self.sketcher and self.k == 1:
            return Decision(pad="take", eagerness=9, sketch=[])
        if self.sketcher and self.k == 2:
            return Decision(sketch=self.sketch, pad="put_down")
        if "nothing" in obs["pad_status"].lower():
            return Decision()
        if "waiting for the run" in obs["task"] and self.jobs:
            # stuck waiting: do another stroke first, come back to this one later
            waiting = int(obs["task"].split("start of stroke ")[1].split(")")[0])
            j = self.jobs.pop(0)
            self.jobs.append(waiting)
            return Decision(do="build", strokes=[{"type": "trace", "stroke": j}])
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


def run(seed: int, repair: bool = False, sketch="fish", return_world: bool = False):
    rng = random.Random(seed)
    strokes = SKETCHES[sketch] if isinstance(sketch, str) else sketch
    order = list(range(1, len(strokes) + 1))
    rng.shuffle(order)
    names = ["A", "B", "C", "D"]
    jobs = {n: order[i::len(names)] for i, n in enumerate(names)}
    agents = [Tracer(n, jobs[n], sketcher=(i == 0), repair=repair, sketch=strokes) for i, n in enumerate(names)]
    skills = {n: {"speed": rng.uniform(0.6, 1.6), "error": rng.uniform(0.5, 2.0)} for n in names}
    w = table_world("table", 30, 20, 250, Physics(pos_sigma=0.025, bump_radius=3.0))
    cfg = LiveConfig(duration=600, seed=seed, seconds_per_domino=3.0, skills=skills, freehand_sigma=0.15,
                     scratchpad_until=600, announce_at=(), idle_quiet=15, max_quiet=15)
    g = LiveGame(w, agents, cfg)
    for a in agents:
        a.world = w
    res = g.run()
    comp = res["per_table"]["table"]["completion"]
    return (comp, g) if return_world else comp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--repair", action="store_true", help="free hands look for breaks and fix them")
    ap.add_argument("--sketch", choices=list(SKETCHES), default="fish")
    args = ap.parse_args()
    comps = [run(s, args.repair, args.sketch) for s in range(args.seeds)]
    full = sum(c >= 0.9 for c in comps)
    print(f"{full}/{len(comps)} runs with 90%+ falling; mean {sum(comps) / len(comps):.0%}")
    print(" ".join(f"{c:.0%}" for c in comps))


if __name__ == "__main__":
    main()
