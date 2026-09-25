#!/usr/bin/env bash
# Reference orchestrator for pipeline.sh
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <net-map-file>" >&2
    exit 1
fi

NET_MAP="$1"
if [[ ! -f "$NET_MAP" ]]; then
    echo "ERROR: net-map file not found: $NET_MAP" >&2
    exit 1
fi

export OPERATIONS_DIR="${OPERATIONS_DIR:-$PWD/operations}"
rm -rf "$OPERATIONS_DIR"
mkdir -p "$OPERATIONS_DIR/ready" "$OPERATIONS_DIR/compiled" "$OPERATIONS_DIR/done"

wait_for() {
    local label=$1 dir=$2 target=$3
    local start count elapsed
    start=$(date +%s)
    while true; do
        count=$(ls "$dir" 2>/dev/null | wc -l)
        elapsed=$(( $(date +%s) - start ))
        [[ $count -ge $target ]] && break
        printf "\r  %-10s %d/%d  (%ds)" "$label" "$count" "$target" "$elapsed"
        sleep 2
    done
    elapsed=$(( $(date +%s) - start ))
    printf "\r  %-10s %d/%d  (%ds)\n" "$label" "$target" "$target" "$elapsed"
}

total=0
while read -r name address; do
    [[ -z "$name" || "$name" == \#* ]] && continue
    config="etc/example/config/direct/$name.sh"
    # This launches locally. Replace with something like an ssh call for example
    NODE_SELF="$name" bash scripts/pipeline.sh "$config" &
    total=$((total + 1))
done < "$NET_MAP"

printf "INFO: Waiting for %d nodes to be ready...\n" "$total"
wait_for "ready:" "$OPERATIONS_DIR/ready" "$total"
ROWS=$(grep -rh '[0-9]' "$OPERATIONS_DIR/ready/" | head -1)
echo "$ROWS" > "$OPERATIONS_DIR/go.flag"
echo "INFO: Go flag written (ROWS=$ROWS)"

printf "INFO: Waiting for %d nodes to finish compiling...\n" "$total"
wait_for "compiled:" "$OPERATIONS_DIR/compiled" "$total"
touch "$OPERATIONS_DIR/exec.flag"
echo "INFO: Exec flag written. All nodes entering MPC phase"

printf "INFO: Waiting for %d nodes to finish...\n" "$total"
wait_for "done:" "$OPERATIONS_DIR/done" "$total"
echo "INFO: All nodes finished"

# Collect results from each node here once they've all reported done

rm -r "$OPERATIONS_DIR"
