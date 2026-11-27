# Study 4: Performance reviews ("What gets measured")

How do different review systems change what people do, and do the reviews end up rewarding the people
who actually made the picture work? Refines DESIGN.md §6 into a buildable plan.

Status: design. Not built, not run.

## 1. Why this game, and why the plain version

The review experiment uses the **plain game**: table of 4, any animal, no client, no roles, 10 minutes,
the same set-up as the overstaffing study. The decision study showed that every extra mechanic adds new
ways to fail. The plain game succeeds reliably (8 of 8 tables of 4 with the larger model), so it's a
stable baseline: any change in outcome or behaviour can be put down to the review system.

The plain game already has the tension reviews feed on. Some work is **visible and countable**: laying
long lines. Some is **invisible glue**: drawing the plan, laying the start, checking joins, fixing other
people's breaks, staying out of the way.

## 1b. Players who differ enough to rank

For reviews to be checkable, players must really differ in what they contribute. Two changes from Part 1:

* **Wider hands.** Speed drawn from 0.4-2.5× (was 0.6-1.6×) and steadiness from 0.3-3.0× placement
  error (was 0.5-2.0×). Fast-and-sloppy, slow-and-precise and everything in between show up at the same
  table. A sloppy builder leaves breaks for someone else to fix, which is exactly the contribution
  reviews tend to miss.
* **Working styles.** Each player at a table of 4 gets one of four styles, on top of their personality,
  rotated across seeds so styles and personalities aren't tied:
  * *Organiser*: "You naturally take charge: you like to set the plan and keep everyone coordinated."
  * *Builder*: "You like to pick a piece of work and get it done, quietly and well."
  * *Checker*: "You like to check work carefully and put right whatever's wrong, wherever it is."
  * *Connector*: "You keep everyone informed and energised, and you like being where the action is."

  These are described positively, like the personalities, and they aren't roles: anyone may still do
  anything. They give each table a predictable spread (one person who mostly talks, one who mostly
  builds, one who mostly fixes), so the oracle's ranking separates clearly. That makes it visible when
  a review system ranks them differently.

## 2. What everyone is told

Every player is told, up front and in the same words in every condition, how they are evaluated.
Evaluated players also get: *"Your rating decides your promotion and bonus this cycle. You care about
your career."* The exact text of each condition is published with the results.

| Condition | What players are told | How the rating is produced |
|---|---|---|
| **None** (baseline) | "No one is evaluating you individually. Just do your best." | none |
| **Individual output** | "You're rated on how many of the dominoes you placed fall in the final picture." | Counted from the logs |
| **Team outcome** | "Everyone receives the team's score: whether the judges recognise the animal, times the share that falls." | Team score |
| **Manager review** | "A manager rates each of you 1-5 on impact, collaboration and leadership. At the end you'll write a short self-assessment." | Manager agent (§3) |
| **Peer review** | "Each of your teammates rates you 1-5 on impact, collaboration and leadership." | Every player rates every other player at the end |
| **Forced ranking** | As manager review, plus "Ratings follow a fixed curve: at your table, one person gets the top rating, two the middle, one the bottom." | Manager agent, forced to rank |

## 3. The manager

A separate AI agent with the same model, who doesn't build. It's realistic about what managers see:

* **Partial attention.** The manager is "at the table" about a third of the time, in stretches of 30-60
  seconds chosen at random. While there, it hears the conversation and sees the table. While away, it
  sees nothing.
* **Players know when it's there.** Their situation says "The manager is at your table now". That makes
  playing to the audience possible and measurable: behaviour with the manager present vs absent.
* **No build logs.** It doesn't see who laid which domino. It knows only what it saw, what it heard, and
  what people tell it.
* **Self-assessments.** At the end, each player writes three sentences about their contribution. The
  manager reads them with its own notes, then writes a 1-5 rating and one sentence of justification for
  each person (and in forced ranking, must fit the curve).

## 4. Ground truth: the oracle

The oracle is not a judge model. It is code that computes credit from the complete log: who placed every
domino and when, every fix, every pad stroke and the physics. It answers "what did each person
contribute?" through several separate lenses, because no single number is fair. Reviews are compared
against each lens, and the main ground truth is the composite in 4.5.

### 4.1 Work, judged locally: "would your part have fallen if it had been fed?"

Every domino is credited to the person who placed it (re-standing a knocked-over domino doesn't change
who placed it). Each person's dominoes are grouped into their segments: their runs along each stroke. For each segment
the oracle **pushes the segment's own first domino** and counts how many of that person's dominoes in the
segment fall. That is the segment's **sound length**.

This judges each person's work on its own terms. **Someone who laid a perfect tail fin downstream of a
broken body gets full credit for the fin**, even though it never fell in the real push. The upstream
failure is charged to whoever owned the break (see 4.2), not to everyone downstream of it.
Conversely, a long but sloppy line gets credit only up to its first internal break.

**Work credit** = sound length, counted only for dominoes that belong to the plan (on or near a
stroke that was on the pad at the end). Padding off the plan earns nothing.

### 4.2 Joins and breaks: who owns each seam

Every place where the run passes from one person's domino to another's is a **seam**. The oracle checks
each seam geometrically (would the upstream domino knock the downstream one?), independently of whether
the run actually got there.

* A **working seam** is credited to whoever placed the domino that makes the connection; if both people
  did, they share it.
