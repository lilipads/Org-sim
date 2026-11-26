"""Turn loop for Domino Art (see DESIGN.md §4.5–4.6).

Every turn all agents decide at once. Then:
  1. conversations form; anyone addressed is pulled in and loses their action;
     each conversation gets up to `exchanges` rounds of messages;
  2. take-downs, then builds (placement error, bumps), inspections, visits;
  3. notices and logs.
After the last turn, the start domino is pushed.
"""
from __future__ import annotations

import json
import math
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field

from .dominoes import Physics, Region, World, expand_stroke
from .render import ascii_map

ACTIONS = ("talk", "listen", "build", "take_down", "inspect", "visit", "wait")


@dataclass
class Action:
    kind: str = "wait"
    to: object = "everyone"          # talk: "everyone" or [names]
    message: str = ""
    strokes: list = field(default_factory=list)   # build
    restand: list | None = None      # build: [x0, y0, x1, y1] area to stand knocked dominoes back up
    start: bool = False              # build: first new domino becomes the start
    area: list | None = None         # take_down / inspect: [x0, y0, x1, y1]
    where: str | None = None         # visit: region name
    at: str | None = None            # any action: walk to this region first (free), then act there
    notes: str | None = None         # agent's private notes, replacing the old ones

    def brief(self) -> dict:
        d = {k: v for k, v in asdict(self).items() if v not in (None, "", [], False)}
        d.pop("notes", None)
        return d


class Agent:
    """Base class. Subclasses: scripted (tests, calibration), LLM (experiments)."""

    def __init__(self, name: str, home: str, persona: str = ""):
        self.name, self.home, self.persona = name, home, persona

    def decide(self, obs: dict) -> Action:  # pragma: no cover - interface
        raise NotImplementedError

    def reply(self, obs: dict, transcript: list) -> str | None:
        return None


@dataclass
class GameConfig:
    round_no: int = 1
    turns: int = 10
    minutes_per_turn: int = 2
    max_build: int = 8
    max_take_down: int = 12
    exchanges: int = 2
    talk_mode: str = "addressed"     # addressed | strict
    time_limit: float | None = None  # round 2: seconds for the row to fall
    reveal_threshold: float = 0.5    # a picture counts as revealed if this share of it falls in time
    shared_pool: str | None = None   # round 2: name of the shared supply pool
    rules_text: str = ""
    eval_text: str = ""
    seed: int = 0


