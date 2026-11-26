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
- **Design legibility** (diagnostic): the same blind judging on the whole layout as if every domino had
  fallen. It separates "did the team share a clear picture?" from "did the chain hold together?" In
  the first runs it was 0 without the scratch pad ("a cap with a brim") and 1.0 with it ("fish"), while
  actual recognition was 0 in both because the chain broke early.
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

### 4.4a No rulers: building by hand and eye

There are no rulers at the table, so agents never get exact numbers:
- **Free-hand strokes** (a line, an arc, or a single domino aimed at a coordinate) land about a third of
  a unit off where they were aimed, turned a few degrees. Spacing within a stroke stays even.
- **Anchored strokes** are precise, because your hands line the new domino up against a real one:
  - `extend`: carry on from the line end nearest a spot (or branch off a line), curving toward another
    spot;
  - `connect`: join two pieces, from a line end to the domino nearest a target, arriving squarely behind
    it. The engine plans a smooth, buildable curve that routes around what's already on the table. It
    succeeds 99 times in 100 on random layouts with normal hand error.
- **Pointing:** while talking, an agent can point at a spot. Everyone sees the pointer's initial on
  their map, and the words say what is there ("the end of a line, facing right").
- **Seeing others' hands:** each agent sees roughly where the others are working ("Ava is building
  around (14, 18), on the left side of the table").
- **Looking closely** (inspect) reports in words and rough positions, with no domino numbers: where the
  chain looks broken and why, where lines end, and, tracing by eye from the start, how much of the table
  would fall and which pieces aren't connected.

### 4.4b Seeing the table: picture vs. text grid

Agents can see the table in one of two ways (a dial, `--view`):
- **text:** a 60 × 40 character grid. Each character is one unit of table, and an arrow shows roughly
  which way a domino faces (8 directions). It's coarse: two dominoes share most characters, small gaps
  and turns don't show, and the model reads it row by row. In runs 1–4 agents lost track of whose
  dominoes were whose, which way lines ran, and where the start was.
- **image** (current default for experiments): a picture of the table is attached to every decision.
  Dominoes are drawn as bars, with an orange tick on the side they'll fall toward. The start is ringed
  in green, and pointing and working hands are labelled. Grid lines are 1 unit apart and labelled
  every 5, so agents can still aim by coordinates. This is closest to what a person at the table sees.

### 4.4c The scratch pad (internal communication only)

A paper scratch pad lies on the table at the start. **Nobody holds it**, and anyone can pick it up.
- One holder at a time. The holder can sketch on it (curves, lines, circles and short labels, in table
  coordinates), hand it to someone, or put it down.
- Everyone at the table sees what's on it. With the picture view it's attached as a second picture.
- Sketching keeps your hands busy, so you place no dominoes in a beat spent sketching.
- At **2:00** the facilitator takes it away for good (`--pad-minutes`; 0 = no pad). After that, people
  work from memory and their own notes.
- It's **only a communication tool**. The final picture is never judged against the sketch. The sketch
  history is logged so we can see who picked it up and how it was used.
- It's a dial for the symmetry-breaking question: who reaches for the pad, and does holding it make
  them the leader?

### 4.4d Making the task humane (round of changes after run 6)

- **People, not archetypes.** Personas (version 3) give each person a job unrelated to the task (accounts
  payable, support, sales, data analysis, HR, an intern, facilities, marketing, legal, finance), mixed
  traits, a mood or quirk, and a way of talking. Nobody is written as the leader, builder or designer;
  any role has to emerge. The table of 4 is Maya, Tom, Priya and Leo.
- **No coordinates out loud.** Coordinates are only for the agent's own hands and eyes. Agents are told
  nobody can see them, so they point and describe ("the tail", "just past where Maya's line ends").
- **Bigger dominoes** (`--big`): the table is 30 × 20 domino lengths with 130 pieces. Hand error and bump
  range are halved relative to the pieces, as they would be with bigger blocks.
- **Natural lining up.** Starting a stroke right where a line ends lines its first domino up with that
  line (precise). A line that ends just behind the start of another line gets its last few dominoes
  bent so it runs into it (up to three lifted and re-laid). In tests, two separately built pieces join
  into one chain 18 times in 20.

### 4.4e Why the task was so hard, and what changed (after run 8)

Across eight pilot runs, tables built **5–11 separate pieces**, but the rules need **one connected
chain from one start**. Any broken joint hides everything after it, so a mostly good table showed
8–50%. (With three starts, most runs would have revealed 70–100%. We considered it and rejected it:
real domino runs have one start, and connecting is the point.) So the changes make connecting
natural rather than removing it:
- **Builder know-how in the rulebook.** Builders grow the run outward from the start, adding each
  stretch onto what's standing, so it stays connected. For a closed outline, the run comes to one
  point and splits into two lines around each side.
