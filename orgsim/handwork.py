"""Building and looking by hand and eye: no rulers at the table.

* Free-hand strokes (line, arc, domino at a coordinate): you can't measure, so
  the whole stroke lands about a third of a unit off where you aimed, and turned a
  few degrees. Within the stroke, spacing is steady.
* Anchored strokes (extend from a domino, connect one domino to another): your
  hands line the new domino up against a real one, so it's precise.
* Looking (inspect, pointing): positions are reported roughly (to half a unit),
  in words, with no domino numbers.
"""
from __future__ import annotations

import math
import random

from .dominoes import World, angle_diff, expand_stroke

FREEHAND_POS = 0.3       # units, std dev of where a free-hand stroke starts
FREEHAND_ROT = 4.0       # degrees, std dev of a free-hand stroke's rotation
SPACING = 0.55
MAX_STEER = 25.0         # degrees per domino when steering toward a target
BRANCH_SIDE, BRANCH_TURN = 0.25, 25.0

DIRS = ["right", "down-right", "down", "down-left", "left", "up-left", "up", "up-right"]


def direction(angle: float) -> str:
    return DIRS[int(round(angle / 45.0)) % 8]


def approx(v: float) -> float:
    return round(v * 2) / 2


def where(x: float, y: float) -> str:
    return f"({approx(x):g}, {approx(y):g})"


def area_words(world: World, x: float, y: float) -> str:
    """'the top-left of the table' etc."""
    r = world.region_at(x, y)
    if r is None:
        return "off the table"
    fx = (x - r.x0) / max(1e-9, r.x1 - r.x0)
    fy = (y - r.y0) / max(1e-9, r.y1 - r.y0)
    h = "left" if fx < 1 / 3 else ("right" if fx > 2 / 3 else "")
    v = "top" if fy < 1 / 3 else ("bottom" if fy > 2 / 3 else "")
    part = "-".join(p for p in (v, h) if p) or "middle"
    return f"the {part} of {'the table' if r.kind == 'table' else r.name}"


def nearest_up(world: World, x: float, y: float, radius: float = 1.5):
    cands = [d for d in world.near(x, y, radius) if d.state == "up"]
    return min(cands, key=lambda d: (d.x - x) ** 2 + (d.y - y) ** 2) if cands else None


def _has_pred(world: World, d) -> bool:
    return any(p.id != d.id and p.state == "up" and world.hit(p, d)[0] for p in world.near(d.x, d.y, 1.0))


def pick(world: World, x: float, y: float, prefer: str) -> object | None:
    """The domino someone means by pointing near (x, y): a line end (prefer="end")
    or a line beginning (prefer="begin") if one is close, else the nearest."""
    cands = [d for d in world.near(x, y, 1.5) if d.state == "up"]
    if not cands:
        return None
    if prefer == "end":
        pref = [d for d in cands if not world.successors(d)]
    else:
        pref = [d for d in cands if not _has_pred(world, d)]
    pool = pref or cands
    return min(pool, key=lambda d: (d.x - x) ** 2 + (d.y - y) ** 2)


def describe_spot(world: World, x: float, y: float) -> str:
    d = nearest_up(world, x, y, 1.2)
    if d is None:
        down = [k for k in world.near(x, y, 1.2) if k.state == "down"]
        return "a knocked-over domino" if down else "an empty spot"
    nxt = world.successors(d)
    prev = [p for p in world.near(d.x, d.y, 1.0) if p.id != d.id and p.state == "up" and world.hit(p, d)[0]]
    if d.start:
        return f"the start domino (facing {direction(d.angle)})"
    if not nxt and prev:
        return f"the end of a line (facing {direction(d.angle)})"
    if nxt and not prev:
        return f"the beginning of a line (facing {direction(d.angle)})"
    if not nxt and not prev:
        return f"a lone domino (facing {direction(d.angle)})"
    return f"the middle of a line (running {direction(d.angle)})"


# ---- strokes ------------------------------------------------------------------

