#!/bin/bash
# Batch 9 (small model only): a redrawn START moves the start when stroke 1 is traced again.
cd "$(dirname "$0")/../.."
run() { mkdir -p results/batch9/$1; python3 experiments/pilot_live.py --view image --big "${@:2}" --out results/batch9/$1 > results/batch9/$1/console.txt 2>&1; }
run haiku_A_s1 --names Maya,Tom,Priya,Leo --seed 91 &
run haiku_A_s2 --names Maya,Tom,Priya,Leo --seed 92 &
run haiku_B_s1 --names Sofia,Omar,Hana,Jack --seed 91 &
run haiku_B_s2 --names Sofia,Omar,Hana,Jack --seed 92 &
wait