- **Seeing what will fall.** In the picture view, dominoes the start would knock over are drawn dark
  and unconnected ones pale, the way people trace a run by eye. The start-domino status line also
  says roughly how much it would knock over.
- **180 dominoes** with the bigger pieces. 130 ran out by minute 8 in run 8.

### 4.4f Personas v4 and an all-round scratch pad

- **Personas v4.** Version 3 still tied personality to job: the lawyer asked "are we sure?", the
  finance person was competitive, the intern was eager. In version 4 a job says nothing about how
  someone behaves. Jobs, traits and genders are mixed against type (an accountant who does pottery
  and lose track of time, a lawyer who is chatty and clumsy, a sales rep who's a patient birdwatcher
  and would rather listen). Each person has a few specific life details and a mix of tendencies, some
  of them pulling against each other. Nobody is written as a leader, builder, designer or checker.
- **The scratch pad stays all round** (default; `--pad-minutes N` to take it away at minute N, `0` for
  no pad). This keeps the shared picture available while building, to make the game easier.

### 4.4g Personas v5 and different hands

- **Personas v5: personality only.** No job titles or roles. Each person is a few sentences about how
  they are with people and with things, plus personal details (hobbies, habits) and tendencies that pull
  against each other.
- **Faster building:** about 5 seconds per domino on average (24 per 2 minutes), up from 10.
- **Different hands.** Each person gets their own speed (0.6–1.6× average) and accuracy (hand error
  0.5–2× average), drawn independently each run, so a table can have someone fast and careless and
  someone slow and precise. Agents aren't told their own numbers; they find out by watching the work.
  The draws are logged with each run (`skills` in the summary). `--same-hands` turns this off.

### 4.4h Redesign for a high success rate: the sketch becomes the plan hands follow

Across nine big-domino runs, one succeeded. Two failure modes multiplied: the build distorted the
sketch (shape legible in only 4 of 9) and the pieces didn't join into one run flowing from the start
(90%+ falling in only 1 of 9). Running out of dominoes made both permanent. The redesign:
- **Tracing.** Pad strokes are numbered, and START marks where stroke 1 begins. A build can say
  `{"type":"trace","stroke":k}`, and the builder's hands copy that stroke onto the table, with their
  own speed and accuracy. Coordinates are no longer needed to build.
- **Flow from the start.** The sketch is read as a run: strokes are oriented away from START along the
  sketch's connections, nearest first. A traced stroke carries on from (or branches off) the line it
  begins on. If that line hasn't arrived yet, the builder waits for it, which is a real dependency.
- **A split at the start** (e.g. the top and belly of a fish both leaving the nose): the start domino
  faces between the lines, and they split just after it.
- **Gentler copying turns** and **close crossings allowed** (lines crossing at a wide angle don't
  topple each other).
- **250 dominoes; 10-minute games; about 3 seconds per domino** on average, with per-person speed and
  accuracy as before.

Mechanics check with no AI (`experiments/check_tracing.py`): four scripted people trace a fish sketch
in shuffled orders with varied hands. 30 games each:
- without repairs: 19/30 games at 90%+ falling, mean 86%;
- with free hands fixing visible breaks: **25/30 at 90%+, 28/30 at 85%+, mean 94%**.

### 4.4i Batch 1 and the fixes after it

Batch 1 (six 10-minute AI games right after the tracing redesign): **4 of 6 recognized as a fish**,
against 1 of 9 before. The two failures came from sketch shapes the engine didn't handle:
- **Stroke through a junction:** a V tail drawn as one stroke through the start never counted as
  connected. Strokes are now split at connection points, and both halves flow outward.
- **Two lines leaving the same point at once:** both builders carried on from the same line end and
  collided. The second now branches off the side.
- **An impossible start:** lines leaving START in opposite directions can't be fed by one falling
  domino, so START moves to the nearest sketch end where the lines leave within about 100°.
- **Deadlock:** everyone waited on strokes that needed stroke 1, and nobody took stroke 1. Agents
  hear every 2 minutes that they're still waiting, and the rulebook says stroke 1 leaves the start.
- **Loops while tracing:** the copying hand now follows the drawn line by looking about 2 units ahead
  along it, instead of aiming at each point in turn. It can't loop and it cuts corners smoothly.

Scripted check after these fixes (20 games each, free hands repair breaks): typical fish 17/20 at
90%+ (mean 94%); lead-in sketch 17/20 (mean 93%); V-tail sketch 10/20 at 90%+, 15/20 at 85%+ (mean 88%).

### 4.4j Batches 2–3 and building only from the pad

- **Batch 2:** 4 of 8 recognized. The failures came from fix and connect spam wrecking good builds, and
  from weak sketches. Fix is now limited to small breaks (up to 5 dominoes); re-tracing a stroke lifts
  it and lays it again; the rulebook says the judge sees only the outline.
- **Batch 3:** 6 of 8 recognized (larger model 3/4, small 3/4). The table that keeps failing (table B,
  seed 2, both batches) drifted back to free-hand lines and connections.
