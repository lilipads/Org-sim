from orgsim.dominoes import Physics
from orgsim.game import table_world
from orgsim.live import Decision, LiveAgentBase, LiveConfig, LiveGame

EXACT = Physics(pos_sigma=0.0, angle_sigma=0.0, bump_chance=0.0)


class Fake(LiveAgentBase):
    """Plays a script keyed by call number; records what it saw."""

    def __init__(self, name, script):
        super().__init__(name, "table")
        self.script, self.seen = script, []

    def act(self, obs):
        self.seen.append(obs)
        return self.script[len(self.seen) - 1] if len(self.seen) <= len(self.script) else Decision()


def game(agents, duration=120.0, **kw):
    kw.setdefault("announce_at", ())
    kw.setdefault("scratchpad_until", None)
    return LiveGame(table_world(phys=EXACT), agents, LiveConfig(duration=duration, **kw))


LINE = {"type": "line", "x0": 5, "y0": 5, "x1": 15, "y1": 5, "spacing": 0.5}


def test_most_eager_takes_the_floor_and_other_holds():
    a = Fake("A", [Decision(say="Let's do a cat " + "really " * 30, eagerness=9)])
    b = Fake("B", [Decision(say="How about a fish? I think a fish would read well", eagerness=3), Decision()])
    g = game([a, b], duration=30)
    g.step()
    rec = g.log["turns"][0]
    assert [c["messages"][0]["speaker"] for c in rec["conversations"]] == ["A"]
    assert rec["held"][0]["who"] == "B"
    g.step()                                       # B is asked again, having heard A
    assert any(m["text"].startswith("Let's do a cat") for m in b.seen[1]["conversation"])
    assert "A said something to the table" in " ".join(b.seen[1]["why_now"])
    assert any("didn't get to say" in x for x in b.seen[1]["inbox"])


def test_build_is_head_down_at_ten_seconds_per_domino():
    a = Fake("A", [Decision(do="build", strokes=[LINE], start=True)])
    g = game([a], duration=120, idle_quiet=1e9, max_quiet=1e9)
    g.run()
    assert len(a.seen) == 1                        # no further calls while working
    assert len(g.world.dominoes) == 12             # 120 s / 10 s per domino
    assert any(d.start for d in g.world.dominoes.values())


def test_talking_slows_your_hands():
    a = Fake("A", [Decision(do="build", strokes=[LINE], say="Building the spine")])
    g = game([a], duration=15, idle_quiet=1e9)
    g.step()
    assert len(g.world.dominoes) == 0              # 1.5 * 0.5 -> nothing yet in the first beat


def test_addressed_builder_is_woken_but_keeps_building():
    a = Fake("A", [Decision(do="build", strokes=[LINE]), Decision(do="continue")])
    b = Fake("B", [Decision(), Decision(say="Ava, which way is the head?", to=["A"])])
    c = Fake("C", [Decision(say="Anyone want coffee?")])
    g = game([a, b, c], duration=60, idle_quiet=15, max_quiet=1e9)
    g.step()                                       # C talks to the table: busy A keeps working
    assert len(a.seen) == 1
    g.step()                                       # B is asked again (idle) and addresses A
    g.step()                                       # A is woken by being addressed
    assert len(a.seen) == 2
    assert "B said something to you" in a.seen[1]["why_now"]
    assert g.task["A"] is not None                 # still building


def test_side_conversation_is_private():
    a = Fake("A", [Decision(say="psst, B", to=["B"])])
    b = Fake("B", [Decision()])
    c = Fake("C", [Decision(), Decision()])
    g = game([a, b, c], duration=30, idle_quiet=15)
    g.step()
    g.step()
    assert not any(m["text"] == "psst, B" for m in c.seen[1]["conversation"])
    assert any("quietly" in x for x in c.seen[1]["inbox"])


def test_take_down_notifies_owner():
    a = Fake("A", [Decision(do="build", strokes=[{"type": "line", "x0": 5, "y0": 5, "x1": 7, "y1": 5, "spacing": 0.5}])])
    b = Fake("B", [Decision(), Decision(), Decision(), Decision(do="take_down", area=[4, 4, 8, 6])])
    g = game([a, b], duration=120, idle_quiet=15)
    g.run()
    assert len(g.world.dominoes) == 0
    assert any("took down" in x for s in a.seen for x in s["inbox"]) or \
        any("took down" in x for x in g.inbox["A"])


