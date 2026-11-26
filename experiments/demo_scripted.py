"""End-to-end demo with scripted agents (no AI): round 1 at three tables, then
the Gallery Run. Writes logs, replays, judge images and push animations.

    python3 experiments/demo_scripted.py [--out results/demo_scripted]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orgsim.agents.scripted import ConnectorCrew, ScriptedAgent, ScriptedConnector, ScriptedTeam  # noqa: E402
from orgsim.designs import LIBRARY  # noqa: E402
from orgsim.game import Agent, Action, Game, GameConfig, gallery_world, table_world  # noqa: E402
from orgsim.render import picture_png, topple_gif  # noqa: E402
from orgsim.replay import write_replay  # noqa: E402


class Idle(Agent):
    def decide(self, obs):
        return Action("wait")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/demo_scripted")
    ap.add_argument("--size", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--crew", type=int, default=3, help="connector builders per table in round 2")
    ap.add_argument("--turns2", type=int, default=6)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    tables = ["Table 1", "Table 2", "Table 3"]
    animals = ["fish", "snail", "cat"]
    worlds, summary = [], {}
    for k, (tname, animal) in enumerate(zip(tables, animals)):
        world = table_world(tname)
        names = [f"{tname[-1]}{chr(65 + i)}" for i in range(args.size)]
        team = ScriptedTeam(LIBRARY[animal](), names, world, discussion_turns=1)
        game = Game(world, [ScriptedAgent(n, tname, team) for n in names], GameConfig(seed=args.seed + k))
        res = game.run()
        slug = f"round1_table{k + 1}"
        game.save(os.path.join(args.out, slug + ".json"))
        write_replay(game.log, os.path.join(args.out, slug + ".html"), f"Round 1 · {tname} · {animal}")
        picture_png(game.pushed_world, os.path.join(args.out, slug + "_judge.png"))
        topple_gif(game.pushed_world, {int(i): t for i, t in res["times"].items()},
                   os.path.join(args.out, slug + "_push.gif"), speedup=2.0)
        summary[slug] = {"animal": animal, **res["per_table"][tname], "seconds": res["duration"]}
        worlds.append(world)

    world, start_region = gallery_world(worlds)
    agents = []
    for k, tname in enumerate(tables):
        names = [f"{tname[-1]}{chr(65 + i)}" for i in range(args.size)]
        if k < len(tables) - 1:
            crew_size = min(args.crew, len(names))
            crew = ConnectorCrew(world, tname, tables[k + 1], crew_size)
            agents += [ScriptedConnector(names[j], tname, crew, j) for j in range(crew_size)]
            names = names[crew_size:]
        agents += [Idle(n, tname) for n in names]
    game = Game(world, agents, GameConfig(round_no=2, turns=args.turns2, time_limit=30.0, shared_pool="shared",
                                          seed=args.seed), start_region=start_region)
    res = game.run()
    game.save(os.path.join(args.out, "round2.json"))
    write_replay(game.log, os.path.join(args.out, "round2.html"), "Round 2 · Gallery Run")
    picture_png(game.pushed_world, os.path.join(args.out, "round2_judge.png"), scale=8)
    topple_gif(game.pushed_world, {int(i): t for i, t in res["times"].items()},
               os.path.join(args.out, "round2_push.gif"), scale=6, speedup=3.0)
    summary["round2"] = {"row_success": res["row_success"], "seconds": res["duration"],
                         "per_table": res["per_table"], "supply_left": game.world.supply}
    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
