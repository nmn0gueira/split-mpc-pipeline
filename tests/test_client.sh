#!/usr/bin/env bash

set -ex

client_command_base="python scripts/match.py --input data/xtabs/alice.csv --output alice.csv --address 127.0.0.1:10010"
server_command_base="python scripts/match.py --input data/xtabs/bob.csv --output bob.csv --address 0.0.0.0:10010"

gen_input(){
    local input_size=$1
    python tests/helper/geninput.py -a "$input_size"
}

generate_psi_input(){
    gen_input 10000
    client_command="$client_command_base psi"
    server_command="$server_command_base psi"

    $server_command & $client_command > /dev/null
}


generate_psi_input

cd MP-SPDZ

./client-input.x 0 3 ../alice.csv 0 0 & 
./client-input.x 1 3 ../bob.csv 1 1 > /dev/null &

cd ..

scripts/compile.sh xtabs.py -R 64 -Z 2 -b 100000 --rows 5000 --protocol psi --aggregation sum --group_by a --values b --as-server
scripts/run.sh ring.sh xtabs-sum-1