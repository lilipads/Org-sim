# Org-Sim: Domino Art

A simulation of organizational health with AI agents. Teams build a domino picture of an animal
under a time limit, then join their tables into one long run. The goal is to study overstaffing,
duplicate work, alternative bets, integration, emergent roles and performance reviews.

See [DESIGN.md](DESIGN.md) for the full spec.

## Status

Stage 1 is done: the domino engine, the turn loop and scripted (no-AI) agents. AI agents come next.

## Try it

Needs Python 3.11+ and Pillow (`pip install pillow`), plus pytest for the tests.

```bash
python3 -m pytest -q tests                 # engine tests
python3 experiments/calibrate.py           # scripted calibration: tables of 1, 4, 10
python3 experiments/demo_scripted.py       # both rounds; writes results/demo_scripted/
```

Open `results/demo_scripted/*.html` in a browser to replay a run turn by turn. Press **Push** to
watch the final push.
