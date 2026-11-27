# Study 3 (revised): Eng, Design, PM, and how much to talk before building

Supersedes the dictator/consensus plan in DECISION_STUDY.md (kept for its client profiles and pilot notes).
Question: how much design discussion does a cross-functional team need? Too little and the design has a flaw
nobody at the table could see; too much and there's no time left to build.

## 1. Roles

Each player keeps their personality and gets an explicit title, shown to everyone ("Priya (Design)").
Table of 4: **2 Eng, 1 Design, 1 PM** (closest to a real team). Roles rotate across seeds so no
personality is always the PM.

| Role | Knows (in their rules) | Check they alone can run (time away from the table) |
|---|---|---|
| **Eng** | The exact mechanics: turn and branch limits, where START can go, which joins break, that a separate eye or dot connects to nothing | **Dry run** (30 s): plays the fall through the current sketch in their head; learns where the run would stop and why, and how much would fall |
| **Design** | What makes an outline read and look good: the one or two features that say "whale" not "fish", proportion, symmetry, flowing curves, filling the table, no clutter | **Squint test** (30 s): how a stranger reads the current sketch, and how good it looks (1-10), with a short reason |
| **PM** | The client: all of the client's notes. Only the PM talks to the client | **Ask the client** (45 s): the client reacts to the current sketch or an idea |

Everyone else knows only the basics: gentle curves, keep it all connected, the judges see only what falls.
Results of a check go only to the person who ran it; they have to say it out loud for it to count.

## 2. Score

Three numbers from independent judges, multiplied:

* **Recognition** (0-1): blind judges name the animal from what fell (as before).
* **Client** (0-1): how happy the client is with the animal (profiles v2: whale, butterfly, snail, swan).
* **Aesthetics** (0-1): an art panel of 3 judges rates how beautiful and well-drawn the fallen picture is,
  1-10, divided by 10.

**Final = recognition x client x aesthetics.** A broken run, a fish-like whale, a shark, or a correct but
ugly whale all score low. The Design check uses the same aesthetic panel prompt, so the designer's eye
predicts the real score; nobody else has that.

## 3. Design lock

Building is closed until the design is **locked** (`"lock": true`). After the lock the pad can still be
edited, but the lock event and time are recorded. Conditions differ only in who can lock and what must
happen first:

| Condition | Who designs | Before the lock | Who locks |
|---|---|---|---|
| **Lone designer** | One person (rotating Eng, Design, PM) holds the pad alone; nobody else may draw | nothing; others are told not to discuss the design | the designer |
| **Design review** | One person drafts | each of the other roles gives one review (`"review": "..."`) | the designer, once every other role has reviewed |
| **Open discussion** | Anyone | nothing | anyone |

## 4. Measures

Final score and its three parts; the locked sketch's design score on the offline scorecard
(`experiments/design_scorecard.py`: legible, buildable, plus aesthetics); time of the lock; words; checks
run (by role, before/after lock); whether check results were said out loud; flaws found before vs after
the lock (re-sketches after the lock, lifted dominoes).

## 5. Predictions

* Inverted U: lone designer < design review ~ open discussion; long discussion costs build time.
* A lone designer's flaw is on their blind axis: Eng draws a safe whale that reads as a fish or is plain;
  Design draws a beautiful whale that breaks at the eye or picks an animal the client hates; PM draws the
  client's animal clumsily.
* The revealing one: in open discussion, does the team ask the right role, or does the loudest voice
  decide? Do check results get shared?

## 6. Validation before AI runs

Offline drafts per client, each failing on one axis, must be flagged by the matching role's check
(dry run catches the break, squint test catches the fish-like whale and the ugly one, client catches the
shark). Then a cheap small-model test game per condition.

## 7. Pilot (two design-review games, Sonnet)

* Garden centre (butterfly): PM chose the client's animal, Design drafted, both Eng reviewed mechanics.
  A dry run later showed the upper wings would never catch; an Eng redrew them steeper. 144 of 155 fell,
  all judges saw a butterfly. Final 0.4 (recognition 1 x client 1 x aesthetics 0.4).
* Rowing club (swan): substantive reviews (Eng on the tight neck corner, PM on a slimmer S-neck), the PM
  asked the client, who disliked the stubby neck, so the neck was redrawn after the lock. The build broke
  near the start: 9 of 111 fell. Final 0.
* Both tables locked at 0:45: reviews came before anyone ran a check; the checks were used after the
  lock, to repair. Art panel scores are low overall (2-5 of 10), so aesthetics mostly separates
  conditions rather than rating absolute quality.
