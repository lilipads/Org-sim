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
{view_rules}
- There are no rulers. You judge positions by eye, to about a unit. Positions people mention, and
  everything you learn by looking, are rough.

HOW DOMINOES FALL
A falling domino knocks over another standing domino if that domino is 0.2 to 0.9 units ahead in the
falling direction, at most 0.35 units to the side of the falling line, and facing within 40 degrees of
the falling domino's direction. So a line can curve gently, but a sharp corner or a gap wider than 0.9
stops the chain. One domino can knock over two standing side by side, so a line can split into two,
and two lines can meet. Each domino lands about 0.05 units and 3 degrees off from where you aim.
Now and then a builder bumps the table and knocks over a run of nearby dominoes, which then have to be
stood back up. It only happens to people working within about {bump_units} units of each other, and even then
it's occasional: two people working side by side for the whole 20 minutes would expect about one bump. Some builders leave deliberate gaps so a bump only
knocks down one segment; any such gap has to be closed before the push.

TIME AND HANDS
- The clock runs continuously. Placing a domino carefully takes a few seconds; some people are quicker
  or steadier than others. You place more slowly while you're talking.
- There are {supply} dominoes for the whole table.
- The table has one start domino: set "start": true on a build and its first domino becomes the start.
  Setting it again later moves the start.

HOW DOMINO BUILDERS USUALLY WORK
- They grow the run outward from the start, adding each new stretch onto the end of what's already
  standing (or branching off its side), so everything stays connected as it grows. Pieces built
  separately have to be joined into the run later, and every joint is a place it can break.
- To draw a closed outline, the run comes from the start to one point of the shape and splits there
  into two lines that go round each side.
