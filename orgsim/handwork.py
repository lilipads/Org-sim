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
          clearance: float, ignore: set) -> tuple:
    """One domino toward (tx, ty): turn at most MAX_STEER, avoid what's on the table."""
    want = math.degrees(math.atan2(ty - y, tx - x))
    base = max(-MAX_STEER, min(MAX_STEER, angle_diff(want, h)))
    for t in [base] + [t for t in (base + 12.5, base - 12.5, MAX_STEER, -MAX_STEER, 0.0) if abs(t) <= MAX_STEER]:
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
          max_steps: int = 120, clearance: float = 0.45, ignore: set = frozenset()) -> list:
    """Lay a path by hand toward waypoints, steering around what's on the table."""
    pts = [(x, y, h % 360)]
    for wx, wy in waypoints:
        best, stall = 1e9, 0
        while math.hypot(wx - x, wy - y) > arrive and len(pts) <= max_steps and stall < 12:
            x, y, h = _step(world, x, y, h, wx, wy, pts, clearance, ignore)
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


def approach(world: World, x: float, y: float, h: float, b, max_steps: int = 160) -> list:
    """Plan a smooth path by hand from pose (x, y, h) to squarely behind domino b,
    facing the way b falls, so the last new domino knocks b over. Tries several
    curve shapes (direct, wider, or round either side) and keeps the shortest
    buildable one."""
    rb = math.radians(b.angle)
    ux, uy = math.cos(rb), math.sin(rb)
    nx, ny = -uy, ux
    end = (b.x - SPACING * ux, b.y - SPACING * uy)
    ignore = {d.id for d in world.near(b.x, b.y, 0.8)} | {d.id for d in world.near(x, y, 0.7)}
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
    return [("place", p) for p in pts[:max_n]], f"bridging the break near {where(d.x, d.y)}"


def freehand_specs(s: dict, rng: random.Random) -> list:
    """A stroke aimed by eye: the whole thing shifts and turns slightly."""
    specs = expand_stroke(s)
    if not specs:
        return specs
    dx, dy = rng.gauss(0, FREEHAND_POS), rng.gauss(0, FREEHAND_POS)
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
