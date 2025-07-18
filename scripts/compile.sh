#!/bin/bash

set -e

src_path=$1
MP_SPDZ_PATH="MP-SPDZ"

if [ -z "$src_path" ]; then
    echo "Usage: $0 <src_path> <protocol_options> <program_args>"
    echo "src_path: Path to the Python script in src"
    echo "Example: $0 cross-psi/hist2d.py -p 2 -r 1000"
    exit 1
fi

shift

python_script=$(basename "$src_path")

cp src/${src_path} $MP_SPDZ_PATH/${python_script}

cd $MP_SPDZ_PATH

start_time=$(date +%s%N)
python3 $python_script $@
end_time=$(date +%s%N)
elapsed_time=$(awk "BEGIN {print ($end_time - $start_time) / 1000000000}")
echo "Compilation time: ${elapsed_time} seconds"