def test_inspect_reports_back():
    a = Fake("A", [Decision(do="build", strokes=[LINE], start=True), Decision(do="inspect", area=[0, 0, 20, 10])])
    g = game([a], duration=240, idle_quiet=1e9, max_quiet=1e9)
    g.run()
    text = " ".join(x for s in a.seen for x in s["inbox"]) + " ".join(g.inbox["A"])
    assert "You look closely" in text and "#" not in text


def test_push_scores_live_game():
    a = Fake("A", [Decision(do="build", strokes=[LINE], start=True)])
    g = game([a], duration=300, idle_quiet=1e9, max_quiet=1e9)
    res = g.run()
    assert res["per_table"]["table"]["completion"] == 1.0


def test_short_remarks_share_a_beat():
    a = Fake("A", [Decision(say="Cat?", eagerness=9)])
    b = Fake("B", [Decision(say="Sure, cat works.", eagerness=3)])
    g = game([a, b], duration=15)
    g.step()
    assert len(g.log["turns"][0]["conversations"]) == 2 and not g.log["turns"][0]["held"]


def test_name_mention_wakes_busy_builder():
    a = Fake("A", [Decision(do="build", strokes=[LINE]), Decision(do="continue")])
    c = Fake("C", [Decision(say="A, can you leave room for the tail?")])
    g = game([a, c], duration=30, idle_quiet=1e9, max_quiet=1e9)
    g.step()
    g.step()
    assert len(a.seen) == 2


def test_pointing_is_seen_on_map_and_in_words():
    a = Fake("A", [Decision(do="build", strokes=[LINE], start=True)])
    b = Fake("B", [Decision(), Decision(say="Continue from here", point=[9, 5])])
    c = Fake("C", [Decision(), Decision(), Decision()])
    g = game([a, b, c], duration=200, idle_quiet=1e9, max_quiet=1e9)
    for _ in range(9):
        g.step()
    b.script[0] = Decision()
    g.wake["B"].append("test")
    g.step()
    g.wake["C"].append("test")
    g.step()
    seen = c.seen[-1]
    said = [m for m in seen["conversation"] if m["speaker"] == "B"][-1]
    assert "pointing" in said and "line" in said["pointing"]
    assert "b" in seen["map"]


def test_extend_and_connect_join_two_pieces():
    from orgsim.dominoes import Physics
    phys = Physics(bump_chance=0.0)             # normal hand error, no bumps
    for seed in range(5):
        a = Fake("A", [Decision(do="build", strokes=[{"type": "line", "x0": 5, "y0": 20, "x1": 10, "y1": 20}], start=True)])
        b = Fake("B", [Decision(do="build", strokes=[{"type": "line", "x0": 20, "y0": 14, "x1": 26, "y1": 14}])])
        g = LiveGame(table_world(phys=phys), [a, b], LiveConfig(duration=600, idle_quiet=1e9, max_quiet=1e9, seed=seed, announce_at=()))
        while g.t < 150:
            g.step()
        connect = Decision(do="build", strokes=[{"type": "connect", "from": [10, 20], "to": [20, 14]}])
        a.script += [Decision()] * (len(a.seen) - len(a.script)) + [connect]
        g.wake["A"].append("test")
        res = g.run()
        assert res["per_table"]["table"]["completion"] == 1.0, seed


def test_freehand_strokes_land_roughly():
    import random
    from orgsim.handwork import freehand_specs
    rng = random.Random(0)
    offs = [freehand_specs({"type": "domino", "x": 10, "y": 10, "angle": 0}, rng)[0] for _ in range(200)]
    mean_err = sum(((x - 10) ** 2 + (y - 10) ** 2) ** 0.5 for x, y, _ in offs) / len(offs)
    assert 0.2 < mean_err < 0.6


def test_facilitator_calls_time_and_start_status():
    a = Fake("A", [Decision(), Decision()])
    g = LiveGame(table_world(phys=EXACT), [a], LiveConfig(duration=180, idle_quiet=1e9, max_quiet=1e9,
                                                           announce_at=(2,)))
    g.run()
    assert any(m["speaker"] == "Facilitator" for m in a.seen[-1]["conversation"])
    assert "no start domino" in a.seen[-1]["start_status"]


