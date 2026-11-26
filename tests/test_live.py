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
        g = LiveGame(table_world(phys=phys), [a, b], LiveConfig(duration=600, idle_quiet=1e9, max_quiet=1e9, seed=seed))
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
