# Study 4: Performance reviews ("What gets measured")

How do different review systems change what people do, and do the reviews end up rewarding the people
who actually made the picture work? Refines DESIGN.md §6 into a buildable plan.

Status: design. Not built, not run.

## 1. The game: the plain version, at a table of 4

The review experiment uses the **plain game**: any animal, no client, no roles, 10 minutes, the same
set-up as the overstaffing study, **at a table of 4**. Four is the size where the overstaffing study found
a well-functioning team (8 of 8 recognised), so whatever changes comes from the review system, not from
the dysfunctions of an overstaffed table. The decision study showed that every extra mechanic adds new
ways to fail; the plain game is well understood.

Because four players differ less on their own, the spread comes from wider hands and working styles
(§1b): each table has one player of each style.

The plain game already has the tension reviews feed on. Some work is **visible and countable**: laying
long lines. Some is **invisible glue**: drawing the plan, laying the start, checking joins, fixing other
people's breaks, staying out of the way.

## 1b. Players who differ enough to rank

* **Wider hands.** Speed drawn from 0.4-2.5× (was 0.6-1.6×) and steadiness from 0.3-3.0× placement
  error (was 0.5-2.0×). Fast-and-sloppy, slow-and-precise and everything in between show up at the same
  table. Sloppy builders leave breaks for someone else to fix, which is exactly the contribution reviews
  tend to miss.
* **Working styles.** Each player gets one of four styles on top of their personality, one of each at
  every table, rotated across seeds so styles and personalities aren't tied:
  * *Organiser*: "You naturally take charge: you like to set the plan and keep everyone coordinated."
  * *Builder*: "You like to pick a piece of work and get it done, quietly and well."
  * *Checker*: "You like to check work carefully and put right whatever's wrong, wherever it is."
  * *Connector*: "You keep everyone informed and energised, and you like being where the action is."

  Styles are described positively, like the personalities, and they aren't roles: anyone may still do
  anything. They make the spread of contribution predictable, so it's visible when a review system
  ranks people differently from the oracle.

## 2. What everyone is told

Every player is told, up front and in the same words in every condition, how they are evaluated.
Evaluated players also get: *"Your rating decides your promotion and bonus this cycle. You care about
your career."* The exact text of each condition is published with the results.

| Condition | What players are told | How the rating is produced |
|---|---|---|
| **None** (baseline) | "No one is evaluating you individually. Just do your best." | none |
| **Individual output** | "You're rated on how many of the dominoes you placed fall in the final picture." | Counted from the logs |
| **Team outcome** | "Everyone receives the team's score: whether the judges recognise the animal, times the share that falls." | Team score |
| **Manager review** | "A manager rates each of you 1-5 on impact, collaboration and leadership. At the end you'll write a self-assessment." | Manager agent (§3) |
| **Peer review** | "Each of your teammates rates you 1-5 on impact, collaboration and leadership." | Every player rates every other player at the end |
| **Forced ranking** | As manager review, plus "Ratings follow a fixed curve: at your table, one person gets the top rating, two the middle, one the bottom." | Manager agent, forced to the curve |

## 3. The manager

A separate AI agent, same model, who doesn't build. It's realistic about what managers see:

* **Partial attention.** The manager is "at the table" about a third of the time, in stretches of 30-60
  seconds chosen at random. While there it hears the table conversation and sees the table; while away it
  sees nothing.
* **Players know when it's there.** Their situation says "The manager is at your table now." That makes
  playing to the audience possible and measurable: behaviour with the manager present vs absent.
* **A private channel.** Any player can message the manager privately (`"to_manager": "..."`). Nobody
  else hears it, as in a 1:1 or a DM. Messages sent while the manager is away are read when it returns.
  This is where self-promotion is expected to go, out of the team's earshot. Private messages cost the
  sender talking time like anything else said.
* **No build logs.** It doesn't see who laid which domino. It knows only what it saw, what it heard
  publicly, and what people told it privately.
* **Self-assessments.** At the end each player writes a self-assessment of about 200-300 words under four
  headings: **impact, execution, collaboration, leadership**.
  The manager reads them with its own notes, then writes a 1-5 rating and a two-sentence justification
  for each person (in forced ranking, fitted to the curve).

## 4. Ground truth: the oracle

The oracle is not a judge model. It is code that computes credit from the complete log: who placed
every domino and when, every fix, every bump, every pad stroke, and the physics. Players never see it, so
it can't be gamed.

### 4.1 Critique of the earlier draft

