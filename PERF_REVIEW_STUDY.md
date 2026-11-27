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

## 4. Ground truth: who actually contributed

The simulator knows exactly what happened, so every rating can be checked against it:

* **Built:** dominoes the player laid that fell in the final push.
* **Marginal contribution (leave-one-out):** remove only that player's dominoes from the final table,
  push again, and count how many fewer dominoes fall. This credits the start domino, the joins and the
  small fixes that whole lines depend on: a 3-domino bridge can be worth 60.
* **Glue work:** inspections, fixes to other people's lines, re-standing others' knocked-over work, and
  drawing the plan.

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
