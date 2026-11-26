"""Real-time engine (interaction model v2, DESIGN.md §4).

The clock runs in short beats (15 s by default). Agents are not polled every
beat. They are asked to decide only when something calls for it:
  * the round starts;
  * someone says their name; or, if their hands are free, anyone talks to the table;
  * their task finishes, or something happens to their work (bump, take-down);
  * they've been quiet too long (a periodic check-in).
Each time, an agent can say something AND do something with their hands. Work is
"head down": a build is a queue of dominoes the engine places over time, at about
10 s per domino (slower while talking).

Taking the floor: if several people start talking to the table in the same beat,
the most eager speaks first and others fit in while the beat has room; the rest
hold their thought (they'll hear the speaker and can say it later).

No rulers (see handwork.py): free-hand strokes land roughly where aimed; strokes
anchored to an existing domino are precise; what agents see is approximate.
"""
from __future__ import annotations

import json
import math
import random
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field

from .dominoes import World
from .handwork import (anchored_specs, area_words, describe_spot, direction, end_join, eye_inspect,
                       fix_specs, freehand_specs, sketch_flow, snap_start, trace_specs, where, begin_join)
from .render import sketch_points
from .handwork import SPACING as SPACING_
from .dominoes import expand_stroke
from .game import push_world
from .render import agent_view_png, ascii_map, sketch_png

DOS = ("continue", "build", "take_down", "inspect", "stop", "walk")


@dataclass
class LiveConfig:
    round_no: int = 1
    duration: float = 1200.0         # seconds of game time (20 minutes)
    beat: float = 15.0
    seconds_per_domino: float = 10.0  # ~12 dominoes per 2 minutes of focused work
    talk_slowdown: float = 0.5       # hands work at this speed in a beat you speak
    take_down_per_beat: int = 6
    take_down_max: int = 30          # per take-down task
    inspect_seconds: float = 15.0
    max_quiet: float = 120.0         # longest an agent goes without being asked
    idle_quiet: float = 60.0         # same, for an agent with nothing to do
    announce_at: tuple = (10, 5, 2)  # facilitator calls time at these minutes left
    max_queue: int = 40              # dominoes per build task
    history_seconds: float = 300.0   # how much recent conversation an agent sees
    max_words: int = 80
    words_per_beat: int = 40         # how much talk fits in one beat at one table (~2.5 words/s)
    time_limit: float | None = None  # round 2
    shared_pool: str | None = None
    reveal_threshold: float = 0.5
    seed: int = 0
    view: str = "text"               # text (ASCII map) | image (rendered picture of the table)
    view_dir: str | None = None      # where image views are written
    scratchpad_until: float | None = 120.0  # a scratch pad lies on the table until then (None: no pad)
    freehand_sigma: float = 0.3      # how far off a stroke aimed by eye lands (units)
    snap: bool = True                # line new dominoes up with a line end / close a small gap by hand
    show_reach: bool = False         # draw what the start dominoes would knock over darker than the rest
    pad_only: bool = False           # builds come from the pad (trace) plus small repairs (fix, restand)
    skills: dict = field(default_factory=dict)  # name -> {"speed": x, "error": y}; 1.0 = average hands


@dataclass
class Decision:
    say: str = ""
    to: object = "everyone"
    eagerness: int = 5
    do: str = "continue"
    strokes: list = field(default_factory=list)
    restand: list | None = None
    start: bool = False
    area: list | None = None
    where: str | None = None
    point: list | None = None        # [x, y]: point at a spot while talking
    pad: str = ""                    # scratch pad: take | put_down | give
    pad_to: str | None = None        # give the pad to this person
    sketch: list = field(default_factory=list)   # strokes to draw on the pad (if you hold it)
    sketch_clear: bool = False       # wipe the pad before drawing
    interrupt: str = ""              # unused (kept so old logs still load)
    notes: str | None = None
    thinking: str = ""

    def brief(self) -> dict:
        d = {k: v for k, v in asdict(self).items() if v not in (None, "", [], False)}
        d.pop("notes", None)
        if not self.say:
            d.pop("to", None)
            d.pop("eagerness", None)
        return d


class LiveAgentBase:
    def __init__(self, name: str, home: str, persona: str = ""):
        self.name, self.home, self.persona = name, home, persona

    def act(self, obs: dict) -> Decision:  # pragma: no cover - interface
        raise NotImplementedError


