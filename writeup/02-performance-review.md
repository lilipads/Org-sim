# Experiment 2: what a performance review can and cannot see

Lab report. Setup and engine are as in [experiment 1](01-overstaffing.md): a table of four AI players has ten
minutes to build a domino picture of an animal; the start domino is pushed and blind judges guess the animal.
Details, pilots and dead ends are in [`PERF_REVIEW_STUDY.md`](../PERF_REVIEW_STUDY.md).

## Question

A review system does two jobs. It tells people what will be rewarded (motivation), and it decides who
contributed (measurement). We tested both, separately.

- **Motivation.** Does telling the table how it will be reviewed change how it plays?
- **Measurement.** Holding the game fixed, how well does each review system identify who contributed?

## Setup

**Review systems.**

| System | What is rated |
|---|---|
| None | Nothing |
| Individual count | Each person's dominoes that fell |
| Team outcome | Everyone gets the table's score |
| Manager | A manager who visits about a third of the time, reads a promotion-style self-assessment from each player, and rates 1-5 |
| Forced ranking | The same manager, required to give one 5, two 3s and one 1 |
| Peer | Each player rates the other three 1-5 from what they saw and heard |

**Ground truth.** An "oracle" replays the finished table: dominoes that fell and cover the plan count for
whoever laid them, repairs that made a stranded section fall are credited to the repairer, open gaps are
charged to whoever left them, and the person who drew the plan gets a planning credit.

**Players.** Four players with different hand speeds, accuracy and working styles (organiser, builder, checker,
connector), reshuffled by seed.

**Runs.**

1. Motivation: 6 seeds x 3 conditions (none, individual count, team outcome) = 18 games. Players see a one-line
   reminder of the review with every decision.
2. Measurement: each of those 18 finished games scored by all four rating systems. The players are not replayed;
   only the reviewers are.
3. Uncounted work: 6 games in which one player is assigned to fetch dominoes for a shared bin instead of
   building, each scored by all four systems.

## Results

### 1. The review announced to the table did not change play

| | Recognised | Dominoes standing | Mean share that fell |
|---|---|---|---|
| None | 6/6 | 139 | 98% |
| Individual count | 6/6 | 124 | 98% |
| Team outcome | 4/6 | 118 | 82% |

No paired difference is statistically reliable (sign test, p >= 0.22); the team-outcome average is pulled down
by one game where a break near the start stranded the picture. The players' private reasoning mentions the
review in about two decisions per game under individual count and in none elsewhere. They do not pad counts,
hoard work or avoid helping.

An earlier 36-game run seemed to show individual counting causing overbuilding. An audit traced that to a
faulty connect tool that laid loops of extra dominoes; with the tool fixed the effect is gone.

### 2. On countable work, counting beat judgment

| System | Rank agreement with oracle | Rank agreement with words spoken | Picks the oracle's top contributor |
|---|---|---|---|
| Individual count | 0.66 | 0.15 | 75% |
| Forced ranking | 0.58 | 0.40 | 72% |
| Manager | 0.40 | 0.48 | 56% |
| Peer | 0.40 | 0.35 | 57% |

- The count agreed with the oracle better than the manager in 14 of 18 games and better than peers in 16 of 18.
- Manager ratings followed talk at least as closely as contribution.
- Ratings were compressed: managers gave a 3 or 4 in 64 of 72 ratings, peers a 4 or 5 in 65 of 72.
- Forcing a curve did not reliably help or hurt the manager's accuracy (better in 9 of 18 games).
- Self-assessments were inflated but ordered correctly: the four claimed shares summed to 114% on average, and
  their ranking agreed with the oracle at 0.68.

### 3. Every system ranked the person doing uncounted work last

| | Mean rank of the supply runner (1 = best of 4) | Ranked last or tied last |
|---|---|---|
| Individual count | 4.0 | 6/6 |
| Forced ranking | 3.8 | 5/6 |
| Peer | 3.7 | 5/6 |
| Manager | 3.3 | 5/6 |

Peers saw the deliveries and said so, then marked the runner down for not building ("she kept the shared bin
stocked ... but she declined to build"). Under the curve the manager gave the runner the 1 in five of six
games, typically for "the thinnest evidence" rather than for poor work.

## Limits

- **The oracle favours the count in result 2.** These games had almost no repairs or hidden work, so true
  contribution is close to sound dominoes plus planning. The count wins partly by construction.
- **Result 3 does not show the runner was under-valued.** In this game a dedicated runner at a table of four
  saves little time, and in three games the runner made one trip. The result is that all four systems put
  unbuilt work at the bottom, not that they were wrong to.
- **Six seeds per cell.** Only large effects would show.
- **The players are language models.** They are cooperative by default and did not respond to incentives.
  Result 1 is a statement about this simulator at least as much as about review systems.

## Reading

The simulator is informative about what reviewers can see and uninformative about how people react to being
reviewed. Within that limit: human-style ratings were lenient, bunched and pulled toward whoever talked, a
plain count did better wherever the work could be counted, and nothing credited the work that could not.
