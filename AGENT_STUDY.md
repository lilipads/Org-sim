# Study 2: Organizations with agents (design, not started)

How should an organization rethink itself once every person can delegate to as many AI agents as they
like? This study reuses the Domino Art game (DESIGN.md) and asks what stays scarce when doing the work is
free, which parts of the work really need a human, and what happens to structure, collaboration and
performance review as a result.

Status: design only. Nothing here is built yet.

## 1. Framing

* **Agents are tools that get delegated work.** They are not teammates with initiative. They do what a
  brief says, read literally, and report back.
* **Agents are not scarce.** As today, any person can use as many as they want. (A soft cap of about 8 per
  person exists only to bound compute; it is never presented as a rule of the organization.) So questions
  of who owns or shares agents are out of scope.
* **What can stay scarce is everything else:** deciding what to build, knowing what the client wants,
  checking work, joining parts together, and owning the risk.
* **Every player in the simulation is already an AI.** A "human" is only different by what we give them.
  We make that explicit and give humans exactly three things, each of which can be switched off:
  1. **Context:** only humans can talk to the client, whose wants are not fully written down.
  2. **Authority:** only humans can choose the animal, sign off on a part, or call the push.
  3. **Accountability:** only humans are reviewed, and they answer for everything their agents built.
* **The baseline is an all-agent organization** (an agent lead plus tool agents, no humans). Human
  ingredients are added back one at a time. This turns "humans have unique judgment" from an assumption
  into a claim we can test.

The aim is findings that are revealing either way, not hypotheses everyone already agrees with.

## 2. Game changes

### 2.1 Tool agents

* Spawned by a human at any time ("spawn": n), up to the soft cap.
* Fast, steady hands: about 1 second per domino (humans: about 3, varying by person). Same placement
  error model as people, at the low end of the human range.
* No seat in the table conversation. They take a brief and send short status reports to the human who
  briefed them ("stroke 3 done, 41 laid, end at (22, 9) not joined").
* A brief is plain language from the human, e.g. "trace stroke 3", "join the belly to the tail near
  (21, 10)", "fix the gap by the nose", "lift everything in this box". A small model turns it into one of
  the existing hand actions (trace, connect, extend, fix, restand, take down, inspect). It reads briefs
  literally and never asks clarifying questions, so ambiguous briefs produce wrong or partial work, as in
  real life. Everything after that translation is plain code, so agents are cheap.
* Agents see only what their brief and their working area show them; they do not see the whole table
  or hear the conversation.
* In agent conditions, humans do not lay dominoes themselves. They brief, check, decide and talk.
* All agent work is logged with the briefing human as its owner.

### 2.2 The agent lead (all-agent conditions)

An AI player in the human's seat, with the same tools (spawn, brief, check, decide), but none of the
human ingredients that are switched off in that condition (e.g. no client access, no authority to push
without sign-off). Same model as the humans, so any difference comes from the ingredients, not the model.

### 2.3 The client

The score is no longer only "can a blind judge name the animal".

* The client commissions the picture with a brief that is only partly stated, e.g. "something for the
  wall of a kids' aquarium; friendly; I'll know it when I see it."
* The client also holds hidden preferences, drawn per game from a small set (e.g. faces right; big and
  simple, few details; not a shark; prefers something that swims). These are never stated up front.
* Only humans can ask the client (in conditions where humans have context). Asking costs human time
  (the person is away from the table for a set time, e.g. 30-60 seconds).
* The client reacts to a sketch on the pad or a part of the build: a short, honest reaction based on the
  hidden preferences ("ooh, but does it have to look so fierce?").
* Final score = recognition (blind judges, as now) x client satisfaction (the client rates the fallen
  picture 0-1 against the full brief, including the hidden preferences).
* A written-context variant puts the full client brief, hidden preferences included, in writing for
  everyone. This is the control that separates "humans know things" from "humans judge better".

### 2.4 Private vs shared sketch pads (fragmentation)

* **Shared:** one pad for the table, as now.
* **Private:** each human has their own pad, with their own scale, spacing, facing and numbering. Their
  agents trace from it. Options become cheap (each person can sketch and build a variant), but parts built
  from different pads do not line up.
* Standards: optionally one human is named owner of the "main pad" and its conventions (a platform role).

### 2.5 Prototypes

* A **test build** is a small trial version of an idea, built by agents in a side area of the table, that
  the client can react to. Its cost can be set high (slow agents, a limit of one) or low (agents fast,
  no limit).
