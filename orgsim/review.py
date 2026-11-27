"""Performance reviews (PERF_REVIEW_STUDY.md): what players are told, working styles, the manager
(partial attention, private messages, notes, final ratings), self-assessments and peer ratings."""
from __future__ import annotations

import json
import os
import random
import tempfile

from .agents.llm import CallLog, call_model, parse_json

CAREER = " Your rating decides your promotion and bonus this cycle. You care about your career."

EVALUATIONS = {
    "none": "No one is evaluating you individually. Just do your best.",
    "individual": ("You're rated individually on how many of the dominoes you placed fall in the final picture."
                   + CAREER),
    "team": ("Everyone at your table receives the same rating: the team's score, which is whether the judges "
             "recognise the animal, times the share of the dominoes that fall." + CAREER),
    "manager": ("A manager rates each of you 1-5 on impact, execution, collaboration and leadership. The manager "
                "is at your table some of the time, and you can talk to them privately. At the end you'll write a "
                "self-assessment for them." + CAREER),
    "peer": ("Each of your teammates rates you 1-5 on impact, execution, collaboration and leadership, and your "
             "rating is the average." + CAREER),
    "forced": ("A manager rates each of you 1-5 on impact, execution, collaboration and leadership. The manager is "
               "at your table some of the time, and you can talk to them privately. At the end you'll write a "
               "self-assessment for them. Ratings follow a fixed curve: at your table, one person gets the top "
               "rating, two the middle, one the bottom." + CAREER),
}
HAS_MANAGER = ("manager", "forced")

# the one-line reminder shown with every decision (people keep their review in mind)
REMINDERS = {
    "none": "",
    "individual": "by how many of the dominoes you placed fall in the final picture (it decides your promotion and bonus).",
    "team": "everyone gets the team's score (it decides your promotion and bonus).",
    "manager": "your manager's 1-5 rating on impact, execution, collaboration and leadership (it decides your promotion and bonus).",
    "peer": "your teammates' 1-5 ratings on impact, execution, collaboration and leadership (they decide your promotion and bonus).",
    "forced": "your manager's rating on a fixed curve: one person top, two middle, one bottom (it decides your promotion and bonus).",
}

STYLES = {
    "organiser": "You naturally take charge: you like to set the plan and keep everyone coordinated.",
    "builder": "You like to pick a piece of work and get it done, quietly and well.",
    "checker": "You like to check work carefully and put right whatever's wrong, wherever it is.",
    "connector": "You keep everyone informed and energised, and you like being where the action is.",
}


def assign_styles(names: list, seed: int) -> dict:
    order = list(STYLES)
    k = seed % len(order)
    order = order[k:] + order[:k]
    return {n: order[i % len(order)] for i, n in enumerate(names)}


