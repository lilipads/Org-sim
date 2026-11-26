#!/bin/bash
# Batch 4: building only from the pad: 10-minute games, table of 4.
cd "$(dirname "$0")/../.."
run() { mkdir -p results/batch4/$1; python3 experiments/pilot_live.py --view image --big "${@:2}" --out results/batch4/$1 > results/batch4/$1/console.txt 2>&1; }
run sonnet_A_s1 --names Maya,Tom,Priya,Leo --model sonnet --seed 41 &
run sonnet_A_s2 --names Maya,Tom,Priya,Leo --model sonnet --seed 42 &
run sonnet_B_s1 --names Sofia,Omar,Hana,Jack --model sonnet --seed 41 &
run sonnet_B_s2 --names Sofia,Omar,Hana,Jack --model sonnet --seed 42 &
run haiku_A_s1 --names Maya,Tom,Priya,Leo --seed 41 &
run haiku_A_s2 --names Maya,Tom,Priya,Leo --seed 42 &
run haiku_B_s1 --names Sofia,Omar,Hana,Jack --seed 41 &
run haiku_B_s2 --names Sofia,Omar,Hana,Jack --seed 42 &
wait
