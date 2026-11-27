"""Role checks for the Eng / Design / PM study (DESIGN_REVIEW_STUDY.md), and the art panel.

* dry_run (Eng): four scripted builders trace the sketch with ordinary hands; report which strokes
  would fall, which wouldn't, and where the run stops.
* squint (Design): a perfect rendering of the sketch, read by one blind judge: what it looks like, and
  how good it looks (1-10).
* ask_client (PM): the client, who knows their own full brief, reacts to the sketch or a question.
* aesthetics_panel: 3 art judges rate the fallen picture 1-10 (part of the final score).

Model calls are cached like everything else.
"""
from __future__ import annotations

import math
import os
import random
import shutil
import tempfile

from .agents.llm import CallLog, call_model, parse_json
from .dominoes import Domino, Physics
from .game import table_world
from .render import picture_png, sketch_points

# ---- dry run (Eng) ----------------------------------------------------------


def _strokes_of(strokes: list) -> list:
    return [s for s in strokes if s.get("type") != "label"]


def dry_run(strokes: list, seeds: int = 2) -> dict:
    """Simulate four ordinary builders tracing every stroke. Returns per-stroke fall shares."""
    from .live import Decision, LiveAgentBase, LiveConfig, LiveGame

    class _Tracer(LiveAgentBase):
        def __init__(self, name, jobs, sketcher):
            super().__init__(name, "table")
            self.jobs, self.sketcher, self.k = list(jobs), sketcher, 0

        def act(self, obs):
            self.k += 1
            if self.sketcher and self.k == 1:
                return Decision(pad="take", eagerness=9)
            if self.sketcher and self.k == 2:
                return Decision(sketch=strokes, pad="put_down")
            if "nothing" in obs["pad_status"].lower():
                return Decision()
            if "waiting for the run" in obs["task"] and self.jobs:
                waiting = int(obs["task"].split("start of stroke ")[1].split(")")[0])
                j = self.jobs.pop(0)
                self.jobs.append(waiting)
                return Decision(do="build", strokes=[{"type": "trace", "stroke": j}])
            if obs["task"].startswith("Building"):
                return Decision(do="continue")
            if self.jobs:
                return Decision(do="build", strokes=[{"type": "trace", "stroke": self.jobs.pop(0)}])
            return Decision()

    n_strokes = len(strokes)
    per_stroke = {k: [] for k in range(1, n_strokes + 1)}
    totals = []
    for seed in range(seeds):
        rng = random.Random(seed)
        order = [k for k in range(1, n_strokes + 1) if strokes[k - 1].get("type") != "label"]
        rng.shuffle(order)
        names = ["A", "B", "C", "D"]
        agents = [_Tracer(n, order[i::4], i == 0) for i, n in enumerate(names)]
        w = table_world("table", 30, 20, 400, Physics(pos_sigma=0.025, bump_radius=3.0, bump_chance=0.0))
        cfg = LiveConfig(duration=600, seed=seed, seconds_per_domino=3.0, freehand_sigma=0.15,
                         scratchpad_until=600, announce_at=(), idle_quiet=15, max_quiet=15)
        g = LiveGame(w, agents, cfg)
        g.run()
        pw = g.pushed_world
        fell_ids = {i for i, d in pw.dominoes.items() if d.state == "down"}
        laid = 0
        for k, ids in g.traced.items():
            ids = [i for i in ids if i in pw.dominoes]
            laid += len(ids)
            if ids:
                per_stroke[k].append(sum(1 for i in ids if i in fell_ids) / len(ids))
        totals.append(len(fell_ids))
    shares = {k: (round(sum(v) / len(v), 2) if v else 0.0) for k, v in per_stroke.items()
              if strokes[k - 1].get("type") != "label"}
    return {"per_stroke": shares, "fell": round(sum(totals) / max(1, len(totals)))}


def dry_run_text(strokes: list) -> str:
    if not _strokes_of(strokes):
        return "There's nothing on the pad to run through yet."
    r = dry_run(strokes)
    falls = [k for k, s in r["per_stroke"].items() if s >= 0.8]
    partly = [k for k, s in r["per_stroke"].items() if 0.2 <= s < 0.8]
    never = [k for k, s in r["per_stroke"].items() if s < 0.2]
    out = [f"You play the fall through the sketch in your head (about {r['fell']} dominoes would go down)."]
    if falls:
        out.append("These strokes would fall: " + ", ".join(map(str, falls)) + ".")
    if partly:
        out.append("These would only partly fall (the run breaks along them): " + ", ".join(map(str, partly)) + ".")
    if never:
        why = []
        for k in never:
            s = strokes[k - 1]
            if s.get("type") in ("circle",) or len(sketch_points(s)) < 2:
                why.append(f"{k} (a separate shape: nothing runs into it)")
            else:
                why.append(f"{k} (the run never gets into it: it doesn't start on a line that falls, "
                           "or it leaves that line too sharply)")
        out.append("These would never fall: " + "; ".join(why) + ".")
    if not never and not partly:
        out.append("It looks sound end to end.")
    return " ".join(out)


