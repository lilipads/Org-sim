"""Blind judging: what does the picture show? (DESIGN.md §3.5)

Each judge sees only an image of the fallen dominoes, copied into an empty folder
as picture.png, so the file name and location give nothing away. Judges are not
told it's an animal.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor

from .agents.llm import CallLog, call_model, parse_json

JUDGE_SYSTEM = ("You look at simple line pictures and say what they show. Be direct. "
                "The picture is made of fallen dominoes seen from above.")
JUDGE_PROMPT = ("Use the Read tool to look at the image file picture.png in the current folder. "
                "What does the picture show? Give your top 3 guesses, a few words each, most likely first. Reply with JSON "
                "only: {\"guesses\": [\"...\", \"...\", \"...\"]}")
MATCH_SYSTEM = "You compare a team's intended subject with a judge's guesses. Be strict but fair."


def judge_once(png_path: str, log: CallLog | None, tag: str) -> list:
    d = tempfile.mkdtemp(prefix="judge_")
    try:
        shutil.copy(png_path, os.path.join(d, "picture.png"))
        text = call_model(JUDGE_SYSTEM, JUDGE_PROMPT, log, tag, tools="Read", cwd=d)
        out = parse_json(text) or {}
        g = out.get("guesses") or []
        return [str(x).strip().lower() for x in g][:3]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def matches(intent: str, guesses: list, log: CallLog | None) -> list:
    if not intent or not guesses:
        return [False] * len(guesses)
    prompt = (f"The team meant to draw: {intent!r}.\nThe judge's guesses, in order: {guesses}.\n"
              "For each guess, does it name the same animal? Count synonyms and closely specific names "
              "(e.g. 'kitten' or 'tabby' for 'cat'), but not vague ones like 'animal' or 'creature'. "
              "Reply with JSON only: {\"matches\": [true or false for each guess]}")
    d = parse_json(call_model(MATCH_SYSTEM, prompt, log, "match")) or {}
    m = d.get("matches") or []
    return [bool(x) for x in m][: len(guesses)] + [False] * max(0, len(guesses) - len(m))


def score(match_list: list) -> float:
    if not match_list:
        return 0.0
    return 1.0 if match_list[0] else (0.5 if any(match_list) else 0.0)


def judge_picture(png_path: str, intent: str, n_judges: int = 3, log: CallLog | None = None) -> dict:
    with ThreadPoolExecutor(n_judges) as ex:
        all_guesses = list(ex.map(lambda k: judge_once(png_path, log, f"judge{k + 1}"), range(n_judges)))
    results = []
    for g in all_guesses:
        m = matches(intent, g, log)
        results.append({"guesses": g, "matches": m, "score": score(m)})
    return {"intent": intent, "judges": results,
            "recognition": round(sum(r["score"] for r in results) / max(1, len(results)), 3)}