def _step(world: World, x: float, y: float, h: float, tx: float, ty: float, pts: list,
          clearance: float, ignore: set, max_turn: float = MAX_STEER) -> tuple:
    """One domino toward (tx, ty): turn at most max_turn, avoid what's on the table."""
    want = math.degrees(math.atan2(ty - y, tx - x))
    base = max(-max_turn, min(max_turn, angle_diff(want, h)))
    for t in [base] + [t for t in (base + 12.5, base - 12.5, max_turn, -max_turn, 0.0) if abs(t) <= max_turn]:
        nh = (h + t) % 360
        nx, ny = x + SPACING * math.cos(math.radians(nh)), y + SPACING * math.sin(math.radians(nh))
        if any(d.id not in ignore for d in world.near(nx, ny, clearance)):
            continue
        if any((px - nx) ** 2 + (py - ny) ** 2 < clearance ** 2 for px, py, _ in pts[:-2]):
            continue
        return nx, ny, nh
    nh = (h + base) % 360
    return x + SPACING * math.cos(math.radians(nh)), y + SPACING * math.sin(math.radians(nh)), nh


def steer(world: World, x: float, y: float, h: float, waypoints: list, arrive: float = 0.6,
          max_steps: int = 120, clearance: float = 0.45, ignore: set = frozenset(),
          max_turn: float = MAX_STEER) -> list:
    """Lay a path by hand toward waypoints, steering around what's on the table."""
    pts = [(x, y, h % 360)]
    for wx, wy in waypoints:
        best, stall = 1e9, 0
        while math.hypot(wx - x, wy - y) > arrive and len(pts) <= max_steps and stall < 12:
            x, y, h = _step(world, x, y, h, wx, wy, pts, clearance, ignore, max_turn)
            pts.append((x, y, h))
            dist = math.hypot(wx - x, wy - y)
            stall = 0 if dist < best - 0.05 else stall + 1
            best = min(best, dist)
    return pts


def _bezier(p0, h0, p1, h1, k0, k1, n=300) -> list:
    c0 = (p0[0] + k0 * math.cos(math.radians(h0)), p0[1] + k0 * math.sin(math.radians(h0)))
    c1 = (p1[0] - k1 * math.cos(math.radians(h1)), p1[1] - k1 * math.sin(math.radians(h1)))
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
        out.append((a * p0[0] + b * c0[0] + c * c1[0] + d * p1[0], a * p0[1] + b * c0[1] + c * c1[1] + d * p1[1]))
    return out


