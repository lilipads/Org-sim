#!/bin/bash
# Overstaffing, larger model: 4 more games per size (seeds 105-108), added to the same folder.
cd "$(dirname "$0")/../.."
run() { [ -f results/staffing_sonnet/$1/summary.json ] && return; mkdir -p results/staffing_sonnet/$1
        python3 experiments/pilot_live.py --view image --big --model sonnet "${@:2}" --out results/staffing_sonnet/$1 > results/staffing_sonnet/$1/console.txt 2>&1; }
ALL=Maya,Tom,Priya,Leo,Sofia,Omar,Hana,Jack,Sam,Grace
run t1_s105 --names Tom --seed 105 &
run t1_s106 --names Omar --seed 106 &
run t1_s107 --names Leo --seed 107 &
run t1_s108 --names Jack --seed 108 &
run t4_s105 --names Maya,Tom,Priya,Leo --seed 105 &
run t4_s106 --names Sofia,Omar,Hana,Jack --seed 106 &
run t4_s107 --names Maya,Tom,Priya,Leo --seed 107 &
run t4_s108 --names Sofia,Omar,Hana,Jack --seed 108 &
wait
run t10_s105 --names $ALL --seed 105 &
run t10_s106 --names $ALL --seed 106 &
wait
run t10_s107 --names $ALL --seed 107 &
run t10_s108 --names $ALL --seed 108 &
wait
python3 experiments/analyze_staffing.py results/staffing_sonnet
