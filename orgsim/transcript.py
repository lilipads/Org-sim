"""Readable Markdown transcript of a real-time (live) run."""
from __future__ import annotations

import json


def _to(to) -> str:
    if to in (None, "everyone"):
        return "everyone"
    return ", ".join(to) if isinstance(to, list) else str(to)


def _doing(d: dict) -> str:
    do = d.get("do", "continue")
    if do == "build":
        strokes = d.get("strokes") or []
        kinds = ", ".join(s.get("type", "?") for s in strokes) or "re-standing"
        return f"starts building ({kinds})" + (" and marks the start" if d.get("start") else "")
    if do == "take_down":
        return f"starts taking down dominoes in {d.get('area')}"
    if do == "inspect":
        return f"inspects {d.get('area')}"
    if do == "stop":
        return "stops and watches"
    if do == "walk":
        return f"walks to {d.get('where')}"
    return ""


def live_transcript(log: dict, title: str = "Transcript") -> str:
    out = [f"# {title}", ""]
    cfg = log["config"]
    out.append(f"Round {cfg['round_no']}, {int(cfg['duration'] // 60)} minutes. Brief: make a picture of an animal.")
    out.append("")
    for a in log["agents"]:
        out.append(f"- **{a['name']}**: {a['persona']}")
    out.append("")
    for rec in log["turns"]:
        lines = []
        said = {c["messages"][0]["speaker"]: c for c in rec["conversations"]}
        for n, d in rec["decisions"].items():
            thinking = d.get("thinking", "").strip()
            act = _doing(d)
            if n in said:
                c = said[n]
                m = c["messages"][0]
                lines.append(f"> **{n}** (to {_to(m['to'])}): {m['message']}")
                extra = f" Meanwhile {n} {act}." if act else ""
                if thinking or extra:
                    lines.append(f">  ")
                    lines.append(f"> _{n} thinks: {thinking}_{extra}")
                lines.append("")
            elif act:
                lines.append(f"- **{n}** {act}." + (f" _{thinking}_" if thinking else ""))
            elif thinking and d.get("do") in ("continue", None):
                lines.append(f"- _{n} keeps going: {thinking}_")
        for h in rec.get("held", []):
            lines.append(f"- _{h['who']} was about to say \"{h['message']}\" but {h['yielded_to']} spoke first._")
        for e in rec["events"]:
            if e["type"] == "bump":
                lines.append(f"- 💥 {e['who']} bumped the table near {e['near']}: {e['knocked']} dominoes fell.")
            elif e["type"] == "take_down":
                lines.append(f"- ✋ {e['who']} took down {len(e['ids'])} dominoes "
                             f"({', '.join(f'{k}: {v}' for k, v in e['whose'].items())}).")
            elif e["type"] == "move":
                lines.append(f"- 🚶 {e['who']} walked to {e['where']}.")
        if lines:
            out.append(f"### {rec['clock']}")
            out.append("")
            out += lines
            out.append("")
    push = log.get("push")
    if push:
        out.append("## The push")
        out.append("")
        for name, v in push["per_table"].items():
            out.append(f"{name}: {v['fell']} of {v['standing_at_push']} standing dominoes fell "
                       f"({round(100 * v['completion'])}%).")
        out.append("")
    if log.get("intents"):
        out.append("**What each person said the animal was:** "
                   + ", ".join(f"{k}: {v}" for k, v in log["intents"].items()))
        out.append("")
    if log.get("judging"):
        out.append(f"**Blind judges' guesses** (recognition {log['judging']['recognition']}):")
        for j in log["judging"]["judges"]:
            out.append(f"- {', '.join(j['guesses'])}")
        out.append("")
    return "\n".join(out)


# ---- story version -------------------------------------------------------------

def _place_words(x: float, y: float, w: float = 60, h: float = 40) -> str:
    fx, fy = x / w, y / h
    hpos = "left" if fx < 1 / 3 else ("right" if fx > 2 / 3 else "")
    vpos = "top" if fy < 1 / 3 else ("bottom" if fy > 2 / 3 else "")
    if not hpos and not vpos:
        return "in the middle of the table"
    if hpos and vpos:
        return f"in the {vpos}-{hpos} corner"
    return f"on the {hpos or vpos} side of the table"


def _story_action(n: str, d: dict) -> str:
    do = d.get("do", "continue")
    if do == "build":
        strokes = d.get("strokes") or []
        kinds = [s.get("type") for s in strokes]
        first = strokes[0] if strokes else {}
        if "connect" in kinds:
            act = f"{n} starts joining two pieces together"
        elif "extend" in kinds:
            act = f"{n} carries a line on"
        elif first:
            x = first.get("x0", first.get("cx", first.get("x")))
            y = first.get("y0", first.get("cy", first.get("y")))
            try:
                act = f"{n} starts laying dominoes {_place_words(float(x), float(y))}"
            except (TypeError, ValueError):
                act = f"{n} starts laying dominoes"
        else:
            act = f"{n} stands knocked-over dominoes back up"
        if d.get("start"):
            act += ", beginning with the start domino"
        return act + "."
    if do == "take_down":
        return f"{n} starts taking some dominoes away."
    if do == "inspect":
        return f"{n} leans in for a close look."
    return ""


