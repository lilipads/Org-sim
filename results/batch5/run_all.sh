#!/bin/bash
# Batch 5: building only from the pad (after deadlock fix): 10-minute games, table of 4.
cd "$(dirname "$0")/../.."
run() { mkdir -p results/batch5/$1; python3 experiments/pilot_live.py --view image --big "${@:2}" --out results/batch5/$1 > results/batch5/$1/console.txt 2>&1; }
run sonnet_A_s1 --names Maya,Tom,Priya,Leo --model sonnet --seed 51 &
run sonnet_A_s2 --names Maya,Tom,Priya,Leo --model sonnet --seed 52 &
run sonnet_B_s1 --names Sofia,Omar,Hana,Jack --model sonnet --seed 51 &
run sonnet_B_s2 --names Sofia,Omar,Hana,Jack --model sonnet --seed 52 &
run haiku_A_s1 --names Maya,Tom,Priya,Leo --seed 51 &
run haiku_A_s2 --names Maya,Tom,Priya,Leo --seed 52 &
run haiku_B_s1 --names Sofia,Omar,Hana,Jack --seed 51 &
run haiku_B_s2 --names Sofia,Omar,Hana,Jack --seed 52 &
wait
