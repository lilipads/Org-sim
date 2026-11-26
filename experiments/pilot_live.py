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

from orgsim.agents.live_llm import PERSONAS_V2, RULES_V2, TABLE_OF_4_V2, VIEW_RULES, LiveLLMAgent  # noqa: E402
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
    ap.add_argument("--minutes", type=float, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="results/pilot/live_table4_run1")
    ap.add_argument("--evaluation", default=NO_EVALUATION)
    ap.add_argument("--view", choices=["text", "image"], default="text")
    ap.add_argument("--pad-minutes", type=float, default=None,
                    help="scratch pad until this minute; 0 = no pad; default: the whole round")
    ap.add_argument("--model", default=None, help="model for the agents (judges keep the default)")
    ap.add_argument("--names", default=None, help="comma-separated persona names to seat (overrides --size)")
    ap.add_argument("--seconds-per-domino", type=float, default=3.0, help="average hand speed")
    ap.add_argument("--same-hands", action="store_true", help="everyone builds at the same speed and accuracy")
    ap.add_argument("--free-hand", action="store_true", help="also allow free-hand strokes (line, arc, extend, connect)")
    ap.add_argument("--big", action="store_true",
                    help="bigger dominoes: 30x20 table in domino lengths, 130 pieces, finer relative hand error")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    calls = CallLog(os.path.join(args.out, "calls.jsonl"))
    open(calls.path, "w").close()

    from orgsim.dominoes import Physics
    if args.big:
        W, H, supply = 30, 20, 250
        phys = Physics(pos_sigma=0.025, bump_radius=3.0)
        freehand = 0.15
    else:
        W, H, supply = 60, 40, 250
        phys = Physics()
        freehand = 0.3
    world = table_world("table", W, H, supply, phys)
    if args.pad_minutes is None:
        args.pad_minutes = args.minutes
    names = [n.strip() for n in args.names.split(",")] if args.names else names_for(args.size)
    unknown = [n for n in names if n not in PERSONAS_V2]
    if unknown:
        raise SystemExit(f"unknown persona(s): {unknown}; choose from {list(PERSONAS_V2)}")
    args.size = len(names)
    import random as _random
    import tempfile
    skills = {}
    if not args.same_hands:
        r = _random.Random(1000 + args.seed)
        for n in names:   # independent draws: fast-and-careless, slow-and-precise, and all between
            skills[n] = {"speed": round(r.uniform(0.6, 1.6), 2), "error": round(r.uniform(0.5, 2.0), 2)}
    cfg = LiveConfig(seconds_per_domino=args.seconds_per_domino, skills=skills,duration=args.minutes * 60, seed=args.seed, view=args.view,
                     scratchpad_until=args.pad_minutes * 60 if args.pad_minutes > 0 else None,
                     freehand_sigma=freehand, show_reach=(args.view == "image"), pad_only=not args.free_hand,
                     view_dir=tempfile.mkdtemp(prefix="views_") if args.view == "image" else None)
    agents = []
    for n in names:
        rules = RULES_V2.format(n_others=len(names) - 1, minutes=int(args.minutes), w=W, h=H,
                                bump_units=int(phys.bump_radius),
                                supply=world.supply["table"], view_rules=VIEW_RULES[args.view],
                                start_rule=("It goes where START is on the pad, and it's laid by whoever traces "
                                            "stroke 1; nobody else sets it." if not args.free_hand else
                                            'Set "start": true on a build and its first domino becomes the start. '
                                            "Setting it again later moves the start."),
                                pad_rule=("The pad stays on the table for the whole activity."
                                          if args.pad_minutes >= args.minutes else
                                          f"At {int(args.pad_minutes)}:{int(args.pad_minutes * 60) % 60:02d} the "
                                          "facilitator takes the pad away for good; after that, work from memory."))
        if len(names) == 1:
            rules = rules.replace("sitting at a table with 0 colleagues", "sitting at a table on your own")
        if args.pad_minutes <= 0:
            import re
            rules = re.sub(r"THE SCRATCH PAD.*?(?=WHAT YOU CAN DO WITH YOUR HANDS)", "", rules, flags=re.S)
        extra = {"model": args.model} if args.model else {}
        agents.append(LiveLLMAgent(n, "table", PERSONAS_V2[n], rules, args.evaluation, calls, **extra))
        agents[-1].cache_salt = f"seed{args.seed}"
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
    jscale = max(14, int(840 / W))
    png = picture_png(game.pushed_world, os.path.join(args.out, "judge.png"), scale=jscale)
    picture_png(game.pushed_world, os.path.join(args.out, "before_push.png"), show_standing=True, scale=jscale)
    judging = judge_picture(png, intent, 3, calls)
    # Design legibility, separate from integration: judge the whole layout as if everything fell.
    import copy
    allfell = copy.deepcopy(game.world)
    for d in allfell.dominoes.values():
        d.state = "down"
    png_all = picture_png(allfell, os.path.join(args.out, "judge_if_all_fell.png"), scale=jscale)
    judging_all = judge_picture(png_all, intent, 3, calls)
    topple_gif(game.pushed_world, {int(i): t for i, t in res["times"].items()},
               os.path.join(args.out, "push.gif"), speedup=2.0)
    game.log["intents"], game.log["judging"] = intents, judging
    game.log["judging_if_all_fell"] = judging_all
    game.save(os.path.join(args.out, "log.json"))
    from orgsim.sketch_record import record as record_sketch
    record_sketch(args.out, game.log)          # sketch.json + sketch.png: the pad as the team left it
    title = f"AI pilot (real-time) · table of {args.size}"
    write_replay(game.log, os.path.join(args.out, "replay.html"), title)
    recap = call_model("You write short, vivid recaps for a blog about teamwork.", recap_prompt(game.log),
                       calls, "recap", cache_salt=f"seed{args.seed}")
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
        "size": args.size, "minutes": args.minutes, "view": args.view, "pad_minutes": args.pad_minutes,
        "big_dominoes": args.big, "personas": names, "skills": skills,
        "seconds_per_domino": args.seconds_per_domino, "agent_model": args.model or "default (small)", "wall_seconds": round(time.time() - t0, 1),
        "intents": intents, "team_intent": intent, "recognition": judging["recognition"],
        "recognition_if_all_fell": judging_all["recognition"],
        "pad_holders": [e.get("who") for r in game.log["turns"] for e in r["events"]
                        if e["type"] == "pad" and e.get("what") in ("picked up", "gave")],
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
