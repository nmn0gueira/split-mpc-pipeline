#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <config_file> [KEY=value ...]" >&2
    exit 1
fi

wait_flag() {
    local flag=$1
    echo "INFO: waiting for $(basename "$flag")..."
    while [[ ! -f "$flag" ]]; do
        sleep 2
    done
}

source "$1"
shift
for override in "$@"; do
    export "$override"
done

if [[ "${RUN_MATCH:-true}" = true ]]; then
    python3 scripts/match.py \
        --input "$INPUT" \
        --output "$MATCHED_OUTPUT" \
        --address "$ADDRESS" \
        "$PROTOCOL" \
        $PROTOCOL_ARGS
    ROWS=$(wc -l < "$MATCHED_OUTPUT" | xargs)
fi

if [[ "${RUN_IPREP:-true}" = true ]]; then
    python3 scripts/iprep.py \
        --input "$MATCHED_OUTPUT" \
        --party "$PARTY" \
        --columns "$INPUT_COLUMNS"
fi

if [[ -n "${OPERATIONS_DIR:-}" ]]; then
    mkdir -p "$OPERATIONS_DIR/ready"
    echo "${ROWS:-}" > "$OPERATIONS_DIR/ready/$NODE_SELF"
    echo "INFO: ready"
    wait_flag "$OPERATIONS_DIR/go.flag"
    [[ -z "${ROWS:-}" ]] && ROWS=$(cat "$OPERATIONS_DIR/go.flag")
fi

if [[ "${RUN_COMPILE:-true}" = true ]]; then
    scripts/compile.sh "$PROGRAM" $COMPILE_FLAGS --rows "$ROWS" $PROGRAM_ARGS
fi

if [[ -n "${OPERATIONS_DIR:-}" ]]; then
    mkdir -p "$OPERATIONS_DIR/compiled"
    touch "$OPERATIONS_DIR/compiled/$NODE_SELF"
    echo "INFO: waiting for exec signal"
    wait_flag "$OPERATIONS_DIR/exec.flag"
fi

if [[ "${RUN_MPC:-true}" = true ]]; then
    scripts/run.sh $MPC_ARGS
fi

if [[ -n "${OPERATIONS_DIR:-}" ]]; then
    mkdir -p "$OPERATIONS_DIR/done"
    touch "$OPERATIONS_DIR/done/$NODE_SELF"
fi
