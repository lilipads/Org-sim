"""AI agents for Domino Art, driven through Claude Code's non-interactive mode.

Each call is a fresh, stateless request with a small custom system prompt and no
tools. Memory lives in the agent's own notes, which the game passes back in every
turn. Every call is recorded (prompt sizes, tokens, time) so a run's usage can be
measured.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time

from ..game import Action, Agent

MODEL = os.environ.get("ORGSIM_MODEL", "haiku")
CALL_TIMEOUT = 180

RULES = """THE GAME: DOMINO ART
You are one of {n} people at a table. Together you build a picture of an ANIMAL out of dominoes.
Your team decides which animal and how to draw it. When time runs out, the team's start domino is
pushed. The picture is made of the dominoes that fall; dominoes still standing are invisible. A judge
who doesn't know your plan looks at the fallen dominoes and guesses what they show. Your team
succeeds if the judge recognizes your animal.

THE TABLE
- x runs from 0 (left) to {w} (right), y from 0 (top) to {h} (bottom). 1 unit = one domino's height.
- A domino falls in the direction it faces. Angles: 0 = right (+x), 90 = down (+y), 180 = left,
  270 = up.
- The map shows standing dominoes as arrows (rough direction), S = the start domino, x = knocked over,
  . = empty. The map is approximate (one character per unit). Inspect gives exact numbers.

HOW DOMINOES FALL
A falling domino knocks over another standing domino only if that domino is
  - 0.2 to 0.9 units ahead in the falling direction,
  - at most 0.35 units to the side of the falling line, and
  - facing within 40 degrees of the falling domino's direction.
So a line can curve gently (at most 40 degrees per domino), but a sharp corner, or a gap wider than
0.9, stops the chain. One domino can knock over two that stand side by side, so a line can split
into two, and two lines can meet. Spacing of about 0.5-0.6 is comfortable; spacing near the limits
saves dominoes but is riskier.
Nobody's hand is perfectly steady: each domino lands about 0.05 units and 3 degrees off from where
you aim. Working within about 6 units of another builder risks bumping the table, which knocks over a
run of dominoes that must then be stood back up. Some builders leave deliberate gaps so a bump only
knocks down one segment; every gap must be closed before the push.

SUPPLIES AND TIME
- {supply} dominoes for the whole table. Each person can place up to 8 dominoes per turn.
- {turns} turns of 2 minutes each. Everyone acts at the same time each turn.
- One start domino: put "start": true on a build and the first new domino becomes the start.
  Marking another later moves the start.

ACTIONS: pick exactly one per turn
- talk: say something. "to" is "everyone" or a list of names. Anyone you address is pulled into the
  conversation and spends their turn there instead of doing what they planned. Each conversation
  allows one round of replies. People not in it only notice that you were talking.
- listen: join the table-wide conversation without speaking.
- build: place up to 8 dominoes, described as strokes (below). "restand": [x0,y0,x1,y1] stands
  knocked-over dominoes in that area back up (this uses the same 8 hands).
- take_down: remove up to 12 dominoes in an area [x0,y0,x1,y1], whoever built them. They go back
  into the supply.
- inspect: look closely at an area [x0,y0,x1,y1]: exact positions and angles, plus every line end
  that won't knock anything over, and why.
- wait: do nothing.

STROKES (for build)
- {{"type":"domino","x":12.0,"y":8.5,"angle":90}}  one domino.
- {{"type":"line","x0":10,"y0":5,"x1":14,"y1":5,"spacing":0.55}}  dominoes from (x0,y0) toward
  (x1,y1), all facing along the line.
- {{"type":"arc","cx":20,"cy":20,"r":4,"a0":180,"a1":270,"spacing":0.55}}  dominoes around a circle
  with centre (cx,cy), from angle a0 to a1 (positions at cx+r*cos(a), cy+r*sin(a)), facing the
  direction of travel. If a1 > a0 the arc goes clockwise on the map; if a1 < a0, anticlockwise.
  Keep r at 1.5 or more so the turn per domino stays well under 40 degrees.
