"""The oracle on the worked example in PERF_REVIEW_STUDY.md §4.4: start -> Ana's body (gap) -> Ben's tail."""
from orgsim.oracle import compute


def _rows(extra=()):
    rows, k = [], 0
    def add(x, who, start=False):
        nonlocal k
        k += 1
        rows.append([k, x, 10.0, 0.0, "up", who, int(start)])
    for i in range(26):                       # Ana: x = 1 .. 13.5
        add(1 + 0.5 * i, "Ana", start=(i == 0))
    for i in range(10):                       # Ana again after a 1.5 gap: x = 15 .. 19.5
        add(15 + 0.5 * i, "Ana")
    for i in range(16):                       # Ben's tail: x = 20 .. 27.5
        add(20 + 0.5 * i, "Ben")
    for x, who in extra:
        add(x, who)
    return rows


def _log(turn_rows, events_last=()):
    turns = [{"time": 15.0 * i, "clock": f"0:{15 * i:02d}", "snapshot": r, "events": [], "decisions": {}}
             for i, r in enumerate(turn_rows)]
    turns[-1]["events"] = list(events_last)
    return {"turns": turns, "agents": [{"name": n} for n in ("Ana", "Ben", "Cal", "Dan")],
            "scratchpad": {"history": [{"t": 0, "who": "Dan", "cleared": False,
                                        "strokes": [{"type": "line", "x0": 1, "y0": 10, "x1": 28, "y1": 10}]}]}}


def test_broken_body_perfect_tail():
    r = compute(_log([_rows(), _rows()]))
    p = r["people"]
    assert p["Ana"]["sound_work"] == 26 and p["Ana"]["open_breaks_owned"] == 1
    assert p["Ben"]["sound_work"] == 16 and p["Ben"]["open_breaks_owned"] == 0   # full credit, though it never fell
    assert p["Dan"]["planning"] == 1.0 and p["Dan"]["sound_work"] == 0
    assert r["contribution"]["Ana"] == 26 - 10


def test_helper_bridges_the_gap():
    before, after = _rows(), _rows(extra=[(14.25, "Cal")])
    ev = [{"type": "build", "who": "Cal", "placed": [len(after)], "restood": [], "lifted": []}]
    r = compute(_log([before, after], ev))
    p = r["people"]
    assert p["Cal"]["fixes"] == 1
    assert p["Ana"]["open_breaks_owned"] == 0 and p["Ana"]["sound_work"] == 36
    assert p["Ben"]["sound_work"] == 16


def test_fix_far_from_start_counts_the_same():
    # no gap in Ana's body; instead a 1.5 gap far downstream in Ben's tail, bridged by Cal
    rows, k = [], 0
    for i in range(38):                       # Ana: x = 1 .. 19.5, no gap
        k += 1
        rows.append([k, 1 + 0.5 * i, 10.0, 0.0, "up", "Ana", int(i == 0)])
    for x in [20 + 0.5 * i for i in range(16)]:
        if x in (24.0, 24.5):                 # Ben's gap: 23.5 -> 25.0
            continue
        k += 1
        rows.append([k, x, 10.0, 0.0, "up", "Ben", 0])
    after = [list(r) for r in rows] + [[999, 24.25, 10.0, 0.0, "up", "Cal", 0]]
    ev = [{"type": "build", "who": "Cal", "placed": [999], "restood": [], "lifted": []}]
    r = compute(_log([rows, after], ev))
    assert r["people"]["Cal"]["fixes"] == 1
    assert r["people"]["Ben"]["open_breaks_owned"] == 0
    before_only = compute(_log([rows, rows]))
    assert before_only["people"]["Ben"]["open_breaks_owned"] == 1
