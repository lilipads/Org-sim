"""The oracle (PERF_REVIEW_STUDY.md §4): who actually contributed, computed from the full log.

Position-neutral by construction. Credit depends on what a person did to their own stretch of the run,
never on how far from the start it sits.

* sound work   - a person's on-plan dominoes that fall when the run is fed past every break that
                 *someone else* owns (their own breaks are not bridged)
* fixes        - breaks closed by a person, by a local test: push from the domino just upstream of the
                 gap, on the table just before and just after; it failed to cross before and crosses
                 after, and still crosses at the push
* open breaks  - breaks left at the push, owned by the last person to touch the gap (the later of the
                 two dominoes across it, or whoever bumped the table if the gap is a knocked domino)
* destruction  - someone else's sound dominoes a person lifted, where nothing sound stands at the push
* planning     - share of the built plan strokes a person drew

    python3 -m orgsim.oracle results/<game folder>
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys

from .dominoes import Domino, Physics, World, Region
from .render import sketch_points
from .sketch_record import final_strokes

GAP_REACH = 2.0      # a standing domino this close ahead of a dead end counts as "the run should continue here"
SIDE_REACH = 1.0
PLAN_DIST = 2.5      # within this of a plan stroke is on the plan (tracing rounds off sharp corners)
FIX_W = 10           # dominoes per fix / per open break (about 30 s of laying); sensitivity uses 5 and 20


# ---- worlds ---------------------------------------------------------------

def world_from_rows(rows: list, w: float = 30, h: float = 20) -> World:
    world = World([Region("table", 0, 0, w, h)], {"table": 0}, Physics())
    for r in rows:
        d = Domino(int(r[0]), float(r[1]), float(r[2]), float(r[3]), r[5], 0, "table")
        d.state = r[4]
        d.start = bool(r[6]) if len(r) > 6 else False
        world.dominoes[d.id] = d
        world._index(d)
    world._next = max(world.dominoes, default=0) + 1
    return world


def _plan_points(strokes: list) -> list:
    pts = []
    for s in strokes:
        if s.get("type") == "label":
            continue
        p = sketch_points(s)
        for i in range(len(p) - 1):          # densify to ~0.25 units
            (x0, y0), (x1, y1) = p[i], p[i + 1]
            n = max(1, int(math.dist(p[i], p[i + 1]) / 0.25))
            pts += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
        if p:
            pts.append(tuple(p[-1]))
    return pts


def on_plan(world: World, plan_pts: list) -> set:
    if not plan_pts:
        return {i for i, d in world.dominoes.items()}
    return {i for i, d in world.dominoes.items()
            if any((d.x - px) ** 2 + (d.y - py) ** 2 <= PLAN_DIST ** 2 for px, py in plan_pts)}


# ---- breaks ---------------------------------------------------------------

def _ahead(world: World, d: Domino, fall_dir: float, pool: set) -> Domino | None:
    """The nearest standing on-plan domino ahead of a fallen domino, within reach of a short gap."""
    r = math.radians(fall_dir)
    ux, uy = math.cos(r), math.sin(r)
    best, bd = None, 1e9
    for b in world.near(d.x, d.y, GAP_REACH + 0.5):
        if b.id == d.id or b.state != "up" or b.id not in pool:
            continue
        dx, dy = b.x - d.x, b.y - d.y
        ahead = dx * ux + dy * uy
        side = abs(-dx * uy + dy * ux)
        if 0 < ahead <= GAP_REACH and side <= SIDE_REACH:
            dist = math.hypot(dx, dy)
            if dist < bd:
                best, bd = b, dist
    return best


def owner_of_gap(base: World, a_id: int, b_id: int, bumps: list) -> str:
    """Who owns a gap. If it's a knocked-over domino nobody re-stood, whoever bumped the table. Otherwise
    whoever laid most of the dominoes around it (within 1.5 units), so a helper who drops one domino into
    someone else's gap doesn't inherit it. Ties go to whoever placed theirs first."""
    a, b = base.dominoes[a_id], base.dominoes[b_id]
    mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
    near = base.near(mx, my, 1.5)
    for d in near:
        if d.state == "down" and d.id not in (a_id, b_id):
            for bump in reversed(bumps):
                if d.id in bump.get("ids", []):
                    return bump["who"]
    counts: dict = {}
    first: dict = {}
    for d in near:
        if d.state != "up":
            continue
        counts[d.builder] = counts.get(d.builder, 0) + 1
        first[d.builder] = min(first.get(d.builder, d.id), d.id)
    if not counts:
        return base.dominoes[min(a_id, b_id)].builder
    return max(counts, key=lambda n: (counts[n], -first[n]))


def fed_fall(base: World, plan: set, bumps: list, skip_owner: str | None = None) -> tuple:
    """Push the start, then keep feeding the run across every gap (except gaps owned by `skip_owner`).
    Returns (fallen ids, [breaks as dicts])."""
    w = copy.deepcopy(base)
    starts = [d.id for d in w.dominoes.values() if d.start and d.state == "up"]
    if not starts:
        return set(), []
    fallen = set(w.topple(starts[:1]))
    breaks = []
    claimed: set = set()                    # stranded pieces already counted: one break per piece
    frontier = list(fallen)
    while frontier:
        new_targets = []
        for i in frontier:
            d = w.dominoes[i]
            nxt = _ahead(w, d, d.angle, plan)      # d.angle is the way it fell
            if nxt is None or nxt.id in claimed:
                continue
            piece = set(copy.deepcopy(w).topple([nxt.id]))
            claimed |= piece
            if len(piece & plan) < 2:
                continue                            # a stray domino or two, not a stranded piece of the run
            owner = owner_of_gap(base, i, nxt.id, bumps)
            breaks.append({"from": i, "to": nxt.id, "owner": owner, "stranded": len(piece), "dir": d.angle,
                           "at": [round((d.x + nxt.x) / 2, 1), round((d.y + nxt.y) / 2, 1)]})
            if owner != skip_owner:
                new_targets.append(nxt.id)
        frontier = []
        for t in new_targets:
            if w.dominoes[t].state == "up":
                got = w.topple([t])
                fallen |= set(got)
                frontier += list(got)
    return fallen, breaks


def crosses(world: World, a_id: int, b_id: int, direction: float | None = None) -> bool:
    """Local test: pushing domino a (upstream of the gap) the way the run travels, does the fall reach b?"""
    if a_id not in world.dominoes or b_id not in world.dominoes:
        return False
    if world.dominoes[a_id].state != "up" or world.dominoes[b_id].state != "up":
        return False
    w = copy.deepcopy(world)
    if direction is not None:
        w.dominoes[a_id].angle = direction       # a standing domino falls whichever way it's pushed
    return b_id in w.topple([a_id])


# ---- the full calculation -------------------------------------------------

def compute(log: dict, weights=(FIX_W,)) -> dict:
    turns = log["turns"]
    names = [a["name"] for a in log["agents"]]
    plan_strokes = (log.get("scratchpad") or {}).get("final") or final_strokes((log.get("scratchpad") or {}).get("history") or [])
    plan_pts = _plan_points(plan_strokes)
    bumps = [dict(e, t=t["time"]) for t in turns for e in t["events"] if e["type"] == "bump"]
    final = world_from_rows(turns[-1]["snapshot"])
    plan = on_plan(final, plan_pts)

    # sound work and open breaks at the push
    _, open_breaks = fed_fall(final, plan, bumps)
    sound = {}
    for n in names:
        fell_n, _ = fed_fall(final, plan, bumps, skip_owner=n)
        sound[n] = sum(1 for i in fell_n if final.dominoes[i].builder == n and i in plan)
    breaks_owned = {n: sum(1 for b in open_breaks if b["owner"] == n) for n in names}

    # fixes: breaks present at one beat and crossed at the next, by a local test, still crossing at the push
    fixes = {n: 0 for n in names}
    fix_log = []
    prev = None
    for k, t in enumerate(turns):
        cur = world_from_rows(t["snapshot"])
        if prev is not None:
            plan_prev = on_plan(prev, plan_pts)
            _, brk = fed_fall(prev, plan_prev, bumps)
            builds = [e for e in t["events"] if e["type"] == "build"]
            for b in brk:
                if not crosses(cur, b["from"], b["to"], b["dir"]):
                    continue
                if not crosses(final, b["from"], b["to"], b["dir"]):
                    continue                       # undone before the push
                mx, my = b["at"]
                who, best = None, 1e9
                for e in builds:
                    for i in e.get("placed", []) + [r[0] for r in e.get("restood", [])]:
                        if i in cur.dominoes:
                            dd = math.hypot(cur.dominoes[i].x - mx, cur.dominoes[i].y - my)
                            if dd < best:
                                who, best = e["who"], dd
                if who in fixes and best <= 1.5:
                    fixes[who] += 1
                    fix_log.append({"clock": t["clock"], "who": who, "at": b["at"], "gap_owner": b["owner"]})
        prev = cur

    # destruction: someone else's dominoes lifted, sound at the time, where nothing sound stands at the push
    destroyed = {n: 0 for n in names}
    final_sound = set()
    for n in names:
        fell_n, _ = fed_fall(final, plan, bumps, skip_owner=n)
        final_sound |= {i for i in fell_n if final.dominoes[i].builder == n and i in plan}
    prev_rows = None
    for t in turns:
        lifts = [(e["who"], l) for e in t["events"] if e["type"] == "build" for l in e.get("lifted", [])]
        if lifts and prev_rows is not None:
            w0 = world_from_rows(prev_rows)
            p0 = on_plan(w0, plan_pts)
            sound0 = set()
            owners = {l[1] for _, l in lifts}
            for o in owners:
                f0, _ = fed_fall(w0, p0, bumps, skip_owner=o)
                sound0 |= {i for i in f0 if w0.dominoes[i].builder == o}
            for who, (did, owner) in lifts:
                if owner == who or did not in sound0 or who not in destroyed:
                    continue
                d0 = w0.dominoes[did]
                if not any(i in final_sound for i in [x.id for x in final.near(d0.x, d0.y, 0.6)]):
                    destroyed[who] += 1
        prev_rows = t["snapshot"]

    # planning: share of the built plan strokes each person drew
    drawn = []
    for h in (log.get("scratchpad") or {}).get("history") or []:
        if h.get("cleared"):
            drawn = []
        drawn = (drawn + [(h["who"], s) for s in h.get("strokes") or []])[-60:]
    built_by = {n: 0 for n in names}
    built_total = 0
    for who, s in drawn:
        if s.get("type") == "label":
            continue
        pts = sketch_points(s)
        if not pts:
            continue
        cover = sum(1 for (x, y) in pts if any(final.dominoes[i].state == "up" for i in
                                               [d.id for d in final.near(x, y, 0.8)]))
        if cover / len(pts) >= 0.5:
            built_total += 1
            if who in built_by:
                built_by[who] += 1
    planning = {n: round(built_by[n] / built_total, 2) if built_total else 0.0 for n in names}

    out = {"people": {}, "open_breaks": open_breaks, "fixes": fix_log, "weights": {}}
    for n in names:
        out["people"][n] = {"sound_work": sound[n], "fixes": fixes[n], "open_breaks_owned": breaks_owned[n],
                            "destroyed": destroyed[n], "planning": planning[n]}
    for wgt in sorted(set(weights) | {5, FIX_W, 20}):
        out["weights"][str(wgt)] = {n: sound[n] + wgt * fixes[n] - wgt * breaks_owned[n] - destroyed[n]
                                    for n in names}
    out["contribution"] = out["weights"][str(FIX_W)]
    # planning counted in: drawing the whole plan is worth one average person's share of the sound work
    avg = sum(sound.values()) / max(1, len(names))
    out["with_planning"] = {n: round(out["contribution"][n] + planning[n] * avg, 1) for n in names}
    return out


if __name__ == "__main__":
    for folder in sys.argv[1:]:
        log = json.load(open(os.path.join(folder, "log.json")))
        res = compute(log)
        json.dump(res, open(os.path.join(folder, "oracle.json"), "w"), indent=1)
        print(folder)
        for n, p in res["people"].items():
            print(f"  {n:6} contribution {res['contribution'][n]:4} (with planning {res['with_planning'][n]:5})  {p}")
        print(f"  open breaks: {[(b['owner'], b['at']) for b in res['open_breaks']]}")
