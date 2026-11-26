# Org-Sim: Domino Art — Design Spec

**Status:** draft for review · **Owner:** project lead · **Last updated:** 2026-11-26

This spec describes a simulation of organizational health using AI agents. It was inspired by an
offsite exercise in which tables of 10 people built ball runs from cardboard and straws, first per table,
then joined across tables. The simulation replaces the physical task with **Domino Art**. That task is
easy to picture, open-ended, and needs real collaboration. Teams draw an **animal**.

Numbers marked *(tune)* are starting values. The pilot (§10) adjusts them.

---

## 1. Purpose and audience

The output is a **series of blog posts** (Medium, reposted on LinkedIn). The tone is serious but not
academic: real agent transcripts, toppling animations, simple charts, and an honest "how much to trust
this" note on each post. There are about 5 runs per condition, and results are reported with ranges,
not significance tests.

## 2. Questions we want to answer

1. **Overstaffing.** How do tables of 1, 4 and 10 split time between talking and doing? When do extra
   people start costing more than they add?
2. **Duplicate work.** Do people with nothing to do start redundant work? How often does that redundant
   work become the backup that saves the team?
3. **Main bet vs. moonshot.** How much effort should go to an alternative bet?
4. **Inward vs. outward attention.** In the integration round, how much should a table look at its
   neighbors and at the joints between tables, rather than at its own work? How many people should step
   out to look at the whole system?
5. **Roles: emergent vs. assigned.** What breaks the symmetry when roles aren't assigned: personality, or
   simple path dependence? Do assigned roles (PM, TPM) help, and at what team size?
6. **Performance reviews.** How do different review styles change behavior? Do reviews reward the people
   who actually contributed?

---

## 3. The task: Domino Art

### 3.1 Brief

> *"Using dominoes, make a picture of **an animal**. When the time is up, your
> first domino is pushed. The picture is made of the dominoes that fall."*

The brief is open-ended: any animal, drawn any way. Teams choose what to draw. At the end, each team
states which animal it intended, and the judge never sees that statement.

### 3.2 Rules (the whole rulebook, as the agents see it)

Positions and angles are **continuous numbers**, not grid cells or a fixed set of directions. Distances
are measured in **domino heights**: a standing domino is 1 unit tall, so it reaches 1 unit when it falls.

1. The table is **60 × 40 units** *(tune)*. You stand a domino at any position (x, y), facing any angle
   (0–360°). It falls in the direction it faces.
2. A falling domino knocks over **any standing domino in its path** *(all limits tune)*:
   - the other domino is **0.2–0.9 units ahead** of it, measured along its falling direction;
   - it is **no more than 0.35 units to either side** of that falling line;
   - it faces **within 40°** of the falling domino's direction.

   The domino it knocks over then falls in *its own* direction, so a line can curve gradually. A sharper
   turn, or a gap that is too wide, stops the chain.
3. **Splitting and merging come for free.** A falling domino can knock over two dominoes standing side by
   side, so one line becomes two. A domino can also be knocked over by two different lines. There are no
   special pieces.
4. Each table has **250 dominoes** *(tune)*. The supply is the same whatever the team size.
5. At the end of the round, **one push** knocks over the team's marked start domino.
6. **Only dominoes knocked over by the push show in the picture.** Standing dominoes are invisible.
   Dominoes that were knocked over early (for example, by a bump) and never stood back up still show,
   but they break the chain at that point.
7. The round has a **time limit**: 20 minutes of game time *(tune)*. See §4.4 for how time works.

### 3.3 Physical realism: placement error and bumps

These are the main sources of risk. They make overstaffing hurt physically, not just
conversationally.

- **Placement error.** No hand is perfectly steady. Every domino ends up slightly off from where it
  was intended: about **0.05 units** in position and **3°** in angle (standard deviation) *(tune)*.
  Spacing in the middle of the allowed range is safe. Spacing or turns near the limits are faster, use
  fewer dominoes and allow tighter curves, but they sometimes leave a gap that nobody notices without
  inspecting. Risk is a matter of degree, not a coin flip.
