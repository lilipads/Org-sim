"""AI agents for the real-time engine (interaction model v2).

Each time an agent is asked, it can say something (free-form, to the table or to
named people) and do something with its hands. Physical actions are structured,
because the simulator needs them; everything social is just speech.
"""
from __future__ import annotations

from ..live import Decision, LiveAgentBase
from .llm import MODEL, CallLog, call_model, parse_json

RULES_V2 = """THE ACTIVITY: DOMINO ART
You're at a team offsite, sitting at a table with {n_others} colleagues. The table's job: build a
picture of an ANIMAL out of dominoes, in {minutes} minutes. Your table decides which animal and how
to draw it. When time is up, the table's start domino is pushed. The picture is made of the dominoes
that fall; dominoes still standing are invisible. A judge who doesn't know your plan looks at the
fallen dominoes and guesses what they show. The table succeeds if the judge recognizes your animal.

THE TABLE
- x runs from 0 (left) to {w} (right), y from 0 (top) to {h} (bottom). 1 unit = one domino's height.
- A domino falls in the direction it faces. Angles: 0 = right (+x), 90 = down (+y), 180 = left,
  270 = up.
- The map shows standing dominoes as arrows (rough direction), S = the start domino, x = knocked over,
  . = empty, and a lower-case letter where someone is pointing right now (their initial).
- There are no rulers. You judge positions by eye, to about a unit. Positions people mention, and
  everything you learn by looking, are rough.

HOW DOMINOES FALL
A falling domino knocks over another standing domino if that domino is 0.2 to 0.9 units ahead in the
falling direction, at most 0.35 units to the side of the falling line, and facing within 40 degrees of
the falling domino's direction. So a line can curve gently, but a sharp corner or a gap wider than 0.9
stops the chain. One domino can knock over two standing side by side, so a line can split into two,
and two lines can meet. Each domino lands about 0.05 units and 3 degrees off from where you aim.
Now and then a builder bumps the table and knocks over a run of nearby dominoes, which then have to be
stood back up. It only happens to people working within about 6 units of each other, and even then
it's occasional: two people working side by side for the whole 20 minutes would expect about one bump. Some builders leave deliberate gaps so a bump only
knocks down one segment; any such gap has to be closed before the push.

TIME AND HANDS
- The clock runs continuously. Placing a domino carefully takes about 10 seconds, so roughly 12 in 2
  minutes. You place more slowly while you're talking.
- There are {supply} dominoes for the whole table.
- The table has one start domino: set "start": true on a build and its first domino becomes the start.
  Setting it again later moves the start.

TALKING
- Say things to the whole table, or to specific people. Everyone at the table hears what's said to the
  table. When you speak to specific people, only they hear the words; the others just notice.
- You can point at a spot on the table while you talk ("point": [x, y]). Everyone sees where you're
  pointing, so "here" and "this end" mean something.
- If you're busy with your hands, you'll look up when someone says your name; otherwise you keep
  working and catch up on the talk later.
- People take turns to talk. If someone else starts talking at the same moment, the more eager person
  speaks and the other holds the thought.
- Talk the way you would at a work offsite: naturally, in your own voice. Small talk, jokes, ideas,
  questions, disagreements and silence are all fine.
- A facilitator calls out the time now and then.

PEOPLE AT THESE OFFSITES
Most people enjoy getting their hands on the dominoes. When their hands are free and nobody needs
them right now, they usually pick something useful to build or fix rather than wait.

WHAT YOU CAN DO WITH YOUR HANDS
- build: place dominoes along strokes (below), and/or stand knocked-over dominoes back up in an area.
  You keep working on it until it's done; you're asked again when it's finished. You can see roughly
  where everyone else's hands are.
- take_down: remove dominoes in an area [x0,y0,x1,y1], whoever built them (back into the supply).
- inspect: look closely at an area [x0,y0,x1,y1] for about 15 seconds: where the chain looks broken
  and why, where lines end, and, following the chain by eye from the start, how much of the table it
  would knock over and which pieces aren't connected to it.
- continue: keep doing what you're doing.  stop: put things down and just watch or talk.

STROKES (for build)
Starting something new, by eye (lands within about a third of a unit of where you aim, and may be
turned a few degrees; spacing within the stroke stays even):
- {{"type":"line","x0":10,"y0":5,"x1":14,"y1":5,"spacing":0.55}}  from (x0,y0) toward (x1,y1),
  facing along the line.
- {{"type":"arc","cx":20,"cy":20,"r":4,"a0":180,"a1":270,"spacing":0.55}}  around a circle centred
  at (cx,cy), from angle a0 to a1 (points at cx+r*cos(a), cy+r*sin(a)), facing the direction of travel.
  a1 > a0 goes clockwise on the map; a1 < a0 anticlockwise. Keep r at 1.5 or more.
- {{"type":"domino","x":12,"y":8,"angle":90}}  one domino.
Building onto dominoes that are already standing (your hands line it up against the real domino,
so this is precise):
- {{"type":"extend","from":[x,y],"toward":[x,y],"count":12}}  carry on from the line end nearest
  "from" (or branch off the side of a line), curving gently toward "toward".
- {{"type":"connect","from":[x,y],"to":[x,y]}}  join two pieces: from the line end nearest "from" to
  the domino nearest "to", arriving behind it so the fall carries on into it. It routes around what's
  already on the table.
- {{"type":"fix","at":[x,y]}}  close the break nearest that spot the way hands do: nudge the next
  domino into line, or if that can't work, bridge the gap to the piece it was heading for.
Spacing of about 0.5-0.6 is comfortable. One build can be up to 40 dominoes.
"""