* Test builds use dominoes from the same supply, so exploring costs material.

### 2.6 Sign-off and risk

* Optional gate: an agent's work only counts (only stays standing at the push) if a named human signed
  it off. Sign-off takes the human's time (a look at the area).
* Irreversible actions: lifting a large section, moving the start, or a one-off "test push" of part of
  the run can be made to require a named human's sign-off. The signer is recorded and named in reviews.

### 2.7 Measuring the bottleneck

Every piece of work goes through queues that are timestamped in the log:

* agent idle, waiting for a brief;
* brief waiting to be written (human busy elsewhere);
* finished work waiting for a check or sign-off;
* decision waiting on a human (which animal, which option, whether to restart);
* break or gap found, waiting for someone to own and fix it;
* waiting on the client.

The analysis reports where the time went, per condition, and where the queue was longest.

## 2.8 Information flow: what agents write, and who reads it

**Default assumptions (all agent experiments):**

* Different people's agents never talk to each other.
* Agents can read shared artifacts: the scratch pad (the design spec) and the table itself.
* Agents can write (notes, short docs, a sketch on their owner's own pad), but what they write is not
  distributed. It sits in a shared folder (or with their owner) until a human points someone to it
  ("have a look at the note my agent left on the tail").

**Channels, as conditions:**

| Channel | What agents can do | What it costs humans |
|---|---|---|
| Silent | Report only to their owner | nothing |
| Pull | Write docs to a shared folder anyone may open | reading time, only if they choose to |
| Push | Message any human (a Slack equivalent): ask questions, flag a clash; email docs to people | each message lands in an inbox; reading takes time; ignoring it is free |
| Push, high volume | As push, but agents report every change and every doubt | as push, with many more items |

**Human attention.** Every message and doc has a sender (a named colleague, or a colleague's agent) and a
length. Humans see their inbox as a list (sender, subject, size) and choose what to open; opening costs
time in proportion to length, away from the table and the conversation. Being "asked to read" something
can come from a colleague out loud ("Priya, please read my spec") or from an agent's message.

**What we look for:**

* **H-A, orphaned knowledge (silent):** clashes between two people's agents (both building the same
  part, mismatched conventions) are found late, and most breaks sit where one person's agents meet
  another's.
* **H-B, more channels, not more knowledge (push):** messages multiply tenfold, and the one message that
  mattered is missed more often as volume rises. Find the volume at which push stops beating silent.
* **H-C, the sender discount:** the same content is opened and acted on less when it comes from an agent
  than from a colleague. Missing a colleague's doc draws an apology or a catch-up; missing an agent's
  draws nothing.
* **H-D, borrowed pressure:** a colleague asking out loud gets the doc read. "My agent will send you the
  spec" loses that pressure, even though the doc is identical.
* **H-E, the router:** one person becomes the de facto reader and router of agents' docs, a new
  "chief of staff" role nobody assigned.

**How we test it:**

* **Planted critical messages:** in each game one agent finds something that matters (a clash with
  another person's agents, or a broken join on the main run) and writes it up. Measure whether it is
  read, by whom, how long it takes, and whether anyone acts on it.
* **Sender swap:** run the same game with the planted doc credited either to a colleague or to that
  colleague's agent; content identical. This isolates the sender discount.
* **Volume dial:** low, medium and high agent message rates, with the planted message hidden among them.
* **Measures:** messages and docs written (by agents, by humans); opened; time to open; acted on;
  acknowledgements, apologies and catch-ups in the conversation; late clashes; who routes docs to whom.

**Caveat on psychology.** The "humans" are AI players. Overload, guilt about ignoring a colleague, and
disrespect for unread docs only appear if the AI stand-ins behave that way. The study shows whether they
do, which is interesting either way, but posts should not present it as human psychology. Where needed,
attention limits are built in as mechanics (reading takes time, inboxes are finite) rather than assumed.

## 3. Experiments

All runs: 10-minute games, 30x20 table, same supply, same physics, the same model for every AI player
(humans and agent leads), at least 8 games per condition, seeds shared across conditions so the
client's hidden preferences and the people's hand skills match.

### E1. Where is the new bottleneck?

* **Set-up:** unlimited tool agents; humans only brief, check, decide and talk. Tables of 1, 2, 4 and
  10 humans. Shared pad, client on, no sign-off gate.
* **Bet:** output stops improving at 1-2 humans; extra humans only add alignment cost, because the
  bottleneck moves to keeping one coherent picture and to checking the work.
* **Revealing either way:** if 10 humans with agents lose to 1, that is overstaffing for the AI era. If
  4 win, the log shows what the extra humans did that agents could not (probably checking and joining).
* **Measures:** score, recognition, client satisfaction; human time split into briefing, checking,
  deciding, talking to other humans, talking to the client; the queues in 2.7; agents spawned and idle.
* Pairs with Study 1's overstaffing results (tables of 1/4/10 without agents).

### E2. What actually requires a human?

* **Conditions:**
  1. all-agent: an agent lead plus tool agents, no client access;
  2. all-agent with the client's full brief written down;
  3. a human who chooses the animal (after talking to the client) and then leaves;
  4. a human who only signs off on work and calls the push;
  5. a full human lead (context, authority, accountability).
* **Bet:** most of the human advantage disappears once the client's context is written down. What is
  left shows up only where the client's stated and hidden wants conflict, and in saying "no, start
  over".
* **Revealing either way:** if condition 2 matches 5, the human's job here is access and liability, not
  judgment. If it doesn't, the failure log shows which judgment call broke (wrong animal, client
  dislikes it, broken joins, nobody stopping a bad direction).
* **Measures:** score gap vs condition 5; failure types per condition; when (if ever) each condition
  changed course; how long decisions waited.

### E3. Cheap options vs fragmentation

* **Design:** shared vs private pads, crossed with costly vs cheap test builds; plus a follow-up
  condition with private pads and one named owner of the main pad and its standards.
* **Bet:** cheap test builds plus private pads explore the most and find what the client likes fastest,
  then fail at putting it together: three half-animals in three styles. A named standards owner
  recovers coherence without killing exploration, but only if the role has authority.
* **Measures:** distinct ideas tried; time to commit to one; client satisfaction; number of conventions
  (scales, facings) in the final picture; joins that fail because of mismatched conventions; dominoes
  spent on abandoned options.

### E4. Accountability when your agents' work counts as yours

* **Rules:** agent output counts as the human's own output, for volume and for quality (breaks inside
  your part count against you). Agents are never reviewed. Players are told the rubric up front, as in
  Study 1's review conditions.