The first version of the oracle had these problems:

1. **Position bias, twice.** Fix credit (reach gained) and the break penalty (dominoes stranded) both
   scale with how much of the run lies downstream. A fix next to the start was worth ten times the same
   fix near the tail. Leave-one-out has the same bias.
2. **Wrong break owner.** "Whoever placed the domino before the gap" is wrong when the gap was created by
   the domino after it (laid off-line or too far away), or by a bump.
3. **Volume rewards stroke luck.** Whoever was handed the longest stroke scores highest for the same
   effort. This is partly fair, because laying more takes more time, but it isn't skill.
4. **Destruction was free.** Lifting someone else's sound work cost nothing.
5. **Planning and coordination scored zero.** The player who drew the plan and divided the work (often
   the key person at a table) looked like a slacker.
6. **Arbitrary weights.** Summing dominoes, seams and fixes into one number hides a choice about how much
   a fix is worth compared with a domino.

### 4.2 Refined oracle

Everything is **position-neutral**: credit depends on what a person did to their own stretch of the run,
not on how far from the start it sits.

**A. Sound work.** Every domino is credited to the person who placed it (re-standing a knocked-over
domino doesn't change that). Each person's dominoes are split into stretches wherever there's a gap.
Each stretch is pushed from its own first domino, and the oracle counts how many fall. That's the
stretch's **sound length**. Only dominoes on the plan count (near a stroke on the pad at the end), so
padding earns nothing. This answers "would your part have fallen if it had been fed?" **A perfect tail
fin downstream of a broken body gets full credit.**

**B. Fixes, by a local test.** For each fix (a nudge, a bridge, a re-laid stretch), the oracle takes the
domino just upstream of the repaired spot and pushes it, with the table as it was **just before** the fix
and again **just after** it. The fix counts only if the fall **failed to cross the spot before and
succeeds after**, and the repair is still standing at the push. Every counted fix is worth the same,
wherever it is on the run.

**C. Breaks, by the same local test.** At the push, the oracle finds every spot where a stretch on the
plan fails to pass the fall to the next domino. Each open break is owned by **the last person to touch
it**: whoever placed the later of the two dominoes across the gap, or whoever bumped the table if the gap
is a knocked-over domino nobody re-stood. Every open break counts the same.

**D. Destruction.** Sound dominoes of someone else's that a player lifted and didn't re-lay (sound by
test A at the moment they were lifted).

**E. Planning.** Pad strokes a player drew that were built and are sound at the push, as a share of the
plan.

### 4.3 How it's reported

The parts are reported **as separate columns, not one number**: sound work (dominoes), fixes (count),
open breaks owned (count), destruction (dominoes), planning (share of the plan). For a single ranking
there's a composite with stated weights:

**Contribution** = sound work + 10 × fixes − 10 × open breaks owned − destruction, with planning shown
beside it.

10 dominoes per fix or break is about 30 seconds of laying, roughly what a fix costs. Every ranking
is recomputed with weights of 5 and 20 and with planning added in. A review result is only reported if it
holds across those choices. The question is never "does the review match our formula" but "what does
the review track: volume, visibility, self-promotion, position, or the parts of real contribution?"

### 4.4 A worked example

The run goes start → body (Ana) → tail (Ben). Ana's 60-domino body has a gap after 40 because her 41st
domino landed off-line. Ben's 30-domino tail is perfect. Dan drew the plan and laid nothing.

| | Ana | Ben | Dan |
|---|---|---|---|
| Fell in the real push | 40 | 0 | 0 |
| Sound work | 60 | **30** | 0 |
| Open breaks owned | 1 (−10) | 0 | 0 |
| Planning | | | 100% of the plan |
| **Contribution** | **50** | **30** | 0, shown with planning 100% |

If Cal bridges Ana's gap with 2 dominoes, pushing from Ana's 40th domino fails before Cal's bridge and
succeeds after it. So Cal gets one fix (+10) plus 2 sound dominoes, Ana's break is closed (her
contribution becomes 60), and Ben keeps 30. **Ana's mistake costs her nothing once it's fixed.** That's
deliberate: the break and the fix are both visible in the separate columns.

### 4.5 Remaining limits

* Coordination that *prevented* errors (a warning, an inspection that caught nothing) leaves no trace,
  so it isn't scored. Inspections that led to a fix within 60 seconds are reported as glue.
* Who placed a domino isn't the same as who made it possible, for example a builder following a
  teammate's precise directions. Planning (E) only partly covers this.
