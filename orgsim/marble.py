"""MarbleGrid: a discrete, agent-friendly stand-in for the physical ball-run exercise.

A board is a side view: H rows (row 0 = top) x W columns. The ball enters on the
left edge moving right and must leave on the right edge. Pieces:

    '='  flat track      ball moves one column, loses `friction` speed
    '\\'  ramp down-right ball must be moving right; drops one row, gains speed
    '/'  ramp down-left  ball must be moving left;  drops one row, gains speed
    'U'  switchback      reverses direction, drops one row, costs speed;
                         flies off if the ball arrives faster than `vmax_turn`
    ' '  empty           ball falls one row; falling two rows in a row = crash

Height is the only energy source, so rows are a conserved budget. That makes the
integration round a shared-commons problem: every row one table spends is a row
a downstream table cannot use, and every unit of speed a table delivers (or
fails to deliver) is a downstream table's problem.

Each placed piece has a reliability (how well it was built). A stochastic run
can snag or collapse a piece, so a design that passes once may fail on demo day.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

FLAT, DOWN_R, DOWN_L, TURN, EMPTY = "=", "\\", "/", "U", " "
PIECES = (FLAT, DOWN_R, DOWN_L, TURN)


@dataclass(frozen=True)
class Physics:
    friction: float = 0.25
    ramp_gain: float = 1.0
    turn_cost: float = 1.0
    fall_gain: float = 0.5
    vmax_turn: float = 5.0
    vmax_junction: float = 5.5
    noise: float = 0.15          # per-piece speed jitter (std) in stochastic runs
    snag_loss: float = 1.0       # speed lost when a weak piece snags
    collapse_share: float = 0.4  # share of piece failures that end the run
    max_steps: int = 600


@dataclass
class Board:
    H: int
    W: int
    cells: dict = field(default_factory=dict)  # (r, c) -> (piece, reliability)

    def piece(self, r: int, c: int) -> str:
        return self.cells.get((r, c), (EMPTY, 1.0))[0]

    def place(self, r: int, c: int, piece: str, rel: float = 1.0) -> None:
        if piece == EMPTY:
            self.cells.pop((r, c), None)
        else:
            self.cells[(r, c)] = (piece, rel)

    def to_ascii(self) -> str:
        rows = []
        for r in range(self.H):
            rows.append("|" + "".join(self.piece(r, c) for c in range(self.W)) + "|")
        return "\n".join(rows)

    @classmethod
    def from_ascii(cls, text: str, rel: float = 1.0) -> "Board":
        lines = [ln.strip("\n") for ln in text.splitlines() if ln.strip()]
        lines = [ln[1:-1] if ln.startswith("|") and ln.endswith("|") else ln for ln in lines]
        W = max(len(ln) for ln in lines)
        b = cls(len(lines), W)
        for r, ln in enumerate(lines):
            for c, ch in enumerate(ln):
                if ch in PIECES:
                    b.place(r, c, ch, rel)
        return b

    @classmethod
    def from_plan(cls, H: int, W: int, plan: dict, rel: float = 1.0) -> "Board":
        b = cls(H, W)
        for (r, c), p in plan.items():
            b.place(r, c, p, rel)
        return b


@dataclass
class RunResult:
    status: str                 # exit | stall | crash | flyoff | floor | wrong_side | timeout
    row: int
    v: float
    switchbacks: int
    fail_cell: tuple | None
    path: list

    @property
    def ok(self) -> bool:
        return self.status == "exit"


def roll(board: Board, entry_row: int, v: float, phys: Physics = Physics(),
         rng: random.Random | None = None) -> RunResult:
    """Roll one ball. rng=None gives the ideal (deterministic, perfectly built) run."""
    r, c, d = entry_row, 0, +1
    falls, sw, path = 0, 0, []

    def end(status, cell=None):
        return RunResult(status, r, v, sw, cell, path)

    for _ in range(phys.max_steps):
        if r >= board.H:
            return end("floor", (r - 1, c))
        piece, rel = board.cells.get((r, c), (EMPTY, 1.0))
        cell = (r, c)
        path.append(cell)
        if rng is not None and piece != EMPTY:
            if rng.random() > rel:
                if rng.random() < phys.collapse_share:
                    return end("crash", cell)
                v -= phys.snag_loss
            v += rng.gauss(0.0, phys.noise)
        if piece == EMPTY:
            falls += 1
            if falls > 1:
                return end("crash", cell)
            r += 1
            v += phys.fall_gain
            continue
        falls = 0
        if piece == FLAT:
            c += d
            v -= phys.friction
        elif piece in (DOWN_R, DOWN_L):
            if d != (+1 if piece == DOWN_R else -1):
                return end("crash", cell)  # rolled into the back of a ramp
            r += 1
            c += d
            v += phys.ramp_gain
        elif piece == TURN:
            if v > phys.vmax_turn:
                return end("flyoff", cell)
            d = -d
            r += 1
            v -= phys.turn_cost
            sw += 1
        if v <= 0:
            return end("stall", cell)
        if c >= board.W:
            return end("exit")
        if c < 0:
            return end("wrong_side", cell)
    return end("timeout")


@dataclass
class ChainResult:
    ok: bool
    where: tuple | None   # ('board', i, RunResult) | ('junction', i, status) | None
    row: int
    v: float


def roll_chain(boards: list, junctions: list, entry_row: int, v: float,
               phys: Physics = Physics(), rng: random.Random | None = None) -> ChainResult:
    """Roll through a row of boards. junctions[i] is the reliability of the joint
    between board i and i+1, or None if nobody has built it."""
    row = entry_row
    for i, b in enumerate(boards):
        if i > 0:
            j = junctions[i - 1]
            if j is None:
                return ChainResult(False, ("junction", i - 1, "missing"), row, v)
            if v > phys.vmax_junction:
                return ChainResult(False, ("junction", i - 1, "flyoff"), row, v)
            if rng is not None and rng.random() > j:
                return ChainResult(False, ("junction", i - 1, "collapse"), row, v)
        res = roll(b, row, v, phys, rng)
        if not res.ok:
            return ChainResult(False, ("board", i, res), res.row, res.v)
        row, v = res.row, res.v
    return ChainResult(True, None, row, v)


def success_rate(board: Board, entry_row: int, v: float, n: int = 200,
                 phys: Physics = Physics(), seed: int = 0, min_switchbacks: int = 0) -> float:
    rng = random.Random(seed)
    wins = 0
    for _ in range(n):
        res = roll(board, entry_row, v, phys, rng)
        wins += res.ok and res.switchbacks >= min_switchbacks
    return wins / n
