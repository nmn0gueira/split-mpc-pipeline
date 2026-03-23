#!/usr/bin/env bash

set -ex

client_command_base="python scripts/match.py --input data/xtabs/alice.csv --output alice.csv --address 127.0.0.1:10010"
server_command_base="python scripts/match.py --input data/xtabs/bob.csv --output bob.csv --address 0.0.0.0:10010"

gen_input(){
    local input_size=$1
    python scripts/geninput.py -a "$input_size"
}

generate_psi_input(){
    gen_input 10000
    client_command="$client_command_base psi"
    server_command="$server_command_base psi"

    $server_command & $client_command > /dev/null
}


generate_psi_input

python3 scripts/iprep.py --input alice.csv --party 0 --columns 0 --transpose
python3 scripts/iprep.py --input bob.csv --party 1 --columns 1 --transpose

scripts/compile.sh xtabs.py -R 64 -Z 2 -b 100000 --rows 5000 --protocol psi --aggregation sum --group_by a --values b
scripts/run.sh ring.sh xtabs-sum-1