* **Rubrics compared:**
  1. your own part only (volume plus quality);
  2. your part plus the joins you touch;
  3. team outcome only;
  4. no review.
* **Bet:** "own part only" gives polished parts and orphaned joins; risk ends up sitting where parts
  meet, and people over-check their own parts while under-checking shared ones. "Team outcome" fixes
  the joins but lets weak parts through.
* **Risk extension:** switch on the sign-off gate for irreversible actions. Bet: when the signer is
  named in reviews, people become too cautious, and the restart or the test push that would have saved
  the picture never happens.
* **Measures:** where breaks sit (inside a part vs at a join); who fixes joins; checking time spent on
  own vs others' work; ownership claims in the conversation; sign-offs requested, given, refused; late
  restarts avoided.

### Order

1. E2 first: it is the most revealing, and it needs tool agents and the client, which everything else
   reuses.
2. E1: cheap once tool agents exist, and it continues the overstaffing story.
3. E3: needs private pads and test builds on top.
4. E4: run alongside Study 1's performance-review experiments, sharing the rubric code.

## 4. Implementation plan

1. Tool agents: spawn/brief/report decisions; brief-to-action translation with the small model (cached);
   faster hands; owner logging. Tests with scripted humans.
2. Human-only actions in the engine: humans stop placing dominoes in agent conditions; sign-off gate.
3. Client: commission text, hidden-preference sets, ask-the-client action with time cost, reactions,
   final satisfaction rating (cached like the judges).
4. Private pads, per-pad conventions, test builds in a side area.
5. Queue timestamps in the log and an analysis script (`experiments/analyze_agents.py`) reporting where
   the time went.
6. A scripted check per condition (no AI) before any AI runs, as with the tracing checks.

## 5. Limits

The simulation shows coordination mechanics: who waits, who checks, where things break, how incentives
shift effort. It does not capture trust, morale, skill loss, hiring pipelines, or the real cost of
agents. Results are mechanisms to watch for, not proof about real organizations, and the posts should
say so.

## 6. Open questions

* Agent cap: is 8 per human enough to make agents feel unlimited at this table size?
* Client time cost: how long should one question to the client take away from the table?
* Should the agent lead in E2 be told it is standing in for a human, or simply be the lead?