def _resample(curve: list, spacing: float) -> list:
    pts, acc = [curve[0]], 0.0
    for (x0, y0), (x1, y1) in zip(curve, curve[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        acc += seg
        if acc >= spacing:
            pts.append((x1, y1))
            acc = 0.0
    if math.hypot(curve[-1][0] - pts[-1][0], curve[-1][1] - pts[-1][1]) > 0.2:
        pts.append(curve[-1])
    else:
        pts[-1] = curve[-1]
    return pts


def _with_headings(pts: list, h_end: float) -> list:
    out = []
    for i, (x, y) in enumerate(pts):
        if i + 1 < len(pts):
            h = math.degrees(math.atan2(pts[i + 1][1] - y, pts[i + 1][0] - x)) % 360
        else:
            h = h_end
        out.append((x, y, h))
    return out


def _cost(world: World, path: list, ignore: set, clearance: float = 0.42) -> float:
    """0 if the path is buildable: gentle turns, clear of other dominoes and itself."""
    bad = 0.0
    for (x0, y0, h0), (x1, y1, h1) in zip(path, path[1:]):
        turn = abs(angle_diff(h1, h0))
        if turn > 32:
            bad += 1 + (turn - 32) / 30
        gap = math.hypot(x1 - x0, y1 - y0)
        if gap > 0.85 or gap < 0.25:
            bad += 1
    for i, (x, y, _) in enumerate(path):
        if any(d.id not in ignore for d in world.near(x, y, clearance)):
            bad += 1
        for j in range(i + 3, len(path)):
            if (path[j][0] - x) ** 2 + (path[j][1] - y) ** 2 < clearance ** 2:
                bad += 1
                break
    return bad


def approach(world: World, x: float, y: float, h: float, b, max_steps: int = 160,
             extra_ignore: set = frozenset()) -> list:
    """Plan a smooth path by hand from pose (x, y, h) to squarely behind domino b,
    facing the way b falls, so the last new domino knocks b over. Tries several
    curve shapes (direct, wider, or round either side) and keeps the shortest
    buildable one."""
    rb = math.radians(b.angle)
    ux, uy = math.cos(rb), math.sin(rb)
    nx, ny = -uy, ux
    end = (b.x - SPACING * ux, b.y - SPACING * uy)
    ignore = {d.id for d in world.near(b.x, b.y, 0.8)} | {d.id for d in world.near(x, y, 0.7)} | set(extra_ignore)
    dist = math.hypot(end[0] - x, end[1] - y)
    cands = []
    for k in (0.35, 0.5, 0.7, 1.0, 1.4):
        L = max(1.5, k * dist)
        cands.append([_bezier((x, y), h, end, b.angle, L, L)])
    ex, ey = end
    for r in (2.0, 3.0, 4.5, 6.0):
        for off in range(-150, 151, 30):
            ang = b.angle + 180 + off                     # around the approach side of b
            v = (ex + r * math.cos(math.radians(ang)), ey + r * math.sin(math.radians(ang)))
            d1 = math.hypot(v[0] - x, v[1] - y)
            d2 = math.hypot(ex - v[0], ey - v[1])
            for hv in {round(math.degrees(math.atan2(ey - v[1], ex - v[0])) % 360), round(b.angle) % 360,
                       round(math.degrees(math.atan2(v[1] - y, v[0] - x)) % 360)}:
                for k in (0.5, 0.9):
                    c1 = _bezier((x, y), h, v, hv, max(1.5, k * d1), max(1.2, k * d1 / 2))
                    c2 = _bezier(v, hv, end, b.angle, max(1.2, k * d2), max(1.2, k * d2))
                    cands.append([c1, c2[1:]])
    best = None
    for parts in cands:
        curve = [p for part in parts for p in part]
        path = _with_headings(_resample(curve, SPACING), b.angle)
        path[0] = (x, y, h)
        if len(path) > max_steps:
            continue
        score = (_cost(world, path, ignore), len(path))
        if best is None or score < best[0]:
            best = (score, path)
    return best[1] if best else [(x, y, h)]


def _xy(v) -> tuple | None:
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        try:
            return float(v[0]), float(v[1])
        except (TypeError, ValueError):
            return None
    return None


def _start_pose(world: World, a, toward: tuple | None) -> tuple:
    """Pose of the first new domino after domino `a`: straight on if `a` is a line
    end, otherwise a branch off its side (toward the target if given)."""
    r = math.radians(a.angle)
    ux, uy = math.cos(r), math.sin(r)
    if not world.successors(a):
        return a.x + SPACING * ux, a.y + SPACING * uy, a.angle
    side = 1
    if toward:
        cross = ux * (toward[1] - a.y) - uy * (toward[0] - a.x)
        side = 1 if cross >= 0 else -1
    nx, ny = -uy, ux
    for sd in (side, -side):
        bx, by = a.x + 0.5 * ux + sd * BRANCH_SIDE * nx, a.y + 0.5 * uy + sd * BRANCH_SIDE * ny
        if not world.near(bx, by, world.phys.min_gap + 0.05):
            return bx, by, a.angle + sd * BRANCH_TURN
    return a.x + 0.5 * ux + side * BRANCH_SIDE * nx, a.y + 0.5 * uy + side * BRANCH_SIDE * ny, a.angle + side * BRANCH_TURN


def anchored_specs(world: World, s: dict, max_n: int) -> tuple:
    """extend: {"type":"extend","from":[x,y],"toward":[x,y],"count":n}
    connect: {"type":"connect","from":[x,y],"to":[x,y]}
    Returns (specs, note)."""
    src = _xy(s.get("from"))
    if not src:
        return [], "extend/connect needs \"from\": [x, y] near an existing domino"
    a = pick(world, *src, prefer="end")
    if a is None:
        return [], f"there's no standing domino near {where(*src)} to build from"
    if s["type"] == "extend":
        toward = _xy(s.get("toward"))
        count = int(s.get("count", 10) or 10)
        x, y, h = _start_pose(world, a, toward)
        if toward:
            pts = steer(world, x, y, h, [toward], arrive=0.6, max_steps=max_n)
        else:
            pts = [(x + k * SPACING * math.cos(math.radians(h)), y + k * SPACING * math.sin(math.radians(h)), h)
                   for k in range(count)]
        pts = pts[: min(count, max_n)]
        return pts, f"extending from {describe_spot(world, a.x, a.y)} near {where(a.x, a.y)}"
    # connect
    dst = _xy(s.get("to"))
    b = pick(world, *dst, prefer="begin") if dst else None
    if b is None:
        return [], "connect needs \"to\": [x, y] near the standing domino you want to reach"
    x, y, h = _start_pose(world, a, (b.x, b.y))
    dist = math.hypot(b.x - x, b.y - y)
    if dist < 0.9 and abs(angle_diff(b.angle, h)) <= 40:
        pts = [(x, y, h)]
    else:
        pts = approach(world, x, y, h, b, max_steps=max_n * 3)
    note = f"connecting {describe_spot(world, a.x, a.y)} near {where(a.x, a.y)} to {describe_spot(world, b.x, b.y)} near {where(b.x, b.y)}"
    if len(pts) > max_n:
        note += f" (it needs about {len(pts)} dominoes; you've got hands for {max_n} in one go)"
    return pts[:max_n], note


def _nudge(world: World, d, b) -> tuple | None:
    """A small move/turn of domino b so that d knocks it over and b still knocks
    over what it fed before (or, if it fed nothing, anything ahead of it)."""
    feeds = [c for c in world.near(b.x, b.y, 1.2) if c.id not in (b.id, d.id) and c.state == "up" and world.hit(b, c)[0]]
    for k in (0.55, 0.5, 0.65, 0.45, 0.75):
        for da in (0, -10, 10, -20, 20, -30, 30):
            ang = (d.angle + da) % 360
            x = d.x + k * math.cos(math.radians(ang))
            y = d.y + k * math.sin(math.radians(ang))
            if math.hypot(x - b.x, y - b.y) > 0.6:          # a nudge, not a rebuild
                continue
            if any(o.id not in (b.id,) and (o.x - x) ** 2 + (o.y - y) ** 2 < world.phys.min_gap ** 2
                   for o in world.near(x, y, world.phys.min_gap)):
                continue
            for ba in sorted({(b.angle + t) % 360 for t in (0, -10, 10, -20, 20, -30, 30)} |
                             {(d.angle + t) % 360 for t in (0, -15, 15, -30, 30)},
                             key=lambda a: abs(angle_diff(a, b.angle))):
                probe = type(b)(b.id, x, y, ba, b.builder, b.turn, b.region)
                if not world.hit(d, probe)[0]:
                    continue
                if feeds and not any(world.hit(probe, c)[0] for c in feeds):
                    continue
                return x, y, ba
    return None


def fix_specs(world: World, s: dict, max_n: int) -> tuple:
    """fix: {"type":"fix","at":[x,y]}: close the break nearest a spot, the way hands
    do it: first try nudging the next domino into line; if that can't work, bridge
    from the line end to the piece it was heading for.
    Returns (ops, note); ops are ("move", id, (x, y, a)) or ("place", (x, y, a))."""
    at = _xy(s.get("at"))
    if not at:
        return [], "fix needs \"at\": [x, y] near the break"
    ends = [d for d in world.near(at[0], at[1], 2.0) if d.state == "up" and not world.successors(d)]
    if not ends:
        return [], f"you don't see a broken spot near {where(*at)}"
    ends.sort(key=lambda d: (d.x - at[0]) ** 2 + (d.y - at[1]) ** 2)
    for d in ends:                       # 1. nudge
        r = math.radians(d.angle)
        ahead = sorted((b for b in world.near(d.x, d.y, 1.3) if b.id != d.id and b.state == "up"
                        and (b.x - d.x) * math.cos(r) + (b.y - d.y) * math.sin(r) > 0),
                       key=lambda b: math.hypot(b.x - d.x, b.y - d.y))
        for b in ahead[:3]:
            pose = _nudge(world, d, b)
            if pose:
                return [("move", b.id, pose)], f"nudging a domino into line near {where(d.x, d.y)}"
    best = None                          # 2. bridge
    for d in ends:
        r = math.radians(d.angle)
        for b in world.near(d.x, d.y, 3.0):
            if b.id == d.id or b.state != "up":
                continue
            if (b.x - d.x) * math.cos(r) + (b.y - d.y) * math.sin(r) <= 0:
                continue
            score = math.hypot(b.x - d.x, b.y - d.y) + (0 if not _has_pred(world, b) else 1.5)
            if best is None or score < best[0]:
                best = (score, d, b)
    if best is None:
        return [], f"the line near {where(*at)} just ends; there's nothing ahead for it to reach"
    _, d, b = best
    x, y, h = _start_pose(world, d, (b.x, b.y))
    if math.hypot(b.x - x, b.y - y) < 0.9 and abs(angle_diff(b.angle, h)) <= 40:
        pts = [(x, y, h)]
    else:
        pts = approach(world, x, y, h, b, max_steps=max_n * 3)
    if len(pts) > 5 or _cost(world, pts, {d.id, b.id}, clearance=0.25) > 0:
        return [], (f"the break near {where(d.x, d.y)} is too big to fix by hand; "
                    "trace that stroke again with \"redo\": true instead")
    return [("place", p) for p in pts[:max_n]], f"bridging the small break near {where(d.x, d.y)}"


def snap_start(world: World, specs: list) -> tuple:
    """People line a new domino up with the last one in a line without thinking about
    it. If a stroke starts just past the end of a standing line, heading roughly the
    same way, it carries on from that domino precisely. Returns (specs, note or "")."""
    if not specs:
        return specs, ""
    x, y, a = specs[0]
    best = None
    for e in world.near(x, y, 1.6):
        if e.state != "up" or world.successors(e):
            continue
        turn = angle_diff(a, e.angle)
        if abs(turn) > 60:
            continue
        r = math.radians(e.angle)
        if (x - e.x) * math.cos(r) + (y - e.y) * math.sin(r) < -0.3:
            continue
        dist = math.hypot(x - e.x, y - e.y)
        if best is None or dist < best[0]:
            best = (dist, e, turn)
    if best is None:
        return specs, ""
    _, e, turn = best
    rot = 0.0 if abs(turn) <= 30 else -(turn - math.copysign(30, turn))
    r = math.radians(e.angle)
    nx, ny = e.x + SPACING * math.cos(r), e.y + SPACING * math.sin(r)
    c, si = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    out = []
    for px_, py_, pa in specs:
        rx, ry = px_ - x, py_ - y
        out.append((nx + rx * c - ry * si, ny + rx * si + ry * c, (pa + rot) % 360))
    return out, f"carrying on from the end of a line near {where(e.x, e.y)}"


def end_join(world: World, d, removable: set = frozenset(), max_n: int = 14) -> list:
    """When a line you're laying ends near the start of another line, heading toward it,
    you bend your last few dominoes so the line runs into it. Lifts up to three of your
    own last dominoes (from `removable`) and lays a smooth curve into the other line.
    Returns ops: ("remove", id), ("place", (x, y, a)); [] if there's nothing to join."""
    if d is None or d.state != "up" or world.successors(d):
        return []
    r = math.radians(d.angle)
    target = None
    for b in sorted(world.near(d.x, d.y, 3.0), key=lambda b: math.hypot(b.x - d.x, b.y - d.y)):
        if b.id == d.id or b.state != "up" or _has_pred(world, b):
            continue
        if (b.x - d.x) * math.cos(r) + (b.y - d.y) * math.sin(r) <= 0:
            continue
        if abs(angle_diff(b.angle, d.angle)) > 70:
            continue
        target = b
        break
    if target is None:
        return []
    for k in range(0, 4):                      # lift 0..3 of the line's own last dominoes
        chain, cur = [d], d
        while len(chain) <= k:
            preds = [p for p in world.near(cur.x, cur.y, 1.0)
                     if p.id != cur.id and p.state == "up" and world.hit(p, cur)[0]]
            if not preds:
                break
            cur = preds[0]
            chain.append(cur)
        if len(chain) <= k:
            break
        lifted, anchor = chain[:k], chain[k]
        if any(x.id not in removable for x in lifted):
            break
        ra = math.radians(anchor.angle)
        x, y, h = anchor.x + SPACING * math.cos(ra), anchor.y + SPACING * math.sin(ra), anchor.angle
        skip = {x_.id for x_ in lifted}
        path = approach(world, x, y, h, target, max_steps=max_n, extra_ignore=skip)
        ign = skip | {o.id for o in world.near(target.x, target.y, 0.8)} | {anchor.id}
        if len(path) <= max_n and _cost(world, path, ign, clearance=0.3) == 0:
            return [("remove", x_.id) for x_ in lifted] + [("place", p) for p in path]
    return []


def follow(world: World, x: float, y: float, h: float, line: list, max_steps: int = 60,
           clearance: float = 0.28, ignore: set = frozenset(), max_turn: float = 18.0,
           look: float = 2.0) -> list:
    """Follow a drawn line the way a hand copies it: always aiming a little way further
    along the line from the closest point to where you are. Never loops; cuts corners
    to what a domino line can turn."""
    pts = _densify(line, 0.25)
    cum = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))
    total = cum[-1]
    out = [(x, y, h % 360)]
    s_at = 0.0
    for _ in range(max_steps):
        # closest point on the line, never going backwards
        best_i = min((i for i in range(len(pts)) if cum[i] >= s_at - 0.5),
                     key=lambda i: math.hypot(pts[i][0] - x, pts[i][1] - y))
        s_at = max(s_at, cum[best_i])
        if total - s_at < 0.4 or math.hypot(pts[-1][0] - x, pts[-1][1] - y) < 0.5:
            break
        target = s_at + look
        j = next((i for i in range(len(pts)) if cum[i] >= target), len(pts) - 1)
        x, y, h = _step(world, x, y, h, pts[j][0], pts[j][1], out, clearance, ignore, max_turn)
        out.append((x, y, h))
    return out


