#!/bin/bash
# Decision study (DECISION_STUDY.md): free / random dictator / worst-taste dictator / best-taste dictator /
# consensus, with a client. Table of 4, larger model, 10 minutes, seeds 201-208 (each client profile twice;
# teams A and B alternate). Runs one seed at a time (5 games in parallel) to stay within usage limits.
# Usage: results/decision/run_all.sh [first_seed] [last_seed]
cd "$(dirname "$0")/../.."
run() { [ -f results/decision/$1/summary.json ] && return; mkdir -p results/decision/$1
        python3 experiments/pilot_live.py --view image --big --model sonnet --client auto "${@:2}" \
          --out results/decision/$1 > results/decision/$1/console.txt 2>&1; }
for s in $(seq ${1:-201} ${2:-208}); do
  if [ $((s % 2)) -eq 1 ]; then T=Maya,Tom,Priya,Leo; else T=Sofia,Omar,Hana,Jack; fi
  run free_s$s --names $T --seed $s &
  run dict_random_s$s --names $T --seed $s --decision dictator --dictator random &
  run dict_worst_s$s --names $T --seed $s --decision dictator --dictator worst &
  run dict_best_s$s --names $T --seed $s --decision dictator --dictator best &
  run consensus_s$s --names $T --seed $s --decision consensus &
  wait
done