def test_fix_nudges_a_too_sharp_turn():
    import random
    from orgsim.dominoes import Region, World
    from orgsim.handwork import fix_specs
    w = World([Region("table", 0, 0, 60, 40)], {"table": 99}, EXACT)
    rng = random.Random(0)
    w.place([(5, 5, 0), (5.55, 5, 0), (6.1, 5, 0), (6.6, 5.3, 55), (6.9, 5.75, 55)], "a", 0, "table",
            ["table"], rng, max_n=9, start_index=0)
    assert len(w.reachable_from_start()) == 3
    ops, note = fix_specs(w, {"type": "fix", "at": [6.2, 5]}, 40)
    assert ops and ops[0][0] == "move", note
    for op in ops:
        w.move(op[1], *op[2], rng) if op[0] == "move" else w.place([op[1]], "a", 0, "table", ["table"], rng)
    assert len(w.reachable_from_start()) == 5


def test_scratch_pad_pick_up_sketch_pass_and_taken_away():
    sketch = [{"type": "curve", "points": [[10, 10], [20, 8], [30, 10]]}, {"type": "label", "x": 20, "y": 12, "text": "fish"}]
    a = Fake("A", [Decision(pad="take", eagerness=8, do="build", strokes=[LINE]),
                   Decision(sketch=sketch, pad="give", pad_to="B")])
    b = Fake("B", [Decision(pad="take", eagerness=2), Decision(), Decision()])
    g = LiveGame(table_world(phys=EXACT), [a, b], LiveConfig(duration=150, idle_quiet=15, max_quiet=15,
                                                           announce_at=(), scratchpad_until=60, seed=0))
    g.step()
    assert g.pad_holder == "A"
    assert any("picked up the scratch pad before you" in x for x in g.inbox["B"])
    built_before = len(g.world.dominoes)
    g.step()                                       # A sketches (hands busy), then hands the pad to B
    assert g.pad_holder == "B" and len(g.pad_strokes) == 2
    assert len(g.world.dominoes) == built_before   # no building in a beat spent sketching
    assert "B's hands" in g.pad_status("A")
    while g.t < 75:
        g.step()
    assert not g.pad_exists and g.log["scratchpad"]["final"] == sketch
    assert "gone" in g.pad_status("A")


def test_snap_start_and_end_join_make_one_chain():
    from orgsim.dominoes import Physics
    phys = Physics(bump_chance=0.0)               # normal hand error
    ok = 0
    for seed in range(10):
        a = Fake("A", [Decision(do="build", start=True,
                                strokes=[{"type": "line", "x0": 5, "y0": 10, "x1": 10, "y1": 10}]),
                       Decision(do="build",       # carries on by eye from roughly where the line ends
                                strokes=[{"type": "line", "x0": 10.8, "y0": 10.3, "x1": 16, "y1": 12}])])
        b = Fake("B", [Decision(do="build",        # a separate piece just ahead
                                strokes=[{"type": "line", "x0": 17.5, "y0": 12.5, "x1": 22, "y1": 14}])])
        g = LiveGame(table_world(phys=phys), [a, b], LiveConfig(duration=400, idle_quiet=1e9, max_quiet=1e9,
                                                               announce_at=(), scratchpad_until=None, seed=seed))
        res = g.run()
        ok += res["per_table"]["table"]["completion"] == 1.0
    assert ok >= 8, ok


def test_people_differ_in_speed_and_accuracy():
    import math
    from orgsim.dominoes import Physics
    phys = Physics(bump_chance=0.0)
    lines = {"Fast": 5, "Slow": 15}
    agents = [Fake(n, [Decision(do="build", strokes=[{"type": "line", "x0": 2, "y0": y, "x1": 40, "y1": y}])])
              for n, y in lines.items()]
    cfg = LiveConfig(duration=120, idle_quiet=1e9, max_quiet=1e9, announce_at=(), scratchpad_until=None,
                     snap=False, freehand_sigma=0.0,
                     skills={"Fast": {"speed": 1.6, "error": 2.0}, "Slow": {"speed": 0.6, "error": 0.5}})
    g = LiveGame(table_world(phys=phys), agents, cfg)
    g.run()
    mine = {n: [d for d in g.world.dominoes.values() if d.builder == n] for n in lines}
    assert len(mine["Fast"]) > 2 * len(mine["Slow"])
    spread = {n: sum(abs(d.y - lines[n]) for d in ds) / len(ds) for n, ds in mine.items()}
    assert spread["Fast"] > 2 * spread["Slow"]


