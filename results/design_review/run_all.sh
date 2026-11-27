#!/bin/bash
# Study 3 (DESIGN_REVIEW_STUDY.md): Eng/Design/PM roles, client, aesthetics score. Table of 4, larger model,
# 10 minutes. Conditions: lone designer (Eng, Design or PM designs alone), design review (Design drafts),
# open discussion. Seeds rotate roles and clients. One seed at a time (5 games in parallel); stops at a
# usage limit. Usage: results/design_review/run_all.sh [first_seed] [last_seed]
cd "$(dirname "$0")/../.."
run() { [ -f results/design_review/$1/summary.json ] && return; mkdir -p results/design_review/$1
        python3 experiments/pilot_live.py --view image --big --model sonnet --client auto --roles "${@:2}" \
          --out results/design_review/$1 > results/design_review/$1/console.txt 2>&1; }
for s in $(seq ${1:-301} ${2:-304}); do
  if [ $((s % 2)) -eq 1 ]; then T=Maya,Tom,Priya,Leo; else T=Sofia,Omar,Hana,Jack; fi
  run lone_eng_s$s --names $T --seed $s --design-mode lone --designer-role eng &
  run lone_design_s$s --names $T --seed $s --design-mode lone --designer-role design &
  run lone_pm_s$s --names $T --seed $s --design-mode lone --designer-role pm &
  run review_s$s --names $T --seed $s --design-mode review --designer-role design &
  run open_s$s --names $T --seed $s --design-mode open &
  wait
  if grep -l "hit your" results/design_review/*_s$s/calls.jsonl >/dev/null 2>&1; then
    echo "usage limit hit in round $s; stopping (rerun to resume)"; exit 1
  fi
done
