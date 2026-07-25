INPUT="${INPUT_BASE_DIR}/bob.csv"
MATCHED_OUTPUT=/tmp/bob_matched.csv

PARTY=1
ADDRESS=http://${NODE_0}:10010
INPUT_COLUMNS=0,3
PROTOCOL=ps3i-xor
PROTOCOL_ARGS="--no-tls"
export RUST_LOG=info
export RAYON_NUM_THREADS=16

PROGRAM=xtabs.py
COMPILE_FLAGS="-R 64 -Z 2 -b 100000"
PROGRAM_ARGS="--protocol ps3i-xor --aggregation avg --group_by a --values b --trunc-pr"
MPC_ARGS="replicated-ring-party.x 1 xtabs-avg-1 -h ${NODE_0}"
