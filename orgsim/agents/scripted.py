"""Scripted agents: no AI. They split a known design, build it, re-stand
bumped dominoes, and inspect and repair breaks in their own section.

Used to test the engine and calibrate the physics and time budget (DESIGN.md §10).
They see the world directly, which is fine for calibration: real agents get the map.
"""
from __future__ import annotations

from ..designs import Design
from ..game import Action, Agent


class ScriptedTeam:
    def __init__(self, design: Design, names: list, world, discussion_turns: int = 1, repair: bool = True):
        self.design, self.names, self.world = design, names, world
        self.discussion_turns, self.repair = discussion_turns, repair
        n = len(design.placements)
        k = len(names)
        self.chunks = {name: list(range(i * n // k, (i + 1) * n // k)) for i, name in enumerate(names)}


class ScriptedAgent(Agent):
    def __init__(self, name: str, home: str, team: ScriptedTeam):
        super().__init__(name, home, "scripted builder")
        self.team = team
        self.todo = list(team.chunks[name])      # spec indices still to place
        self.ids: dict = {}                      # spec index -> domino id
        self.sent: list = []
        self.inspected_after = -1
        self.retries: dict = {}

    def _absorb(self, obs: dict):
        data = obs.get("last_data") or {}
        if self.sent and "placed" in data:
            blocked_xy = {(round(x, 6), round(y, 6)) for x, y, _ in data.get("blocked", [])}
            placed = list(data["placed"])
            unplaced = []
            for k in self.sent[: len(self.sent) - data.get("truncated", 0)]:
                x, y, _, _ = self.team.design.placements[k]
                if (round(x, 6), round(y, 6)) in blocked_xy or not placed:
                    unplaced.append(k)
                else:
                    self.ids[k] = placed.pop(0)
            unplaced += self.sent[len(self.sent) - data.get("truncated", 0):]
            for k in unplaced:
                self.retries[k] = self.retries.get(k, 0) + 1
                if self.retries[k] <= 2:
                    self.todo.append(k)
        self.sent = []
        # dominoes someone took down are gone: rebuild them
        for k, i in list(self.ids.items()):
            if i not in self.team.world.dominoes:
                del self.ids[k]
                if k not in self.todo:
                    self.todo.append(k)
        self.todo.sort()

    def decide(self, obs: dict) -> Action:
        self._absorb(obs)
        t = obs["turn"]
        if t <= self.team.discussion_turns:
            if self.name == self.team.names[0]:
                return Action("talk", "everyone", f"Let's make a {self.team.design.animal}. "
                              f"I'll split it into {len(self.team.names)} sections, one each.")
            return Action("listen")
        world = self.team.world
        down = [world.dominoes[i] for i in self.ids.values()
                if i in world.dominoes and world.dominoes[i].state == "down"]
        if down:
            xs, ys = [d.x for d in down], [d.y for d in down]
            return Action("build", restand=[min(xs) - .3, min(ys) - .3, max(xs) + .3, max(ys) + .3])
        if self.todo:
            self.sent = self.todo[:8]
            self.todo = self.todo[8:]
            specs = [self.team.design.placements[k] for k in self.sent]
            strokes = [{"type": "domino", "x": x, "y": y, "angle": a} for x, y, a, _ in specs]
            return Action("build", strokes=strokes, start=(self.sent[0] == 0))
        if not self.team.repair:
            return Action("wait")
        data = obs.get("last_data") or {}
        if "line_ends" in data and self.inspected_after == t - 1:
            by_id = {i: k for k, i in self.ids.items()}
            chunk = set(self.team.chunks[self.name])
            for e in data["line_ends"]:
                k = by_id.get(e["id"])
                if k is None or (k + 1) not in chunk or (k + 1) not in self.ids:
                    continue
                if self.team.design.placements[k + 1][3] != self.team.design.placements[k][3]:
                    continue
                d = world.dominoes.get(self.ids[k + 1])
                if d is None:
                    continue
                return Action("take_down", area=[d.x - .08, d.y - .08, d.x + .08, d.y + .08])
            return Action("wait")
        if self.ids and self.inspected_after < t - 2:
            pts = [world.dominoes[i] for i in self.ids.values() if i in world.dominoes]
            if pts:
                self.inspected_after = t
                xs, ys = [d.x for d in pts], [d.y for d in pts]
                return Action("inspect", area=[min(xs) - .5, min(ys) - .5, max(xs) + .5, max(ys) + .5])
        return Action("wait")


def plan_connector(world, from_region: str, to_region: str, spacing: float = 0.55) -> list:
    """Plan a domino path from the picture on `from_region` to the start domino on
    `to_region`: branch off the eastmost domino the push reaches, then steer into the
    start from behind. Returns [(x, y, angle)] or [] if there's nothing to connect."""
    import math
    from ..designs import BRANCH_AHEAD, BRANCH_SIDE, BRANCH_TURN, turtle
    reach = world.reachable_from_start(from_region) if any(
        d.start and d.region == from_region for d in world.dominoes.values()) else set()
    src = [world.dominoes[i] for i in reach if world.dominoes[i].region == from_region]
    dst = [d for d in world.dominoes.values() if d.start and d.region == to_region]
    if not src or not dst:
        return []
    # prefer a domino heading roughly east, near the right edge
    a = max(src, key=lambda d: d.x + 3 * math.cos(math.radians(d.angle)))
    b = dst[0]
    r = math.radians(a.angle)
    nx, ny = -math.sin(r), math.cos(r)
    bx = a.x + BRANCH_AHEAD * math.cos(r) + BRANCH_SIDE * nx
    by = a.y + BRANCH_AHEAD * math.sin(r) + BRANCH_SIDE * ny
    rb = math.radians(b.angle)
    behind = lambda k: (b.x - k * math.cos(rb), b.y - k * math.sin(rb))  # noqa: E731
    pts = turtle(bx, by, a.angle + BRANCH_TURN, [behind(4.0), behind(2.0)], spacing)
    pts += turtle(*pts[-1], [behind(0.55)], spacing, arrive=0.3)[1:]
    return [(x, y, h) for x, y, h in pts]


class ConnectorCrew:
    """Shares one connector plan among several agents, split into contiguous segments."""

    def __init__(self, world, from_region: str, to_region: str, size: int):
        self.world, self.from_region, self.to_region, self.size = world, from_region, to_region, size
        self._segments = None

    def segment(self, k: int) -> list:
        if self._segments is None:
            plan = plan_connector(self.world, self.from_region, self.to_region)
            n = len(plan)
            self._segments = [plan[i * n // self.size:(i + 1) * n // self.size] for i in range(self.size)]
        return list(self._segments[k])


class ScriptedConnector(Agent):
    """Round 2: walks out and builds its segment of a connector from its table's
    picture to the next table's start, 8 dominoes per turn, visiting each region
    the segment passes through."""

    def __init__(self, name: str, home: str, crew: ConnectorCrew, k: int = 0):
        super().__init__(name, home, "scripted connector")
        self.crew, self.k = crew, k
        self.world = crew.world
        self.plan: list | None = None

    def decide(self, obs: dict) -> Action:
        if self.plan is None:
            self.plan = self.crew.segment(self.k)
        if not self.plan:
            return Action("wait")
        x, y, _ = self.plan[0]
        reg = self.world.region_at(x, y)
        if reg is None:
            self.plan.pop(0)
            return Action("wait")
        batch = []
        while self.plan and len(batch) < 8 and self.world.region_at(*self.plan[0][:2]) is reg:
            batch.append(self.plan.pop(0))
        return Action("build", at=reg.name,
                      strokes=[{"type": "domino", "x": bx, "y": by, "angle": ba} for bx, by, ba in batch])