class Game:
    def __init__(self, world: World, agents: list, cfg: GameConfig, start_region: str | None = None):
        self.world, self.agents, self.cfg = world, agents, cfg
        self.by_name = {a.name: a for a in agents}
        self.rng = random.Random(cfg.seed)
        self.location = {a.name: a.home for a in agents}
        self.notes = {a.name: "" for a in agents}
        self.heard = {a.name: [] for a in agents}
        self.notices = {a.name: [] for a in agents}
        self.last_result = {a.name: "" for a in agents}
        self.last_data = {a.name: {} for a in agents}
        self.start_region = start_region
        self.log: dict = {"config": asdict(cfg), "regions": [asdict(r) for r in world.regions.values()],
                          "agents": [{"name": a.name, "home": a.home, "persona": a.persona} for a in agents],
                          "initial": world.snapshot(), "turns": []}

    # ---- pools -----------------------------------------------------------
    def pool_for_region(self, region: str) -> str:
        r = self.world.regions[region]
        return region if r.kind == "table" else (self.cfg.shared_pool or region)

    def pools_for(self, name: str) -> list:
        pools = [self.by_name[name].home]
        if self.cfg.shared_pool:
            pools.append(self.cfg.shared_pool)
        return pools

    # ---- observation -----------------------------------------------------
    def observe(self, a: Agent, turn: int) -> dict:
        loc = self.world.regions[self.location[a.name]]
        others = [o.name for o in self.agents if o.name != a.name and self.location[o.name] == loc.name]
        obs = {
            "name": a.name, "persona": a.persona, "rules": self.cfg.rules_text,
            "evaluation": self.cfg.eval_text, "round": self.cfg.round_no,
            "turn": turn, "turns_total": self.cfg.turns, "turns_left": self.cfg.turns - turn + 1,
            "minutes_left": (self.cfg.turns - turn + 1) * self.cfg.minutes_per_turn,
            "home": a.home, "location": loc.name, "people_here": others,
            "supply": {p: self.world.supply.get(p, 0) for p in self.pools_for(a.name)},
            "map": ascii_map(self.world, loc.x0, loc.y0, loc.x1, loc.y1),
            "region_bounds": [loc.x0, loc.y0, loc.x1, loc.y1],
            "heard": self.heard[a.name], "notices": self.notices[a.name],
            "last_result": self.last_result[a.name], "last_data": self.last_data[a.name],
            "notes": self.notes[a.name],
        }
        if len(self.world.regions) > 1:
            obs["room_overview"] = ascii_map(self.world, 0, 0, self.world.width, self.world.height, step=3.0)
            obs["regions"] = {r.name: [r.x0, r.y0, r.x1, r.y1, r.kind] for r in self.world.regions.values()}
        return obs

    # ---- one turn ----------------------------------------------------------
    def _parallel(self, fn, items):
        with ThreadPoolExecutor(max_workers=min(16, max(1, len(items)))) as ex:
            return list(ex.map(fn, items))

    def step(self, turn: int) -> dict:
        obs = {a.name: self.observe(a, turn) for a in self.agents}

        def decide(a):
            try:
                act = a.decide(obs[a.name])
            except Exception as e:  # an agent failing must not stop the game
                act = Action("wait", notes=None)
                act.message = f"[error: {e}]"
            return act if act.kind in ACTIONS else Action("wait")

        acts = dict(zip([a.name for a in self.agents], self._parallel(decide, self.agents)))
        for n, act in acts.items():
            if act.notes is not None:
                self.notes[n] = act.notes[:2000]
        rec = {"turn": turn, "decisions": {n: act.brief() for n, act in acts.items()},
               "conversations": [], "events": []}
        # walking is quick: move first, then act where you are
        for n, act in acts.items():
            dest = act.where if act.kind == "visit" else act.at
            if dest and dest in self.world.regions and dest != self.location[n]:
                self.location[n] = dest
                rec["events"].append({"type": "move", "who": n, "where": dest})
        heard = {n: [] for n in acts}
        notices = {n: [] for n in acts}
        result = {n: "" for n in acts}
        data = {n: {} for n in acts}

        # 1. conversations
        groups, pulled = self._groups(acts, result)
        busy = set()
        for g in groups:
            members = sorted(g)
            busy |= g
            speakers = [m for m in members if acts[m].kind == "talk" and acts[m].message]
            self.rng.shuffle(speakers)
            transcript = [{"speaker": s, "to": acts[s].to, "message": acts[s].message[:1500]} for s in speakers]
            if self.cfg.exchanges >= 2 and transcript:
                snap = list(transcript)
                replies = self._parallel(
                    lambda m: (m, self._safe_reply(m, obs[m], snap)), members)
                self.rng.shuffle(replies)
                for m, msg in replies:
                    if msg:
                        transcript.append({"speaker": m, "to": "group", "message": msg[:1500]})
            for m in members:
                heard[m].append({"with": members, "messages": transcript})
                if m in pulled:
                    result[m] = f"You were pulled into a conversation, so your {acts[m].kind} did not happen."
                elif not result[m]:
                    result[m] = "You spent the turn in a conversation."
            rec["conversations"].append({"members": members, "pulled_in": sorted(g & pulled),
                                         "location": self.location[members[0]], "messages": transcript})
            here = [n for n in acts if n not in g and self.location[n] == self.location[members[0]]]
            for n in here:
                notices[n].append(f"{', '.join(members)} were talking.")

        # 2. physical actions, for those not in a conversation
        free = {n: act for n, act in acts.items() if n not in busy}
        for n, act in free.items():
            if act.kind == "take_down":
                self._take_down(n, act, result, rec, notices)
        work = {}
        for n, act in free.items():
            if act.kind == "build":
                c = self._build(n, act, turn, result, data, rec)
                if c:
                    work[n] = c
        self._bumps(work, rec, notices, result)
        for n, act in free.items():
            if act.kind == "inspect":
                self._inspect(n, act, result, data, rec)
            elif act.kind == "visit":
                if act.where in self.world.regions:
                    r = self.world.regions[act.where]
                    result[n] = (f"You went to {act.where} and looked closely:\n"
                                 + ascii_map(self.world, r.x0, r.y0, r.x1, r.y1))
                    rec["events"].append({"type": "visit", "who": n, "where": act.where})
                else:
                    result[n] = f"There is no place called {act.where!r}."
            elif act.kind == "listen":
                result[n] = result[n] or "You listened, but nobody at the table was talking to everyone."
            elif act.kind == "wait":
                result[n] = "You waited."
            elif act.kind == "talk" and not result[n]:
                result[n] = result[n] or "Nobody you addressed was here."

        self.heard, self.notices, self.last_result, self.last_data = heard, notices, result, data
        rec["results"] = result
        rec["notes"] = dict(self.notes)
        rec["supply"] = dict(self.world.supply)
        rec["locations"] = dict(self.location)
        rec["snapshot"] = self.world.snapshot()
        self.log["turns"].append(rec)
        return rec

    def _safe_reply(self, name, obs, transcript):
        try:
            return self.by_name[name].reply(obs, transcript)
        except Exception:
            return None

    def _groups(self, acts: dict, result: dict) -> tuple:
        parent: dict = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            parent[find(a)] = find(b)

        talkers = [n for n, a in acts.items() if a.kind == "talk" and a.message]
        strict = self.cfg.talk_mode == "strict"
        for n, a in acts.items():
            loc = self.location[n]
            if a.kind == "listen":
                union(n, f"ALL@{loc}")
            if a.kind != "talk" or not a.message:
                continue
            if strict or a.to in ("everyone", None, "", "all") or a.to == ["everyone"]:
                union(n, f"ALL@{loc}")
                if strict:
                    for m in acts:
                        if self.location[m] == loc:
                            union(m, f"ALL@{loc}")
            else:
                names = [a.to] if isinstance(a.to, str) else list(a.to)
                missing = []
                for m in names:
                    if m in acts and m != n and self.location[m] == loc:
                        union(n, m)
                    elif m != n:
                        missing.append(m)
                union(n, n)
                if missing:
                    result[n] = f"Not here, so they didn't hear you: {', '.join(map(str, missing))}."
        comps: dict = {}
        for n in acts:
            if n in parent:
                comps.setdefault(find(n), set()).add(n)
        groups = [g for g in comps.values() if any(m in talkers for m in g)]
        pulled = {m for g in groups for m in g if acts[m].kind not in ("talk", "listen")}
        return groups, pulled

    def _area(self, name: str, area) -> tuple:
        loc = self.world.regions[self.location[name]]
        if not area or len(area) != 4:
            return loc.x0, loc.y0, loc.x1, loc.y1
        x0, y0, x1, y1 = (float(v) for v in area)
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        return max(x0, loc.x0), max(y0, loc.y0), min(x1, loc.x1), min(y1, loc.y1)

    def _take_down(self, n, act, result, rec, notices):
        x0, y0, x1, y1 = self._area(n, act.area)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        inside = [d for d in self.world.dominoes.values() if x0 <= d.x <= x1 and y0 <= d.y <= y1]
        inside.sort(key=lambda d: (d.x - cx) ** 2 + (d.y - cy) ** 2)
        chosen = inside[: self.cfg.max_take_down]
        whose: dict = {}
        for d in chosen:
            whose[d.builder] = whose.get(d.builder, 0) + 1
        removed = []
        for d in chosen:
            removed += self.world.remove([d.id], self.pool_for_region(d.region))
        result[n] = (f"You took down {len(removed)} dominoes in [{x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f}]"
                     + (f" ({len(inside) - len(removed)} more are still there)." if len(inside) > len(removed) else "."))
        rec["events"].append({"type": "take_down", "who": n, "area": [x0, y0, x1, y1],
                              "ids": [d.id for d in removed], "whose": whose})
        for m in self.by_name:
            if m != n and self.location[m] == self.location[n] and removed:
                notices[m].append(f"{n} took down {len(removed)} dominoes around ({cx:.0f}, {cy:.0f}).")

    def _build(self, n, act, turn, result, data, rec):
        loc = self.location[n]
        budget = self.cfg.max_build
        restood = []
        if act.restand:
            x0, y0, x1, y1 = self._area(n, act.restand)
            down = [d.id for d in self.world.dominoes.values()
                    if d.state == "down" and x0 <= d.x <= x1 and y0 <= d.y <= y1][:budget]
            restood = self.world.restand(down, self.rng)
            budget -= len(restood)
        specs = []
        bad = []
        for s in act.strokes or []:
            try:
                specs += expand_stroke(s)
            except Exception as e:
                bad.append(f"{s!r}: {e}")
        res = self.world.place(specs, n, turn, loc, self.pools_for(n), self.rng, max_n=max(0, budget),
                               start_index=0 if act.start and specs else None)
        if budget <= 0 and specs:
            res.truncated = len(specs)
        msg = [f"You placed {len(res.placed)} dominoes" + (f" and stood {len(restood)} back up" if restood else "") + "."]
        if res.placed:
            msg.append("New: " + ", ".join(f"#{d.id} ({d.x:.2f},{d.y:.2f}) {d.angle:.0f}°" for d in res.placed))
        if res.truncated:
            msg.append(f"{res.truncated} more were in your plan but you only have hands for {self.cfg.max_build} per turn.")
        if res.blocked:
            msg.append("Couldn't place: " + "; ".join(f"({x:.1f},{y:.1f}) {why}" for x, y, why in res.blocked[:6]))
        if bad:
            msg.append("Didn't understand: " + "; ".join(bad[:3]))
        if act.start and res.placed:
            msg.append(f"#{res.placed[0].id} is now the start domino.")
        result[n] = " ".join(msg)
        data[n] = {"placed": [d.id for d in res.placed], "restood": [d.id for d in restood],
                   "blocked": res.blocked, "truncated": res.truncated}
        rec["events"].append({"type": "build", "who": n, "placed": [d.id for d in res.placed],
                              "restood": [[d.id, d.builder] for d in restood],
                              "blocked": len(res.blocked), "truncated": res.truncated,
                              "start": bool(act.start and res.placed)})
        pts = [(d.x, d.y) for d in res.placed + restood] or [(x, y) for x, y, _ in specs[:1]]
        if not pts:
            return None
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

    def _bumps(self, work: dict, rec, notices, result):
        p = self.world.phys
        names = list(work)
        for i in names:
            xi, yi = work[i]
            for j in names:
                if j == i:
                    continue
                xj, yj = work[j]
                if math.hypot(xi - xj, yi - yj) > p.bump_radius:
                    continue
                if self.rng.random() >= p.bump_chance:
                    continue
                cand = [d for d in self.world.near(xi, yi, p.bump_reach) if d.state == "up"]
                if not cand:
                    continue
                victim = self.rng.choice(cand)
                times = self.world.topple([victim.id], cause="bump")
                whose: dict = {}
                for k in times:
                    b = self.world.dominoes[k].builder
                    whose[b] = whose.get(b, 0) + 1
                rec["events"].append({"type": "bump", "who": i, "near": j, "at": [round(xi, 1), round(yi, 1)],
                                      "knocked": len(times), "whose": whose})
                for m in self.by_name:
                    if self.location[m] == self.location[i]:
                        who = "You" if m == i else i
                        notices[m].append(f"{who} bumped the table while working next to {j}: "
                                          f"{len(times)} dominoes fell near ({xi:.0f}, {yi:.0f}).")

    def _inspect(self, n, act, result, data, rec):
        x0, y0, x1, y1 = self._area(n, act.area)
        rep = self.world.inspect(x0, y0, x1, y1)
        data[n] = rep
        lines = [f"Inspection of [{x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f}]: {rep['count']} dominoes, "
                 f"{rep['knocked_over']} knocked over, {rep['not_reached_from_start']} standing ones the start "
                 f"can't reach{'' if rep['has_start'] else ' (there is no start domino yet)'}."]
        if rep["line_ends"]:
            lines.append("Line ends (these knock nothing over): " + "; ".join(
                f"#{e['id']} at ({e['x']},{e['y']}) facing {e['angle']}°: {e['why']}" for e in rep["line_ends"]))
        lines.append("Dominoes [id, x, y, angle, state]: " + json.dumps(rep["dominoes"]))
        result[n] = "\n".join(lines)
        rec["events"].append({"type": "inspect", "who": n, "area": [x0, y0, x1, y1],
                              "line_ends": len(rep["line_ends"])})

    # ---- whole round ---------------------------------------------------------
    def run(self, progress=None) -> dict:
        for t in range(1, self.cfg.turns + 1):
            self.step(t)
            if progress:
                progress(t, self)
        return self.push()

    def push(self) -> dict:
        """Push the start domino on a copy of the world, so the standing picture
        survives (round-1 pictures carry into round 2). The toppled copy is kept
        in self.pushed_world for rendering."""
        import copy
        before = self.world.snapshot()
        w = self.pushed_world = copy.deepcopy(self.world)
        standing = {d.id for d in w.dominoes.values() if d.state == "up"}
        early = {d.id for d in w.dominoes.values() if d.state == "down"}
        regions = [r.name for r in w.regions.values() if r.kind == "table"]
        pushes = [self.start_region] if self.start_region else regions
        times: dict = {}
        for reg in pushes:
            starts = [d.id for d in w.dominoes.values() if d.start and d.region == reg and d.state == "up"]
            times.update(w.topple(starts[:1]))
        per_table = {}
        limit = self.cfg.time_limit
        for reg in regions:
            ids = {d.id for d in w.dominoes.values() if d.region == reg}
            st = ids & standing
            fell = [i for i in st if i in times]
            in_time = [i for i in fell if limit is None or times[i] <= limit]
            per_table[reg] = {"placed": len(ids), "standing_at_push": len(st), "fell": len(fell),
                              "fell_in_time": len(in_time), "early_down": len(ids & early),
                              "completion": round(len(in_time) / len(st), 3) if st else 0.0,
                              "revealed": bool(st) and len(in_time) / len(st) >= self.cfg.reveal_threshold}
        out = {"times": {str(k): round(v, 2) for k, v in times.items()},
               "duration": round(max(times.values()), 2) if times else 0.0,
               "per_table": per_table,
               "row_success": all(v["revealed"] for v in per_table.values()) if self.start_region else None,
               "before_push": before}
        self.log["push"] = out
        return out

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.log, f)


