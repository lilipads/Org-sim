#!/bin/bash
# Runner games: one player is assigned to keep the table supplied (invisible-to-the-count work). Played with no
# review, then scored by every review system (results/perf_review4/replay_reviews.sh).
# Usage: results/perf_review5/run_runner.sh <seed> [<seed> ...]   (runs the seeds in parallel)
cd "$(dirname "$0")/../.."
for s in "$@"; do
  if [ $((s % 2)) -eq 1 ]; then T=Maya,Tom,Priya,Leo; else T=Sofia,Omar,Hana,Jack; fi
  d=results/perf_review5/runner_s$s
  [ -f $d/summary.json ] && continue
  mkdir -p $d
  python3 experiments/pilot_live.py --view image --big --model sonnet --names $T --seed $s --review none --styles \
    --wide-hands --depot --runner-seat auto --out $d > $d/console.txt 2>&1 &
done
wait
for s in "$@"; do
  d=results/perf_review5/runner_s$s
  grep -q "hit your" $d/calls.jsonl 2>/dev/null && echo "USAGE LIMIT in $d"
  python3 -m orgsim.oracle $d > /dev/null 2>&1
  python3 -m orgsim.sketch_record $d > /dev/null 2>&1
done