- **Building only from the pad** (default; `--free-hand` restores the old strokes). Everything on the
  table is built by tracing pad strokes; to add something, sketch it on the pad first, then trace it.
  Hands still fix small breaks, stand knocked dominoes back up, take dominoes away and inspect. Who
  sketches, how the work is split, waiting on dependencies and repairs all remain; the free-hand
  failure route is gone.

### 4.4k Personas v6 and the model-call cache

- **Personas v6: personality only, described positively.** No jobs, hobbies, family, age or tenure:
  just how each person talks, decides and works with others, framed as strengths. They live in
  `orgsim/agents/personas.json`, fixed text that never needs generating.
- **Model-call cache** (`cache/llm/`, committed so later sessions reuse it). An identical call (same
  model, system prompt, prompt, tools and images) returns the saved answer instead of calling the
  model. Agent calls are salted with the run's seed: a rerun of the same seed replays for free (resume
  after a usage limit, regenerate a report), while a new seed samples afresh, so runs stay independent.
  Judging is cached per judge per picture, and the recap and "what animal" answers per seed.
  `ORGSIM_CACHE=0` turns it off.

### 4.5 When an agent is asked to decide

An agent is asked only when something calls for it:
- the round starts;
- someone talks to them, or says their name. If their hands are free, anything said to the table also
  gets their attention. Busy builders still hear table talk and catch up on it the next time they're
  asked;
- their task finishes, or something happens to their work (a bump, someone taking it down);
- a check-in: 2 minutes without being asked while busy, or 30 seconds while idle.

Each time, the agent can **say something and do something** in one decision:
- **Say:** free-form, to the table or to named people, with an **eagerness** from 1 to 10.
- **Do:** `continue`, `build` (strokes and/or re-standing an area, optional start mark), `take_down` (an
  area), `inspect` (an area), `stop`, or `walk` (round 2).
- Plus updated private notes and the interrupt preference.

### 4.6 Talking

- **Taking the floor.** If several people start talking to the table in the same beat, the most eager
  speaks first. Others also get in while the beat has room (about 40 words, roughly 15 seconds of
  speech). Anyone left over doesn't get to speak. They're told so next time they're asked, and can say
  it then if it still matters. This doesn't trigger an extra call.
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
- **Run 2 (real-time, table of 4).** Much more human: Chloe emerged as the leader, Ben pushed back,
  and Ava and Chloe collided. But the plan made everyone wait for Ava's exact end coordinates, so Ben
  and Dev idled for about 12 minutes. Only 70 dominoes were placed and 43% of them fell. The animal
  drifted from snake to "giraffe" and "swan." It took 236 calls. This led to: no rulers, pointing,
  anchored building (extend and connect), seeing others' hands, cheaper chatter, and story transcripts.
- **Run 3 (real-time with no rulers, table of 4):** in progress.

### 10.3 Transcripts

Each run writes two transcripts:
- `story.md`: readable as a story. A short recap written by the model (told to stick strictly to the
  log), then minute by minute: dialogue, plain-language actions, bumps and take-downs. No coordinates in
  the narration, no private thoughts, no held-back remarks.
- `transcript_detailed.md`: everything, including private reasoning.

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

### 4.4l After batch 5: joins come back

Batch 5 (pad-only building) fell to 1/8: with only `trace` and `fix`, pieces traced from the pad often
stood next to each other without touching. The anchored joining tools (`extend`, `connect`) are allowed
again; only free-hand work aimed by eye (lines, arcs, single dominoes) stays banned. Repeating a trace of
the stroke you are already laying now means "keep going", and tracing a stroke someone else is still
laying is refused with a note naming who is on it. Batch 6 measures the effect (seeds 61/62).

### 4.4m Batch 6, and dominoes fall either way

Batch 6 (anchored joins back): 5/8 recognized (haiku 3/4, sonnet 2/4), up from 1/8. Both sonnet failures
built a whole fish (one would have scored 1.0 had everything fallen) but the belly never fell: the outline
is a loop, the belly had been laid running "backwards" relative to how the fall reached it, and our
physics only let a domino fall the way it faced. Real dominoes fall whichever way they're pushed, so the
physics now does too: a standing domino falls along its own line in the direction closer to the push,
and lies that way afterwards. Lines laid in either direction now carry the fall. Batch 7 (seeds 71/72)
measures it.

### 4.4n Batch 7, and one start only

Batch 7 (dominoes fall either way): sonnet 4/4 recognized, every fish 95-100% fallen. Haiku 0/4: in each
game someone also set `"start": true` on their own stroke, which moved the start onto it, and the push
then toppled only that stroke (6-44 dominoes). On pad tables the start is now fixed: it sits at START on
the pad and comes with stroke 1; a `start` flag on any other build is ignored with a note. Batch 8
(seeds 81/82) measures it.