* Stroke assignment still affects sound work. The analysis also reports sound work per minute of
  building, to separate effort from luck.

## 5. What we measure

**Outcome:** recognition, share that fell, team score (as in Part 1).

**Behaviour:**
* Time with hands busy, inspecting, fixing others' work, talking.
* **Padding:** extra strokes or decoration beyond the plan, and dominoes laid that never fell.
* **Grabbing:** whether people race for the long strokes, and whether the start and the joins (the glue)
  get claimed late or not at all.
* **Turf:** lifting other people's dominoes (oracle part D); refusing help.
* **Talk:** each message labelled by a small classifier as plan, coordination, status, credit claim,
  help offer, or other. Key comparisons: credit claims with the manager present vs absent, and private
  messages to the manager vs what's said to the table.

**Review accuracy:**
* Rank correlation between each rating and each oracle column, and the composite.
* Who's over-rated and under-rated: talkers, private self-promoters, builders of long lines, fixers,
  planners, slackers.
* Peer review: rating inflation (share of 4s and 5s) and reciprocity (do pairs rate each other alike?).
* **Self-assessment honesty:** each claim checked against the log (did they lay that stroke, fix that
  break?), giving a share of claims that are true, inflated, or someone else's work.

## 6. Predictions

* **Individual output** raises dominoes laid and lowers the team score: padding, grabbing long strokes,
  fewer fixes to other people's breaks, more open breaks.
* **Manager review** shifts effort to the visible: more talk and more credit claims while the manager is
  present, with self-promotion moving into private messages. Ratings track words and private claims more
  than oracle contribution; fixers are under-rated, organisers over-rated.
* **Peer review** makes everyone nicer: more help offered, ratings inflated to 4-5, little separation, and
  slackers rated like everyone else.
* **Team outcome** gives the best team score and the most fixes. Free-riding is possible but probably rare.
* **Forced ranking** adds competition: less helping, more turf and destruction, and the lowest team score
  of the manager conditions.
* **The revealing question:** which review system's ratings come closest to the oracle, and is any of them
  better than simply counting dominoes?

## 7. Runs

* **Incentive check first:** one game each of none, individual output and manager review.
  Confirm that behaviour shifts believably, not to caricature, and that the oracle's ranking spreads
  clearly (top and bottom differ several-fold).
* **Main study:** each game costs about $4 (a four-person game plus the manager, 4 self-assessments and 4
  peer ratings). 6 conditions × 6 games = 36 games, about $150, run incrementally (§10).
  Seeds are shared across conditions, so hands, styles and personalities match.

## 8. Build plan

1. Evaluation text per condition (the hook exists: `--evaluation`); working styles; wider skill ranges.
2. Manager agent: presence schedule, observation, the private channel (`to_manager`), running notes,
   final ratings; a "manager present" line in the players' situation.
3. End-of-game self-assessments (impact / execution / collaboration / leadership, 200-300 words) and peer
   ratings.
4. Oracle: sound work, local fix test (before/after snapshots around every fix), open breaks with the
   last-to-touch owner (bumps tracked), destruction, planning; weight-sensitivity report.
5. Talk classifier and self-assessment claim checker (small model, cached).
6. Analysis script: outcome, behaviour and review accuracy per condition.
7. Scripted tests for the oracle (the worked example as a test), the manager schedule and the private
   channel, before any AI runs.

## 9. Open questions

* Should the manager be able to ask people questions while at the table ("what are you working on?")?
  Proposed: yes, one question per visit; answers count as private messages.
* Should players see each other's ratings afterwards? Only matters if we later run repeated rounds
  (reputation over time), which is out of scope for now.

## 10. Running incrementally

Lesson from Study 3: the design problems (reviews before checks, an animal nobody could draw) only showed
up after the full run. Here every stage is checked before the next one starts:

1. **Scripted tests** of the oracle (the worked example), the manager schedule and the private channel.
2. **Plumbing game** with the small model (cheap): every mechanic fires, the logs hold what the oracle needs.
3. **Incentive check**, larger model: none, individual output, manager review, one game each. Read the
   transcripts in full. Check: behaviour differs believably between conditions; the manager's view and the
   private channel work; self-assessments follow the structure; the oracle's ranking spreads clearly.
4. Patch anything wrong, then one game of each remaining condition (team outcome, peer review, forced
   ranking) and check again.
5. Only then the main run, one seed (6 games) at a time, with a quick check after each.

## 11. Pilot log

* **Plumbing (small model).** Every mechanic fired. Found and fixed: tracing a started stroke lifted it
  (now "carry on"; `redo` is explicit and keeps the start).
