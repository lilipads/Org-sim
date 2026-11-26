"""Continuous domino physics for Domino Art.

Units: 1 unit = one domino height (how far a domino reaches when it falls).
Coordinates: x to the right, y downwards (screen convention). Angles in degrees,
0 = +x (east), 90 = +y (south). A domino falls in the direction it faces.

A falling domino A knocks over a standing domino B when B is
  * reach_min..reach_max ahead of A along A's falling direction,
  * within side_tol of A's falling line, and
  * facing within max_turn degrees of A.
Splits and merges need no special pieces: one domino can satisfy the rule for
two neighbours, and two lines can feed one domino.
"""
from __future__ import annotations

import heapq
import math
import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Physics:
    reach_min: float = 0.2
    reach_max: float = 0.9
    side_tol: float = 0.35
    max_turn: float = 40.0        # degrees
    pos_sigma: float = 0.05       # placement error, units (std dev)
    angle_sigma: float = 3.0      # placement error, degrees (std dev)
    min_gap: float = 0.2          # two domino centres can't be closer than this
    fall_time: float = 0.1        # seconds per domino-to-domino hop
    bump_radius: float = 6.0      # builders closer than this can bump each other (~30 cm reach)
    bump_chance: float = 0.05     # per nearby builder, per turn
    bump_reach: float = 2.0       # a bump hits a domino this close to the bumper's work


