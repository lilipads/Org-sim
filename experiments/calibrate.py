"""Calibration with scripted agents (no AI): how much of each design can teams
of 1, 4 and 10 finish in the time box, and how much does crowding cost?

    python3 experiments/calibrate.py [--seeds 10]
"""
from __future__ import annotations

import argparse
import os
import statistics as st
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orgsim.agents.scripted import ScriptedAgent, ScriptedTeam  # noqa: E402
from orgsim.designs import LIBRARY  # noqa: E402
from orgsim.dominoes import Physics  # noqa: E402
from orgsim.game import Game, GameConfig, table_world  # noqa: E402


def run_once(size: int, animal: str, seed: int, turns: int = 10, discussion=None, phys: Physics = Physics()):
    world = table_world("table", phys=phys)
    design = LIBRARY[animal]()
    names = [f"A{i + 1}" for i in range(size)]
    disc = discussion if discussion is not None else {1: 0, 4: 1, 10: 2}.get(size, 1)
    team = ScriptedTeam(design, names, world, discussion_turns=disc)
    agents = [ScriptedAgent(n, "table", team) for n in names]
    game = Game(world, agents, GameConfig(turns=turns, seed=seed))
    res = game.run()
    tab = res["per_table"]["table"]
    bumps = [e for r in game.log["turns"] for e in r["events"] if e["type"] == "bump"]
    return {
        "design_n": design.n,
        "placed": tab["placed"],
        "fell": tab["fell"],
        "share_of_design": tab["fell"] / design.n,
        "completion": tab["completion"],
        "bumps": len(bumps),
        "knocked_by_bumps": sum(b["knocked"] for b in bumps),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--bump-radius", type=float, default=Physics.bump_radius)
    ap.add_argument("--bump-chance", type=float, default=Physics.bump_chance)
    args = ap.parse_args()
    phys = Physics(bump_radius=args.bump_radius, bump_chance=args.bump_chance)
    print(f"bump radius {phys.bump_radius} units, chance {phys.bump_chance} per nearby builder per turn")
    print(f"{'size':>4} {'animal':>6} {'design':>6} {'placed':>7} {'fell':>6} "
          f"{'%design':>8} {'bumps':>6} {'knocked':>8}")
    for size in (1, 4, 10):
        for animal in LIBRARY:
            rs = [run_once(size, animal, s, phys=phys) for s in range(args.seeds)]
            m = lambda k: st.mean(r[k] for r in rs)  # noqa: E731
            print(f"{size:>4} {animal:>6} {rs[0]['design_n']:>6} {m('placed'):>7.0f} {m('fell'):>6.0f} "
                  f"{100 * m('share_of_design'):>7.0f}% {m('bumps'):>6.1f} {m('knocked_by_bumps'):>8.1f}")


if __name__ == "__main__":
    main()