def _densify(points: list, step: float = 0.5) -> list:
    out = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    out.append(points[-1])
    return out


def _leaving(raw: dict, p: tuple, close) -> list:
    """Directions (degrees) in which sketch lines leave point p."""
    out = []
    for pts in raw.values():
        for i, q in enumerate(pts):
            if not close(q, p):
                continue
            for j in (i + 1, i - 1):
                if 0 <= j < len(pts) and not close(pts[j], p):
                    out.append(math.degrees(math.atan2(pts[j][1] - p[1], pts[j][0] - p[0])))
                elif 0 <= j < len(pts):
                    k = j + (1 if j > i else -1)
                    if 0 <= k < len(pts):
                        out.append(math.degrees(math.atan2(pts[k][1] - p[1], pts[k][0] - p[0])))
            break
    return out


# A separate shape (an eye, a dot, a stroke touching nothing else) can't be where the run starts.
# (On from Study 3; the overstaffing games ran before this fix.)
SKIP_DETACHED_START = True


def _detached(raw: dict, close) -> set:
    out = set()
    for k, p in raw.items():
        others = [q for kk, pp in raw.items() if kk != k for q in pp]
        closed = len(p) > 2 and close(p[0], p[-1])
        if closed or not any(close(a, b) for a in p for b in others):
            out.add(k)
    return out


