# Ten people, ten minutes, one fish: what a domino game says about overstaffing

*Part 1 of a series on organisational health, run as experiments with AI players.*

> **Draft.** Numbers are from 4 games per table size. Four more per size are running; figures will be updated.

At a team offsite a while ago, we played one of those exercises everyone has done in some form: tables of
people, a pile of parts, a time limit, build something together. What stuck with me wasn't who won. It was
watching the big tables. A few people built. A few people talked about building. Several hovered, offered
to "help wherever", and mostly watched.

Everyone has a theory about this. More people means more ideas; more people means more meetings. I wanted
to watch it happen under controlled conditions, many times over, and count. So I built the game as a
simulation and filled the tables with AI players.

## The game

Each table gets ten minutes to make a picture of an animal out of dominoes. When time is up, the start
domino is pushed. The picture is whatever falls; anything still standing is invisible. Blind judges who
don't know the plan look at the fallen dominoes and guess the animal.

It is a small game, but it has the shape of real work:

- **A vision has to be agreed.** Which animal, which way it faces, where the run starts.
- **The work can be split.** People can lay different lines at the same time, like engineers on
  different parts of a system.
- **Everything has to join up.** A beautiful tail that the run never reaches doesn't fall, so it doesn't
  count. Integration is where most pictures die.
- **Talking costs time.** Only one person can hold the floor at once, and while you talk your hands slow
  down.

Each player is an AI with a short personality ("patient and precise with fiddly work", "upbeat and full of
ideas") and its own speed and steadiness of hand. Players talk, point, sketch a plan on a shared scratch
pad, lay dominoes, inspect each other's work and fix breaks, all on a real-time clock.

I ran tables of **1, 4 and 10** people. Same task, same table, same 250 dominoes, same ten minutes.

## What happened

Every table picked a fish.

| Per game, on average | Table of 1 | Table of 4 | Table of 10 |
|---|---|---|---|
| Fish recognised by the judges | 1 of 4 | **4 of 4** | **4 of 4** |
| Picture essentially finished (90% laid) | 8:45 | **5:30** | 6:34 |
| Words spoken at the table | 57 | 1,258 | 1,726 |
| Share of time anyone's hands were busy | 76% | 21% | 12% |
| Dominoes laid per person | 107 | 36 | 18 |
| People who laid fewer than 10 dominoes | 0 | 0 | 4 |
| Close inspections of the work | under 1 | 22 | 74 |

### 1. Ten people got the same result as four, and got there later

Both the four-person and ten-person tables made recognisable fish every time. But the ten-person
tables weren't faster. Four people had their picture essentially done at five and a half minutes; ten
people needed about a minute longer, and kept tinkering until the eight-minute mark.

Ten people laid only about a quarter more dominoes than four. Per person, output halved.

### 2. The work only had five pieces

The reason is visible in the plans. Every team sketched its fish as four to six strokes on the scratch pad:
top of the body, belly, two tail fins, maybe an eye. That is the natural number of independent pieces of
work in this picture. And that is roughly how many people actually built: at the ten-person tables, four
to eight people laid at least ten dominoes. The rest found other things to do.

Not because they were lazy. They did what conscientious people do when the work is already spoken for:

> **Omar:** Quick sort-out: Leo's on the tail edge, so I'll leave that one with him. I'm floating to patch breaks.

"Floating" was the most common role nobody was assigned. Floaters inspected (74 close inspections per
ten-person game, against 22 at four), offered help, checked in on joins, and stepped back when someone
said a line was theirs. In one game, four people laid 151 of the 158 dominoes; the other six laid seven
between them. One of those six, the person who sketched the plan and divided the work, laid none at all
and spoke more than anyone else at the table.

None of that is wasted, exactly. Someone has to coordinate, and an extra pair of eyes on a join can save a
picture. But it is not what you hire ten people for. **Headcount beyond the number of independent pieces
of work turns into coordination and checking, not output.**

### 3. Alone, nobody tells you it's broken

The solo tables did worst, and not because their ideas were bad. One solo player, Maya, sketched a perfectly good
fish, and spent the last minutes saying "body still isn't lighting up, checking the joint by the tail",
bridging, re-tracing, checking again. At the push, nothing fell. Two others kept lifting and re-laying their
own work and finished with 16 to 30 dominoes standing.

The difference at four was not hands, it was eyes. Someone else noticed the gap, someone else said "leave it,
there's no time", someone else held the line while you fixed yours.

### 4. With weaker players, ten people actively hurt

I first ran the same experiment with a smaller, less capable AI model. There, ten people didn't just
waste effort; they made things worse. Only 47% of standing dominoes fell at the ten-person tables (81% at
four), and people started undoing each other's work: half of all the dominoes lifted and re-laid at the
ten-person tables had been laid by someone else. Each table spoke over 4,000 words a game, and talk crowded
out building.

The more capable players absorbed the extra people gracefully: they floated, deferred and stayed out of
each other's way. The less capable ones collided. The cost of overstaffing depends on how good the team is
at not getting in its own way.

## What I take from it

- **Size the team to the pieces of work, not to the importance of the work.** The fish had five strands.
  Four or five people was the sweet spot; ten bought nothing but overhead.
- **Extra people don't sit idle; they convert into coordination.** Floating, checking, offering help, asking
  "is that yours?" It looks like engagement. It is real work, but it scales with headcount, not with the
  task.
- **The second and third person matter most.** Going from one to four transformed the result, mostly
  through someone else catching breaks. Going from four to ten changed almost nothing.
- **Overstaffing is cheaper for strong teams and expensive for weak ones.** A capable team quietly absorbs
  extra people. A struggling team turns them into collisions and rework.

## Caveats

These are AI players, not people, and a ten-minute domino game is not a product launch. The numbers come
from a handful of games per table size, so treat them as directions, not measurements. What the
simulation is good at is making mechanisms visible: who waits, who checks, where things break. Whether
those mechanisms match your own teams is for you to judge.

*Next in the series: who should decide? A dictator with poor taste, a dictator with good taste, or
consensus, when the client's real wishes are scattered across the team.*