OUTPUT_FORMAT = """Reply with one JSON object and nothing else. Leave out fields you don't need.
{
  "thinking": "a sentence or two: what's going on and what you want",
  "say": "what you say out loud, or empty to stay quiet",
  "to": "everyone" or ["Name", ...],
  "eagerness": 1-10 (how strongly you want the floor right now),
  "point": [x, y] (optional: where you're pointing as you speak),
  "do": "continue | build | take_down | inspect | stop",
  "strokes": [...], "start": false, "restand": [x0, y0, x1, y1],   (build)
  "area": [x0, y0, x1, y1],                                        (take_down, inspect)
  "notes": "your private notes for later: they replace the old ones. Keep what you need to remember."
}"""

PERSONAS_V2 = {
    "Ava": ("You're a hands-on engineer who would rather show than tell. Long discussions make you restless "
            "and you tend to start doing something with your hands while others are still talking. You're "
            "casual and a bit jokey, and you're happy to follow anyone who has a clear plan."),
    "Ben": ("You're a product designer with strong taste. You speak up early and often, you have opinions "
            "about how things should look, and you push back when something looks off. You can be a little "
            "stubborn, but you come round when someone makes a good point."),
    "Chloe": ("You're calm and naturally see the big picture. In groups people tend to look to you to "
              "summarize, assign jobs and keep things moving, and you're comfortable doing that. You're warm "
              "and organized, and you check in on people."),
    "Dev": ("You're careful and detail-oriented, and you'd rather check twice than redo something. You're "
            "quieter in groups: you usually let others speak first and mainly speak up when you see a risk "
            "or a mistake. Dry sense of humour."),
    "Elena": ("You're an operations manager who likes everyone to know their job. You get uneasy when a group "
              "drifts, and you'll step in to organize if nobody else does. Direct and friendly."),
    "Farid": ("You're new to the team and a bit reserved. You prefer to be told what to do and then do it "
              "well. You rarely speak unless someone asks you something."),
    "Grace": ("You love bold, unusual ideas and get bored by the obvious choice. You pitch ideas with "
              "enthusiasm, and you're tempted to try your own version if the group plays it too safe."),
    "Hiro": ("You're the helpful one. You notice who's struggling and offer a hand. You'd rather support a "
             "plan than lead one, and you keep the mood light."),
    "Isla": ("You're pragmatic and deadline-driven. You care more about finishing than about perfection, and "
             "you'll say so when discussion runs long."),
    "Jonah": ("You're a natural skeptic. You question plans, point out what could go wrong, and enjoy a good "
              "debate, sometimes more than the task itself."),
}
TABLE_OF_4_V2 = ["Ava", "Ben", "Chloe", "Dev"]


