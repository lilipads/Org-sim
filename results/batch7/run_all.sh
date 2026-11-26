#!/bin/bash
# Batch 7: as batch 6, plus dominoes fall whichever way they are pushed; 10-minute games, table of 4.
cd "$(dirname "$0")/../.."
run() { mkdir -p results/batch7/$1; python3 experiments/pilot_live.py --view image --big "${@:2}" --out results/batch7/$1 > results/batch7/$1/console.txt 2>&1; }
run sonnet_A_s1 --names Maya,Tom,Priya,Leo --model sonnet --seed 71 &
run sonnet_A_s2 --names Maya,Tom,Priya,Leo --model sonnet --seed 72 &
run sonnet_B_s1 --names Sofia,Omar,Hana,Jack --model sonnet --seed 71 &
run sonnet_B_s2 --names Sofia,Omar,Hana,Jack --model sonnet --seed 72 &
run haiku_A_s1 --names Maya,Tom,Priya,Leo --seed 71 &
run haiku_A_s2 --names Maya,Tom,Priya,Leo --seed 72 &
run haiku_B_s1 --names Sofia,Omar,Hana,Jack --seed 71 &
run haiku_B_s2 --names Sofia,Omar,Hana,Jack --seed 72 &
wait