# ---- rendering a sketch -----------------------------------------------------

def ideal_png(strokes: list, path: str, size=(30, 20)) -> str:
    """The sketch as a perfect domino picture with everything fallen (what judges would see)."""
    w = table_world("table", size[0], size[1], 10000)
    k = 0
    for s in _strokes_of(strokes):
        pts = sketch_points(s)
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            seg = math.dist(pts[i], pts[i + 1])
            ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
            for t in range(max(1, int(seg / 0.5))):
                f = t * 0.5 / seg if seg else 0
                k += 1
                d = Domino(k, x0 + f * (x1 - x0), y0 + f * (y1 - y0), ang, "ideal", 0, "table")
                d.state = "down"
                w.dominoes[k] = d
    picture_png(w, path, scale=28)
    return path


def _with_picture(png: str, fn):
    d = tempfile.mkdtemp(prefix="look_")
    try:
        shutil.copy(png, os.path.join(d, "picture.png"))
        return fn(d)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _digest(png: str) -> str:
    import hashlib
    with open(png, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---- aesthetics -------------------------------------------------------------

ART_SYSTEM = ("You are an art judge. You rate simple line pictures for how beautiful and well drawn they are, "
              "the way an illustrator would. Be honest and use the whole scale.")
ART_PROMPT = ("Use the Read tool to look at the image file picture.png in the current folder. It is a line "
              "picture made of fallen dominoes, seen from above. Ignore what it's made of. How beautiful and well "
              "drawn is it as a picture? 1 = a clumsy scribble, 5 = ordinary, 10 = elegant, like a skilled "
              "illustrator's: flowing lines, good proportions, balance, clear and uncluttered. "
              'Reply with JSON only: {"score": 1-10, "why": "one short sentence"}')


def rate_beauty(png: str, log: CallLog | None, tag: str) -> dict:
    dig = _digest(png)

    def go(d):
        return call_model(ART_SYSTEM, ART_PROMPT, log, tag, tools="Read", cwd=d, cache_salt=tag, cache_extra=dig)
    out = parse_json(_with_picture(png, go)) or {}
    try:
        sc = max(1.0, min(10.0, float(out.get("score"))))
    except (TypeError, ValueError):
        sc = 5.0
    return {"score": sc, "why": str(out.get("why") or "")}


def aesthetics_panel(png: str, log: CallLog | None, n: int = 3) -> dict:
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(n) as ex:
        rs = list(ex.map(lambda k: rate_beauty(png, log, f"art{k + 1}"), range(n)))
    return {"ratings": rs, "aesthetics": round(sum(r["score"] for r in rs) / len(rs) / 10, 3)}


# ---- squint test (Design) ---------------------------------------------------

def squint_text(strokes: list, log: CallLog | None, salt: str) -> str:
    if not _strokes_of(strokes):
        return "There's nothing on the pad to look at yet."
    from .judge import judge_once
    d = tempfile.mkdtemp(prefix="squint_")
    try:
        png = ideal_png(strokes, os.path.join(d, "s.png"))
        guesses = judge_once(png, log, f"squint/{salt}")
        beauty = rate_beauty(png, log, f"squint-art/{salt}")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    reads = ", then ".join(guesses[:2]) if guesses else "nothing clear"
    return (f"You squint at the sketch the way a stranger would see it built. It reads as: {reads}. "
            f"As a picture it's about a {beauty['score']:.0f}/10: {beauty['why']}")


# ---- the client (PM) --------------------------------------------------------

def client_text(profile: dict, strokes: list, question: str, log: CallLog | None, salt: str, model: str | None) -> str:
    """The client looks at the current sketch (if any) and answers the PM."""
    guide = ", ".join(f"{k} {v}" for k, v in sorted(profile["guide"].items(), key=lambda kv: -kv[1]))
    system = ("You are the client in a role-play. " + profile["commission"] + " What you really want, which you "
              "know but never list outright: " + " ".join(profile["shared"] + profile["unique"]) +
              f" How you feel about animals, 0-1: {guide}. React briefly (two or three sentences), honestly and in "
              "character, the way a real client talks: say what you like and what bothers you. Don't design it "
              "for them and don't mention scores.")
    prompt = f"The team's PM asks: {question or 'What do you think of this?'}"
    img = None
    d = None
    if _strokes_of(strokes):
        d = tempfile.mkdtemp(prefix="client_")
        img = ideal_png(strokes, os.path.join(d, "sketch.png"))
        prompt += "\n(The attached picture is their current sketch.)"
    try:
        kw = {"model": model} if model else {}
        out = call_model(system, prompt, log, "client/ask", image=img, cache_salt=salt, **kw)
    finally:
        if d:
            shutil.rmtree(d, ignore_errors=True)
    return "The client says: " + (out.strip() or "(no answer)")
