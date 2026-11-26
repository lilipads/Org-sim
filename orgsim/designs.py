"""Hand-made animal designs for scripted agents (calibration and tests only).

LLM agents design their own pictures. These exist so we can tune the physics
and the turn budget without spending any model calls.

A design is a tree of strokes. The root stroke starts at the start domino. A
branch starts beside a domino of its parent stroke, angled off to one side, so
the falling parent knocks over both its own next domino and the branch.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .dominoes import Physics, Region, World, angle_diff

SPACING = 0.55
MAX_STEP_TURN = 20.0
BRANCH_AHEAD, BRANCH_SIDE, BRANCH_TURN = 0.5, 0.25, 25.0


def turtle(x: float, y: float, heading: float, waypoints: list, spacing: float = SPACING,
           max_turn: float = MAX_STEP_TURN, arrive: float = 0.7, max_steps: int = 800) -> list:
    """Steer from a pose through waypoints, turning at most max_turn per domino."""
    pts = [(x, y, heading % 360)]
    steps = 0
    for wx, wy in waypoints:
        while math.hypot(wx - x, wy - y) > arrive and steps < max_steps:
            want = math.degrees(math.atan2(wy - y, wx - x))
            turn = max(-max_turn, min(max_turn, angle_diff(want, heading)))
            heading = (heading + turn) % 360
            x += spacing * math.cos(math.radians(heading))
            y += spacing * math.sin(math.radians(heading))
            pts.append((x, y, heading))
            steps += 1
    return pts


@dataclass
class Stroke:
    name: str
    waypoints: list
    start: tuple | None = None          # (x, y, heading) for the root stroke
    parent: tuple | None = None         # (stroke index, domino index; negative = from end)
    side: int = 1                       # +1 branch to the right of travel, -1 to the left


@dataclass
class Design:
    animal: str
    strokes: list
    placements: list                    # [(x, y, angle, stroke index)] in build order

    @property
    def n(self) -> int:
        return len(self.placements)


def build_design(animal: str, strokes: list) -> Design:
    paths: list = []
    for s in strokes:
        if s.parent is None:
            pts = turtle(*s.start, s.waypoints)
        else:
            px, py, ph = paths[s.parent[0]][s.parent[1]]
            r = math.radians(ph)
            nx, ny = -math.sin(r), math.cos(r)        # right-hand normal (y down)
            bx = px + BRANCH_AHEAD * math.cos(r) + s.side * BRANCH_SIDE * nx
            by = py + BRANCH_AHEAD * math.sin(r) + s.side * BRANCH_SIDE * ny
            pts = turtle(bx, by, ph + s.side * BRANCH_TURN, s.waypoints)
        paths.append(pts)
    placements = [(x, y, a, i) for i, pts in enumerate(paths) for (x, y, a) in pts]
    return Design(animal, strokes, placements)


def check_design(design: Design, width: float = 60, height: float = 40,
                 phys: Physics = Physics()) -> dict:
    """Place perfectly (no hand error) and push: does every domino fall?"""
    import random
    w = World([Region("T", 0, 0, width, height)], {"T": 10_000},
              Physics(**{**phys.__dict__, "pos_sigma": 0.0, "angle_sigma": 0.0}))
    rng = random.Random(0)
    blocked = []
    for k, (x, y, a, _) in enumerate(design.placements):
        r = w.place([(x, y, a)], "check", 0, "T", ["T"], rng, start_index=0 if k == 0 else None)
        blocked += r.blocked
    times = w.topple([d.id for d in w.dominoes.values() if d.start])
    return {"n": design.n, "placed": len(w.dominoes), "fell": len(times),
            "blocked": blocked, "seconds": round(max(times.values()), 1) if times else 0}


# ---- the library ------------------------------------------------------------

def fish(cx: float = 30, cy: float = 20, s: float = 1.0) -> Design:
    """Small: body loop, tail, eye. ~70-90 dominoes."""
    P = lambda x, y: (cx + x * s, cy + y * s)  # noqa: E731
    body = Stroke("body", [P(-4, -5), P(3, -5.5), P(8.5, -1.5), P(9, 0.5), P(3, 5.5),
                           P(-4, 5), P(-8, 1.2)], start=(*P(-8, -1.2), -30))
    tail = Stroke("tail", [P(-13, -4.5), P(-13.2, 4.5), P(-9, 2)], parent=(0, -1), side=-1)
    eye = Stroke("eye", [P(5, -2), P(4, -3)], parent=(0, 14), side=1)
    return build_design("fish", [body, tail, eye])


def snail(cx: float = 30, cy: float = 22, s: float = 1.0) -> Design:
    """Medium: spiral shell on a long foot, two antennae. ~120-150 dominoes."""
    P = lambda x, y: (cx + x * s, cy + y * s)  # noqa: E731
    sx, sy, R = -2.0, -1.0, 5.0     # shell centre and outer radius
    spiral = [P(sx + R * (1 - k / 24) * math.cos(math.radians(90 - 40 * k)),
                sy + R * (1 - k / 24) * math.sin(math.radians(90 - 40 * k))) for k in range(1, 19)]
    foot = Stroke("foot", [P(8, 4.6), P(13, 3.5), P(15, 1)], start=(*P(-14, 4.6), 0))
    neck = Stroke("neck", [P(14, -3), P(13, -6)], parent=(0, -1), side=-1)
    antenna = Stroke("antenna", [P(17, -7), P(18.5, -8)], parent=(1, 3), side=1)
    shell = Stroke("shell", spiral, parent=(0, 20), side=-1)
    return build_design("snail", [foot, neck, antenna, shell])


def cat(cx: float = 30, cy: float = 21, s: float = 1.0) -> Design:
    """Large: round face, two pointed ears, whiskers. ~180-220 dominoes."""
    P = lambda x, y: (cx + x * s, cy + y * s)  # noqa: E731
    R = 10
    face_pts = [P(R * math.cos(math.radians(a)), R * math.sin(math.radians(a))) for a in range(110, 470, 30)]
    face = Stroke("face", face_pts, start=(*P(0, R), 180))
    lear = Stroke("left ear", [P(-8, -16), P(-2.5, -10)], parent=(0, 46), side=-1)
    rear = Stroke("right ear", [P(8, -16), P(9.6, -3)], parent=(0, 58), side=-1)
    wl = Stroke("whiskers left", [P(-16, 1), P(-17, 3)], parent=(0, 18), side=1)
    wr = Stroke("whiskers right", [P(17, 1), P(18, -1)], parent=(0, 86), side=1)
    eyes = Stroke("nose and eyes", [P(0, 2), P(-3.5, -3), P(-4, -3.5)], parent=(0, 2), side=1)
    return build_design("cat", [face, lear, rear, wl, wr, eyes])


LIBRARY = {"fish": fish, "snail": snail, "cat": cat}