def start_point(raw: dict, close) -> tuple:
    """Where the run should start: where stroke 1 begins, unless lines leave there in
    directions a single falling domino can't feed (more than about 100 degrees apart);
    then the nearest sketch end where they can."""
    def spread(p):
        dirs = _leaving(raw, p, close)
        return max((abs(angle_diff(a, b)) for a in dirs for b in dirs), default=0.0)
    skip = _detached(raw, close) if SKIP_DETACHED_START else set()
    if len(skip) == len(raw):
        skip = set()
    first = raw[min(k for k in raw if k not in skip)]
    if spread(first[0]) <= 100:
        return first[0]
    ends = [pts[i] for k, pts in raw.items() if k not in skip for i in (0, -1)]
    ok = [e for e in ends if spread(e) <= 100]
    if not ok:
        return first[0]
    return min(ok, key=lambda e: math.hypot(e[0] - first[0][0], e[1] - first[0][1]) + (0 if e in (first[0], first[-1]) else 5))


def sketch_flow(strokes: list, points_of) -> tuple:
    """Orient the sketch's strokes the way a domino run would flow: away from the
    start, which is where the first stroke begins. Strokes whose ends meet (within
    1.6 units) connect. A stroke that passes *through* a connection point (the start,
    or another stroke's end) is split there into two pieces that both flow outward.
    Returns (origin, {stroke number: [oriented piece, ...]})."""
    raw = {k: points_of(s) for k, s in enumerate(strokes, start=1) if s.get("type") != "label"}
    raw = {k: p for k, p in raw.items() if len(p) >= 2}
    if not raw:
        return None, {}
    close = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1]) <= 1.6  # noqa: E731
    origin = start_point(raw, close)
    hubs = [origin] + [p[i] for p in raw.values() for i in (0, -1)]
    pieces = []                            # (stroke number, points)
    for k, p in raw.items():
        cut = None
        for i in range(1, len(p) - 1):
            if any(close(p[i], h) for h in hubs) and not close(p[i], p[0]) and not close(p[i], p[-1]):
                cut = i
                break
        if cut is None:
            pieces.append((k, p))
        else:                              # both halves start at the hub
            pieces.append((k, p[cut::-1]))
            pieces.append((k, p[cut:]))
    oriented: dict = {}
    done = set()
    queue = [origin]
    while queue:
        here = queue.pop(0)
        for idx, (k, p) in enumerate(pieces):
            if idx in done:
                continue
            if close(p[0], here):
                q = p
            elif close(p[-1], here):
                q = p[::-1]
            else:
                continue
            done.add(idx)
            oriented.setdefault(k, []).append(q)
            queue.append(q[-1])
    for idx, (k, p) in enumerate(pieces):  # not connected to the rest: keep as drawn
        if idx not in done:
            oriented.setdefault(k, []).append(p)
    return origin, oriented


