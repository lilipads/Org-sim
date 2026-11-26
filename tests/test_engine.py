import random

from orgsim.designs import LIBRARY, check_design
from orgsim.dominoes import Physics, Region, World, expand_stroke
from orgsim.game import Action, Agent, Game, GameConfig, gallery_world, table_world

EXACT = Physics(pos_sigma=0.0, angle_sigma=0.0, bump_chance=0.0)


def world(phys=EXACT, supply=500):
    return World([Region("T", 0, 0, 60, 40)], {"T": supply}, phys)


def place(w, specs, start=True):
    return w.place(specs, "a", 1, "T", ["T"], random.Random(0), max_n=len(specs),
                   start_index=0 if start else None)


# ---- physics ----------------------------------------------------------------

def test_straight_line_falls():
    w = world()
    place(w, expand_stroke({"type": "line", "x0": 5, "y0": 5, "x1": 15, "y1": 5, "spacing": 0.5}))
    times = w.topple([d.id for d in w.dominoes.values() if d.start])
    assert len(times) == len(w.dominoes) == 21


def test_gap_too_wide_stops_chain():
    w = world()
    place(w, [(5, 5, 0), (5.5, 5, 0), (6.6, 5, 0)])      # second gap 1.1 > reach 0.9
    assert len(w.topple([1])) == 2


def test_sharp_turn_stops_chain():
    w = world()
    place(w, [(5, 5, 0), (5.5, 5, 0), (6.0, 5, 60)])     # 60 deg turn > 40
    assert len(w.topple([1])) == 2


def test_split_into_two_lines():
    w = world()
    place(w, [(5, 5, 0), (5.5, 4.75, -20), (5.5, 5.25, 20)])
    assert len(w.topple([1])) == 3


def test_hit_zone_far_corner_falls():
    w = world()
    place(w, [(5, 5, 0), (5.88, 5.33, 0)])               # 0.88 ahead, 0.33 aside: 0.94 away
    assert len(w.topple([1])) == 2


def test_arc_curves_and_falls():
    w = world()
    place(w, expand_stroke({"type": "arc", "cx": 20, "cy": 20, "r": 4, "a0": 0, "a1": 270, "spacing": 0.55}))
    assert len(w.topple([1])) == len(w.dominoes)


def test_cannot_place_on_top_of_another():
    w = world()
    r = place(w, [(5, 5, 0), (5.05, 5, 0)])
    assert len(r.placed) == 1 and "too close" in r.blocked[0][2]


def test_supply_runs_out():
    w = world(supply=3)
    r = place(w, [(5 + 0.5 * k, 5, 0) for k in range(6)])
    assert len(r.placed) == 3 and w.supply["T"] == 0


def test_inspect_reports_line_end_reason():
    w = world()
    place(w, [(5, 5, 0), (5.5, 5, 0), (6.6, 5, 0)])
    rep = w.inspect(0, 0, 60, 40)
    ends = {e["id"]: e["why"] for e in rep["line_ends"]}
    assert "too far" in ends[2]
    assert rep["not_reached_from_start"] == 1


def test_library_designs_are_buildable():
    for f in LIBRARY.values():
        r = check_design(f())
        assert r["fell"] >= 0.95 * r["n"], r


# ---- game -------------------------------------------------------------------

class Scripted(Agent):
    def __init__(self, name, actions, home="table"):
        super().__init__(name, home)
        self.actions = actions

    def decide(self, obs):
        return self.actions.get(obs["turn"], Action("wait"))


def run(agents, turns=1, **cfg):
    g = Game(table_world(phys=EXACT), agents, GameConfig(turns=turns, **cfg))
    g.run()
    return g


def test_addressed_builder_is_pulled_in():
    a = Scripted("A", {1: Action("talk", to=["B"], message="hi B")})
    b = Scripted("B", {1: Action("build", strokes=[{"type": "domino", "x": 5, "y": 5, "angle": 0}])})
    c = Scripted("C", {1: Action("build", strokes=[{"type": "domino", "x": 9, "y": 5, "angle": 0}])})
    g = run([a, b, c])
    t = g.log["turns"][0]
    assert t["conversations"][0]["pulled_in"] == ["B"]
    builders = {g.world.dominoes[i].builder for i in g.world.dominoes}
    assert builders == {"C"}
    assert any("A, B were talking" in n for n in g.notices["C"])


