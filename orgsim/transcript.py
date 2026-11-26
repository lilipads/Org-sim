"""Readable Markdown transcript of a real-time (live) run."""
from __future__ import annotations


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
