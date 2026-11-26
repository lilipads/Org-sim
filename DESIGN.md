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
7. The round has a **time limit**: 10 turns of 2 game-minutes each *(tune)*.

### 3.3 Physical realism: placement error and bumps

These are the main sources of risk. They make overstaffing hurt physically, not just
conversationally.

- **Placement error.** No hand is perfectly steady. Every domino ends up slightly off from where it
  was intended: about **0.05 units** in position and **3°** in angle (standard deviation) *(tune)*.
  Spacing in the middle of the allowed range is safe. Spacing or turns near the limits are faster, use
  fewer dominoes and allow tighter curves, but they sometimes leave a gap that nobody notices without
  inspecting. Risk is a matter of degree, not a coin flip.
- **Bumping.** Each builder has a chance of bumping for each *other* builder working within 3 units that
  turn (**6%** each *(tune)*). A bump knocks over a nearby standing domino. It falls forward along its
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
- Round-1 pictures stay where they are. Teams may change or take down any part of them, but nothing
  forces them to.
- **Supply:** each table keeps its leftover dominoes, plus a **shared pool of 60 connector dominoes**
  *(tune)* for the row, first come, first served.
- **Time limit:** 6 turns *(tune)*.
- **Score:** pass or fail for the full row, the number of pictures revealed within the limit, and the
  judge's score for each revealed picture.

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
- Agents **decide simultaneously** each turn. Calls within a turn run in parallel.

### 4.2 Personas

Each agent has a name and a short persona written in plain words, for example "You like to get your
hands dirty," "You have strong opinions about design," "You tend to look at the big picture," or
"You're careful and like to double-check."

- **Heterogeneous** (default): a fixed set of 10 personas covering builders, design-opinionated people,
  big-picture people, cautious people and risk-takers. A table of 4 uses a fixed, balanced subset.
- **Homogeneous**: everyone gets the same neutral persona and only names differ. This tests whether roles
  emerge without personality differences.

### 4.3 Memory: no shared blueprint

There is **no plan file**. Each agent keeps **its own notes**, a short scratchpad it rewrites every
turn. The notes hold its understanding of the design ("fox facing left, I'm doing the tail, bottom
right"). Two agents can leave the same discussion with different pictures in their heads, so alignment
has to be maintained while building.

### 4.4 What an agent sees each turn

- The rules, its persona, and its **evaluation condition** (§6).
- The clock (turn number and turns left) and the remaining supply.
- **Its own table, in full**, as an ASCII map with one character per unit, coordinate rulers, an arrow
  showing roughly which way each domino faces, and marks for dominoes knocked over by bumps. The map is
  approximate. **Inspect** gives exact positions and angles. Everyone can see the table, but they can't
  tell who built what unless someone says so.
- In round 2: a **coarse view** of the other tables, and the detailed view only when visiting.
- Everything said in conversations it took part in last turn.
- **Notices** about other activity: "Agent 3 and Agent 7 are talking," "a bump knocked down 9 dominoes
  near (12, 30)," "someone took down 6 dominoes in the top-left."
- Its own notes.

### 4.5 Actions (one per turn)

| Action | Parameters | Effect |
|---|---|---|
| **Talk** | audience: `everyone` or named agents; message | Starts or joins a conversation. **Everyone addressed is pulled in and spends the turn in it, even if they meant to build.** |
| **Listen** | — | Joins the table-wide conversation without speaking |
| **Build** | up to **8 dominoes** *(tune)*, described as strokes: a single domino (x, y, angle); a straight line (from, to, spacing); or an arc (centre, radius, start and end angle, spacing). Optional start mark | Places or re-stands dominoes. Dominoes in a line or arc face along the stroke automatically. Each one gets placement error, and the builder may bump others |
| **Take down** | an area (rectangle or circle) | Removes up to **12 dominoes**, whoever built them; they return to the supply |
| **Inspect** | an area | Lists exact positions and angles there, and flags pairs that wouldn't knock each other over: gaps, sharp turns, safety gaps not yet closed |
| **Visit** (round 2) | another table or a gap strip | The agent spends the turn there: it sees it in detail and can talk or build there |
| **Wait** | — | Nothing |

### 4.6 How a turn is resolved

1. **Decide:** every agent returns an action and its updated notes, in parallel.
2. **Talk:** conversation groups form from the speakers, their named audiences, and anyone who chose
   Listen. Any builder who was addressed is interrupted, and their build is cancelled. Each group gets
   **up to 2 exchanges**. In the first exchange, speakers' messages are shown in random order. Then
   every member, including those pulled in, gets one reply call. People outside a conversation see only
   that it happened.
3. **Take downs**, then **builds** (applying placement error and rolling for bumps), then **inspections**.
4. **Notices** are generated, and everything is logged with who did what.

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

## 13. Architecture (planned)

```
orgsim/
  dominoes.py     continuous positions and angles, hit physics, placement error, bumps, push and topple, timing
  render.py       ASCII board views (for agents), images and animations (for judges and the blog)
  game.py         turn loop, conversations, action resolution, round 1 and 2, logging
  agents/
    llm.py        prompt building, calls through Claude Code non-interactive mode, JSON parsing, retries
    scripted.py   simple scripted agents for tests and calibration
    rules.py      rules-based model (§9)
  review.py       manager, peer and automatic ratings; true contribution
  judge.py        blind judging and intent matching
  metrics.py      metrics from logs (§8)
experiments/      one config per experiment; batch runner that resumes after interruptions
viewer/           replay viewer page
results/          run logs and charts
```

The existing MarbleGrid prototype (`orgsim/marble.py`, `orgsim/solver.py`) will be removed once
`dominoes.py` exists.

## 14. Defaults I chose (please confirm or change)

- Table 60 × 40 units (1 unit = 1 domino height); a domino knocks over others 0.2–0.9 units ahead,
  within 0.35 units to the side and 40° of its angle; placement error 0.05 units and 3°.
- 250 dominoes, 8 dominoes per build, 6% bump chance per nearby builder.
- Round 1: 10 turns of 2 game-minutes. Round 2: 6 turns, a 30-second limit, 60 shared connector
  dominoes, a 6-unit-wide gap strip.
- Rows of 3 tables in round 2 (scaled down from 5).
- 5 runs per condition.
- Up to 2 exchanges per conversation per turn.
- Reviews run on round 1 only (one table), at size 4.
- Evaluated agents get the promotion-and-bonus line.