def manager_schedule(seed: int, duration: float = 600.0, beat: float = 15.0, share: float = 1 / 3) -> list:
    """Visits of 30-60 s at beat boundaries, covering about `share` of the game, never overlapping."""
    rng = random.Random(f"manager/{seed}")
    slots = int(duration // beat)
    busy = [False] * slots
    target = int(round(slots * share))
    visits = []
    tries = 0
    while sum(busy) < target and tries < 500:
        tries += 1
        length = rng.choice([2, 3, 4])                 # 30, 45 or 60 seconds
        start = rng.randrange(0, slots - length + 1)
        if any(busy[max(0, start - 1): start + length + 1]):   # keep a gap between visits
            continue
        for i in range(start, start + length):
            busy[i] = True
        visits.append([start * beat, (start + length) * beat])
    return sorted(visits)


# ---- the manager --------------------------------------------------------------

MANAGER_SYSTEM = ("You are the manager of a team of four at an offsite team activity: in 10 minutes they build a "
                  "picture of an animal out of dominoes, which is then pushed over and judged. You're responsible "
                  "for rating each person 1-5 on impact, execution, collaboration and leadership. You can't be at "
                  "their table all the time; you see and hear only what happens while you're there, plus anything "
                  "people tell you privately. You don't know who placed which domino. Be fair, and form your own "
                  "view.")


class Manager:
    def __init__(self, names: list, schedule: list, log: CallLog | None, model: str | None, salt: str,
                 forced: bool = False):
        self.names, self.schedule, self.log, self.model, self.salt = names, schedule, log, model, salt
        self.forced = forced
        self.notes = ""
        self.visit: list = []          # lines seen in the current visit
        self.queued: list = []         # private messages sent while away
        self.visits_done = 0
        self.present_prev = False
        self.history: list = []        # [{t, notes}] for the log

    def _kw(self):
        return {"model": self.model} if self.model else {}

    def observe(self, game, rec: dict):
        """Call after every beat with the beat's log record."""
        t = rec["time"]
        present = game.manager_present(t)
        if present:
            if not self.present_prev and self.queued:
                self.visit += [f"(waiting for you when you got back) {q}" for q in self.queued]
                self.queued = []
            for c in rec.get("conversations", []):
                for m in c.get("messages", []):
                    to = m["to"] if isinstance(m["to"], str) else ", ".join(m["to"])
                    self.visit.append(f"[{rec['clock']}] {m['speaker']} (to {to}): {m['message']}")
        for e in rec.get("events", []):
            if e.get("type") == "to_manager":
                line = f"[{rec['clock']}] {e['who']} told you privately: {e['text']}"
                (self.visit if present else self.queued).append(line)
        if self.present_prev and not present:
            self._end_visit(game, rec["clock"])
        self.present_prev = present

    def _end_visit(self, game, clock: str):
        self.visits_done += 1
        img = None
        d = tempfile.mkdtemp(prefix="mgr_")
        try:
            from .render import agent_view_png
            hands = {}
            for o, tk in game.task.items():
                if tk and tk.get("kind") == "build" and (tk.get("last") or tk.get("aim")):
                    hands[o] = tk.get("last") or tk.get("aim")
            loc = game.world.regions["table"]
            img = os.path.join(d, "table.png")
            agent_view_png(game.world, loc, img, {}, hands, show_reach=True)
        except Exception:
            img = None
        seen = "\n".join(self.visit) or "(nobody said anything while you were there)"
        prompt = (f"You've just left the team's table at {clock} (visit {self.visits_done}).\n"
                  f"YOUR NOTES SO FAR:\n{self.notes or '(none yet)'}\n\n"
                  f"WHAT YOU SAW AND HEARD ON THIS VISIT:\n{seen}\n\n"
                  "The attached picture is the table as you left it: dark dominoes are connected to the start, pale "
                  "ones aren't; labels show where people's hands were. Update your notes on each person "
                  f"({', '.join(self.names)}): what they did, how it went, anything you want to remember for the "
                  'review. Reply with JSON only: {"notes": "your updated notes, under 250 words"}')
        out = parse_json(call_model(MANAGER_SYSTEM, prompt, self.log, f"manager/visit{self.visits_done}",
                                    image=img, cache_salt=self.salt, **self._kw())) or {}
        if out.get("notes"):
            self.notes = str(out["notes"])[:3000]
        self.history.append({"clock": clock, "seen": list(self.visit), "notes": self.notes})
        self.visit = []
        try:
            import shutil
            shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass

    def finish(self, game, self_assessments: dict) -> dict:
        if self.present_prev or self.visit:
            self._end_visit(game, "10:00")
        if self.queued:
            self.notes += "\n(Private messages that arrived after your last visit:)\n" + "\n".join(self.queued)
        sa = "\n\n".join(f"--- {n} ---\n{t}" for n, t in self_assessments.items())
        curve = ("\nYou must follow the curve: exactly one person gets 5, two people get 3, one person gets 1."
                 if self.forced else "")
        prompt = (f"The activity is over. YOUR NOTES:\n{self.notes or '(none)'}\n\n"
                  f"THEIR SELF-ASSESSMENTS:\n{sa}\n\n"
                  "Rate each person 1-5 on their overall performance (impact, execution, collaboration, "
                  f"leadership), with a two-sentence justification.{curve}\n"
                  'Reply with JSON only: {"ratings": {"Name": {"rating": 1-5, "why": "..."}, ...}}')
        out = parse_json(call_model(MANAGER_SYSTEM, prompt, self.log, "manager/final", cache_salt=self.salt,
                                    **self._kw())) or {}
        ratings = {}
        for n in self.names:
            r = (out.get("ratings") or {}).get(n) or {}
            try:
                v = int(round(float(r.get("rating"))))
            except (TypeError, ValueError):
                v = None
            ratings[n] = {"rating": v, "why": str(r.get("why") or "")}
        if self.forced:
            ratings = _fit_curve(ratings)
        return ratings


def _fit_curve(ratings: dict) -> dict:
    """If the manager didn't follow the 5/3/3/1 curve, keep their order and impose it."""
    vals = sorted(v["rating"] for v in ratings.values() if v["rating"] is not None)
    if vals == [1, 3, 3, 5] and len(ratings) == 4:
        return ratings
    order = sorted(ratings, key=lambda n: -(ratings[n]["rating"] or 0))
    curve = [5] + [3] * (len(order) - 2) + [1] if len(order) >= 2 else [3]
    for n, v in zip(order, curve):
        ratings[n] = dict(ratings[n], rating=v, curve_imposed=True)
    return ratings


# ---- self-assessments and peer ratings ------------------------------------------

def self_assessment(agent, obs: dict, full_conversation: list) -> str:
    o = dict(obs, conversation=full_conversation)
    prompt = (agent.situation(o) + "\n\nTime is up and the picture has been pushed. Write your self-assessment for "
              "your manager, about 200-300 words, under four headings: Impact, Execution, Collaboration, "
              "Leadership. Write it in your own voice. Reply with JSON only: {\"self_assessment\": \"...\"}")
    d = parse_json(call_model(agent.system, prompt, agent.log, f"{agent.name}/self_assessment", agent.model,
                              image=agent._image(obs), cache_salt=agent.cache_salt)) or {}
    return str(d.get("self_assessment") or "").strip()


def peer_ratings(agent, obs: dict, full_conversation: list, others: list) -> dict:
    o = dict(obs, conversation=full_conversation)
    prompt = (agent.situation(o) + f"\n\nTime is up and the picture has been pushed. Rate each of your teammates "
              f"({', '.join(others)}) 1-5 on their overall performance (impact, execution, collaboration, "
              "leadership), with one sentence each. Your ratings decide their promotion and bonus. Reply with JSON "
              'only: {"ratings": {"Name": {"rating": 1-5, "why": "..."}, ...}}')
    d = parse_json(call_model(agent.system, prompt, agent.log, f"{agent.name}/peer_ratings", agent.model,
                              image=agent._image(obs), cache_salt=agent.cache_salt)) or {}
    out = {}
    for n in others:
        r = (d.get("ratings") or {}).get(n) or {}
        try:
            v = int(round(float(r.get("rating"))))
        except (TypeError, ValueError):
            v = None
        out[n] = {"rating": v, "why": str(r.get("why") or "")}
    return out


def save(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