def trace_specs(world: World, points: list, rng: random.Random, max_n: int = 60,
                drift: float = 0.1, lead: tuple | None = None, taken: set | None = None,
                exclude: set = frozenset()) -> tuple:
    """Copy a sketch stroke (already oriented the way the run flows) onto the table,
    the way people copy a drawing. Where it begins on an existing line heading the same
    way, it carries on from that line's end (or branches off its side), lined up by hand.
    Corners are rounded to what a domino line can turn; it steers round other dominoes.
    Returns (specs, note)."""
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) < 2:
        return [], "that sketch stroke has no length"
    head0 = math.degrees(math.atan2(pts[min(2, len(pts) - 1)][1] - pts[0][1],
                                    pts[min(2, len(pts) - 1)][0] - pts[0][0]))
    note = "tracing the sketch"
    anchor = None
    cands = [d for d in world.near(pts[0][0], pts[0][1], 1.8) if d.state == "up" and d.id not in exclude]
    taken = taken if taken is not None else set()
    ends = [d for d in cands if not world.successors(d) and d.id not in taken
            and abs(angle_diff(d.angle, head0)) <= 60]
    if ends:
        anchor = min(ends, key=lambda d: abs(angle_diff(d.angle, head0)) + math.hypot(d.x - pts[0][0], d.y - pts[0][1]))
    elif cands:
        anchor = min(cands, key=lambda d: math.hypot(d.x - pts[0][0], d.y - pts[0][1]))
    prefix = []
    if lead is not None:                   # the start domino goes first, facing between the lines
        lx, ly, lh = lead
        prefix = [(lx, ly, lh)]
        x, y, h = lx + SPACING * math.cos(math.radians(lh)), ly + SPACING * math.sin(math.radians(lh)), lh
        anchor = None
        note = "laying the start domino, then tracing the sketch"
    elif anchor is not None:
        if anchor.id in taken:             # someone is already carrying this line on: branch off it
            r = math.radians(anchor.angle)
            ux, uy = math.cos(r), math.sin(r)
            tx, ty = pts[min(3, len(pts) - 1)]
            side = 1 if ux * (ty - anchor.y) - uy * (tx - anchor.x) >= 0 else -1
            x = anchor.x + 0.5 * ux - side * BRANCH_SIDE * uy
            y = anchor.y + 0.5 * uy + side * BRANCH_SIDE * ux
            h = anchor.angle + side * BRANCH_TURN
        else:
            x, y, h = _start_pose(world, anchor, pts[min(3, len(pts) - 1)])
        taken.add(anchor.id)
        note = f"tracing the sketch on from the line near {where(anchor.x, anchor.y)}"
    else:
        dx, dy = rng.gauss(0, drift), rng.gauss(0, drift)
        pts = [(px_ + dx, py_ + dy) for px_, py_ in pts]
        x, y = pts[0]
        h = head0
    path = follow(world, x, y, h, pts, max_steps=max_n, clearance=0.28, max_turn=18.0,
                  ignore=({anchor.id} if anchor else set()) | set(exclude))   # lines may cross close by
    return (prefix + [(px_, py_, a) for px_, py_, a in path])[:max_n], note