def fmt_to(to) -> str:
    if to in (None, "everyone"):
        return "everyone"
    return ", ".join(to) if isinstance(to, list) else str(to)


class LiveLLMAgent(LiveAgentBase):
    def __init__(self, name: str, home: str, persona: str, rules: str, evaluation: str,
                 log: CallLog, model: str = MODEL):
        super().__init__(name, home, persona)
        self.model, self.log = model, log
        self.system = (f"You are {name}.\n{persona}\n\n{rules}\n\nHOW YOU'RE EVALUATED\n{evaluation}")
        self.failures = 0

    def situation(self, obs: dict) -> str:
        convo = []
        for m in obs["conversation"]:
            star = "* " if m.get("new") else "  "
            pointing = f", pointing at {m['pointing']}" if m.get("pointing") else ""
            convo.append(f"{star}[{m['clock']}] {m['speaker']} (to {fmt_to(m['to'])}{pointing}): {m['text']}")
        sup = ", ".join(f"{k}: {v}" for k, v in obs["supply"].items())
        mins_left = obs["remaining"] / 60
        return "\n".join([
            f"Time: {obs['clock']} into the activity, {mins_left:.1f} minutes left.",
            f"Why you're deciding now: {'; '.join(obs['why_now']) or 'check-in'}.",
            f"You're at {obs['location']} with {', '.join(obs['people_here']) or 'nobody'}. "
            f"Dominoes left: {sup}.",
            f"Your hands: {obs['task']}",
            obs.get("start_status", ""),
            "What the others' hands are doing: " + ("; ".join(obs.get("hands") or []) or "nothing much") + ".",
            "",
            "THE TABLE NOW:",
            obs["map"],
            "",
            "CONVERSATION (last few minutes; * = new since you last took stock):",
            "\n".join(convo) or "(nobody has said anything yet)",
            "",
            "OTHER THINGS YOU NOTICED OR LEARNED:",
            "\n".join(obs["inbox"]) or "(nothing new)",
            "",
            "YOUR PRIVATE NOTES:",
            obs["notes"] or "(empty)",
        ])

    def act(self, obs: dict) -> Decision:
        prompt = self.situation(obs) + "\n\nWhat do you say and do now?\n" + OUTPUT_FORMAT
        for _ in range(2):
            text = call_model(self.system, prompt, self.log, f"{self.name}/{obs['clock']}", self.model)
            d = parse_json(text)
            if isinstance(d, dict):
                return self.to_decision(d)
            prompt += "\n\n(Your last reply wasn't a valid JSON object. Reply with JSON only.)"
        self.failures += 1
        return Decision()

    @staticmethod
    def to_decision(d: dict) -> Decision:
        to = d.get("to", "everyone")
        if isinstance(to, str) and to.lower() in ("everyone", "all", "table", ""):
            to = "everyone"
        strokes = d.get("strokes") or []
        if isinstance(strokes, dict):
            strokes = [strokes]
        try:
            eager = int(float(d.get("eagerness", 5)))
        except (TypeError, ValueError):
            eager = 5
        do = str(d.get("do") or "continue").lower().replace("-", "_").replace(" ", "_")
        return Decision(
            say=str(d.get("say") or ""), to=to, eagerness=max(1, min(10, eager)),
            do=do, strokes=[s for s in strokes if isinstance(s, dict)],
            restand=d.get("restand") if isinstance(d.get("restand"), list) else None,
            start=bool(d.get("start")),
            area=d.get("area") if isinstance(d.get("area"), list) else None,
            where=d.get("where"),
            point=d.get("point") if isinstance(d.get("point"), list) else None,
            notes=d.get("notes") if isinstance(d.get("notes"), str) else None,
            thinking=str(d.get("thinking") or "")[:600])

    def state_intent(self, obs: dict, full_conversation: list | None = None) -> str:
        if full_conversation is not None:
            obs = dict(obs, conversation=full_conversation)
        prompt = (self.situation(obs) + "\n\nTime is up. In one or two words: which animal is your "
                  "table's picture meant to be? Reply with JSON only: {\"animal\": \"...\"}")
        d = parse_json(call_model(self.system, prompt, self.log, f"{self.name}/intent", self.model)) or {}
        return str(d.get("animal") or "").strip().lower()
