#!/bin/bash
# Score one finished game with every review system (same game, different reviewers).
# Usage: results/perf_review4/replay_reviews.sh <game folder> [<review> ...]
# EXTRA="--depot --runner-seat auto" for the runner games.
cd "$(dirname "$0")/../.."
d=$1; shift
s=$(basename $d | sed 's/.*_s\([0-9]*\).*/\1/')
if [ $((s % 2)) -eq 1 ]; then T=Maya,Tom,Priya,Leo; else T=Sofia,Omar,Hana,Jack; fi
for r in ${@:-individual peer manager forced}; do
  [ -f $d/reviews_replay_$r.json ] && continue
  python3 experiments/pilot_live.py --view image --big --model sonnet --names $T --seed $s --review $r --styles \
    --wide-hands $EXTRA --out $d --reviews-only > $d/replay_$r.txt 2>&1 &
done
wait
grep -l "hit your" $d/replay_*.txt 2>/dev/null | sed 's/^/USAGE LIMIT /'
