"""Design generator for MarbleGrid. Parametric agents call this when they 'design';
LLM agents are expected to design boards themselves and can use it as a baseline.

Two design concepts stand in for 'main bet' vs 'moonshot':

* zigzag  - full-width switchbacks. Many pieces (slow to build), forgiving.
* narrow  - switchbacks packed into a 3-column tower, then one run to the exit.
            Fewer pieces and rows (fast, cheap), but tight turns are hard to
            build well (see CONCEPT_RELIABILITY_PENALTY in sim.py).
"""
from __future__ import annotations

from dataclasses import dataclass

from .marble import DOWN_L, DOWN_R, FLAT, TURN, Board, Physics, roll

CONCEPT_SPAN = {"zigzag": None, "narrow": 3}
# Speed head-room each concept keeps above stalling. Safety costs rows.
CONCEPT_MARGIN = {"zigzag": 1.5, "narrow": 0.6}


@dataclass
class Design:
    concept: str
    plan: dict            # (r, c) -> piece
    path: list            # cells in the order the ball visits them (build order)
    entry_row: int
    entry_v: float
    exit_row: int
    exit_v: float
    H: int
    W: int

    @property
    def n_pieces(self) -> int:
        return len(self.plan)

    @property
    def rows_used(self) -> int:
        return self.exit_row - self.entry_row + 1


def plan_board(entry_row: int, entry_v: float, H: int, W: int, switchbacks: int,
               concept: str = "zigzag", max_row: int | None = None,
               min_exit_v: float = 0.5, phys: Physics = Physics(),
               margin: float | None = None) -> Design | None:
    """Greedy constructive design. Returns None if infeasible within the rows."""
    if switchbacks % 2:
        switchbacks += 1  # enter left, exit right => even number of reversals
    max_row = H - 1 if max_row is None else min(max_row, H - 1)
    span = CONCEPT_SPAN.get(concept) or W
    span = min(span, W)
    margin = CONCEPT_MARGIN.get(concept, 1.0) if margin is None else margin
    plan: dict = {}
    r, c, d, v = entry_row, 0, +1, entry_v
    for p in range(switchbacks + 1):
        last = p == switchbacks
        end_col = (W - 1) if last else (span - 1 if d > 0 else 0)
        while True:
            if r > max_row:
                return None
            if c == end_col and not last:
                if v > phys.vmax_turn:
                    return None
                plan[(r, c)] = TURN
                v -= phys.turn_cost
                d, r = -d, r + 1
                break
            # Look ahead: speed needed to survive to (and through) the next turn.
            steps_left = abs(end_col - c)
            floor_v = margin if not last else max(min_exit_v, margin)
            projected = v - phys.friction * steps_left - (0 if last else phys.turn_cost)
            fits = v + phys.ramp_gain <= phys.vmax_turn - 0.5 or last
            want_ramp = (v - phys.friction < floor_v) or (projected < floor_v and fits)
            if want_ramp and r + 1 <= max_row:
                plan[(r, c)] = DOWN_R if d > 0 else DOWN_L
                r, c, v = r + 1, c + d, v + phys.ramp_gain
            else:
                plan[(r, c)] = FLAT
                c, v = c + d, v - phys.friction
            if v <= 0:
                return None
            if c >= W:
                break
    board = Board.from_plan(H, W, plan)
    res = roll(board, entry_row, entry_v, phys)
    if not res.ok or res.switchbacks < switchbacks or res.v < min_exit_v:
        return None
    return Design(concept, plan, res.path, entry_row, entry_v, res.row, res.v, H, W)