- **Bumping.** Each builder has a chance of bumping for each *other* builder working within 6 units (about
  30 cm, a working arm's reach) that turn (**5%** each *(tune)*). A bump knocks over a nearby standing domino. It falls forward along its
  line, using the same physics, and keeps going until the line reaches a gap. The fallen dominoes must be
  stood back up. The risk grows with crowding, which is the overstaffing effect.
- **Safety gaps** (a technique bet). Builders may leave deliberate gaps so that a bump only knocks down
  one segment. Every safety gap must be closed before the push. A gap someone forgets leaves the rest of
  the line standing, so that part of the picture doesn't show.

### 3.4 Round 2: the Gallery Run

Teams **are not told about round 2** until round 1 is over.

- **Rows of 3 tables** are placed left to right, with a **6-unit-wide gap strip** between neighboring
  tables. The tables are scaled down from the offsite's 5 to keep the number of model calls
  manageable. The gap strips **belong to nobody**.
- **Goal:** **one push** at table 1 must reveal **all three pictures**, in sequence, **within 30 seconds**
  *(tune)*. Each domino takes about 0.1 seconds to fall into the next. The limit is set so that chaining naively from the end of each
  picture to the next table's start usually takes too long. Teams have to branch off mid-picture or take
  shortcuts, and every table's choices affect the time left for the others.
- Round-1 pictures stay where they are: the round-1 push is scored on a copy of the table, so the pictures
  are still standing. Teams may change or take down any part of them, but nothing forces them to.
- **Supply:** each table keeps its leftover dominoes, plus a **shared pool of 60 connector dominoes**
  *(tune)* for the row, first come, first served.
- **Time limit:** 6 turns *(tune)*.
- **Score:** pass or fail for the full row, the number of pictures revealed within the limit, and the
  judge's score for each revealed picture. A picture counts as **revealed** if at least **half** of its
  standing dominoes fall within the time limit *(tune)*.
- Whether a domino is on a table or in a gap is judged by where the builder **aimed**, not where it
  landed after placement error.

### 3.5 Judging (blind)

- The final board is rendered as an image showing **only the fallen dominoes**, each drawn lying flat in
  the direction it fell.
- **3 independent judge calls** each see only the image: "What does this picture show? Give your top 3
  guesses." They aren't told it's an animal, and they see no brief, no intent and no transcript.
- **Recognition score:** 1 if the first guess matches the team's stated intent, 0.5 if it appears in the
  top 3, and 0 otherwise. The three judges are averaged. A separate small-model call decides whether a
  guess matches the intent ("fox" vs. "red fox" counts as a match).
- Aesthetics are **not** scored.
- **Team score (round 1)** = recognition × completion. Completion is the share of placed dominoes that
  fell from the push.

---

## 4. Agents

### 4.1 Model and setup

- **One small, fast model for everything:** players, manager, peer reviewers and judges. The task tests
  coordination, not intelligence.
- Calls go through Claude Code's non-interactive mode in the cloud session, on the Pro plan. There is no
  API key. Each call uses a **minimal custom system prompt with tools disabled**, to keep usage per call
  low.
- Agents are asked to decide only when something calls for it (§4.5). Agents asked at the same moment
  are called in parallel.

### 4.2 Personas

Each agent has a name and a persona of three or four plain sentences. It covers how they work, how they
behave in groups (for example "you tend to take charge" or "you usually let others speak first"), and how
they talk. Example: *"You're careful and detail-oriented, and you'd rather check twice than redo
something. You're quieter in groups: you usually let others speak first and mainly speak up when you
see a risk or a mistake. Dry sense of humour."*

The rulebook describes the mechanics neutrally. It doesn't say whether talking is good or bad, and it
tells agents to talk naturally, in their own voice.

- **Heterogeneous** (default): a fixed set of 10 personas covering builders, design-opinionated people,
  big-picture people, cautious people and risk-takers. A table of 4 uses a fixed, balanced subset.
- **Homogeneous**: everyone gets the same neutral persona and only names differ. This tests whether roles
  emerge without personality differences.

### 4.3 Memory: no shared blueprint

There is **no plan file**. Each agent keeps **its own notes**, a short scratchpad it rewrites every
turn. The notes hold its understanding of the design ("fox facing left, I'm doing the tail, bottom
right"). Two agents can leave the same discussion with different pictures in their heads, so alignment
has to be maintained while building.

### 4.4 Time: a continuous clock (interaction model v2)

The first AI pilot used fixed turns with one action each. It felt unrealistic: everyone moved at the
same instant, so nobody could take the floor first, and you could talk *or* build but never both. The
rulebook also framed talking as a cost, and agents avoided it. Version 2 replaces turns with a clock.

- The round is **20 minutes** of game time, advancing in **15-second beats**.
- Placing a domino carefully takes about **10 seconds** (about **12 per 2 minutes**). A beat in which you
  speak, your hands work at half speed.
- **Work is "head down".** A build is a list of strokes, up to 40 dominoes. The engine places them over
  time without asking the agent again. Take-downs and inspections are tasks too: an inspection takes
  15 seconds and reports when done.

### 4.5 When an agent is asked to decide

An agent is asked only when something calls for it:
- the round starts;
- someone talks to them by name, or talks to the table. Agents choose which applies: "interrupt me for
  anything said to the table," or "only when someone talks to me." Either way they hear everything said
  to the table; the choice only decides whether it pulls their attention right away;
- their task finishes, or something happens to their work (a bump, someone taking it down);
- they were about to speak but someone else took the floor;
- a check-in: 2 minutes without being asked while busy, or 30 seconds while idle.

Each time, the agent can **say something and do something** in one decision:
- **Say:** free-form, to the table or to named people, with an **eagerness** from 1 to 10.
- **Do:** `continue`, `build` (strokes and/or re-standing an area, optional start mark), `take_down` (an
  area), `inspect` (an area), `stop`, or `walk` (round 2).
- Plus updated private notes and the interrupt preference.

### 4.6 Talking

- **Taking the floor.** If several people start talking to the table in the same beat, the most eager
  speaks first. Others also get in while the beat has room (about 40 words, roughly 15 seconds of
  speech). Anyone left over holds the thought and is asked again next beat, having heard what was said.
- **Who hears what.** Everyone at the table hears what's said to the table. Words said to named people
  are heard only by them; the others notice "Ava said something quietly to Ben."
- **Being addressed** no longer cancels your work: it gets your attention (you're asked), and you choose
  whether to stop and engage or keep going.
- Each agent sees the **last 5 minutes** of conversation it heard, with new lines marked.

### 4.7 What an agent sees when asked

- The rules, its persona, and its **evaluation condition** (§6).
- The clock (time elapsed and left), why it's being asked now, what its hands are doing, and the
  remaining supply.
- **Its own table, in full**, as an ASCII map with one character per unit, coordinate rulers, an arrow
  showing roughly which way each domino faces, and marks for knocked-over dominoes. Everyone can see the
  table, but they can't tell who built what unless someone says so.
- In round 2: a **coarse view** of the other tables.
- Recent conversation, things it noticed (bumps, take-downs, quiet side conversations), results of its
  own tasks (finished builds with exact end positions, inspection reports), and its own notes.

### 4.8 Version 1 (turn-based), kept for calibration

The original turn-based engine (`orgsim/game.py`) stays for the scripted calibration agents. Fixed
2-minute turns, one action per turn (talk, listen, build up to a cap, take down, inspect, visit, wait),
and addressed agents pulled into conversations.

---

## 5. Conditions (the dials)

| Dial | Values |
|---|---|
| Table size | **1, 4, 10** |
| Personas | heterogeneous (default), homogeneous |
| Roles | emergent (default); assigned: **PM** (owns decisions), **design lead**, builders; round 2 adds a **TPM/integrator** for each row |
| Alternative bets | emergent (default); deliberate (prompted: "you may hedge with a backup design"); assigned backup share of **0%, 25% or 50%** of agents |
| Evaluation | none (default), individual output, manager review, team outcome, peer review, *optional:* forced ranking |
| Talk mode | addressed people are pulled in (default); strict (any talk pulls in the whole table) |

## 6. Performance-review conditions

Agents are **told up front** whether they are evaluated, and they are given the explicit rubric. To give
the incentives some weight, evaluated agents are also told: *"Your rating decides your promotion and
bonus this cycle. You care about your career."*

| Condition | What agents are told | How the rating is produced |
|---|---|---|
| **None** | "No one is evaluating you individually. Just do your best." | — |
| **Individual output** | "You're rated on dominoes you placed that fell in the final picture." | Counted from the logs |
| **Manager review** | "A manager rates you on impact, collaboration and leadership (1–5)." | A **manager agent** walks around. Each turn it sees a random sample of about ⅓ of conversations, and a board snapshot every 3 turns, but no build logs. It keeps notes and writes ratings at the end |
| **Team outcome** | "Everyone receives the team's score." | Team score |
| **Peer review** | "Your teammates rate you on impact, collaboration and leadership (1–5)." | Each agent rates every teammate at the end |
| **Forced ranking** *(optional)* | Same as manager review, plus "ratings follow a fixed distribution: top 25%, middle 50%, bottom 25%." | The manager must rank |

**True contribution** is used to check whether reviews are accurate. The simulator knows it exactly:
- **Built:** dominoes the agent placed that fell in the final push.
- **Unlocked:** dominoes downstream of gaps or safety gaps that the agent fixed, if
  they fell in the final push.
- **Connectors:** connector dominoes the agent built in round 2.

---

## 7. Experiments, mapped to blog posts

Each combination has 5 runs *(tune)*. Runs are reused across experiments wherever the conditions match; for
example, E1's 4- and 10-person no-evaluation runs are the baselines for E3 and E5.

| # | Experiment | Conditions | Blog post |
|---|---|---|---|
| E1 | Team size | sizes 1 / 4 / 10, everything else default | *Too many cooks* |
| E2 | Roles | emergent vs. assigned × heterogeneous vs. homogeneous, at sizes 4 and 10 | *Born or assigned* |
| E3 | Alternative bets | emergent / deliberate / assigned 25% / assigned 50%, at size 10 | *Busywork and backup plans* |
| E4 | Integration (round 2) | emergent vs. one assigned TPM per row, tables of 4 (and 10 if budget allows) | *Who steps out* |
| E5 | Performance reviews | 5 (or 6) evaluation conditions, at size 4 (a subset at size 10 if budget allows) | *What gets measured* |

A first post, *The offsite*, introduces the exercise and the setup and needs no experiment.

## 8. Metrics

**Outcome**
- Completion, recognition and team score (round 1).
- In round 2: row success, pictures revealed, and seconds used.

**Time use**
- Share of agent-turns spent on each action.
- Turn of the first domino placed.
- Interruptions: builders pulled into conversations.

**Talk content.** Each message is labeled by a small-model classifier as one of:
- design debate;
- coordination or alignment;
- status update;
- credit claim or self-promotion;
- other.

**Waste**
- Dominoes knocked down by bumps.
- Dominoes taken down (own work vs. others').
- Duplicate work: dominoes built but never revealed.
- Edit wars: the same spot built and taken down repeatedly.

**Glue work.** The share of turns spent on:
- inspecting;
- fixing other people's gaps;
- closing safety gaps;
- building connectors;
- visiting.

**Bets**
- Backups started, their size, and whether a backup was the version connected.
- Safety-gap use.

**Roles**
- Each agent's mix of actions.
- How concentrated talk and decisions are, for example the share of design decisions coming from the top
  speaker.

**Review accuracy**
- The correlation between ratings and true contribution.
- Who is over-rated or under-rated: talkers? glue workers?

## 9. Rules-based model (companion, for sweep charts)

This is a no-AI version used for smooth "what if" charts, for example team sizes 1–12. It reuses the
same domino physics but represents ideas as numbers:

- The picture is a list of **parts** (about 5–8). Each part has a few **design choices** stored as
  numbers: facing, size and position.
- Each agent holds a **mental image**, its own numbers for each part, which start out random.
- **Talking** pulls participants' numbers toward each other, weighted by assertiveness. Larger groups
  converge more slowly. Assertive agents sometimes propose changes, which pushes the numbers apart again
  (bikeshedding). Agents who aren't in the conversation don't update.
- **Building** stamps the builder's current numbers onto the dominoes it places.
- **Talking to a neighbor** about a shared border makes the two sides meet in the middle. This fixes
  seams but not global incoherence.
- **Taking down** happens when built work differs strongly from an agent's mental image. Agents are
  more willing to take down their own work than other people's.
- **Coherence** (how consistent the stamped numbers are, between neighbors and across the whole picture)
  is converted into a probability that the judge recognizes the picture. That conversion is
  **calibrated from the LLM runs**.

All its behavior parameters are tuned so that it matches what the LLM agents actually did. The blog
makes clear which charts come from which source.

## 10. Pilot plan

1. **Engine and scripted agents.** Build the domino physics, rendering, turn resolution and logging, and
   test them with simple scripted agents (no AI).
2. **Calibration with scripted agents.** Tune the table size, hit limits, placement error, supply, dominoes per build and bump rate so
   that one person can finish only a simple picture, four people can finish a good one, and ten people
   can finish it in principle but face real crowding.
3. **One real run of 4 agents.** Measure calls, time, and Pro-plan usage per run. Check that agents
   understand the rules and that the board view is readable to them.
4. **Judge check.** Make sure blind judges can recognize clean pictures and fail on scrambled ones.
5. **Incentive check.** Run short pilots of the evaluation conditions and confirm that behavior shifts in
   a believable way, not an extreme one.
6. **Schedule** the full batches within the plan's usage windows. Results are committed to the repo after
   every batch, because the cloud container is temporary.

**Rough volume** *(to be replaced by pilot data)*:
- **Round 1 run:** about 10 / 60 / 150 calls for tables of 1 / 4 / 10, counting reply exchanges.
- **Round 2 run:** about 300 calls, including its three round-1 runs.
- **All experiments:** with runs reused, roughly 6,000–9,000 calls.

### 10.1 Stage 1 status (done): engine and scripted agents

Built and tested: physics, building, take-downs, inspection, bumps, conversations with pulled-in
listeners, free walking and visits, the non-destructive push, the round-2 gallery set-up, logs, judge
images, push animations, and the HTML replay. 18 engine tests pass.

What scripted calibration (no AI, 20 seeds) shows so far:
- **One person** can place at most 80 dominoes in 10 turns, so a solo table only finishes about
  half of a mid-sized animal. Solo players will have to pick a simple design.
- **Unowned seams.** Scripted agents repair only their own section. Breaks where two people's
  sections meet go unfixed, so 4- and 10-person tables lose 10–30% of the picture at seams, before any
  talking costs.
- **Bumping** depends heavily on reach. At 6 units, a table of 10 gets 1–2 bumps per round, knocking
  over 5–35 dominoes. Scripted agents re-stand them quickly.
- **The time box barely binds** for scripted 4- and 10-person tables, because they spend almost no
  turns talking. How much it binds for real agents is the main thing stage 3 measures.
- **Round 2 staffing.** Connecting table to table takes about 80 dominoes per gap. One connector
  builder per table can't finish in 6 turns; three can. That's an early hint for the "who steps out"
  post.

Open tuning questions for stage 3: dominoes per build (8 is conservative; careful hands manage about
12–20 per 2 minutes), table size, and whether round 2 needs more turns.

### 10.2 Stage 3 status: first AI runs

- **Run 1 (turn-based, table of 4).** It works technically: 61 calls, no failures, rules understood. But
  the behavior was unrealistic: two agents built before anyone spoke, two proposed at once, and nobody
  owned the joins. 33% of dominoes fell and the judges saw "a hill." This led to interaction model v2
  (§4.4–4.6).
- **Run 2 (real-time, table of 4):** in progress.

## 11. Deliverables

- A **replay viewer** for each run (HTML page): the board turn by turn, plus the chat, with a
  timeline of who did what.
- A **toppling animation** of each final push (GIF or animated SVG).
- **Charts** for each blog post comparing conditions.
- **Transcript excerpts** for each post, chosen from the logs.
- The run data: logs as JSON, committed to the repo.

## 12. Caveats to state in the posts

- These are AI agents, not people. They are agreeable, wordy, and all the same model underneath.
- Samples are small, so treat the results as illustrations, not proof.
- Prompt wording matters. Each post includes the exact rules and evaluation text the agents saw.
- The rules-based model only shows consequences of behavior we wrote in. It doesn't discover anything.

## 13. Architecture

```
orgsim/
  dominoes.py      continuous positions and angles, hit physics, placement error, bumps, push, inspection
  game.py          turn loop, conversations, actions, round-1 table and round-2 gallery set-up, logging
  render.py        ASCII map (for agents), judge images and push animations (for judges and the blog)
  replay.py        self-contained HTML replay of a run
  designs.py       hand-made animal designs (scripted agents only)
  agents/
    scripted.py    scripted agents for tests and calibration (no AI)
    llm.py         (stage 3) prompts and calls through Claude Code non-interactive mode
  review.py        (later) manager, peer and automatic ratings; true contribution
  judge.py         (stage 4) blind judging and intent matching
  metrics.py       (later) metrics from logs (§8)
experiments/
  calibrate.py     scripted calibration across table sizes
  demo_scripted.py both rounds end to end with scripted agents
tests/             engine tests
results/           run logs, replays, images
```

## 14. Defaults I chose (please confirm or change)

- Table 60 × 40 units (1 unit = 1 domino height); a domino knocks over others 0.2–0.9 units ahead,
  within 0.35 units to the side and 40° of its angle; placement error 0.05 units and 3°.
- 250 dominoes, about 12 dominoes per 2 minutes per person, 5% bump chance per 2 minutes per builder
  within 6 units.
- Round 1: 20 minutes in 15-second beats. Round 2: 6 turns, a 30-second limit, 60 shared connector
  dominoes, a 6-unit-wide gap strip.
- Rows of 3 tables in round 2 (scaled down from 5).
- 5 runs per condition.
- Up to 2 exchanges per conversation per turn.
- Reviews run on round 1 only (one table), at size 4.
- Evaluated agents get the promotion-and-bonus line.

## 15. Backlog: later posts

### Functional teams vs. embedded specialists (after the first three posts)

**Question.** Compare two ways of organizing the same people with the same skills:
- **Functional:** each specialist belongs to a functional team, such as designers (good at the overall
  picture) or builders (fast, steady hands). The functional teams serve several tables.
- **Embedded:** specialists sit at a table and work only on that table's picture.

Functional teams can bottleneck on availability. They also add back-and-forth between functions and
coordination (TPM) overhead. Embedded specialists avoid that, but each table gets fewer of them.

**What the engine needs, so this post is cheap to add later:**
- **Per-agent skill settings**, for example:
  - builders place more dominoes per turn, with less placement error;
  - designers place fewer, but can sketch a faint guide outline that everyone sees.
- **Agents who belong to a function but serve several tables**, with requests and queueing between
  tables and functional teams.
- An optional **TPM role** that only coordinates.

Status: parked. It isn't part of the first experiments.
