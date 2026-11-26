#!/bin/bash
# Batch 6: pad tracing plus anchored joins (extend, connect, fix); v6 personas; 10-minute games, table of 4.
cd "$(dirname "$0")/../.."
run() { mkdir -p results/batch6/$1; python3 experiments/pilot_live.py --view image --big "${@:2}" --out results/batch6/$1 > results/batch6/$1/console.txt 2>&1; }
run sonnet_A_s1 --names Maya,Tom,Priya,Leo --model sonnet --seed 61 &
run sonnet_A_s2 --names Maya,Tom,Priya,Leo --model sonnet --seed 62 &
run sonnet_B_s1 --names Sofia,Omar,Hana,Jack --model sonnet --seed 61 &
run sonnet_B_s2 --names Sofia,Omar,Hana,Jack --model sonnet --seed 62 &
run haiku_A_s1 --names Maya,Tom,Priya,Leo --seed 61 &
run haiku_A_s2 --names Maya,Tom,Priya,Leo --seed 62 &
run haiku_B_s1 --names Sofia,Omar,Hana,Jack --seed 61 &
run haiku_B_s2 --names Sofia,Omar,Hana,Jack --seed 62 &
wait
