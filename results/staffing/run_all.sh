#!/bin/bash
# Overstaffing experiment: tables of 1, 4 and 10, same task, table, supply and 10 minutes.
# Small model for every agent; 4 games per size; seeds 101-104.
cd "$(dirname "$0")/../.."
run() { mkdir -p results/staffing/$1; python3 experiments/pilot_live.py --view image --big "${@:2}" --out results/staffing/$1 > results/staffing/$1/console.txt 2>&1; }
ALL=Maya,Tom,Priya,Leo,Sofia,Omar,Hana,Jack,Sam,Grace
run t1_s101 --names Maya --seed 101 &
run t1_s102 --names Sofia --seed 102 &
run t1_s103 --names Priya --seed 103 &
run t1_s104 --names Hana --seed 104 &
run t4_s101 --names Maya,Tom,Priya,Leo --seed 101 &
run t4_s102 --names Sofia,Omar,Hana,Jack --seed 102 &
run t4_s103 --names Maya,Tom,Priya,Leo --seed 103 &
run t4_s104 --names Sofia,Omar,Hana,Jack --seed 104 &
run t10_s101 --names $ALL --seed 101 &
run t10_s102 --names $ALL --seed 102 &
run t10_s103 --names $ALL --seed 103 &
run t10_s104 --names $ALL --seed 104 &
wait
python3 experiments/analyze_staffing.py results/staffing
