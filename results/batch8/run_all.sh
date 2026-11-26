#!/bin/bash
# Batch 8: as batch 7, plus only stroke 1 lays the start (no moving it); 10-minute games, table of 4.
cd "$(dirname "$0")/../.."
run() { mkdir -p results/batch8/$1; python3 experiments/pilot_live.py --view image --big "${@:2}" --out results/batch8/$1 > results/batch8/$1/console.txt 2>&1; }
run sonnet_A_s1 --names Maya,Tom,Priya,Leo --model sonnet --seed 81 &
run sonnet_A_s2 --names Maya,Tom,Priya,Leo --model sonnet --seed 82 &
run sonnet_B_s1 --names Sofia,Omar,Hana,Jack --model sonnet --seed 81 &
run sonnet_B_s2 --names Sofia,Omar,Hana,Jack --model sonnet --seed 82 &
run haiku_A_s1 --names Maya,Tom,Priya,Leo --seed 81 &
run haiku_A_s2 --names Maya,Tom,Priya,Leo --seed 82 &
run haiku_B_s1 --names Sofia,Omar,Hana,Jack --seed 81 &
run haiku_B_s2 --names Sofia,Omar,Hana,Jack --seed 82 &
wait