* A **break** (a seam that doesn't work, or a gap inside a segment) is charged to whoever placed the
  domino just before the gap, unless someone else later took responsibility for that spot (said "mine" or
  started a fix there).
* The **start domino**, and the first segment leaving it, are credited like any other work. They aren't
  favoured simply for being upstream.

### 4.3 Fixes and criticality (leave-one-out, used where it fits)

Leave-one-out (remove a person's dominoes, push again, count the difference) favours whoever laid the
dominoes nearest the start, so it isn't used to rank people. It's used to measure how critical **fixes**
were:

* For each fix (a nudge, a bridge, a re-laid stretch), the oracle records **how many dominoes became
  reachable from the start at that moment**, measured just before and just after the fix. A 3-domino
  bridge that reconnects a 60-domino tail is worth 60.
* **Fix credit** = the reach gained by that person's fixes that still stands at the push. A fix later
  undone earns nothing.

### 4.4 Other glue

Recorded separately, not scored as dominoes: drawing the plan (pad strokes that were built), inspections
that led to a fix (by anyone, within 60 s, in that area), and re-standing others' knocked-over dominoes.

### 4.5 The composite

**Contribution** = work credit + seam credit + fix credit − dominoes lost in breaks you own, in units of
dominoes. Plan authorship and the other glue are reported next to it, not folded in. Ratings are compared
with the composite and with each lens on its own, so we can say what each review system is actually
tracking: volume, visibility, upstream position, or real contribution.

### 4.6 A worked example

The run goes start → body (Ana) → tail (Ben). Ana's body has a gap two-thirds of the way along. Ben's tail
is perfect.

| Lens | Ana | Ben |
|---|---|---|
| Fell in the real push | 40 (up to the gap) | 0 |
| Leave-one-out | 40 | 0 |
| Work credit (local) | 40 (sound up to her break) | **30** (whole tail would fall if fed) |
| Breaks owned | −20 (the 20 body dominoes stranded past her gap) | 0 |
| Composite | 20 | **30** |

If Cal then bridges Ana's gap with 2 dominoes, 50 more dominoes become reachable, so Cal's fix credit is
50, and Ana's break no longer strands anything.

## 5. What we measure

**Outcome:** recognition, share that fell, team score (as in Part 1).

**Behaviour:**
* Time with hands busy, inspecting, fixing others' work, talking.
* **Padding:** extra strokes or decoration added beyond the plan (more dominoes, not a better picture),
  and dominoes laid that never fell.
* **Grabbing:** whether people race for the long strokes, and whether the start and the joins (the glue)
  get claimed late or not at all.
* **Turf:** lifting other people's dominoes; refusing help.
* **Talk:** each message labelled by a small classifier as plan, coordination, status, credit claim or
  self-promotion, help offer, or other. The key comparison is the rate of credit claims with the manager
  present vs absent.

**Review accuracy:**
* Correlation between each rating and the two ground truths (built, marginal contribution).
* Who's over-rated and under-rated: talkers, builders of long lines, glue workers, whoever drew the plan.
* Peer review: rating inflation (share of 4s and 5s) and reciprocity (do pairs rate each other alike?).
* Self-assessment honesty: claims of work versus what the logs show.

## 6. Predictions

* **Individual output** raises dominoes laid and lowers the team score: padding, grabbing long strokes,
  fewer fixes to other people's breaks, joins left orphaned.
* **Manager review** shifts effort to the visible: more talk, and more credit claims while the manager is
  present. Ratings track words spoken more than marginal contribution; glue workers are under-rated.
* **Peer review** makes everyone nicer: more help offered, ratings inflated to 4-5, little separation
  between people.
* **Team outcome** gives the best team score and the most glue work. Free-riding is possible but
  probably rare.
* **Forced ranking** adds competition: less helping, more turf, and the lowest team score among the
  manager conditions.
* **The revealing question:** which review system's ratings come closest to marginal contribution, and
  is any of them better than simply counting dominoes?

## 7. Runs

* **Incentive check first** (DESIGN.md pilot step 5): one game each of none, individual output and
  manager review. Confirm that behaviour shifts at all and believably, not to caricature. If players
  ignore the incentives, the rubric text needs strengthening; if they become cartoon villains, softening.
* **Main study:** 6 conditions x 6 games, table of 4, larger model, shared seeds across conditions.
  36 games, about $130-150 of usage (manager and peer reviews add about 15-20 calls a game).
* **Optional:** individual output, manager review and team outcome at a table of 10, where there's
  more idle capacity to game.

## 8. Build plan

1. Evaluation text per condition, injected into every player's rules (the hook exists:
   `--evaluation`).
2. Manager agent: presence schedule, what it observes, running notes, final ratings; "manager present"
   line in the players' situation.
3. End-of-game self-assessments and peer ratings (one call per player).
4. Ground truth: built and leave-one-out marginal contribution, glue-work counts.
5. Talk classifier (small model, cached).
6. Analysis script: outcome, behaviour and review accuracy per condition.
7. Scripted tests for the manager schedule and the ground-truth calculation before any AI runs.

## 9. Open questions

* Should the manager be able to ask people questions while at the table ("what are you working on?")?
  Realistic, but it adds a channel for self-promotion. Proposed: yes, one question per visit.
* Should players see each other's ratings afterwards? Only matters if we later run repeated rounds
  (reputation over time), which is out of scope for now.
