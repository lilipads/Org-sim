"""Eng / Design / PM roles for DESIGN_REVIEW_STUDY.md: what each knows, what each can check, and the
rules text for each design mode."""
from __future__ import annotations

import re

TITLES = {"eng": "Eng", "design": "Design", "pm": "PM"}


def assign_roles(names: list, seed: int) -> dict:
    """2 Eng, 1 Design, 1 PM at a table of 4 (more Eng at bigger tables); rotated by seed so no
    personality always gets the same role."""
    base = ["design", "pm"] + ["eng"] * max(0, len(names) - 2)
    k = seed % len(names)
    rot = base[k:] + base[:k]
    return dict(zip(names, rot))


VAGUE_FALL = """HOW DOMINOES FALL
A falling domino knocks over the next one if it's close enough and roughly in line, so a line can curve
gently but a sharp corner or a wide gap stops the chain. Lines can split and meet. Hands aren't perfectly
accurate. Now and then a builder bumps the table and knocks over a run of nearby dominoes, which then have to
be stood back up; it only happens to people working close together, and it's occasional.
(The Eng at your table knows the exact mechanics.)

"""

KNOWLEDGE = {
    "eng": """YOUR EXPERTISE: ENG (domino mechanics)
You know exactly how dominoes behave (the rules under HOW DOMINOES FALL are second nature), plus what
experience teaches:
- A branch has to leave the line it grows from within about 40 degrees of that line's direction; a stroke
  that leaves at a steep angle never gets the fall.
- A separate shape (an eye, a dot, a detail that doesn't touch the outline) never falls: nothing runs
  into it. Neither does any stroke that isn't joined to the run.
- At START, every line leaving has to head roughly the same way (within about 100 degrees).
- Every join is a weak point; fewer joins, fewer breaks. Very short strokes are fiddly and break easily.
- One person lays about 15-20 dominoes a minute; a stroke can only be laid by one person at a time.
YOUR CHECK: a dry run. Add "check": "dry_run" and you spend about 30 seconds playing the fall through the
current sketch in your head; you then know which strokes would fall, which wouldn't, and where it stops.
Only you can do this. What you learn is yours until you say it out loud.
""",
    "design": """YOUR EXPERTISE: DESIGN (how it looks)
You know what makes a line picture read instantly and look good:
- Every animal has one or two tell-tale features that make it unmistakable in outline; without them it reads
  as something else (similar body shapes are easily confused). Make those features big and clear.
- Proportion and balance: a big, confident shape that fills the table reads better than a small one.
- Flowing, smooth curves look skilled; wobbly, cramped or cluttered lines look clumsy. Fewer, stronger lines
  beat many small details. Symmetry helps where the animal is symmetrical.
- The picture is judged twice for looks: blind judges must name it, and an art panel rates its beauty.
YOUR CHECK: a squint test. Add "check": "squint" and you spend about 30 seconds studying the current sketch
the way a stranger would see it built; you learn what it reads as, and how good it looks. Only you can do
this. What you learn is yours until you say it out loud.
""",
    "pm": """YOUR EXPERTISE: PM (the client)
You own the relationship with the client. Only you talk to them, and only you have the notes from meeting
them (under THE CLIENT). The others know only the one-line commission.
YOUR CHECK: ask the client. Add "check": "ask_client" and "check_note": "what you want to ask" and you step
away for about 45 seconds to show the client the current sketch (or put an idea to them) and hear their
reaction. What you learn is yours until you say it out loud.
""",
}

SCORE = """HOW THE PICTURE IS SCORED
Three independent judgements, multiplied: blind judges must recognise the animal from what falls; the client
must be happy with it; and an art panel rates how beautiful it is. A broken run, an animal the client
dislikes, or a clumsy drawing all pull the score down.

"""

MODE_RULES = {
    "lone": ("HOW THE DESIGN GETS MADE\n{designer} ({title}) designs alone: only they draw on the scratch pad, and the "
             "rest of you don't discuss the design with them. Nobody can lay a domino until {designer} locks the "
             "design (\"lock\": true). Then everyone builds it.\n\n"),
    "review": ("HOW THE DESIGN GETS MADE\n{designer} ({title}) drafts the design on the scratch pad. Before it can be "
               "locked, each of the other roles gives one review of the draft (\"review\": \"your review\"), like a "
               "design doc review. Then {designer} decides and locks it (\"lock\": true). Nobody can lay a domino "
               "until the design is locked.\n\n"),
    "open": ("HOW THE DESIGN GETS MADE\nAnyone can sketch and discuss. Nobody can lay a domino until someone locks the "
             "design (\"lock\": true); after that, building is open. Lock it when the table is ready.\n\n"),
}


def team_line(name: str, roles: dict) -> str:
    who = ", ".join(f"{n} ({TITLES[r]})" for n, r in roles.items())
    return f"YOUR TEAM\nYou are the {TITLES[roles[name]]}. At your table: {who}.\n\n"


def role_rules(rules: str, name: str, roles: dict, mode: str | None, designer: str | None,
               client_block: str, commission: str) -> tuple:
    """Rewrite the shared rules for one person. Returns (rules, extra output format)."""
    role = roles[name]
    if role != "eng":
        rules = re.sub(r"HOW DOMINOES FALL\n.*?\n\n(?=TIME AND HANDS)", VAGUE_FALL, rules, flags=re.S)
    if role == "pm":
        client = client_block
    else:
        client = ("THE CLIENT\n" + commission + " Only the PM talks to the client and has their notes.\n")
    extra = team_line(name, roles) + KNOWLEDGE[role] + "\n" + client + "\n" + SCORE
    if mode:
        extra += MODE_RULES[mode].format(designer=designer, title=TITLES[roles[designer]] if designer else "")
    rules = rules.replace("THE TABLE\n", extra + "THE TABLE\n", 1)
    check = {"eng": "dry_run", "design": "squint", "pm": "ask_client"}[role]
    fmt = f'\nYour check: "check": "{check}"' + (', "check_note": "your question"' if role == "pm" else "") + "."
    if mode in ("lone", "review") and name == designer or mode == "open":
        fmt += ' To lock the design: "lock": true.'
    if mode == "review" and name != designer:
        fmt += ' Your review of the draft (once): "review": "what works, what to change".'
    return rules, fmt