def test_re_issuing_a_trace_of_stroke_1_does_not_deadlock():
    sketch = [{"type": "curve", "points": [[4, 10], [10, 7], [18, 6]]}]
    tr = {"type": "trace", "stroke": 1}
    a = Fake("A", [Decision(pad="take", eagerness=9), Decision(sketch=sketch, pad="put_down"),
                   Decision(do="build", strokes=[tr]), Decision(do="build", strokes=[tr]), Decision(do="continue")])
    g = LiveGame(table_world(phys=EXACT), [a], LiveConfig(duration=300, idle_quiet=15, max_quiet=15,
                                                           announce_at=(), scratchpad_until=300, seconds_per_domino=3))
    res = g.run()
    assert res["per_table"]["table"]["placed"] > 10 and res["per_table"]["table"]["completion"] > 0.9


def test_tracing_a_stroke_someone_else_is_laying_is_refused():
    sketch = [{"type": "curve", "points": [[4, 10], [10, 7], [18, 6]]}]
    tr = {"type": "trace", "stroke": 1}
    a = Fake("A", [Decision(pad="take", eagerness=9), Decision(sketch=sketch, pad="put_down"),
                   Decision(do="build", strokes=[tr])] + [Decision(do="continue")] * 20)
    b = Fake("B", [Decision(), Decision(), Decision(), Decision(do="build", strokes=[tr])] + [Decision()] * 20)
    g = LiveGame(table_world(phys=EXACT), [a, b], LiveConfig(duration=120, idle_quiet=15, max_quiet=15,
                                                              announce_at=(), scratchpad_until=300, seconds_per_domino=3))
    for _ in range(6):
        g.step()
    assert any("already laying stroke 1" in x for o in b.seen for x in o["inbox"])


def test_pad_tables_ignore_a_second_start():
    sketch = [{"type": "curve", "points": [[4, 10], [10, 7], [18, 6]]},
              {"type": "curve", "points": [[18, 6], [20, 10], [18, 14]]}]
    a = Fake("A", [Decision(pad="take", eagerness=9), Decision(sketch=sketch, pad="put_down"),
                   Decision(do="build", strokes=[{"type": "trace", "stroke": 1}])] + [Decision(do="continue")] * 30)
    b = Fake("B", [Decision(), Decision(), Decision(),
                   Decision(do="build", strokes=[{"type": "trace", "stroke": 2}], start=True)] + [Decision()] * 30)
    g = LiveGame(table_world(phys=EXACT), [a, b], LiveConfig(duration=300, idle_quiet=15, max_quiet=15, pad_only=True,
                                                              announce_at=(), scratchpad_until=300, seconds_per_domino=3))
    g.run()
    starts = [d for d in g.world.dominoes.values() if d.start]
    assert len(starts) == 1 and starts[0].x < 6


def test_redrawing_start_moves_the_start_when_stroke_1_is_traced_again():
    s1 = [{"type": "curve", "points": [[4, 10], [10, 7], [18, 6]]}]
    s2 = [{"type": "curve", "points": [[18, 14], [12, 13], [6, 14]]}]
    tr = {"type": "trace", "stroke": 1}
    a = Fake("A", [Decision(pad="take", eagerness=9), Decision(sketch=s1),
                   Decision(do="build", strokes=[tr])] + [Decision(do="continue")] * 8
             + [Decision(sketch_clear=True, sketch=s2), Decision(do="build", strokes=[tr])] + [Decision(do="continue")] * 30)
    g = LiveGame(table_world(phys=EXACT), [a], LiveConfig(duration=600, idle_quiet=15, max_quiet=15, pad_only=True,
                                                           announce_at=(), scratchpad_until=600, seconds_per_domino=3))
    g.run()
    starts = [d for d in g.world.dominoes.values() if d.start]
    assert len(starts) == 1 and starts[0].x > 15 and starts[0].y > 12


