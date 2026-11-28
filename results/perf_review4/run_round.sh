#!/bin/bash
# Rerun of none / individual / team on the fixed engine (same seeds, same settings as results/perf_review).
# Usage: results/perf_review4/run_round.sh <seed> <condition> [<condition> ...]   (runs the conditions in parallel)
cd "$(dirname "$0")/../.."
s=$1; shift
if [ $((s % 2)) -eq 1 ]; then T=Maya,Tom,Priya,Leo; else T=Sofia,Omar,Hana,Jack; fi
for c in "$@"; do
  d=results/perf_review4/${c}_s$s
  [ -f $d/summary.json ] && continue
  mkdir -p $d
  python3 experiments/pilot_live.py --view image --big --model sonnet --names $T --seed $s --review $c --styles \
    --wide-hands --out $d > $d/console.txt 2>&1 &
done
wait
for c in "$@"; do
  d=results/perf_review4/${c}_s$s
  grep -q "hit your" $d/calls.jsonl 2>/dev/null && echo "USAGE LIMIT in $d"
  python3 -m orgsim.oracle $d > /dev/null 2>&1
  python3 -m orgsim.sketch_record $d > /dev/null 2>&1
done