def table_world(name: str = "table", width: float = 60, height: float = 40, supply: int = 250,
                phys: Physics = Physics()) -> World:
    return World([Region(name, 0, 0, width, height)], {name: supply}, phys)


def gallery_world(round1: list, gap: float = 6.0, shared: int = 60, phys: Physics = Physics()) -> tuple:
    """Build the round-2 room from finished round-1 worlds (left to right).
    Returns (world, start_region). Round-1 dominoes are copied in, standing,
    with their builders, and keep their positions relative to their table."""
    regions, x = [], 0.0
    offsets = []
    for i, w in enumerate(round1):
        (r,) = [r for r in w.regions.values() if r.kind == "table"]
        regions.append(Region(r.name, x, 0, x + (r.x1 - r.x0), r.y1 - r.y0, "table"))
        offsets.append((r.name, x))
        x += r.x1 - r.x0
        if i < len(round1) - 1:
            regions.append(Region(f"gap {i + 1}-{i + 2}", x, 0, x + gap, r.y1 - r.y0, "gap"))
            x += gap
    supply = {r.name: w.supply.get(r.name, 0) for (r, w) in
              ((next(rr for rr in w.regions.values() if rr.kind == "table"), w) for w in round1)}
    supply["shared"] = shared
    world = World(regions, supply, phys)
    for (name, ox), w in zip(offsets, round1):
        for d in sorted(w.dominoes.values(), key=lambda d: d.id):
            ix, iy, ia = d.intended
            nd = world.dominoes.setdefault(world._next, type(d)(
                world._next, d.x + ox, d.y, d.angle, d.builder, d.turn, name, d.state, d.down_cause,
                d.start, (ix + ox, iy, ia)))
            world._index(nd)
            world._next += 1
    return world, offsets[0][0]