def test_dictator_gates_building_and_the_pad():
    sketch = [{"type": "curve", "points": [[4, 10], [10, 7], [18, 6]]}]
    tr = {"type": "trace", "stroke": 1}
    d = Fake("D", [Decision(pad="take", eagerness=9), Decision(sketch=sketch, pad="put_down"),
                   Decision(do="build", strokes=[tr]), Decision(decide="Fish")] + [Decision(do="continue")] * 30)
    o = Fake("O", [Decision(pad="take", eagerness=10)] + [Decision()] * 40)
    g = LiveGame(table_world(phys=EXACT), [d, o], LiveConfig(duration=300, idle_quiet=15, max_quiet=15, pad_only=True,
                 announce_at=(), scratchpad_until=300, decision="dictator", dictator="D"))
    for _ in range(3):
        g.step()
    assert g.pad_strokes and not g.world.dominoes          # D drew; build refused before the call
    assert any("Only D draws" in x for ob in o.seen for x in ob["inbox"])
    assert any("can't start building yet" in x for x in g.inbox["D"] + [y for ob in d.seen for y in ob["inbox"]])
    g.step()
    assert g.decided == "fish" and g.building_open()


def test_consensus_opens_only_when_everyone_agrees():
    a = Fake("A", [Decision(aligned="fish"), Decision(), Decision()])
    b = Fake("B", [Decision(aligned="cat"), Decision(aligned="Fish"), Decision()])
    g = LiveGame(table_world(phys=EXACT), [a, b], LiveConfig(duration=120, idle_quiet=15, max_quiet=15,
                 announce_at=(), scratchpad_until=None, decision="consensus"))
    g.step()
    assert not g.building_open()
    g.step()
    assert g.building_open() and g.decided == "fish"


def _role_game(mode, agents, designer="D"):
    roles = {"D": "design", "E": "eng", "P": "pm"}
    seen = []

    def checker(kind, name, strokes, note):
        seen.append((kind, name))
        return f"result of {kind}"
    g = LiveGame(table_world(phys=EXACT), agents, LiveConfig(duration=300, idle_quiet=15, max_quiet=15, pad_only=True,
                 announce_at=(), scratchpad_until=300, roles=roles, design_mode=mode, designer=designer),
                 checker=checker)
    return g, seen


SK = [{"type": "curve", "points": [[4, 10], [10, 7], [18, 6]]}]


def test_review_needs_every_other_role_before_lock_and_checks_are_role_gated():
    d = Fake("D", [Decision(pad="take", eagerness=9), Decision(sketch=SK, lock=True), Decision(lock=True)]
             + [Decision()] * 20)
    e = Fake("E", [Decision(), Decision(check="squint"), Decision(review="joins look fine", check="dry_run")]
             + [Decision()] * 20)
    p = Fake("P", [Decision(), Decision(), Decision(review="client wants it bigger")] + [Decision()] * 20)
    g, seen = _role_game("review", [d, e, p])
    for _ in range(2):
        g.step()
    assert g.locked_at is None and not g.building_open()          # tried to lock before reviews
    for _ in range(6):
        g.step()
    assert any("Only the Design" in x for x in g.inbox["E"] + [y for o in e.seen for y in o["inbox"]])
    assert set(g.reviews) == {"E", "P"} and ("dry_run", "E") in seen
    assert g.locked_at is not None and g.building_open()


def test_lone_designer_owns_pad_and_lock():
    d = Fake("D", [Decision(pad="take", eagerness=5), Decision(sketch=SK), Decision(lock=True)] + [Decision()] * 20)
    e = Fake("E", [Decision(pad="take", eagerness=9), Decision(lock=True)] + [Decision()] * 20)
    p = Fake("P", [Decision()] * 20)
    g, _ = _role_game("lone", [d, e, p])
    for _ in range(4):
        g.step()
    assert g.pad_holder in ("D", None) and g.locked_at is not None
    assert any(ev["type"] == "lock" and ev["who"] == "D" for r in g.log["turns"] for ev in r["events"])
