"""Pilot with the real-time engine (interaction model v2): one table, round 1.

    python3 experiments/pilot_live.py --size 4 --minutes 20 --out results/pilot/live_table4_run1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orgsim.agents.live_llm import PERSONAS_V2, RULES_V2, TABLE_OF_4_V2, LiveLLMAgent  # noqa: E402
from orgsim.agents.llm import NO_EVALUATION, CallLog  # noqa: E402
from orgsim.game import table_world  # noqa: E402
from orgsim.judge import judge_picture  # noqa: E402
from orgsim.live import LiveConfig, LiveGame  # noqa: E402
from orgsim.render import picture_png, topple_gif  # noqa: E402
from orgsim.replay import write_replay  # noqa: E402
from orgsim.agents.llm import call_model  # noqa: E402
from orgsim.transcript import live_transcript, recap_prompt, story_transcript  # noqa: E402


def names_for(size: int) -> list:
    return TABLE_OF_4_V2 if size == 4 else list(PERSONAS_V2)[:size]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=4)
    ap.add_argument("--minutes", type=float, default=20)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="results/pilot/live_table4_run1")
    ap.add_argument("--evaluation", default=NO_EVALUATION)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    calls = CallLog(os.path.join(args.out, "calls.jsonl"))
    open(calls.path, "w").close()

    world = table_world("table")
    names = names_for(args.size)
    cfg = LiveConfig(duration=args.minutes * 60, seed=args.seed)
    agents = []
    for n in names:
        rules = RULES_V2.format(n_others=len(names) - 1, minutes=int(args.minutes), w=60, h=40,
                                supply=world.supply["table"])
        agents.append(LiveLLMAgent(n, "table", PERSONAS_V2[n], rules, args.evaluation, calls))
    game = LiveGame(world, agents, cfg)
    t0 = time.time()

    def progress(g):
        rec = g.log["turns"][-1]
        line = f"[{time.time() - t0:5.0f}s] {rec['clock']} asked {','.join(rec['asked']) or '-'} | dominoes {len(g.world.dominoes)} | calls {len(calls.calls)}"
        print(line, flush=True)
        for c in rec["conversations"]:
            m = c["messages"][0]
            print(f"    {m['speaker']} -> {m['to'] if isinstance(m['to'], str) else ','.join(m['to'])}: {m['message'][:200]}", flush=True)
        for h in rec["held"]:
            print(f"    ({h['who']} held a thought)", flush=True)
        if len(g.log["turns"]) % 8 == 0:
            g.save(os.path.join(args.out, "log.json"))

    res = game.run(progress=progress)
    with ThreadPoolExecutor(len(agents)) as ex:
        intents = dict(zip(names, ex.map(
            lambda a: a.state_intent(game.observe(a.name), [dict(m, new=False) for m in game.heard[a.name]]),
            agents)))
    vals = [v for v in intents.values() if v]
    intent = max(set(vals), key=vals.count) if vals else ""
    png = picture_png(game.pushed_world, os.path.join(args.out, "judge.png"))
    picture_png(game.pushed_world, os.path.join(args.out, "before_push.png"), show_standing=True)
    judging = judge_picture(png, intent, 3, calls)
    topple_gif(game.pushed_world, {int(i): t for i, t in res["times"].items()},
               os.path.join(args.out, "push.gif"), speedup=2.0)
    game.log["intents"], game.log["judging"] = intents, judging
    game.save(os.path.join(args.out, "log.json"))
    title = f"AI pilot (real-time) · table of {args.size}"
    write_replay(game.log, os.path.join(args.out, "replay.html"), title)
    recap = call_model("You write short, vivid recaps for a blog about teamwork.", recap_prompt(game.log),
                       calls, "recap")
    game.log["recap"] = recap
    game.save(os.path.join(args.out, "log.json"))
    with open(os.path.join(args.out, "transcript_detailed.md"), "w") as f:
        f.write(live_transcript(game.log, title))
    with open(os.path.join(args.out, "story.md"), "w") as f:
        f.write(story_transcript(game.log, title, recap))

    tab = res["per_table"]["table"]
    msgs = [c["messages"][0] for r in game.log["turns"] for c in r["conversations"]]
    by_speaker = {}
    for m in msgs:
        by_speaker[m["speaker"]] = by_speaker.get(m["speaker"], 0) + 1
    first_build = next((r["clock"] for r in game.log["turns"]
                        if any(e["type"] == "build" and e["placed"] for e in r["events"])), None)
    summary = {
        "size": args.size, "minutes": args.minutes, "wall_seconds": round(time.time() - t0, 1),
        "intents": intents, "team_intent": intent, "recognition": judging["recognition"],
        "judge_guesses": [j["guesses"] for j in judging["judges"]],
        "placed": tab["placed"], "fell": tab["fell"], "completion": tab["completion"],
        "team_score": round(judging["recognition"] * tab["completion"], 3),
        "first_domino_at": first_build, "messages": len(msgs), "messages_by_speaker": by_speaker,
        "held_thoughts": sum(len(r["held"]) for r in game.log["turns"]),
        "parse_failures": {a.name: a.failures for a in agents}, "usage": calls.totals(),
    }
    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