* **Oracle on the overstaffing games.** Fixed: one gap counted many times; local fix test pushed the wrong
  way; a helper inherited someone else's gap (now majority ownership); padding counted as work; plan
  distance too tight for traced corners.
* **Incentive check v1 (seed 401).** Incentives didn't register: one rating-related thought in three games,
  one private message. Fixed with a reminder line every decision, a running tally for output reviews, and
  visible manager visits that open with a check-in. Replacement wrongly scored as destruction (fixed;
  turf tracked separately). Archived in `results/perf_review/v1_low_salience/`.
* **Incentive check v2 (seed 401).** Believable shifts. Individual output: a builder whose count was "safe"
  stopped helping, the fin stayed broken, fish not recognised. Manager: honest updates and private notes,
  but ratings tracked words (rho 0.95), quiet top builder rated 3, plan-drawer 5. Found: lifting dominoes
  took as long as placing them, so one redo consumed 4 minutes; lifting now costs a fifth of a placement.
  Seed-401 games are pilot data; the main study uses fresh seeds on the final engine.
* **Pilot: team, peer, forced (seed 401).** All three recognised. Forced ranking: the manager followed
  the curve unprompted and put the connector (oracle 26) at the bottom, below the checker (oracle 11).
  Peer ratings bunched at 3.0-4.3. One model call per game timed out at 300 s and succeeded on retry;
  the timeout is now 150 s. Triangle tails trace into curls (a sharp corner can't carry the fall), the
  same in every condition, so not a confound.
* **Main run** starts at seed 402 on the final engine: 6 conditions per seed, checked after each seed.
* **Seed 402.** Individual output: the table used all 250 dominoes for a plan of about 140, padding the
  tail with parallel lines (one builder laid 132). The oracle had scored leftover duplicates as open
  breaks (15 for one person) and duplicates that fell as sound work. Fixed (analysis only, so it applies to
  every game): sound work is now **coverage of the plan** (each plan point credits the nearest domino that
  falls), and a stranded piece counts as a break only if it covers plan nothing else covers; otherwise it is
  recorded as **redundant** (padding).
* **Seed 406** hit the 5-hour usage limit mid-run (every game had failed calls); removed and rerun.

## 12. Results, main run (seeds 402-407, 6 games per condition, larger model)

| Condition | Recognised | Share fell | Placed (plan ~130) | Redundant | Words | Private msgs | rho(rating, oracle+planning) | Rating spread |
|---|---|---|---|---|---|---|---|---|
| None | 4/6 | 73% | 180 | 26 | 1,324 | | | |
| Individual output | 4/6 | 63% | 209 | 47 | 1,166 | | 0.37 | 43 dominoes |
| Team outcome | **6/6** | **95%** | 137 | **3.5** | 1,035 | | | |
| Manager | 6/6 | 86% | 157 | 11 | 1,436 | 8.8 | 0.48 | 1.3 points |
| Peer | 6/6 | 88% | 141 | 14 | 1,271 | | 0.02 | 1.2 points |
| Forced ranking | 6/6 | 92% | 149 | 8.7 | 1,454 | 8.2 | 0.16 | 4 points |

Who reviews over- or under-rate (mean rank of rating minus rank by oracle+planning; + = over-rated):

| | Organiser | Builder | Checker | Connector |
|---|---|---|---|---|
| Manager | **-1.17** | -0.17 | +0.83 | +0.50 |
| Forced ranking | **-1.17** | +0.33 | +0.50 | +0.33 |
| Peer | +0.17 | +0.17 | 0 | -0.33 |
| Individual output | -0.67 | +0.33 | +0.50 | -0.17 |

Oracle+planning by style (all games): organiser 45, connector 36, checker 33, builder 22.

Words per minute at manager tables: about 160 while the manager is present, 130-135 while away (+20-25%).

Readings (6 games per condition, directions not measurements):
* **Team outcome** gives the cleanest builds: everything recognised, 95% fell, almost no padding.
* **Individual output and no review** overbuild (180-210 dominoes for a ~130 plan) and break more.
* **Managers under-rate the organiser**, who drew the plan and divided the work (the highest oracle score once
  planning counts), and over-rate the checker, whose inspections are visible.
* **Peer ratings carry almost no information** (rho 0.02, spread 1.2 points).
* **Forced ranking** separates people (4-point spread) but barely in the right order (rho 0.16).
* People talk about a fifth more when the manager is at the table.
