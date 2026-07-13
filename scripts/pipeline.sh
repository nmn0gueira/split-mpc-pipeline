#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <config_file> [KEY=value ...]" >&2
    exit 1
fi

source "$1"
shift
for override in "$@"; do
    export "$override"
done

if [ "${RUN_MATCH:-true}" = true ]; then
    python scripts/match.py \
        --input "$INPUT" \
        --output "$MATCHED_OUTPUT" \
        --address "$ADDRESS" \
        "$PROTOCOL" \
        $PROTOCOL_ARGS
fi

if [ "${RUN_IPREP:-true}" = true ]; then
    python scripts/iprep.py \
        --input "$MATCHED_OUTPUT" \
        --party "$PARTY" \
        --columns "$INPUT_COLUMNS" \
       
fi

if [ "${RUN_COMPILE:-true}" = true ]; then
    scripts/compile.sh "$PROGRAM" $COMPILE_FLAGS $PROGRAM_ARGS
fi

if [ "${RUN_MPC:-true}" = true ]; then
    scripts/run.sh $MPC_ARGS
fi
