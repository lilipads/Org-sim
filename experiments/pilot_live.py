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
    ap.add_argument("--client", default="none",
                    help="none | auto (by seed) | a profile id from orgsim/clients.json")
    ap.add_argument("--decision", choices=["free", "dictator", "consensus"], default="free")
    ap.add_argument("--dictator", default="random", help="random | worst | best | a name (with --decision dictator)")
    ap.add_argument("--roles", action="store_true", help="Eng / Design / PM roles (DESIGN_REVIEW_STUDY.md)")
    ap.add_argument("--design-mode", choices=["lone", "review", "open"], default=None)
    ap.add_argument("--designer-role", choices=["eng", "design", "pm"], default="design")
    ap.add_argument("--review", choices=["none", "individual", "team", "manager", "peer", "forced"], default=None,
                    help="performance review condition (PERF_REVIEW_STUDY.md); overrides --evaluation")
    ap.add_argument("--styles", action="store_true", help="give each player a working style")
    ap.add_argument("--style-override", default=None,
                    help="Name=style, e.g. Tom=glue (paired design: switch one player's style)")
    ap.add_argument("--seams", action="store_true", help="joins between people's lines are a separate job")
    ap.add_argument("--depot", action="store_true",
                    help="dominoes come from boxes by the door: trays, bulk fetching, a shared bin (§14)")
    ap.add_argument("--runner-seat", default=None,
                    help="'auto' (seat = seed mod table size) or a name: that player is the assigned supply runner")
    ap.add_argument("--fetch-policy", default=None,
                    help="Name=share,Name=selfish: how those players fetch (both still build)")
    ap.add_argument("--manager-visibility", choices=["full", "low"], default="full",
                    help="low: visits a fifth of the time and no close look at the table")
    ap.add_argument("--ambition", action="store_true",
                    help="score = recognition x ambition x uniqueness against the other tables in the round")
    ap.add_argument("--reviews-only", action="store_true",
                    help="re-run only the end-of-game reviews on the finished game in --out (writes reviews_replay.json)")
    ap.add_argument("--wide-hands", action="store_true", help="speed 0.4-2.5x, placement error 0.3-3.0x")
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
            if args.wide_hands:
                skills[n] = {"speed": round(r.uniform(0.4, 2.5), 2), "error": round(r.uniform(0.3, 3.0), 2)}
            else:
                skills[n] = {"speed": round(r.uniform(0.6, 1.6), 2), "error": round(r.uniform(0.5, 2.0), 2)}
    cfg = LiveConfig(seconds_per_domino=args.seconds_per_domino, skills=skills,duration=args.minutes * 60, seed=args.seed, view=args.view,
                     scratchpad_until=args.pad_minutes * 60 if args.pad_minutes > 0 else None,
                     freehand_sigma=freehand, show_reach=(args.view == "image"), pad_only=not args.free_hand,
                     view_dir=tempfile.mkdtemp(prefix="views_") if args.view == "image" else None)
    # the client: who the picture is for, and what each person privately knows about them
    from orgsim import client as clientmod
    profile = clientmod.profile_for(args.seed, args.client) if args.client != "none" else None
    notes, pitches, dictator = {}, [], None
    roles, designer, checker = {}, None, None
    if not args.roles:                        # anyone can play the fall through the sketch (a dry run)
        from orgsim import design_check as _dc

        def checker(kind, who, strokes, note):
            return _dc.dry_run_text(strokes) if kind == "dry_run" else ""

    if args.roles:
        from orgsim import handwork, roles as rolesmod
        from orgsim import design_check
        handwork.SKIP_DETACHED_START = True         # an eye or a dot can't be the start (fixed rule)
        if not profile:
            raise SystemExit("--roles needs a client (--client auto)")
        roles = rolesmod.assign_roles(names, args.seed)
        designer = next(n for n in names if roles[n] == args.designer_role) if args.design_mode in ("lone", "review") else None
        cfg.roles, cfg.design_mode, cfg.designer = roles, args.design_mode, designer
        salt = f"seed{args.seed}"

        def checker(kind, who, strokes, note):
            if kind == "dry_run":
                return design_check.dry_run_text(strokes)
            if kind == "squint":
                return design_check.squint_text(strokes, calls, f"{salt}/{who}")
            return design_check.client_text(profile, strokes, note, calls, f"{salt}/{who}", args.model)
    if profile and args.roles:                   # only the PM met the client, and has all their notes
        pm = next(n for n in names if roles[n] == "pm")
        notes = {n: (list(profile["shared"]) + list(profile["unique"]) if n == pm else []) for n in names}
    elif profile:
        notes = clientmod.deal_notes(profile, names, args.seed)
    if profile and not args.roles:
        with ThreadPoolExecutor(len(names)) as ex:
            pitches = list(ex.map(lambda n: clientmod.pitch(n, PERSONAS_V2[n], profile, notes[n], calls, args.model,
                                                            f"seed{args.seed}"), names))
        print("pitches:", [(p["name"], p["animal"], p["score"]) for p in pitches], flush=True)
    if args.decision == "dictator":
        rank = clientmod.taste_ranking(pitches) if pitches else list(names)
        dictator = {"random": _random.Random(f"dictator/{args.seed}").choice(sorted(names)),
                    "worst": rank[0], "best": rank[-1]}.get(args.dictator, args.dictator)
        if dictator not in names:
            raise SystemExit(f"dictator {dictator!r} isn't at the table")
        cfg.decision, cfg.dictator = "dictator", dictator
    elif args.decision == "consensus":
        cfg.decision = "consensus"
    from orgsim import review as reviewmod
    styles = reviewmod.assign_styles(names, args.seed) if args.styles else {}
    if args.style_override:
        who, st_ = args.style_override.split("=")
        styles[who] = st_
    fetch_policy = dict(kv.split("=") for kv in args.fetch_policy.split(",")) if args.fetch_policy else {}
    if args.runner_seat:
        runner = names[args.seed % len(names)] if args.runner_seat == "auto" else args.runner_seat
        styles[runner] = "runner"
    cfg.depot = args.depot
    cfg.seams = args.seams
    manager = None
    cfg.show_tally = args.review == "individual"     # output-based reviews come with the metric on display
    if args.review in reviewmod.HAS_MANAGER:
        low = args.manager_visibility == "low"
        cfg.manager_schedule = reviewmod.manager_schedule(args.seed, cfg.duration, cfg.beat,
                                                          share=(0.2 if low else 1 / 3))
        manager = reviewmod.Manager(names, cfg.manager_schedule, calls, args.model, f"seed{args.seed}",
                                    forced=(args.review == "forced"), low_visibility=low)
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
        if args.depot:
            rules = rules.replace("THE TABLE\n", (
                "WHERE THE DOMINOES ARE\nThe dominoes are in boxes by the door, a short walk from the table. Your own tray "
                "at the table holds at most 12; there's also a shared bin at the table that anyone can take from and that "
                "has no limit. A trip to the boxes takes 40 seconds plus half a second per domino carried, up to 40 at a "
                "time, so carrying a lot at once is much cheaper per domino: 12 for your tray takes 46 s, 40 for the bin "
                "takes 60 s. While you're away your hands are off the table; a stroke you were laying waits and carries on "
                "when you're back. Laying takes from your tray first, then the shared bin; with neither, your stroke waits. "
                "To fetch: \"fetch\": {\"n\": how many, \"for\": \"me\" or \"bin\"}.\n\nTHE TABLE\n"), 1)
        if args.ambition:
            rules = rules.replace("The judge sees only the outline that falls,", (
                "Several tables at the offsite are doing this at once. Judges score three things, multiplied: whether "
                "they recognise the animal; how ambitious and well-made the picture is; and how unique it is, meaning "
                "different from what the other tables build (two tables with the same animal both score low on "
                "uniqueness). The judge sees only the outline that falls,"), 1)
        if not args.roles:
            rules = rules.replace("Sketch strokes use the table's coordinates:", (
                "To test a sketch before anyone builds it, add \"check\": \"dry_run\": for about 30 seconds you "
                "play the fall through the current sketch in your head, and learn which strokes would fall and which "
                "wouldn't.\nSketch strokes use the table's coordinates:"), 1)
        if args.seams:
            rules = rules.replace("THE TABLE\n", (
                "JOINS BETWEEN PEOPLE'S LINES\nWhen you trace a stroke that grows from a line someone else is laying, your "
                "hands start a hand's width short of their line, so you don't knock their work. Joining the two lines is a "
                "separate small job that anyone can do: {\"type\":\"connect\",\"from\":[x,y],\"to\":[x,y]} from the end of "
                "the line the fall arrives along to the first domino of the next line, or \"fix\" for a gap of a domino "
                "or two. A join nobody makes is a break in the run.\n\nTHE TABLE\n"), 1)
        if args.pad_minutes <= 0:
            import re
            rules = re.sub(r"THE SCRATCH PAD.*?(?=WHAT YOU CAN DO WITH YOUR HANDS)", "", rules, flags=re.S)
        fmt = ""
        if args.roles:
            rules, fmt = rolesmod.role_rules(rules, n, roles, args.design_mode, designer,
                                             clientmod.client_rules(profile, notes[n]), profile["commission"])
        elif profile:
            rules = rules.replace("THE TABLE\n", clientmod.client_rules(profile, notes[n]) + "\nTHE TABLE\n", 1)
        if args.decision == "dictator":
            if n == dictator:
                rules = rules.replace("THE TABLE\n", "WHO DECIDES\nYou alone decide what the table builds. Others may "
                                      "advise; the call is yours. Only you draw on the scratch pad, and nobody can lay a "
                                      "domino until you call the decision (say which animal, with \"decide\").\n\nTHE TABLE\n", 1)
                fmt = ('\nTo call the decision, add "decide": "<name of the animal>" (you can do this together with '
                       "anything else).")
            else:
                rules = rules.replace("THE TABLE\n", f"WHO DECIDES\n{dictator} alone decides what the table builds. You can "
                                      f"advise, but the call is {dictator}'s. Only {dictator} draws on the scratch pad, and "
                                      f"nobody can lay a domino until {dictator} calls the decision.\n\nTHE TABLE\n", 1)
        elif args.decision == "consensus":
            rules = rules.replace("THE TABLE\n", "WHO DECIDES\nThe table decides by consensus. Nobody can lay a domino "
                                  "until every person has said they're aligned on the same animal (with \"aligned\"). "
                                  "Talk it through until you all agree. You can change or withdraw your alignment "
                                  "later, but while the table isn't aligned, no new building starts.\n\nTHE TABLE\n", 1)
            fmt = ("\nTo say you're on board, add \"aligned\": \"<name of the animal>\" (or \"\" to withdraw). "
                   "You can do this together with anything else.")
        extra = {"model": args.model} if args.model else {}
        persona = PERSONAS_V2[n] + (f" Your working style: {reviewmod.STYLES[styles[n]]}" if styles.get(n) else "")
        if fetch_policy.get(n):
            persona += " " + reviewmod.FETCH_POLICIES[fetch_policy[n]]
        evaluation = reviewmod.EVALUATIONS[args.review] if args.review else args.evaluation
        if args.review in reviewmod.HAS_MANAGER:
            fmt += ("\nOptional: \"to_manager\": \"something you tell the manager privately (nobody else hears "
                    "it; if they're away, it waits for them)\".")
        agents.append(LiveLLMAgent(n, "table", persona, rules, evaluation, calls, **extra))
        agents[-1].extra_format = fmt
        if args.review:
            agents[-1].eval_line = reviewmod.REMINDERS[args.review]
        agents[-1].cache_salt = f"seed{args.seed}"
    game = LiveGame(world, agents, cfg, checker=checker)
    t0 = time.time()

    def run_reviews():
        heard = {a.name: [dict(m, new=False) for m in game.heard[a.name]] for a in agents}
        rv = {"condition": args.review, "evaluation_text": reviewmod.EVALUATIONS[args.review],
              "styles": styles, "skills": skills, "manager_schedule": cfg.manager_schedule,
              "fetch_policy": fetch_policy, "manager_visibility": args.manager_visibility}
        if manager is not None:
            with ThreadPoolExecutor(len(agents)) as ex:
                packets = dict(zip(names, ex.map(
                    lambda a: reviewmod.self_assessment(a, game.observe(a.name), heard[a.name],
                                                        reviewmod.own_log(game.log, a.name)), agents)))
            sas = {n: p["text"] for n, p in packets.items()}
            rv["self_assessments"] = sas
            rv["claimed_share"] = {n: p["share"] for n, p in packets.items()}
            rv["ratings"] = manager.finish(game, sas)
            rv["manager_visits"] = manager.history
        elif args.review == "peer":
            logs = {n: reviewmod.work_log(game.log, n) for n in names}
            with ThreadPoolExecutor(len(agents)) as ex:
                given = dict(zip(names, ex.map(lambda a: reviewmod.peer_ratings(
                    a, game.observe(a.name), heard[a.name], [o for o in names if o != a.name], logs[a.name][0]),
                    agents)))
            rv["peer_ratings_given"] = given
            rv["peer_seen"] = {n: logs[n][1] for n in names}
            rv["ratings"] = {n: reviewmod.peer_score(given, n, rv["peer_seen"]) for n in names}
        elif args.review == "individual":
            fell = {n: 0 for n in names}
            if getattr(game, "pushed_world", None) is not None:
                for d in game.pushed_world.dominoes.values():
                    if d.state == "down" and d.down_cause == "push" and d.builder in fell:
                        fell[d.builder] += 1
            else:                                   # replay: count from the log's push
                down = {int(k) for k in (game.log.get("push") or {}).get("times", {})}
                for d in game.world.dominoes.values():
                    if d.id in down and d.builder in fell:
                        fell[d.builder] += 1
            rv["ratings"] = {n: {"dominoes_fell": fell[n]} for n in names}
        return rv

    if args.reviews_only:
        # re-run only the end-of-game reviews on a finished game (same game, new review prompts)
        from orgsim.oracle import world_from_rows
        old = json.load(open(os.path.join(args.out, "log.json")))
        game.log = old
        game.world = world_from_rows(old["turns"][-1]["snapshot"], W, H)
        game.t = cfg.duration
        game.notes = dict(old["turns"][-1].get("notes") or game.notes)
        game.pad_strokes = (old.get("scratchpad") or {}).get("final") or []
        for n in names:
            game.heard[n] = [{"t": t["time"], "clock": t["clock"], "speaker": m["speaker"], "to": m["to"],
                              "text": m["message"], "side": False}
                             for t in old["turns"] for c in t["conversations"] for m in c["messages"]]
            game.inbox[n], game.task[n] = [], None
        if manager is not None:
            prev = json.load(open(os.path.join(args.out, "reviews.json")))
            manager.history = prev.get("manager_visits") or []
            manager.notes = manager.history[-1]["notes"] if manager.history else ""
            manager.present_prev, manager.visit, manager.queued = False, [], []
        rv = run_reviews()
        reviewmod.save(os.path.join(args.out, f"reviews_replay_{args.review}.json"), rv)
        print(json.dumps(rv.get("ratings"), indent=1))
        return

    def progress(g):
        rec = g.log["turns"][-1]
        line = f"[{time.time() - t0:5.0f}s] {rec['clock']} asked {','.join(rec['asked']) or '-'} | dominoes {len(g.world.dominoes)} | calls {len(calls.calls)}"
        print(line, flush=True)
        for c in rec["conversations"]:
            m = c["messages"][0]
            print(f"    {m['speaker']} -> {m['to'] if isinstance(m['to'], str) else ','.join(m['to'])}: {m['message'][:200]}", flush=True)
        for h in rec["held"]:
            print(f"    ({h['who']} held a thought)", flush=True)
        if manager is not None:
            manager.observe(g, rec)
        if len(g.log["turns"]) % 8 == 0:
            g.save(os.path.join(args.out, "log.json"))

    res = game.run(progress=progress)
    with ThreadPoolExecutor(len(agents)) as ex:
        intents = dict(zip(names, ex.map(
            lambda a: a.state_intent(game.observe(a.name), [dict(m, new=False) for m in game.heard[a.name]]),
            agents)))
    vals = [v for v in intents.values() if v]
    intent = max(set(vals), key=vals.count) if vals else ""
    reviews = None
    if args.review:
        reviews = run_reviews()
        reviewmod.save(os.path.join(args.out, "reviews.json"), reviews)
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
    if args.roles:
        from orgsim.design_check import aesthetics_panel, dry_run, ideal_png
        art = aesthetics_panel(png, calls)
        des = game.log.get("design") or {}
        locked = des.get("locked_sketch") or []
        quality = None
        if locked:
            ip = ideal_png(locked, os.path.join(args.out, "locked_design.png"))
            jl = judge_picture(ip, intent, 3, calls)
            dr = dry_run(locked)
            quality = {"recognition": jl["recognition"], "aesthetics": aesthetics_panel(ip, calls)["aesthetics"],
                       "dry_run_fell": dr["fell"], "per_stroke": dr["per_stroke"]}
        checks = [e for r in game.log["turns"] for e in r["events"] if e["type"] == "check"]
        summary.update({"roles": roles, "design_mode": args.design_mode, "designer": designer,
                        "locked_at": des.get("locked_at"), "reviews": des.get("reviews"),
                        "aesthetics": art["aesthetics"], "art_ratings": art["ratings"],
                        "locked_design_quality": quality,
                        "checks": [{"who": c["who"], "check": c["check"]} for c in checks]})
    if profile:
        built = clientmod.rate_animal(profile, intent, calls)
        summary.update({
            "client": profile["id"], "client_best": profile["best"], "notes": notes, "pitches": pitches,
            "taste_ranking_worst_first": clientmod.taste_ranking(pitches),
            "client_score": built["score"], "client_matched": built["matched"],
            "final_score": round(judging["recognition"] * built["score"] * (summary.get("aesthetics") or 1.0), 3),
            "notes_surfaced": clientmod.notes_surfaced(profile, notes, game.log, calls),
        })
    dec = game.log.get("decision") or {}
    if args.ambition:
        from orgsim.design_check import ambition_panel
        amb = ambition_panel(png, calls)
        summary.update({"ambition": amb["ambition"], "ambition_ratings": amb["ratings"],
                        "score_without_uniqueness": round(judging["recognition"] * amb["ambition"], 3),
                        "uniqueness": "computed across the round's tables (experiments/uniqueness.py)"})
    if args.review:
        summary.update({"review": args.review, "styles": styles, "review_ratings": reviews.get("ratings")})
    summary.update({"decision": args.decision, "dictator": dictator, "decided": dec.get("animal"),
                    "decision_open_at": dec.get("open_at")})
    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