def clock(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


class LiveGame:
    def __init__(self, world: World, agents: list, cfg: LiveConfig, start_region: str | None = None):
        self.world, self.agents, self.cfg = world, agents, cfg
        self.start_region = start_region
        self.rng = random.Random(cfg.seed)
        self.by_name = {a.name: a for a in agents}
        n = [a.name for a in agents]
        self.location = {a.name: a.home for a in agents}
        self.notes = dict.fromkeys(n, "")
        self.interrupt = dict.fromkeys(n, "any")
        self.task: dict = dict.fromkeys(n)
        self.credit = dict.fromkeys(n, 0.0)
        self.heard: dict = {a: [] for a in n}        # [{t, speaker, to, text, side}]
        self.inbox: dict = {a: [] for a in n}        # things since last asked: notices, results
        self.wake: dict = {a: ["the round is starting"] for a in n}
        self.last_asked = dict.fromkeys(n, -1e9)
        self.last_seen_msg = dict.fromkeys(n, 0)
        self.markers: dict = {}                     # name -> (x, y, t, description)
        self.pad_exists = cfg.scratchpad_until is not None
        self.pad_holder: str | None = None
        self.pad_strokes: list = []
        self._start_claimed = False
        self._taken: set = set()                    # line ends someone is already carrying on
        self.traced: dict = {}                      # sketch stroke number -> domino ids laid for it
        self.t = 0.0
        self.log: dict = {"engine": "live", "config": asdict(cfg),
                          "regions": [asdict(r) for r in world.regions.values()],
                          "agents": [{"name": a.name, "home": a.home, "persona": a.persona} for a in agents],
                          "initial": world.snapshot(), "turns": []}
        self.log["scratchpad"] = {"until": cfg.scratchpad_until, "history": []}

    # ---- helpers ------------------------------------------------------------
    def pools_for(self, name: str) -> list:
        pools = [self.by_name[name].home]
        if self.cfg.shared_pool:
            pools.append(self.cfg.shared_pool)
        return pools

    def pool_for_region(self, region: str) -> str:
        r = self.world.regions[region]
        return region if r.kind == "table" else (self.cfg.shared_pool or region)

    def here(self, name: str) -> list:
        return [o for o in self.by_name if o != name and self.location[o] == self.location[name]]

    def hands(self, name: str) -> list:
        """What you can see the others doing with their hands."""
        out = []
        for o in self.here(name):
            t = self.task[o]
            if not t:
                continue
            if t["kind"] == "build":
                x, y = t.get("last") or t.get("aim") or (None, None)
                if x is not None:
                    out.append(f"{o} is building around {where(x, y)} ({area_words(self.world, x, y)})")
            elif t["kind"] in ("take_down", "inspect"):
                x0, y0, x1, y1 = t["area"]
                verb = "taking dominoes away" if t["kind"] == "take_down" else "looking closely"
                out.append(f"{o} is {verb} around {where((x0 + x1) / 2, (y0 + y1) / 2)}")
        return out

    def overlay(self, text: str, loc) -> str:
        """Show recent pointing on the map: the pointer's initial, in lower case."""
        lines = text.split("\n")
        for n, (x, y, t, _) in self.markers.items():
            if self.t - t > 30 or not loc.contains(x, y):
                continue
            r, c = 2 + int(y - loc.y0), 5 + int(x - loc.x0)
            if 0 <= r < len(lines) and 0 <= c < len(lines[r]):
                lines[r] = lines[r][:c] + n[0].lower() + lines[r][c + 1:]
        return "\n".join(lines)

    def task_status(self, name: str) -> str:
        task = self.task[name]
        if not task:
            return "Nothing in your hands right now."
        if task["kind"] == "build":
            done, total = task["done"], task["total"]
            return (f"Building ({task['label']}): {done} of {total} placed so far"
                    + (f", {len(task['queue'])} still to go." if task["queue"] else "."))

        if task["kind"] == "take_down":
            return f"Taking down dominoes in {task['area']}: {task['removed']} removed so far."
        if task["kind"] == "inspect":
            return f"Inspecting {task['area']}."
        return task["kind"]

    def observe(self, name: str) -> dict:
        a = self.by_name[name]
        loc = self.world.regions[self.location[name]]
        new_from = self.last_seen_msg[name]
        recent = [dict(m, new=(i >= new_from)) for i, m in enumerate(self.heard[name])
                  if m["t"] >= self.t - self.cfg.history_seconds]
        obs = {
            "name": name, "persona": a.persona, "round": self.cfg.round_no,
            "clock": clock(self.t), "elapsed": self.t,
            "remaining": max(0.0, self.cfg.duration - self.t),
            "why_now": list(self.wake[name]), "location": loc.name, "people_here": self.here(name),
            "supply": {p: self.world.supply.get(p, 0) for p in self.pools_for(name)},
            "map": ascii_map(self.world, loc.x0, loc.y0, loc.x1, loc.y1),
            "conversation": recent,
            "inbox": list(self.inbox[name]), "task": self.task_status(name),
            "hands": self.hands(name), "notes": self.notes[name],
            "start_status": self.start_status(name),
            "pad_status": self.pad_status(name),
        }
        obs["map"] = self.overlay(obs["map"], loc)
        if self.cfg.view == "image":
            import os
            import tempfile
            base = self.cfg.view_dir or tempfile.gettempdir()
            folder = os.path.join(base, f"{name}_{int(self.t)}")
            os.makedirs(folder, exist_ok=True)
            markers = {o: (x, y) for o, (x, y, t, _) in self.markers.items() if self.t - t <= 30}
            hands = {}
            for o in self.here(name):
                t = self.task[o]
                if t and t["kind"] == "build" and (t.get("last") or t.get("aim")):
                    hands[o] = t.get("last") or t.get("aim")
                elif t and t["kind"] in ("take_down", "inspect"):
                    a0, b0, a1, b1 = t["area"]
                    hands[o] = ((a0 + a1) / 2, (b0 + b1) / 2)
            agent_view_png(self.world, loc, os.path.join(folder, "table.png"), markers, hands,
                           show_reach=self.cfg.show_reach)
            obs["view_dir"] = folder
            if self.pad_exists and self.pad_strokes and self.location[name] == loc.name:
                sketch_png(self.pad_strokes, os.path.join(folder, "pad.png"), (loc.x1 - loc.x0, loc.y1 - loc.y0),
                           self.pad_holder)
        if len(self.world.regions) > 1:
            obs["room_overview"] = ascii_map(self.world, 0, 0, self.world.width, self.world.height, step=3.0)
        return obs

    # ---- one beat -------------------------------------------------------------
    def due(self) -> list:
        out = []
        for n in self.by_name:
            quiet = self.t - self.last_asked[n]
            limit = self.cfg.idle_quiet if not self.task[n] else self.cfg.max_quiet
            if quiet >= limit:
                self.wake[n].append(f"a check-in: {int(quiet)} seconds since you last took stock")
            if self.wake[n]:
                out.append(n)
        return out

    def step(self) -> dict:
        cfg = self.cfg
        rec = {"turn": len(self.log["turns"]) + 1, "time": self.t, "clock": clock(self.t),
               "asked": [], "decisions": {}, "conversations": [], "held": [], "events": []}
        self._announce(rec)
        asked = self.due()
        decisions: dict = {}
        if asked:
            obs = {n: self.observe(n) for n in asked}

            def call(n):
                try:
                    return self.by_name[n].act(obs[n])
                except Exception as e:  # an agent failing must not stop the game
                    return Decision(thinking=f"[error: {e}]")

            with ThreadPoolExecutor(max_workers=min(16, len(asked))) as ex:
                decisions = dict(zip(asked, ex.map(call, asked)))
            for n in asked:
                self.wake[n] = []
                self.inbox[n] = []
                self.last_asked[n] = self.t
                self.last_seen_msg[n] = len(self.heard[n])
            rec["asked"] = asked
            rec["decisions"] = {n: d.brief() for n, d in decisions.items()}

        # walking first (free), then notes and interrupt preferences
        for n, d in decisions.items():
            if d.notes is not None:
                self.notes[n] = d.notes[:2500]
            dest = d.where if d.do == "walk" else None
            if dest and dest in self.world.regions and dest != self.location[n]:
                self.location[n] = dest
                rec["events"].append({"type": "move", "who": n, "where": dest})

        sketched = self._pad(decisions, rec)
        for n, d in decisions.items():
            self._start_task(n, d, rec)
        spoke = self._speech(decisions, rec)
        placed_at = self._work(spoke, rec, sketched)
        self._bumps(placed_at, rec)
        rec["notes"] = dict(self.notes)
        rec["supply"] = dict(self.world.supply)
        rec["locations"] = dict(self.location)
        rec["tasks"] = {n: self.task_status(n) for n in self.by_name}
        rec["snapshot"] = self.world.snapshot()
        self.log["turns"].append(rec)
        self.t += cfg.beat
        return rec

    def _facilitator(self, text: str, rec: dict, reason: str):
        msg = {"t": self.t, "clock": clock(self.t), "speaker": "Facilitator", "to": "everyone",
               "text": text, "side": False}
        for n in self.by_name:
            self.heard[n].append(dict(msg))
            self.wake[n].append(reason)
        rec["conversations"].append({"members": ["Facilitator"], "pulled_in": [], "location": None,
                                     "messages": [{"speaker": "Facilitator", "to": "everyone", "message": text}]})

    def _announce(self, rec: dict):
        """The facilitator calls time, as at a real offsite, and collects the scratch pad."""
        for m in self.cfg.announce_at:
            at = self.cfg.duration - m * 60
            if at < 0 or not (at <= self.t < at + self.cfg.beat):
                continue
            self._facilitator(f"{m} minutes left! When time's up I'll push your start domino; "
                              "only what's connected to it will fall.", rec, "the facilitator called time")
        until = self.cfg.scratchpad_until
        if self.pad_exists and until is not None and self.t >= until:
            self.pad_exists = False
            self.log["scratchpad"]["taken_at"] = self.t
            self.log["scratchpad"]["final"] = list(self.pad_strokes)
            self.log["scratchpad"]["holder_when_taken"] = self.pad_holder
            self.pad_holder = None
            self._facilitator("Time's up for the scratch pad, I'm taking it away now. From here on, "
                              "work from what you remember.", rec, "the facilitator took the scratch pad away")
            rec["events"].append({"type": "pad", "what": "taken away"})

    def pad_status(self, name: str) -> str:
        if self.cfg.scratchpad_until is None:
            return ""
        if not self.pad_exists:
            return "The scratch pad is gone: the facilitator took it away."
        left = max(0, self.cfg.scratchpad_until - self.t)
        when = ("It stays on the table for the whole activity." if self.cfg.scratchpad_until >= self.cfg.duration
                else f"The facilitator will take it away in {int(left)} seconds.")
        if self.pad_holder is None:
            what = "is lying on the table; anyone can pick it up"
        elif self.pad_holder == name:
            what = "is in your hands"
        else:
            what = f"is in {self.pad_holder}'s hands"
        drawn = (f" It has a sketch on it (attached as the second picture)." if self.pad_strokes
                 else " Nothing is drawn on it yet.")
        return f"The scratch pad {what}.{drawn} {when}"

    def _pad(self, decisions: dict, rec: dict) -> set:
        """Picking up, passing, putting down and sketching. Returns who sketched this beat
        (their hands were busy with the pad, not dominoes)."""
        sketched = set()
        if not self.pad_exists:
            return sketched
        names = list(decisions)
        self.rng.shuffle(names)
        h = self.pad_holder                     # 1. the holder draws
        if h and h in decisions and (decisions[h].sketch or decisions[h].sketch_clear):
            d = decisions[h]
            if d.sketch_clear:
                self.pad_strokes = []
            good = [s for s in d.sketch if isinstance(s, dict)][:20]
            self.pad_strokes = (self.pad_strokes + good)[-60:]
            sketched.add(h)
            rec["events"].append({"type": "pad", "who": h, "what": "sketched", "strokes": good,
                                  "cleared": bool(d.sketch_clear)})
            self.log["scratchpad"]["history"].append({"t": self.t, "who": h, "strokes": good,
                                                      "cleared": bool(d.sketch_clear)})
            for n in self.by_name:
                if n != h and self.location[n] == self.location[h] and not self.task[n]:
                    self.wake[n].append(f"{h} sketched on the scratch pad")
        if h and h in decisions:                # 2. then passes it on or puts it down
            d = decisions[h]
            if d.pad == "put_down":
                self.pad_holder = None
                rec["events"].append({"type": "pad", "who": h, "what": "put down"})
            elif d.pad == "give" and d.pad_to in self.by_name and d.pad_to != h:
                self.pad_holder = d.pad_to
                self.wake[d.pad_to].append(f"{h} handed you the scratch pad")
                rec["events"].append({"type": "pad", "who": h, "what": "gave", "to": d.pad_to})
        takers = [n for n in names if decisions[n].pad == "take" and n != self.pad_holder]
        if takers:                              # 3. someone picks it up if it's free
            if self.pad_holder is None:
                taker = max(takers, key=lambda n: decisions[n].eagerness)
                self.pad_holder = taker
                rec["events"].append({"type": "pad", "who": taker, "what": "picked up"})
                for n in takers:
                    if n != taker:
                        self.inbox[n].append(f"{taker} picked up the scratch pad before you could.")
            else:
                for n in takers:
                    self.inbox[n].append(f"{self.pad_holder} has the scratch pad; ask them for it.")
        return sketched

    def _someone_laying_start(self, name: str) -> bool:
        """Is anyone else, right now, about to lay this table's start domino?"""
        for o, t in self.task.items():
            if o == name or not t or t.get("kind") != "build" or not t.get("start"):
                continue
            if t["queue"] and not t["placed"] and self.location[o] == self.location[name]:
                return True
        return False

    def start_status(self, name: str) -> str:
        loc = self.location[name]
        starts = [d for d in self.world.dominoes.values() if d.start and d.region == loc]
        if not starts:
            return "There is no start domino on the table right now, so nothing would fall."
        d = starts[0]
        if d.state != "up":
            return f"The start domino near {where(d.x, d.y)} has been knocked over; it needs standing back up."
        status = f"The start domino is near {where(d.x, d.y)}, facing {direction(d.angle)}."
        if self.cfg.show_reach:
            reach = len(self.world.reachable_from_start(loc))
            standing = sum(1 for x in self.world.dominoes.values() if x.region == loc and x.state == "up")
            status += f" Tracing it by eye, it would knock over about {reach} of the {standing} standing dominoes."
        return status

    def _speech(self, decisions: dict, rec: dict) -> set:
        """Resolve who gets the floor. Returns the set of agents who spoke."""
        spoke = set()
        wanting = [(n, d) for n, d in decisions.items() if d.say.strip()]
        table_talk: dict = {}
        for n, d in wanting:
            to = d.to
            if to in (None, "", "everyone", "all", ["everyone"]):
                table_talk.setdefault(self.location[n], []).append((n, d))
            else:
                names = [to] if isinstance(to, str) else list(to)
                self._say(n, d, [m for m in names if m in self.by_name and m != n], rec)
                spoke.add(n)
        for loc, cands in table_talk.items():
            # Most eager first; others get in too while the beat has room for their words.
            self.rng.shuffle(cands)
            cands.sort(key=lambda nd: -int(nd[1].eagerness or 0))
            used, first = 0, cands[0][0]
            for k, (n, d) in enumerate(cands):
                words = len(d.say.split())
                if k == 0 or used + words <= self.cfg.words_per_beat:
                    self._say(n, d, "everyone", rec)
                    spoke.add(n)
                    used += words
                else:
                    self.inbox[n].append(f"You didn't get to say \"{d.say.strip()}\": {first} was talking. "
                                         "Say it again if it still matters.")
                    rec["held"].append({"who": n, "message": d.say.strip(), "yielded_to": first})
        return spoke

    def _say(self, n: str, d: Decision, audience, rec: dict):
        words = d.say.strip().split()
        text = " ".join(words[: self.cfg.max_words]) + (" ..." if len(words) > self.cfg.max_words else "")
        here = self.here(n)
        if audience == "everyone":
            hearers, missing = here, []
        else:
            hearers = [m for m in audience if m in here]
            missing = [m for m in audience if m not in here]
            if missing:
                self.inbox[n].append(f"Not here, so they didn't hear you: {', '.join(missing)}.")
        msg = {"t": self.t, "clock": clock(self.t), "speaker": n,
               "to": "everyone" if audience == "everyone" else hearers, "text": text}
        pt = d.point if isinstance(d.point, list) and len(d.point) >= 2 else None
        if pt:
            try:
                px, py = float(pt[0]), float(pt[1])
                desc = describe_spot(self.world, px, py)
                self.markers[n] = (px, py, self.t, desc)
                msg["pointing"] = f"{desc} near {where(px, py)}"
            except (TypeError, ValueError):
                pass
        self.heard[n].append(dict(msg, side=False))
        for m in hearers:
            self.heard[m].append(dict(msg, side=False))
            addressed = audience != "everyone"
            named = re.search(r"\b" + re.escape(m) + r"\b", text, re.I) is not None
            if addressed or named or not self.task[m]:
                reason = (f"{n} said something to you" if addressed or named
                          else f"{n} said something to the table")
                if reason not in self.wake[m]:
                    self.wake[m].append(reason)
        if audience != "everyone":
            for m in here:
                if m not in hearers:
                    self.inbox[m].append(f"[{clock(self.t)}] {n} said something quietly to {', '.join(hearers)}.")
        rec["conversations"].append({"members": [n] + list(hearers), "pulled_in": [], "location": self.location[n],
                                     "messages": [{"speaker": n, "to": msg["to"], "message": text,
                                                   **({"pointing": msg["pointing"]} if "pointing" in msg else {})}]})

    def _start_task(self, n: str, d: Decision, rec: dict):
        if d.do in ("continue", "walk") or d.do not in DOS:
            return
        if d.do == "stop":
            self.task[n] = None
            return
        if d.do == "build":
            cur = self.task.get(n)
            asked = [s.get("stroke") for s in (d.strokes or []) if s.get("type") == "trace"]
            if (cur and cur.get("kind") == "build" and cur.get("trace_k") is not None and len(d.strokes or []) == 1
                    and asked and str(asked[0]) == str(cur["trace_k"]) and (cur["queue"] or cur.get("pending"))):
                return                         # already laying that stroke: just keep going
            if asked:
                for o, t in self.task.items():
                    if (o != n and t and t.get("kind") == "build" and str(t.get("trace_k")) in map(str, asked)
                            and (t["queue"] or t.get("pending"))):
                        self.inbox[n].append(f"{o} is already laying stroke {t['trace_k']}; leave it to them "
                                             "or ask them about it.")
                        self.wake[n].append("someone else is on that stroke")
                        return
            specs, bad, notes = [], [], []
            trace_start = False
            pending = None
            trace_k = None
            for s in d.strokes or []:
                try:
                    room = self.cfg.max_queue - len(specs)
                    if self.cfg.pad_only and s.get("type") not in ("trace", "fix", "extend", "connect"):
                        bad.append(f"{s.get('type')!r} isn't how this table builds: sketch it on the pad, then trace it")
                        continue
                    if s.get("type") == "trace":
                        try:
                            k = int(s.get("stroke"))
                        except (TypeError, ValueError):
                            k = 0
                        drawn = [st for st in self.pad_strokes]
                        if not self.pad_exists or not (1 <= k <= len(drawn)) or drawn[k - 1].get("type") == "label":
                            bad.append(f"there's no sketch stroke {s.get('stroke')} on the pad to trace")
                            continue
                        origin, flow = sketch_flow(drawn, sketch_points)
                        segs = flow.get(k) or [sketch_points(drawn[k - 1])]
                        pts_src = segs[0]
                        err = self.cfg.skills.get(n, {}).get("error", 1.0)
                        # tracing a stroke again: its old dominoes are lifted first, so plan as if gone
                        old = set(i for i in self.traced.get(k, ()) if i in self.world.dominoes)
                        has_start = any(x.start for x in self.world.dominoes.values()
                                        if x.region == self.location[n] and x.id not in old) \
                            or self._someone_laying_start(n)
                        lead = None
                        at_origin = origin is not None and math.hypot(pts_src[0][0] - origin[0],
                                                                      pts_src[0][1] - origin[1]) <= 1.0
                        if at_origin and not has_start and not specs:
                            # the run starts where the sketch starts: the start domino faces between
                            # all the lines leaving that point, and they split off just after it
                            heads = [math.atan2(p[min(2, len(p) - 1)][1] - p[0][1], p[min(2, len(p) - 1)][0] - p[0][0])
                                     for ps in flow.values() for p in ps
                                     if math.hypot(p[0][0] - origin[0], p[0][1] - origin[1]) <= 1.0]
                            bis = math.degrees(math.atan2(sum(math.sin(a) for a in heads), sum(math.cos(a) for a in heads)))
                            lead = (origin[0] - SPACING_ * math.cos(math.radians(bis)),
                                    origin[1] - SPACING_ * math.sin(math.radians(bis)), bis % 360)
                            trace_start = True
                            self._start_claimed = True   # (kept for old logs; see _someone_laying_start)
                        # Does this stroke begin where another line has to arrive first?
                        begin = pts_src[0]
                        feeds_in = lead is None and (
                            at_origin or any(math.hypot(p[-1][0] - begin[0], p[-1][1] - begin[1]) <= 1.6
                                             for kk, ps in flow.items() for p in ps if p is not pts_src))
                        if feeds_in and not specs and not any(
                                x.state == "up" and x.id not in old for x in self.world.near(begin[0], begin[1], 1.4)):
                            pending = {"k": k, "pts": pts_src, "err": err, "room": max(0, room), "begin": begin,
                                       "more": segs[1:]}
                            trace_k = k
                            notes.append(f"waiting for the run to reach the start of stroke {k}")
                            continue
                        pts, note = trace_specs(self.world, pts_src, self.rng, max(0, room),
                                                drift=self.cfg.freehand_sigma * 0.5 * err, lead=lead,
                                                taken=self._taken, exclude=old)
                        if old:                # tracing a stroke again: lift what's there first
                            specs = [("remove", i) for i in old] + specs
                            self.traced[k] = set()
                            notes.append(f"lifting the old stroke {k} and laying it again")
                        notes.append(f"{note} (stroke {k})")
                        specs += [("place", sp) for sp in pts]
                        trace_k = k
                        if len(segs) > 1:      # the other half of a stroke through a junction
                            pending = {"k": k, "pts": segs[1], "err": err, "room": max(0, room - len(pts)),
                                       "begin": segs[1][0], "more": segs[2:]}
                        continue
                    if s.get("type") == "fix":
                        ops, note = fix_specs(self.world, s, max(0, room))
                        notes.append(note)
                        if not ops:
                            bad.append(note)
                        specs += ops
                        continue
                    if s.get("type") in ("extend", "connect"):
                        pts, note = anchored_specs(self.world, s, max(0, room))
                        notes.append(note)
                        if not pts:
                            bad.append(note)
                    else:
                        pts, snapped = (snap_start(self.world, expand_stroke(s)) if self.cfg.snap
                                        else ([], ""))
                        if snapped:
                            notes.append(snapped)
                        else:
                            pts = freehand_specs(s, self.rng, self.cfg.freehand_sigma
                                                 * self.cfg.skills.get(n, {}).get("error", 1.0))
                    specs += [("place", sp) for sp in pts]
                except Exception as e:
                    bad.append(f"{s!r}: {e}")
            if d.restand and len(d.restand) == 4:
                x0, y0, x1, y1 = (float(v) for v in d.restand)
                down = [dd.id for dd in self.world.dominoes.values() if dd.state == "down"
                        and min(x0, x1) <= dd.x <= max(x0, x1) and min(y0, y1) <= dd.y <= max(y0, y1)]
                specs = [("restand", i) for i in down] + specs
            cut = max(0, len(specs) - self.cfg.max_queue)
            specs = specs[: self.cfg.max_queue]
            label = "; ".join(notes) or ", ".join(s.get("type", "?") for s in (d.strokes or [])) or "re-standing"
            aim = next(((op[1][0], op[1][1]) for op in specs if op[0] == "place"), None)
            explicit = bool(d.start)
            if explicit and self.cfg.pad_only:     # the start sits at START on the pad, laid with stroke 1
                explicit = False
                self.inbox[n].append("The start goes where START is on the pad and comes with stroke 1, "
                                     "so your build doesn't move it.")
            self.task[n] = {"kind": "build", "queue": specs, "total": len(specs), "done": 0,
                            "start": explicit or trace_start, "label": label, "placed": [], "blocked": [],
                            "at": self.location[n], "aim": aim}
            if bad:
                self.inbox[n].append("Didn't understand: " + "; ".join(bad[:3]))
            if cut:
                self.inbox[n].append(f"That was more than {self.cfg.max_queue} dominoes in one go; the last {cut} "
                                     "were left out. Ask for them again when this batch is done.")
            if trace_k is not None:
                self.task[n]["trace_k"] = trace_k
            if pending:
                self.task[n]["pending"] = pending
                self.task[n]["label"] = "; ".join(notes)
            if not specs and not pending:
                self.task[n] = None
                self.wake[n].append("your build had nothing to place")
        elif d.do in ("take_down", "inspect"):
            loc = self.world.regions[self.location[n]]
            area = d.area if d.area and len(d.area) == 4 else [loc.x0, loc.y0, loc.x1, loc.y1]
            x0, y0, x1, y1 = (float(v) for v in area)
            area = [max(min(x0, x1), loc.x0), max(min(y0, y1), loc.y0),
                    min(max(x0, x1), loc.x1), min(max(y0, y1), loc.y1)]
            if d.do == "take_down":
                self.task[n] = {"kind": "take_down", "area": area, "removed": 0}
            else:
                self.task[n] = {"kind": "inspect", "area": area, "ends": self.t + self.cfg.inspect_seconds}

    def _work(self, spoke: set, rec: dict, sketched: set = frozenset()) -> dict:
        cfg = self.cfg
        placed_at = {}
        for n, task in list(self.task.items()):
            if not task:
                continue
            if task["kind"] == "build" and task.get("pending") and not task["queue"]:
                pend = task["pending"]       # waiting for the run to reach where this stroke begins
                bx, by = pend["begin"]
                if any(x.state == "up" for x in self.world.near(bx, by, 1.4)):
                    pts, note = trace_specs(self.world, pend["pts"], self.rng, pend["room"],
                                            drift=self.cfg.freehand_sigma * 0.5 * pend["err"], taken=self._taken)
                    task["queue"] = [("place", sp) for sp in pts]
                    task["total"] += len(pts)
                    task["label"] = f"{note} (stroke {pend['k']})"
                    more = pend.get("more") or []
                    task["pending"] = ({**pend, "pts": more[0], "begin": more[0][0], "more": more[1:]}
                                       if more else None)
                    self.inbox[n].append(f"The run has reached the start of stroke {pend['k']}, so you carry it on.")
                else:
                    continue
            if task["kind"] == "build":
                skill = cfg.skills.get(n, {})
                rate = (cfg.beat / cfg.seconds_per_domino * skill.get("speed", 1.0)
                        * (cfg.talk_slowdown if n in spoke else 1.0))
                if n in sketched:
                    rate = 0.0                   # hands are on the pad this beat
                self.credit[n] += rate
                k = int(self.credit[n])
                self.credit[n] -= k
                batch, task["queue"] = task["queue"][:k], task["queue"][k:]
                pts, new, restood = [], [], []
                for op in batch:
                    kind, item = op[0], op[1]
                    if kind == "remove":
                        d0 = self.world.dominoes.get(item)
                        if d0 is not None:
                            self.world.remove([item], self.pool_for_region(d0.region))
                        continue
                    if kind == "move":
                        moved = self.world.move(item, *op[2], self.rng, err=skill.get("error", 1.0))
                        if moved:
                            restood.append(moved)
                        continue
                    if kind == "restand":
                        restood += self.world.restand([item], self.rng, err=skill.get("error", 1.0))
                    else:
                        start_idx = 0 if task["start"] and not task["placed"] and not new else None

                        res = self.world.place([item], n, rec["turn"], self.location[n], self.pools_for(n),
                                               self.rng, max_n=1, start_index=start_idx,
                                               err=skill.get("error", 1.0))
                        new += res.placed
                        task["blocked"] += res.blocked
                        if task.get("trace_k") is not None:
                            self.traced.setdefault(task["trace_k"], set()).update(x.id for x in res.placed)
                task["done"] += len(batch)
                task["placed"] += [d.id for d in new]
                pts = [(d.x, d.y) for d in new + restood]
                if pts:
                    task["last"] = pts[-1]
                    placed_at[n] = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
                if new or restood:
                    rec["events"].append({"type": "build", "who": n, "placed": [d.id for d in new],
                                          "restood": [[d.id, d.builder] for d in restood],
                                          "start": any(d.start for d in new)})
                if not task["queue"]:
                    self._finish_build(n, task)
            elif task["kind"] == "take_down":
                x0, y0, x1, y1 = task["area"]
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                inside = sorted((d for d in self.world.dominoes.values()
                                 if x0 <= d.x <= x1 and y0 <= d.y <= y1),
                                key=lambda d: (d.x - cx) ** 2 + (d.y - cy) ** 2)
                room = min(cfg.take_down_per_beat, cfg.take_down_max - task["removed"])
                chosen = inside[:room]
                whose: dict = {}
                for d in chosen:
                    whose[d.builder] = whose.get(d.builder, 0) + 1
                    self.world.remove([d.id], self.pool_for_region(d.region))
                task["removed"] += len(chosen)
                if chosen:
                    rec["events"].append({"type": "take_down", "who": n, "ids": [d.id for d in chosen],
                                          "whose": whose, "area": task["area"]})
                    for owner, k in whose.items():
                        if owner != n and owner in self.by_name:
                            self.inbox[owner].append(f"[{clock(self.t)}] {n} took down {k} of your dominoes "
                                                     f"around {where(cx, cy)}.")
                            if self.location[owner] == self.location[n]:
                                self.wake[owner].append(f"{n} is taking down your dominoes")
                if len(inside) <= room or task["removed"] >= cfg.take_down_max:
                    left = max(0, len(inside) - room)
                    self.inbox[n].append(f"Done taking down: {task['removed']} removed from {task['area']}"
                                         + (f"; {left} still there." if left else "."))
                    self.wake[n].append("you finished taking down")
                    self.task[n] = None
            elif task["kind"] == "inspect" and self.t + cfg.beat >= task["ends"]:
                report = eye_inspect(self.world, task["area"])
                self.inbox[n].append(report)
                self.wake[n].append("your inspection finished")
                rec["events"].append({"type": "inspect", "who": n, "area": task["area"]})
                self.task[n] = None
        return placed_at

    def _finish_build(self, n: str, task: dict):
        if task.get("pending"):                       # more of this stroke to come once the run arrives
            return
        if task.get("trace_k") is not None and not task.get("rejoined"):
            task["rejoined"] = True                   # lines that grew from a re-laid stroke get fed again
            mine = [self.world.dominoes[i] for i in task["placed"] if i in self.world.dominoes]
            for x in mine:
                for b in self.world.near(x.x, x.y, 1.2):
                    if b.id in task["placed"] or b.state != "up" or b.start:
                        continue
                    ops = begin_join(self.world, b, set(task["placed"]), max_n=6)
                    if ops:
                        task["queue"] = ops
                        task["total"] += len(ops)
                        return
        if self.cfg.snap and not task.get("begun") and task["placed"]:
            task["begun"] = True
            first = self.world.dominoes.get(task["placed"][0])
            ops = begin_join(self.world, first, set(task["placed"]))
            if ops:                                  # bring the run into this line's beginning
                task["queue"] = ops
                task["total"] += len(ops)
                return
        if self.cfg.snap and not task.get("joined") and task["placed"]:
            task["joined"] = True
            last = self.world.dominoes.get(task["placed"][-1])
            ops = end_join(self.world, last, set(task["placed"]))
            if ops:                                  # close the little gap into the next line
                task["queue"] = ops
                task["total"] += len(ops)
                return
        ids = task["placed"]
        doms = [self.world.dominoes[i] for i in ids if i in self.world.dominoes]
        msg = f"Finished building ({task['label']}): placed {len(ids)}."
        if doms:
            first, last = doms[0], doms[-1]
            msg += (f" They run from about {where(first.x, first.y)} to about {where(last.x, last.y)}, "
                    f"ending facing {direction(last.angle)}.")
            if any(d.start for d in doms):
                msg += " The first one is the start domino."
        if task["blocked"]:
            msg += " Some wouldn't fit: " + "; ".join(f"near {where(x, y)} ({why})" for x, y, why in task["blocked"][:5])
        self.inbox[n].append(msg)
        self.wake[n].append("you finished what you were building")
        self.task[n] = None

    def _bumps(self, placed_at: dict, rec: dict):
        p = self.world.phys
        chance = p.bump_chance * self.cfg.beat / 120.0
        for i, (xi, yi) in placed_at.items():
            for j, (xj, yj) in placed_at.items():
                if j == i or math.hypot(xi - xj, yi - yj) > p.bump_radius or self.rng.random() >= chance:
                    continue
                cand = [d for d in self.world.near(xi, yi, p.bump_reach) if d.state == "up"]
                if not cand:
                    continue
                times = self.world.topple([self.rng.choice(cand).id], cause="bump")
                whose: dict = {}
                for k in times:
                    b = self.world.dominoes[k].builder
                    whose[b] = whose.get(b, 0) + 1
                rec["events"].append({"type": "bump", "who": i, "near": j, "at": [round(xi, 1), round(yi, 1)],
                                      "knocked": len(times), "whose": whose})
                for m in self.by_name:
                    if self.location[m] == self.location[i]:
                        who = "You" if m == i else i
                        self.inbox[m].append(f"[{clock(self.t)}] {who} bumped the table while working next to {j}: "
                                             f"{len(times)} dominoes fell near ({xi:.0f}, {yi:.0f}).")
                        if m in whose or m == i:
                            self.wake[m].append("a bump knocked over dominoes")

    # ---- whole round ------------------------------------------------------------
    def run(self, progress=None) -> dict:
        while self.t < self.cfg.duration:
            self.step()
            if progress:
                progress(self)
        return self.push()

    def push(self) -> dict:
        out, self.pushed_world = push_world(self.world, self.start_region, self.cfg.time_limit,
                                            self.cfg.reveal_threshold)
        self.log["push"] = out
        return out

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.log, f)