Anything beyond your 8 dominoes is cut off; continue next turn from where it stopped.
Your result message lists the exact position and angle of every domino you placed.
"""

REPLY_FORMAT = """Reply with a single JSON object and nothing else:
{"message": "what you say, or an empty string to stay quiet", "notes": "your updated private notes"}"""

DECIDE_FORMAT = """Reply with a single JSON object and nothing else:
{
  "thinking": "one or two short sentences: why this action",
  "action": "talk | listen | build | take_down | inspect | wait",
  "to": "everyone" or ["Name", ...],          (talk)
  "message": "...",                           (talk)
  "strokes": [ ... ], "start": false,         (build)
  "restand": [x0, y0, x1, y1],                (build, optional)
  "area": [x0, y0, x1, y1],                   (take_down, inspect)
  "notes": "your private notes for later turns: they replace your old notes. Keep the plan, your
            part, coordinates you need, and what to do next."
}"""


PERSONAS = {
    "Ava": "You like to get your hands dirty and start building early.",
    "Ben": "You have strong opinions about design and want the picture to look right.",
    "Chloe": "You tend to step back and look at the whole picture and how the parts fit together.",
    "Dev": "You're careful and like to double-check work before calling it done.",
    "Elena": "You like organizing people and making sure everyone has a clear job.",
    "Farid": "You're quiet and prefer to follow a clear plan rather than debate it.",
    "Grace": "You love bold ideas and trying things nobody else would.",
    "Hiro": "You like helping whoever seems stuck.",
    "Isla": "You care more about finishing on time than about perfection.",
    "Jonah": "You question plans and point out what could go wrong.",
}
# A balanced table of 4: a builder, a designer, a big-picture person, a checker.
TABLE_OF_4 = ["Ava", "Ben", "Chloe", "Dev"]

NO_EVALUATION = "No one is evaluating you individually. Just do your best."


class CallLog:
    """Thread-safe record of every model call in a run."""

    def __init__(self, path: str | None = None):
        self.path, self.lock, self.calls = path, threading.Lock(), []

    def add(self, rec: dict):
        with self.lock:
            self.calls.append(rec)
            if self.path:
                with open(self.path, "a") as f:
                    f.write(json.dumps(rec) + "\n")

    def totals(self) -> dict:
        t = {"calls": len(self.calls), "failed": sum(1 for c in self.calls if not c.get("ok")),
             "input_tokens": 0, "cache_creation_tokens": 0, "cache_read_tokens": 0, "output_tokens": 0,
             "seconds": 0.0, "api_equivalent_usd": 0.0}
        for c in self.calls:
            u = c.get("usage") or {}
            t["input_tokens"] += u.get("input_tokens", 0)
            t["cache_creation_tokens"] += u.get("cache_creation_input_tokens", 0)
            t["cache_read_tokens"] += u.get("cache_read_input_tokens", 0)
            t["output_tokens"] += u.get("output_tokens", 0)
            t["seconds"] += c.get("seconds", 0.0)
            t["api_equivalent_usd"] += c.get("cost_usd") or 0.0
        t["api_equivalent_usd"] = round(t["api_equivalent_usd"], 4)
        t["seconds"] = round(t["seconds"], 1)
        return t


def call_model(system: str, prompt: str, log: CallLog | None = None, tag: str = "",
               model: str = MODEL, tools: str = "", cwd: str | None = None,
               image: str | list | None = None) -> str:
    """One stateless call through Claude Code's non-interactive mode. Returns the text.
    With `image` (a PNG path, or a list of them), the pictures are attached to the message."""
    cmd = ["claude", "-p", "--model", model, "--system-prompt", system,
           "--tools", tools, "--no-session-persistence", "--strict-mcp-config", "--setting-sources", ""]
    if image:
        import base64
        content = []
        for path in ([image] if isinstance(image, str) else image):
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}})
        content.append({"type": "text", "text": prompt})
        stdin = json.dumps({"type": "user", "message": {"role": "user", "content": content}}) + "\n"
        cmd += ["--input-format", "stream-json", "--output-format", "stream-json", "--verbose"]
    else:
        stdin = prompt
        cmd += ["--output-format", "json"]
    t0 = time.time()
    rec = {"tag": tag, "model": model, "system_chars": len(system), "prompt_chars": len(prompt),
           "image": bool(image)}
    try:
        p = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=CALL_TIMEOUT, cwd=cwd)
        out = {}
        if image:
            for line in p.stdout.splitlines():
                line = line.strip()
                if line.startswith("{"):
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if ev.get("type") == "result":
                        out = ev
        elif p.stdout.strip().startswith("{"):
            out = json.loads(p.stdout)
        text = out.get("result", "") or ""
        rec.update(ok=bool(text) and not out.get("is_error"), usage=out.get("usage"),
                   cost_usd=out.get("total_cost_usd"), seconds=round(time.time() - t0, 2),
                   result=text[:4000], stderr=p.stderr[-500:] if p.returncode else "")
        return text
    except Exception as e:
        rec.update(ok=False, error=str(e), seconds=round(time.time() - t0, 2))
        return ""
    finally:
        if log:
            log.add(rec)


def parse_json(text: str) -> dict | None:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def fmt_conversations(convos: list) -> str:
    if not convos:
        return "(none)"
    out = []
    for c in convos:
        out.append(f"Conversation with {', '.join(c['with'])}:")
        for m in c["messages"]:
            to = m["to"]
            to = "everyone" if to in ("everyone", None) else ("the group" if to == "group" else ", ".join(to) if isinstance(to, list) else to)
            out.append(f"  {m['speaker']} (to {to}): {m['message']}")
    return "\n".join(out)


class LLMAgent(Agent):
    def __init__(self, name: str, home: str, persona: str, rules: str, evaluation: str,
                 log: CallLog, model: str = MODEL):
        super().__init__(name, home, persona)
        self.model, self.log = model, log
        self.system = (f"You are {name}.\n{persona}\n\n{rules}\n\nEVALUATION\n{evaluation}\n\n"
                       "Stay in character as a person at this table. Be concise.")
        self.failures = 0

    def _situation(self, obs: dict) -> str:
        sup = ", ".join(f"{k}: {v}" for k, v in obs["supply"].items())
        return "\n".join([
            f"Turn {obs['turn']} of {obs['turns_total']} ({obs['minutes_left']} minutes left including this turn).",
            f"You are at {obs['location']} with: {', '.join(obs['people_here']) or 'nobody'}.",
            f"Dominoes left in the supply: {sup}.",
            "",
            "THE TABLE NOW:",
            obs["map"],
            "",
            "WHAT YOU HEARD LAST TURN:",
            fmt_conversations(obs["heard"]),
            "",
            "WHAT YOU NOTICED:",
            "\n".join(obs["notices"]) or "(nothing)",
            "",
            "RESULT OF YOUR LAST ACTION:",
            obs["last_result"] or "(this is the first turn)",
            "",
            "YOUR PRIVATE NOTES:",
            obs["notes"] or "(empty)",
        ])

    def decide(self, obs: dict) -> Action:
        prompt = self._situation(obs) + "\n\nWhat do you do this turn?\n" + DECIDE_FORMAT
        for attempt in range(2):
            text = call_model(self.system, prompt, self.log, f"{self.name}/t{obs['turn']}/decide", self.model)
            d = parse_json(text)
            if d and d.get("action") in ("talk", "listen", "build", "take_down", "inspect", "wait", "visit"):
                return self._to_action(d)
            prompt += "\n\n(Your last reply was not a valid JSON object with an allowed action. Reply with JSON only.)"
        self.failures += 1
        return Action("wait", message="")

    def _to_action(self, d: dict) -> Action:
        kind = d.get("action")
        to = d.get("to", "everyone")
        if isinstance(to, str) and to.lower() in ("everyone", "all", "table"):
            to = "everyone"
        strokes = d.get("strokes") or []
        if isinstance(strokes, dict):
            strokes = [strokes]
        act = Action(kind=kind, to=to, message=str(d.get("message") or ""),
                     strokes=[s for s in strokes if isinstance(s, dict)],
                     restand=d.get("restand") if isinstance(d.get("restand"), list) else None,
                     start=bool(d.get("start")),
                     area=d.get("area") if isinstance(d.get("area"), list) else None,
                     where=d.get("where"), at=d.get("at"),
                     notes=d.get("notes") if isinstance(d.get("notes"), str) else None)
        act.thinking = str(d.get("thinking") or "")[:600]
        return act

    def reply(self, obs: dict, transcript: list) -> dict | None:
        convo = fmt_conversations([{"with": [], "messages": transcript}]).split("\n", 1)[-1]
        prompt = (self._situation(obs) + "\n\nYOU ARE IN A CONVERSATION RIGHT NOW (it uses your turn). "
                  "So far:\n" + convo + "\n\nYou may reply once.\n" + REPLY_FORMAT)
        text = call_model(self.system, prompt, self.log, f"{self.name}/t{obs['turn']}/reply", self.model)
        d = parse_json(text)
        if not d:
            return None
        return {"message": str(d.get("message") or ""),
                "notes": d.get("notes") if isinstance(d.get("notes"), str) else None}

    def state_intent(self, obs: dict) -> str:
        prompt = (self._situation(obs) + "\n\nTime is up. In one or two words: which animal is your "
                  "team's picture meant to be? Reply with JSON only: {\"animal\": \"...\"}")
        d = parse_json(call_model(self.system, prompt, self.log, f"{self.name}/intent", self.model)) or {}
        return str(d.get("animal") or "").strip().lower()
