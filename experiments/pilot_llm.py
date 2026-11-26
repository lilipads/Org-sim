"""Pilot: one table of AI agents playing round 1 (DESIGN.md §10, step 3).

Measures model calls, tokens and time per run, and produces the replay, the
judge image, the push animation and blind judging.

    python3 experiments/pilot_llm.py --size 4 --turns 10 --out results/pilot/run1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orgsim.agents.llm import NO_EVALUATION, PERSONAS, RULES, TABLE_OF_4, CallLog, LLMAgent  # noqa: E402
from orgsim.game import Game, GameConfig, table_world  # noqa: E402
from orgsim.judge import judge_picture  # noqa: E402
from orgsim.render import picture_png, topple_gif  # noqa: E402
from orgsim.replay import write_replay  # noqa: E402


def names_for(size: int) -> list:
    if size == 4:
        return TABLE_OF_4
    return list(PERSONAS)[:size]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=4)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="results/pilot/run1")
    ap.add_argument("--evaluation", default=NO_EVALUATION)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    calls = CallLog(os.path.join(args.out, "calls.jsonl"))
    open(calls.path, "w").close()

    world = table_world("table")
    rules = RULES.format(n=args.size, w=60, h=40, supply=world.supply["table"], turns=args.turns)
    agents = [LLMAgent(n, "table", PERSONAS[n], rules, args.evaluation, calls) for n in names_for(args.size)]
    cfg = GameConfig(turns=args.turns, seed=args.seed, rules_text="(see system prompt)", eval_text=args.evaluation)
    game = Game(world, agents, cfg)
    t0 = time.time()

    def progress(t, g):
        rec = g.log["turns"][-1]
        acts = ", ".join(f"{n}:{d.get('kind')}" for n, d in rec["decisions"].items())
        print(f"[{time.time() - t0:5.0f}s] turn {t}: {acts} | dominoes {len(g.world.dominoes)} | "
              f"calls {len(calls.calls)}", flush=True)
        for c in rec["conversations"]:
            for m in c["messages"][:6]:
                print(f"    {m['speaker']}: {m['message'][:160]}", flush=True)
        g.save(os.path.join(args.out, "log.json"))

    res = game.run(progress=progress)

    with ThreadPoolExecutor(len(agents)) as ex:
        intents = dict(zip([a.name for a in agents],
                           ex.map(lambda a: a.state_intent(game.observe(a, args.turns)), agents)))
    vals = [v for v in intents.values() if v]
    intent = max(set(vals), key=vals.count) if vals else ""
    png = picture_png(game.pushed_world, os.path.join(args.out, "judge.png"))
    judging = judge_picture(png, intent, 3, calls)
    topple_gif(game.pushed_world, {int(i): t for i, t in res["times"].items()},
               os.path.join(args.out, "push.gif"), speedup=2.0)

    game.log["intents"] = intents
    game.log["judging"] = judging
    game.save(os.path.join(args.out, "log.json"))
    write_replay(game.log, os.path.join(args.out, "replay.html"), f"AI pilot · table of {args.size}")

    tab = res["per_table"]["table"]
    actions = {}
    for r in game.log["turns"]:
        for d in r["decisions"].values():
            actions[d.get("kind")] = actions.get(d.get("kind"), 0) + 1
    first_build = next((r["turn"] for r in game.log["turns"]
                        if any(e["type"] == "build" and e["placed"] for e in r["events"])), None)
    summary = {
        "size": args.size, "turns": args.turns, "wall_seconds": round(time.time() - t0, 1),
        "intents": intents, "team_intent": intent,
        "recognition": judging["recognition"], "judge_guesses": [j["guesses"] for j in judging["judges"]],
        "placed": tab["placed"], "fell": tab["fell"], "completion": tab["completion"],
        "team_score": round(judging["recognition"] * tab["completion"], 3),
        "first_build_turn": first_build, "action_counts": actions,
        "parse_failures": {a.name: a.failures for a in agents},
        "usage": calls.totals(),
    }
    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
