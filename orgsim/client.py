"""The client (DECISION_STUDY.md): who the picture is for, what each person knows about
what they want, private pitches, and how happy the client is with an animal.

Profiles are fixed (clients.json). Mapping a free-text animal onto the client's guide uses a
small cached model call only when the name isn't in the guide already.
"""
from __future__ import annotations

import json
import os
import random

from .agents.llm import CallLog, call_model, parse_json

with open(os.path.join(os.path.dirname(__file__), "clients.json")) as _f:
    PROFILES = {p["id"]: p for p in json.load(_f)["profiles"]}


def profile_for(seed: int, which: str | None = None) -> dict:
    if which and which != "auto":
        return PROFILES[which]
    ids = sorted(PROFILES)
    return PROFILES[ids[seed % len(ids)]]


def deal_notes(profile: dict, names: list, seed: int, rumour: bool = True) -> dict:
    """Each person: the shared notes plus one unique note (cycled if more people than notes).
    One person, chosen by lot, also has the rumour."""
    rng = random.Random(f"notes/{profile['id']}/{seed}")
    uniq = list(profile["unique"])
    rng.shuffle(uniq)
    order = list(names)
    rng.shuffle(order)
    notes = {n: list(profile["shared"]) for n in names}
    for i, n in enumerate(order):
        notes[n].append(uniq[i % len(uniq)])
    if rumour and profile.get("rumour"):
        notes[rng.choice(names)].append(profile["rumour"])
    return notes


def client_rules(profile: dict, my_notes: list) -> str:
    lines = "\n".join(f"- {x}" for x in my_notes)
    return ("THE CLIENT\n"
            f"{profile['commission']} The picture is judged twice: blind judges must recognise the animal, and "
            "the client must be happy with the choice. Your score is the two multiplied, so a perfectly built "
            "animal the client dislikes scores nothing.\n"
            "Each of you met the client separately, so you may know different things. Your own notes from "
            "meeting them (nobody else has seen these unless you say them out loud):\n" + lines + "\n")


def _norm(s: str) -> str:
    return " ".join(str(s or "").lower().replace("-", " ").split())


def rate_animal(profile: dict, animal: str, log: CallLog | None = None) -> dict:
    """{'animal', 'matched', 'score'}: how happy this client is with this animal."""
    a = _norm(animal)
    guide = profile["guide"]
    if not a:
        return {"animal": a, "matched": None, "score": 0.0}
    if a in guide:
        return {"animal": a, "matched": a, "score": guide[a]}
    for k in sorted(guide, key=len, reverse=True):          # "a big sea turtle" -> "sea turtle"
        if f" {k} " in f" {a} " or f" {k}s " in f" {a} ":
            return {"animal": a, "matched": k, "score": guide[k]}
    prompt = (f"Animal named by a team: {animal!r}.\nOptions: {sorted(guide)}.\n"
              "Which option is the same animal (synonym, or a more specific kind of it)? If none is, say null. "
              'Reply with JSON only: {"match": "option" or null}')
    out = parse_json(call_model("You match animal names. Be strict.", prompt, log, "client/match",
                                cache_salt=profile["id"])) or {}
    m = out.get("match")
    if isinstance(m, str) and _norm(m) in guide:
        return {"animal": a, "matched": _norm(m), "score": guide[_norm(m)]}
    return {"animal": a, "matched": None, "score": profile.get("default", 0.1)}


PITCH_SYSTEM = "You are taking part in a team activity. Answer briefly and in character."


def pitch(name: str, persona: str, profile: dict, notes: list, log: CallLog | None, model: str | None,
          salt: str) -> dict:
    """One private answer before the game: what would you build for this client, and why?"""
    prompt = (f"Your personality: {persona}\n\n{client_rules(profile, notes)}\n"
              "Before your table starts, on your own: which animal would you build for this client, and why? "
              "You can't ask anyone; go with what you know. "
              'Reply with JSON only: {"animal": "...", "why": "one or two sentences"}')
    kw = {"model": model} if model else {}
    out = parse_json(call_model(PITCH_SYSTEM, prompt, log, f"{name}/pitch", cache_salt=salt, **kw)) or {}
    animal = str(out.get("animal") or "")
    return {"name": name, "animal": animal, "why": str(out.get("why") or ""), **rate_animal(profile, animal, log)}


def taste_ranking(pitches: list) -> list:
    """Names, worst taste first (ties broken by name so it's stable)."""
    return [p["name"] for p in sorted(pitches, key=lambda p: (p["score"], p["name"]))]


def notes_surfaced(profile: dict, notes: dict, log: dict, calls: CallLog | None) -> dict:
    """Which unique notes (and the rumour) were said out loud, by whom, and when (seconds)."""
    said = []
    for t in log.get("turns", []):
        for c in t.get("conversations", []):
            for m in c.get("messages", []):
                said.append(f"[{t['time']:.0f}s] {m['speaker']}: {m['message']}")
    facts = list(profile["unique"]) + ([profile["rumour"]] if profile.get("rumour") else [])
    holders = {f: [n for n, ns in notes.items() if f in ns] for f in facts}
    prompt = ("Here is what a team said, with times in seconds:\n" + "\n".join(said)[:60000] +
              "\n\nFor each fact below, did anyone say its substance out loud (not word for word)? If so, give the "
              "earliest time and who said it.\n" + "\n".join(f"{i + 1}. {f}" for i, f in enumerate(facts)) +
              '\nReply with JSON only: {"facts": [{"n": 1, "said": true, "at": 75, "by": "Name"}, ...]}')
    out = parse_json(call_model("You check transcripts carefully and literally.", prompt, calls, "client/surfaced",
                                cache_salt=profile["id"])) or {}
    res = []
    for i, f in enumerate(facts):
        r = next((x for x in out.get("facts") or [] if isinstance(x, dict) and x.get("n") == i + 1), {})
        res.append({"fact": f, "rumour": f == profile.get("rumour"), "holders": holders[f],
                    "said": bool(r.get("said")), "at": r.get("at"), "by": r.get("by")})
    return {"facts": res, "unique_said": sum(1 for r in res if r["said"] and not r["rumour"]),
            "unique_total": len(profile["unique"])}