def angle_diff(a: float, b: float) -> float:
    """Signed smallest difference a - b in degrees, in (-180, 180]."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


@dataclass
class Domino:
    id: int
    x: float
    y: float
    angle: float
    builder: str
    turn: int
    region: str
    state: str = "up"              # up | down
    down_cause: str | None = None  # bump | push
    start: bool = False
    intended: tuple = ()           # (x, y, angle) the builder aimed for

    def as_row(self) -> list:
        return [self.id, round(self.x, 3), round(self.y, 3), round(self.angle, 1),
                self.state, self.builder, int(self.start)]


@dataclass
class Region:
    name: str
    x0: float
    y0: float
    x1: float
    y1: float
    kind: str = "table"            # table | gap

    def contains(self, x: float, y: float) -> bool:
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    @property
    def center(self) -> tuple:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)


@dataclass
class PlaceResult:
    placed: list = field(default_factory=list)     # Domino
    blocked: list = field(default_factory=list)    # (x, y, reason)
    truncated: int = 0


class World:
    """All dominoes in a room. Round 1 = one table region; round 2 = tables + gaps."""

    def __init__(self, regions: list, supply: dict, phys: Physics = Physics()):
        self.regions = {r.name: r for r in regions}
        self.supply = dict(supply)    # pool name -> dominoes left
        self.phys = phys
        self.dominoes: dict = {}
        self._next = 1
        self._grid: dict = {}
        self.width = max(r.x1 for r in regions)
        self.height = max(r.y1 for r in regions)

    # ---- spatial index -------------------------------------------------
    def _key(self, x, y):
        return (int(math.floor(x)), int(math.floor(y)))

    def _index(self, d: Domino):
        self._grid.setdefault(self._key(d.x, d.y), set()).add(d.id)

    def _unindex(self, d: Domino):
        self._grid.get(self._key(d.x, d.y), set()).discard(d.id)

    def near(self, x: float, y: float, r: float) -> list:
        out = []
        kx0, ky0 = self._key(x - r, y - r)
        kx1, ky1 = self._key(x + r, y + r)
        for kx in range(kx0, kx1 + 1):
            for ky in range(ky0, ky1 + 1):
                for i in self._grid.get((kx, ky), ()):
                    d = self.dominoes[i]
                    if (d.x - x) ** 2 + (d.y - y) ** 2 <= r * r:
                        out.append(d)
        return out

    def region_at(self, x: float, y: float) -> Region | None:
        for r in self.regions.values():
            if r.contains(x, y):
                return r
        return None

    # ---- placing and removing -----------------------------------------
    def place(self, specs: list, builder: str, turn: int, allowed_region: str,
              pools: list, rng: random.Random, max_n: int = 8,
              start_index: int | None = None) -> PlaceResult:
        """specs: list of (x, y, angle) intended placements. pools: supply pools
        to draw from, in order. start_index: which spec (if any) is the start."""
        res = PlaceResult()
        if len(specs) > max_n:
            res.truncated = len(specs) - max_n
            specs = specs[:max_n]
        region = self.regions[allowed_region]
        for k, (ix, iy, ia) in enumerate(specs):
            pool = next((p for p in pools if self.supply.get(p, 0) > 0), None)
            if pool is None:
                res.blocked.append((ix, iy, "out of dominoes"))
                continue
            if not region.contains(ix, iy):     # judged by where the builder aimed
                res.blocked.append((ix, iy, f"outside {region.name}"))
                continue
            x = ix + rng.gauss(0, self.phys.pos_sigma)
            y = iy + rng.gauss(0, self.phys.pos_sigma)
            a = (ia + rng.gauss(0, self.phys.angle_sigma)) % 360.0
            if any(o.id for o in self.near(x, y, self.phys.min_gap)):
                res.blocked.append((ix, iy, "too close to another domino"))
                continue
            d = Domino(self._next, x, y, a, builder, turn, region.name,
                       intended=(ix, iy, ia))
            self._next += 1
            self.dominoes[d.id] = d
            self._index(d)
            self.supply[pool] -= 1
            res.placed.append(d)
            if start_index is not None and k == start_index:
                self.set_start(d.id, region.name)
        return res

    def set_start(self, did: int, region: str):
        for d in self.dominoes.values():
            if d.region == region:
                d.start = False
        self.dominoes[did].start = True

    def restand(self, ids: list, rng: random.Random) -> list:
        """Stand knocked-over dominoes back up near where they were meant to be."""
        out = []
        for i in ids:
            d = self.dominoes.get(i)
            if d is None or d.state != "down":
                continue
            ix, iy, ia = d.intended
            self._unindex(d)
            d.x = ix + rng.gauss(0, self.phys.pos_sigma)
            d.y = iy + rng.gauss(0, self.phys.pos_sigma)
            d.angle = (ia + rng.gauss(0, self.phys.angle_sigma)) % 360.0
            d.state, d.down_cause = "up", None
            self._index(d)
            out.append(d)
        return out

    def move(self, did: int, x: float, y: float, angle: float, rng: random.Random) -> Domino | None:
        """Nudge a standing domino to a new pose (with ordinary hand error)."""
        d = self.dominoes.get(did)
        if d is None or d.state != "up":
            return None
        self._unindex(d)
        d.x = x + rng.gauss(0, self.phys.pos_sigma)
        d.y = y + rng.gauss(0, self.phys.pos_sigma)
        d.angle = (angle + rng.gauss(0, self.phys.angle_sigma)) % 360.0
        d.intended = (x, y, angle)
        self._index(d)
        return d

    def remove(self, ids: list, pool: str) -> list:
        out = []
        for i in ids:
            d = self.dominoes.pop(i, None)
            if d is None:
                continue
            self._unindex(d)
            self.supply[pool] = self.supply.get(pool, 0) + 1
            out.append(d)
        return out

    # ---- physics -------------------------------------------------------
    def hit(self, a: Domino, b: Domino) -> tuple:
        """(ok, reason). Reason explains the nearest failure, for Inspect."""
        p = self.phys
        rad = math.radians(a.angle)
        ux, uy = math.cos(rad), math.sin(rad)
        dx, dy = b.x - a.x, b.y - a.y
        ahead = dx * ux + dy * uy
        side = -dx * uy + dy * ux
        turn = angle_diff(b.angle, a.angle)
        if ahead < p.reach_min:
            return False, f"too close ({ahead:.2f} ahead)"
        if ahead > p.reach_max:
            return False, f"too far ({ahead:.2f} ahead, max {p.reach_max})"
        if abs(side) > p.side_tol:
            return False, f"off the line ({abs(side):.2f} to the side, max {p.side_tol})"
        if abs(turn) > p.max_turn:
            return False, f"turn too sharp ({abs(turn):.0f} deg, max {p.max_turn:.0f})"
        return True, "ok"

    def successors(self, a: Domino) -> list:
        reach = math.hypot(self.phys.reach_max, self.phys.side_tol) + 0.01   # far corner of the hit zone
        return [b for b in self.near(a.x, a.y, reach)
                if b.id != a.id and b.state == "up" and self.hit(a, b)[0]]

    def topple(self, start_ids: list, cause: str = "push") -> dict:
        """Knock over the given dominoes and everything they reach. Returns
        {id: time in seconds}. Mutates state to 'down'."""
        times: dict = {}
        heap = [(0.0, i) for i in start_ids
                if i in self.dominoes and self.dominoes[i].state == "up"]
        heapq.heapify(heap)
        while heap:
            t, i = heapq.heappop(heap)
            if i in times:
                continue
            d = self.dominoes[i]
            if d.state != "up":
                continue
            times[i] = t
            d.state, d.down_cause = "down", cause
            for b in self.successors(d):
                if b.id not in times:
                    heapq.heappush(heap, (t + self.phys.fall_time, b.id))
        return times

    def reachable_from_start(self, region: str | None = None) -> set:
        """Ideal check without mutating: which standing dominoes the push would reach."""
        starts = [d.id for d in self.dominoes.values() if d.start and d.state == "up"
                  and (region is None or d.region == region)]
        seen, stack = set(starts), list(starts)
        while stack:
            d = self.dominoes[stack.pop()]
            for b in self.successors(d):
                if b.id not in seen:
                    seen.add(b.id)
                    stack.append(b.id)
        return seen

    # ---- inspection ----------------------------------------------------
    def inspect(self, x0, y0, x1, y1, max_items: int = 25) -> dict:
        """What a careful look at an area reveals: exact dominoes, line ends that
        don't knock anything over (with the nearest near-miss), and dominoes the
        start can't reach."""
        inside = [d for d in self.dominoes.values()
                  if x0 <= d.x <= x1 and y0 <= d.y <= y1]
        reach = self.reachable_from_start()
        dead_ends, unreached = [], []
        for d in inside:
            if d.state != "up":
                continue
            if not self.successors(d):
                cands = [b for b in self.near(d.x, d.y, 1.5) if b.id != d.id and b.state == "up"]
                best = None
                for b in cands:
                    rad = math.radians(d.angle)
                    ahead = (b.x - d.x) * math.cos(rad) + (b.y - d.y) * math.sin(rad)
                    if ahead > 0 and (best is None or ahead < best[0]):
                        best = (ahead, b)
                why = self.hit(d, best[1])[1] + f" to #{best[1].id}" if best else "nothing ahead"
                dead_ends.append({"id": d.id, "x": round(d.x, 2), "y": round(d.y, 2),
                                  "angle": round(d.angle), "why": why})
            if d.id not in reach:
                unreached.append(d.id)
        return {
            "area": [x0, y0, x1, y1],
            "dominoes": [[d.id, round(d.x, 2), round(d.y, 2), round(d.angle), d.state]
                         for d in sorted(inside, key=lambda d: d.id)][:max_items * 4],
            "count": len(inside),
            "knocked_over": sum(d.state == "down" for d in inside),
            "line_ends": dead_ends[:max_items],
            "not_reached_from_start": len(unreached),
            "has_start": any(d.start for d in self.dominoes.values()),
        }

    def snapshot(self) -> list:
        return [d.as_row() for d in self.dominoes.values()]