def story_transcript(log: dict, title: str = "Story", recap: str = "") -> str:
    """A readable, story-like transcript: who said what, what people did, what went
    wrong. No coordinates in the narration, no private thoughts, no held remarks."""
    out = [f"# {title}", ""]
    cfg = log["config"]
    out.append(f"*{len(log['agents'])} people, {int(cfg['duration'] // 60)} minutes, one brief: "
               "make a picture of an animal out of dominoes.*")
    out.append("")
    out.append("**The table**")
    out.append("")
    for a in log["agents"]:
        first = a["persona"].split(". ")[0].rstrip(".")
        out.append(f"- **{a['name']}**: {first}.")
    out.append("")
    if recap:
        out.append("## In short")
        out.append("")
        out.append(recap.strip())
        out.append("")
    out.append("## What happened")
    current_minute = -1
    last_build: dict = {}
    for rec in log["turns"]:
        lines = []
        for c in rec["conversations"]:
            m = c["messages"][0]
            to = "" if m["to"] in ("everyone", None) else f" *(to {_to(m['to'])})*"
            point = " *(pointing)*" if m.get("pointing") else ""
            lines.append(f"**{m['speaker']}**{to}{point}: {m['message']}")
        for n, d in rec["decisions"].items():
            if d.get("do") == "build":
                sig = json.dumps(d.get("strokes"), sort_keys=True) + str(d.get("restand"))
                if last_build.get(n) == sig:
                    continue
                last_build[n] = sig
            act = _story_action(n, d)
            if act:
                lines.append(f"*{act}*")
        for e in rec["events"]:
            if e["type"] == "bump":
                lines.append(f"*Bump! {e['who']} jolts the table and {e['knocked']} dominoes go down.*")
            elif e["type"] == "take_down":
                others = {k: v for k, v in e["whose"].items() if k != e["who"]}
                if others:
                    lines.append(f"*{e['who']} removes {', '.join(f'{v} of {k}' + chr(39) + 's' for k, v in others.items())} dominoes.*")
            elif e["type"] == "move":
                lines.append(f"*{e['who']} walks over to {e['where']}.*")
        if not lines:
            continue
        minute = int(rec["time"] // 60)
        if minute != current_minute:
            current_minute = minute
            out.append("")
            left = int((cfg["duration"] - rec["time"]) // 60)
            out.append(f"### {minute}:00 ({left} minutes left)")
        out.append("")
        out.append("\n\n".join(lines))
    push = log.get("push")
    if push:
        out.append("")
        out.append("## The push")
        out.append("")
        for name, v in push["per_table"].items():
            out.append(f"Someone flicks the start domino. {v['fell']} of the {v['standing_at_push']} standing "
                       f"dominoes fall ({round(100 * v['completion'])}%).")
    if log.get("intents"):
        out.append("")
        out.append("Asked afterwards what the picture was meant to be: "
                   + "; ".join(f"{k}: *{v}*" for k, v in log["intents"].items()) + ".")
    if log.get("judging"):
        out.append("")
        out.append("The judges, seeing only what fell, guessed: "
                   + "; ".join("*" + ", ".join(j["guesses"]) + "*" for j in log["judging"]["judges"]) + ".")
    return "\n".join(out) + "\n"


def recap_prompt(log: dict) -> str:
    lines = []
    for rec in log["turns"]:
        for c in rec["conversations"]:
            m = c["messages"][0]
            lines.append(f"[{rec['clock']}] {m['speaker']}: {m['message']}")
        for e in rec["events"]:
            if e["type"] in ("bump", "take_down"):
                lines.append(f"[{rec['clock']}] ({e['type']} by {e['who']})")
    push = log.get("push", {}).get("per_table", {})
    res = "; ".join(f"{v['fell']} of {v['standing_at_push']} fell" for v in push.values())
    guesses = "; ".join(", ".join(j["guesses"]) for j in log.get("judging", {}).get("judges", []))
    return ("Here is the log of a team building a domino picture of an animal in 20 minutes.\n\n"
            + "\n".join(lines)
            + f"\n\nResult: {res}. People said it was: {log.get('intents')}. Blind judges guessed: {guesses}.\n\n"
            "Write a recap of what happened at this table in 120-160 words, as a short story for a blog "
            "about teamwork. Plain, vivid English. Name who did what and the turning points. Stick strictly to "
            "the log: don't invent dialogue, gestures, feelings or events. You may quote lines from the log. "
            "No coordinates or numbers except the final result. Reply with the recap only.")