def begin_join(world: World, b, removable: set = frozenset(), max_n: int = 12) -> list:
    """The mirror of end_join: a traced line whose first domino nothing knocks over,
    laid before the line that should feed it was there. Bring a short branch from the
    nearest part of the run into it. Returns ops or []."""
    if b is None or b.state != "up" or _has_pred(world, b):
        return []
    reach = world.reachable_from_start()
    cands = [d for d in world.near(b.x, b.y, 3.5) if d.state == "up" and d.id != b.id
             and d.id not in removable and (not reach or d.id in reach)]
    cands.sort(key=lambda d: math.hypot(d.x - b.x, d.y - b.y))
    for d in cands[:6]:
        x, y, h = _start_pose(world, d, (b.x, b.y))
        if abs(angle_diff(math.degrees(math.atan2(b.y - y, b.x - x)), h)) > 100:
            continue
        path = approach(world, x, y, h, b, max_steps=max_n, extra_ignore={d.id})
        if len(path) <= max_n and _cost(world, path, {d.id, b.id} | {o.id for o in world.near(b.x, b.y, 0.8)},
                                         clearance=0.3) == 0:
            return [("place", p) for p in path]
    return []


def freehand_specs(s: dict, rng: random.Random, pos_sigma: float | None = None) -> list:
    """A stroke aimed by eye: the whole thing shifts and turns slightly."""
    specs = expand_stroke(s)
    if not specs:
        return specs
    sig = FREEHAND_POS if pos_sigma is None else pos_sigma
    dx, dy = rng.gauss(0, sig), rng.gauss(0, sig)
    rot = rng.gauss(0, FREEHAND_ROT)
    ox, oy = specs[0][0], specs[0][1]
    c, si = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    out = []
    for x, y, a in specs:
        rx, ry = x - ox, y - oy
        out.append((ox + dx + rx * c - ry * si, oy + dy + rx * si + ry * c, (a + rot) % 360))
    return out


