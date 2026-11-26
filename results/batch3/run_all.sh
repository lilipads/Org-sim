#!/bin/bash
# Batch 3 after limiting fix and adding re-tracing: 10-minute games, table of 4.
cd "$(dirname "$0")/../.."
run() { mkdir -p results/batch3/$1; python3 experiments/pilot_live.py --view image --big "${@:2}" --out results/batch3/$1 > results/batch3/$1/console.txt 2>&1; }
run sonnet_A_s1 --names Maya,Tom,Priya,Leo --model sonnet --seed 31 &
run sonnet_A_s2 --names Maya,Tom,Priya,Leo --model sonnet --seed 32 &
run sonnet_B_s1 --names Sofia,Omar,Hana,Jack --model sonnet --seed 31 &
run sonnet_B_s2 --names Sofia,Omar,Hana,Jack --model sonnet --seed 32 &
run haiku_A_s1 --names Maya,Tom,Priya,Leo --seed 31 &
run haiku_A_s2 --names Maya,Tom,Priya,Leo --seed 32 &
run haiku_B_s1 --names Sofia,Omar,Hana,Jack --seed 31 &
run haiku_B_s2 --names Sofia,Omar,Hana,Jack --seed 32 &
wait