- They keep an eye on what the start would actually knock over.

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
- A real table has no coordinates on it. The numbers are only for your own hands and eyes; nobody
  else can see them, so don't say coordinates or numbers for positions out loud. Talk about places
  the way people do: point at them, and describe them ("the tail", "the top of the head", "just past
  where Maya's line ends", "a hand's width to the left").
- A facilitator calls out the time now and then.

PEOPLE AT THESE OFFSITES
Most people enjoy getting their hands on the dominoes. When their hands are free and nobody needs
them right now, they usually pick something useful to build or fix rather than wait.

THE SCRATCH PAD
At the start a paper scratch pad lies on the table. Anyone can pick it up ("pad": "take"); only one
person holds it at a time. Whoever holds it can sketch on it ("sketch": strokes, below) and everyone
at the table can see what's on it. The holder can hand it to someone ("pad": "give", "pad_to": name)
or put it down ("pad": "put_down"). Sketching keeps your hands busy, so you don't place dominoes in
that moment. {pad_rule}
Strokes on the pad are numbered, and the run starts where stroke 1 begins (marked START on the pad).
One falling domino can only send the fall forward, so at START the lines should all leave in roughly
the same direction (if they can't, START moves to the nearest end of the sketch where they can).
Sketch the way the run will flow: begin stroke 1 at the start, and begin every other stroke on a line
that's already drawn (where it branches off or carries on).
Building from the pad is the easy way to get the shape right: {{"type":"trace","stroke":3}} in a build
copies stroke 3 onto the table with your own hands. It's laid so it flows away from the start; where it
begins on another line, it carries on from it (or branches off it). If that line hasn't reached it yet,
you wait until it does, then carry on. Several people can trace different strokes at the same time,
but stroke 1 leaves the start and everything else grows from it, so make sure someone is on it.
Sketch strokes use the table's coordinates:
  {{"type":"curve","points":[[x,y],[x,y],...]}}   {{"type":"line","x0":..,"y0":..,"x1":..,"y1":..}}
  {{"type":"circle","cx":..,"cy":..,"r":..}}      {{"type":"label","x":..,"y":..,"text":"eye"}}
"sketch_clear": true wipes the pad first.

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
Lining up comes naturally: if you start a stroke right where a line ends, your hands line the first
domino up with that line's last one. If what you're laying ends just behind the start of another
line, you bend your last few dominoes so it runs into it.
Spacing of about 0.5-0.6 is comfortable. One build can be up to 40 dominoes.
"""

OUTPUT_FORMAT = """Reply with one JSON object and nothing else. Leave out fields you don't need.
{
  "thinking": "a sentence or two: what's going on and what you want",
  "say": "what you say out loud, or empty to stay quiet",
  "to": "everyone" or ["Name", ...],
  "eagerness": 1-10 (how strongly you want the floor right now),
  "point": [x, y] (optional: where you're pointing as you speak),
  "pad": "take | give | put_down" (optional, the scratch pad), "pad_to": "Name" (with give),
  "sketch": [...] (optional: strokes to draw on the pad, if you hold it), "sketch_clear": false,
  "do": "continue | build | take_down | inspect | stop",
  "strokes": [...], "start": false, "restand": [x0, y0, x1, y1],   (build)
  "area": [x0, y0, x1, y1],                                        (take_down, inspect)
  "notes": "your private notes for later: they replace the old ones. Keep what you need to remember."
}"""

# Version 5 (current): personality only. No job titles or roles (v3 tied traits to jobs; v4 still
# named jobs). Each person is a few plain sentences about how they are with other people and with
# things, with some specific details and tendencies that pull against each other. Nobody is written
# as a leader, builder, designer or checker. Hand speed and accuracy are set separately (skills).
PERSONAS_V2 = {
    "Maya": ("You coach your daughter's football team and you're in a pub quiz league. In a group you're "
             "usually relaxed and happy to go along, but once an idea grabs you, you can dig in. You say what "
             "you think, sometimes a beat too quickly."),
    "Tom": ("You took up pottery last year and love making things with your hands. With people you don't know "
            "well you're quiet at first, then you warm up and get funny. You lose track of time easily."),
    "Priya": ("You stay calm when things go wrong and you notice when someone's struggling, but with several good "
              "options in front of you, you can go back and forth. You laugh easily, including at yourself."),
    "Leo": ("You're a keen birdwatcher and patient with fiddly things. In a new group you'd rather listen than "
            "talk, and you're harder on yourself than on anyone else."),
    "Sofia": ("You love board games and get properly into the rules. You're upbeat and quick to suggest things, and "
              "sometimes you start before everyone has agreed."),
    "Omar": ("You played bass in a band for years. You're easy-going and a bit absent-minded, and you have a good "
             "eye for how things look."),
    "Hana": ("You keep lists and like to know the plan before you start, and you're usually the first to say out "
             "loud when something isn't working."),
    "Jack": ("You're friendly, chatty and slightly clumsy, you enjoy a bit of friendly competition, and you hand "
             "out credit freely."),
    "Sam": ("You've been to a lot of these team days and you're a little sceptical of them, but you can't stand "
            "seeing a job done badly. You're dry and to the point."),
    "Grace": ("You're at ease with drawings and space, and unsure how much to speak up in front of people you've "
              "only just met. You notice small things and mostly keep them to yourself."),
}
TABLE_OF_4_V2 = ["Maya", "Tom", "Priya", "Leo"]

VIEW_RULES = {
    "text": ("- The map shows standing dominoes as arrows (rough direction), S = the start domino, x = knocked\n"
             "  over, . = empty, and a lower-case letter where someone is pointing right now (their initial)."),
    "image": ("- Each time you decide, you see the table: a picture comes with every message. Standing dominoes are bars\n"
              "  with an orange tick on the side they'll fall toward. Dark ones are those the start would knock over if\n"
              "  it were pushed now (you can trace that by eye); pale ones aren't connected to it yet."),
    "image_plain": ("- Each time you decide, you see the table: a picture comes with every message. Standing dominoes are dark bars\n"
              "  with an orange tick on the side they'll fall toward. Knocked-over ones lie flat in red. The start\n"
              "  domino is ringed in green. A purple circle shows where someone is pointing, and a blue label shows\n"
              "  where someone's hands are working. Grid lines are 1 unit apart, labelled every 5."),
}


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
            obs.get("pad_status", ""),
            "What the others' hands are doing: " + ("; ".join(obs.get("hands") or []) or "nothing much") + ".",
            "",
            "THE TABLE NOW:",
            ("(the attached picture: the table as you see it right now)" if obs.get("view_dir") else obs["map"]),
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

    @staticmethod
    def _image(obs: dict) -> list | None:
        import os
        if not obs.get("view_dir"):
            return None
        paths = [os.path.join(obs["view_dir"], f) for f in ("table.png", "pad.png")]
        paths = [p for p in paths if os.path.exists(p)]
        return paths or None

    def act(self, obs: dict) -> Decision:
        prompt = self.situation(obs) + "\n\nWhat do you say and do now?\n" + OUTPUT_FORMAT
        for _ in range(2):
            text = call_model(self.system, prompt, self.log, f"{self.name}/{obs['clock']}", self.model,
                              image=self._image(obs))
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
            pad=str(d.get("pad") or "").lower().replace(" ", "_").replace("-", "_"),
            pad_to=d.get("pad_to") if isinstance(d.get("pad_to"), str) else None,
            sketch=[x for x in (d.get("sketch") or []) if isinstance(x, dict)] if isinstance(d.get("sketch"), list) else [],
            sketch_clear=bool(d.get("sketch_clear")),
            notes=d.get("notes") if isinstance(d.get("notes"), str) else None,
            thinking=str(d.get("thinking") or "")[:600])

    def state_intent(self, obs: dict, full_conversation: list | None = None) -> str:
        if full_conversation is not None:
            obs = dict(obs, conversation=full_conversation)
        prompt = (self.situation(obs) + "\n\nTime is up. In one or two words: which animal is your "
                  "table's picture meant to be? Reply with JSON only: {\"animal\": \"...\"}")
        d = parse_json(call_model(self.system, prompt, self.log, f"{self.name}/intent", self.model,
                                  image=self._image(obs))) or {}
        return str(d.get("animal") or "").strip().lower()