# ---- looking -----------------------------------------------------------------------

PLAIN = {"too far": "the next domino looks a bit too far away",
         "too close": "the next domino is jammed too close",
         "off the line": "the next domino sits off to the side of its path",
         "turn too sharp": "the line turns too sharply there"}


def _plain(reason: str) -> str:
    for k, v in PLAIN.items():
        if reason.startswith(k):
            return v
    return reason


def _clusters(world: World, ids: set) -> list:
    ids = set(ids)
    out = []
    while ids:
        seed = ids.pop()
        comp, stack = {seed}, [seed]
        while stack:
            d = world.dominoes[stack.pop()]
            for n in world.near(d.x, d.y, 1.0):
                if n.id in ids:
                    ids.discard(n.id)
                    comp.add(n.id)
                    stack.append(n.id)
        out.append(comp)
    return sorted(out, key=len, reverse=True)


def eye_inspect(world: World, area: list, trace: bool = True) -> str:
    x0, y0, x1, y1 = area
    inside = [d for d in world.dominoes.values() if x0 <= d.x <= x1 and y0 <= d.y <= y1]
    up = [d for d in inside if d.state == "up"]
    lines = [f"You look closely at {where(x0, y0)} to {where(x1, y1)}: about {len(up)} standing dominoes"
             + (f" and {len(inside) - len(up)} knocked over" if len(up) < len(inside) else "") + "."]
    breaks, ends = [], []
    for d in up:
        if world.successors(d):
            continue
        cands = [b for b in world.near(d.x, d.y, 1.6) if b.id != d.id and b.state == "up"]
        best = None
        for b in cands:
            r = math.radians(d.angle)
            ahead = (b.x - d.x) * math.cos(r) + (b.y - d.y) * math.sin(r)
            side = abs(-(b.x - d.x) * math.sin(r) + (b.y - d.y) * math.cos(r))
            if 0 < ahead < 1.6 and side < 0.8 and (best is None or ahead < best[0]):
                best = (ahead, b)
        if best:
            breaks.append(f"near {where(d.x, d.y)} {_plain(world.hit(d, best[1])[1])}")
        else:
            ends.append(f"near {where(d.x, d.y)} (facing {direction(d.angle)})")
    if breaks:
        lines.append("Places where the chain looks broken: " + "; ".join(breaks[:12]) + ".")
    if ends:
        lines.append("Line ends with nothing ahead: " + "; ".join(ends[:12]) + ".")
    if trace:
        starts = [d for d in world.dominoes.values() if d.start and d.state == "up"]
        if not starts:
            lines.append("There's no start domino yet.")
        else:
            s = starts[0]
            reach = world.reachable_from_start()
            standing = {d.id for d in world.dominoes.values() if d.state == "up"}
            lines.append(f"Following the chain by eye from the start near {where(s.x, s.y)}: it would carry "
                         f"through about {len(reach)} of the {len(standing)} standing dominoes on the table.")
            loose = _clusters(world, standing - reach)
            if loose:
                parts = []
                for comp in loose[:6]:
                    ds = [world.dominoes[i] for i in comp]
                    xs, ys = [d.x for d in ds], [d.y for d in ds]
                    parts.append(f"about {len(ds)} around {where(min(xs), min(ys))} to {where(max(xs), max(ys))}")
                lines.append("Not connected to the start: " + "; ".join(parts) + ".")
    return "\n".join(lines)