# ---- strokes: how builders describe what to place --------------------------

def expand_stroke(s: dict) -> list:
    """Turn a stroke into intended (x, y, angle) placements.

    {"type": "domino", "x", "y", "angle"}
    {"type": "line", "x0", "y0", "x1", "y1", "spacing"}
    {"type": "arc", "cx", "cy", "r", "a0", "a1", "spacing"}   # a0->a1 in degrees, either way
    """
    t = s.get("type")
    if t == "domino":
        return [(float(s["x"]), float(s["y"]), float(s["angle"]) % 360.0)]
    sp = max(0.05, float(s.get("spacing", 0.55)))
    if t == "line":
        x0, y0, x1, y1 = (float(s[k]) for k in ("x0", "y0", "x1", "y1"))
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 360.0
        n = int(L // sp) + 1
        return [(x0 + (x1 - x0) * (k * sp / L if L else 0), y0 + (y1 - y0) * (k * sp / L if L else 0), ang)
                for k in range(n)]
    if t == "arc":
        cx, cy, r = float(s["cx"]), float(s["cy"]), float(s["r"])
        a0, a1 = float(s["a0"]), float(s["a1"])
        sweep = a1 - a0
        sign = 1.0 if sweep >= 0 else -1.0
        L = abs(math.radians(sweep)) * r
        n = int(L // sp) + 1
        out = []
        for k in range(n):
            a = a0 + sign * math.degrees(k * sp / r) if r else a0
            ar = math.radians(a)
            out.append((cx + r * math.cos(ar), cy + r * math.sin(ar), (a + 90.0 * sign) % 360.0))
        return out
    raise ValueError(f"unknown stroke type {t!r}")
