#!/bin/bash
# Perf review v2, paired design (PERF_REVIEW_STUDY.md §13): seams on, styles, wide hands, larger model.
# Usage: results/perf_review2/run_pair.sh <seed> <player> <condition> [<condition> ...]
# Runs each condition twice: <player> as builder and <player> as glue.
cd "$(dirname "$0")/../.."
s=$1; who=$2; shift 2
if [ $((s % 2)) -eq 1 ]; then T=Maya,Tom,Priya,Leo; else T=Sofia,Omar,Hana,Jack; fi
for c in "$@"; do for st in builder glue; do
  d=results/perf_review2/${c}_${st}_s$s
  [ -f $d/summary.json ] && continue
  mkdir -p $d
  python3 experiments/pilot_live.py --view image --big --model sonnet --names $T --seed $s --review $c --styles \
    --wide-hands --seams --style-override $who=$st --out $d > $d/console.txt 2>&1 &
done; done
wait
for c in "$@"; do for st in builder glue; do
  d=results/perf_review2/${c}_${st}_s$s
  grep -q "hit your" $d/calls.jsonl 2>/dev/null && echo "USAGE LIMIT in $d"
  python3 -m orgsim.oracle $d > /dev/null 2>&1; python3 -m orgsim.sketch_record $d > /dev/null 2>&1
done; done
