# Study 3: Who decides? Dictators, consensus, and agents

When a team has to read what a client wants, does it matter who makes the call, and how? This study
compares a dictator picked at random, a dictator with the worst taste, a dictator with the best taste,
and full consensus, then adds agents to see how they change the answer.

Status: built (client, notes, pitches, decision modes, notes-surfaced check); runner in
`results/decision/run_all.sh`. A 3-minute test game ran end to end.

## 1. The client

Every table works for a client. The picture is scored on two things:

* **Recognition:** blind judges guess the animal (as before).
* **Client satisfaction (0-1):** the client rates the fallen picture against what they really wanted.

**Final score = recognition x client satisfaction.**

The client's wants are spread across the team, the classic "hidden profile" set-up from research on
group decisions:

* **Shared notes** (everyone has them) point to an obvious but wrong answer.
  Example: "It's for the entrance of a children's aquarium." "They want something big and bold."
  Read alone, that says *shark*.
* **Unique notes** (one per person) together point to the best answer.
  Example: "Sharks frighten the little ones" / "Their best-loved exhibit is the sea-turtle pool" /
  "It has to read from across the lobby: one simple shape" / "They want something that swims."
  Together, that says *sea turtle*.
* Some profiles add a **rumour** (plausible but wrong) to one person's notes.

Profiles are written by hand, fixed and stored in a file (no AI needed to make them), each with a
scoring guide: the best answer (1.0), acceptable answers (e.g. other friendly sea animals, 0.5-0.7),
and answers the client dislikes (e.g. shark, 0).
The client's rating of a finished picture uses the same guide and is cached like the judges.

At a table of 4 each person holds one unique note. Notes are private: a person learns the others' notes
only if they're said out loud.

## 2. Measuring taste

Before the game, each person, alone with their notes, pitches what they'd build and why (one private
answer each; nobody hears the others). The client rates every pitch with the scoring guide.

* **Worst taste:** the person whose pitch the client rated lowest.
* **Best taste:** the person whose pitch the client rated highest.

So "taste" here is the quality of someone's read of the client, given what they know: partly
information, partly judgment. This is measured, not assumed, and the same pitches are reused across
conditions with the same seed.

## 3. Decision rules (table of 4)

The game, table, supply and 10 minutes are unchanged. Everyone is told the rule up front.

| Condition | Who decides | Enforced by the game |
|---|---|---|
| **Free** (baseline) | Nobody in particular, as in the games so far | nothing new |
| **Random dictator** | A person picked by lot | only the dictator can draw on the pad; no building until the dictator calls the decision |
| **Worst-taste dictator** | The lowest-rated pitch | as above |
| **Best-taste dictator** | The highest-rated pitch | as above |
| **Consensus** | Everyone | no building until every person has declared they're aligned on the same animal; the clock keeps running |

Dictators are told: "You alone decide what the table builds. Others may advise; the call is yours."
The others are told who the dictator is and that the call is theirs.
In the dictator conditions, players are not told how the dictator was chosen.

New decision fields:

* `"decide": "<animal>"` (dictator only): the decision; building opens.
* `"aligned": "<animal>"` (consensus): "I'm on board with this"; can be changed or withdrawn.

## 4. Hypotheses

* **H1 (the obvious one):** the best-taste dictator scores highest and the worst lowest; consensus is
  right more often than a random dictator, but slower.
* **H2 (the interesting one): does anyone share their notes?** Research on hidden profiles finds groups
  mostly discuss what everyone already knows. Prediction: consensus tables spend their time on the
  shared notes and land on the obvious answer anyway, so consensus is slow *and* wrong. A dictator who
  asks each person what they know beats consensus.
* **H3: voice.** Does the team correct a bad dictator? Prediction: people speak up once, then go
  along with it. The worst-taste dictator's picture is built well but is the wrong animal.
* **H4: speed vs. quality.** Dictators start building sooner and finish more of the picture;
  consensus tables run out of time.

## 5. The agent flavour

Two additions, both with agents as tools (as in AGENT_STUDY.md):

* **A1. The dictator with agents instead of a team.** The dictator alone, with tool agents that build
  exactly what they're told and never push back.
  *Bet:* agents amplify the leader. Execution stops being the limit, so the gap between the best- and
  worst-taste dictator widens. Agents also never mention a note the dictator doesn't have.
* **A2. An AI advisor.** A client-research agent has read all the client's notes and gives one
  recommendation, with reasons, to the table (or to the dictator only).
  *Bets:* the worst-taste dictator improves the most, if they listen; consensus tables anchor on the
  AI's answer and stop sharing their own notes, so they converge fast. When the advisor is given a
  slightly wrong read (it hears the rumour too), do teams catch it?

## 6. Runs

* Sonnet for every player (it builds reliably); judges and client unchanged.
* Main study: 5 conditions x 8 games (seeds shared across conditions, so client profiles, notes,
  pitches and hand skills match).
* Agent flavour: A1 with best/worst dictators x 8; A2 with worst dictator and consensus x 8.

## 7. Measures

* Final score, recognition, client satisfaction; chosen animal vs the client's best answer.
* Time to the decision (dictator's call, or the moment everyone is aligned) and to the first domino.
* Share of standing dominoes that fell.
* **Notes surfaced:** how many of the unique notes were said out loud, by whom, and before or after
  the decision.
* Dissent: objections raised, and whether the decision changed after one.
* For A2: whether the final choice matches the advisor's, and how many own notes people shared after
  the advice.

## 8. Build plan

1. `orgsim/client.py`: profiles (fixed file), note dealing, pitch rating and final rating (cached).
2. Pre-game pitches: one private call per person; client ratings; pick worst and best.
3. Engine: decision modes (free, dictator, consensus), the `decide` and `aligned` fields, the pad
   and build gates, rules text for each mode.
4. Notes surfaced: match each unique note against what's said (a cached check per game).
5. `experiments/pilot_live.py` flags: `--client`, `--decision {free,dictator,consensus}`,
   `--dictator {random,worst,best,<name>}`; summary fields; analysis script.
6. Agent flavour after the main study.

## 9. First runs (rounds 201-202) and a problem

The 5-hour usage limit hit mid-run: rounds 203-204 and two round-202 games failed (removed; the runner
redoes them). Of the 8 valid games, **none was recognised**, even if every domino had fallen: the
client's best animals (cat, hen, hare, sea turtle) and the teams' other picks (elephant, donkey) are
much harder to draw in dominoes than the fish every earlier table chose. Judges saw a boot, a horse's
head, a long-beaked bird, a tulip. With recognition at zero the final score can't separate conditions,
so the client profiles need animals that read well as an outline before the study continues.
Early signals worth keeping: every dictator called the decision in the first beat (0:00), before any
discussion; consensus tables took 75-135 s to align.