def test_everyone_talk_reaches_listeners_only():
    a = Scripted("A", {1: Action("talk", message="let's do a fox")})
    b = Scripted("B", {1: Action("listen")})
    c = Scripted("C", {1: Action("build", strokes=[{"type": "domino", "x": 9, "y": 5, "angle": 0}])})
    g = run([a, b, c])
    assert g.heard["B"] and g.heard["B"][0]["messages"][0]["message"] == "let's do a fox"
    assert g.heard["C"] == []
    assert len(g.world.dominoes) == 1


def test_strict_mode_pulls_in_whole_table():
    a = Scripted("A", {1: Action("talk", to=["B"], message="hi")})
    c = Scripted("C", {1: Action("build", strokes=[{"type": "domino", "x": 9, "y": 5, "angle": 0}])})
    g = run([a, Scripted("B", {}), c], talk_mode="strict")
    assert len(g.world.dominoes) == 0


def test_take_down_others_work_returns_supply():
    line = [{"type": "line", "x0": 5, "y0": 5, "x1": 8, "y1": 5, "spacing": 0.5}]
    a = Scripted("A", {1: Action("build", strokes=line, start=True)})
    b = Scripted("B", {2: Action("take_down", area=[4, 4, 9, 6])})
    g = run([a, b], turns=2)
    assert len(g.world.dominoes) == 0 and g.world.supply["table"] == 250
    ev = [e for e in g.log["turns"][1]["events"] if e["type"] == "take_down"][0]
    assert ev["whose"] == {"A": 7}


def test_push_is_non_destructive_and_scored():
    line = [{"type": "line", "x0": 5, "y0": 5, "x1": 8, "y1": 5, "spacing": 0.5}]
    g = run([Scripted("A", {1: Action("build", strokes=line, start=True)})])
    res = g.log["push"]
    assert res["per_table"]["table"]["completion"] == 1.0
    assert all(d.state == "up" for d in g.world.dominoes.values())
    assert all(d.state == "down" for d in g.pushed_world.dominoes.values())


def test_crowded_builders_bump():
    phys = Physics(pos_sigma=0, angle_sigma=0, bump_chance=1.0)
    w = table_world(phys=phys)
    line = lambda y: [{"type": "line", "x0": 5, "y0": y, "x1": 8, "y1": y, "spacing": 0.5}]  # noqa: E731
    agents = [Scripted("A", {1: Action("build", strokes=line(5)), 2: Action("build", strokes=line(6))}),
              Scripted("B", {2: Action("build", strokes=line(7))})]
    g = Game(w, agents, GameConfig(turns=2))
    g.run()
    bumps = [e for e in g.log["turns"][1]["events"] if e["type"] == "bump"]
    assert bumps and any(d.state == "down" for d in w.dominoes.values())


def test_gallery_world_keeps_round1_pictures():
    w1 = table_world("Table 1", phys=EXACT)
    w2 = table_world("Table 2", phys=EXACT)
    for w, reg in ((w1, "Table 1"), (w2, "Table 2")):
        w.place([(5, 5, 0), (5.5, 5, 0)], "a", 1, reg, [reg], random.Random(0), start_index=0)
    room, start = gallery_world([w1, w2])
    assert start == "Table 1"
    assert set(room.regions) == {"Table 1", "gap 1-2", "Table 2"}
    assert len(room.dominoes) == 4
    assert room.regions["Table 2"].x0 == 66
    assert room.supply["shared"] == 60


def test_walking_is_free():
    phys = EXACT
    w1, w2 = table_world("Table 1", phys=phys), table_world("Table 2", phys=phys)
    room, start = gallery_world([w1, w2])
    a = Scripted("A", {1: Action("build", at="gap 1-2",
                                 strokes=[{"type": "domino", "x": 63, "y": 5, "angle": 0}])}, home="Table 1")
    g = Game(room, [a], GameConfig(round_no=2, turns=1, shared_pool="shared"), start_region=start)
    g.run()
    assert len(room.dominoes) == 1 and g.location["A"] == "gap 1-2"
