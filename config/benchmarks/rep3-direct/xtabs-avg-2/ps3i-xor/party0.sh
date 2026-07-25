INPUT="${INPUT_BASE_DIR}/alice.csv"
MATCHED_OUTPUT=/tmp/alice_matched.csv

PARTY=0
ADDRESS=0.0.0.0:10010
INPUT_COLUMNS=0,2,3
PROTOCOL=ps3i-xor
PROTOCOL_ARGS="--no-tls"
export RUST_LOG=info
export RAYON_NUM_THREADS=16

PROGRAM=xtabs.py
COMPILE_FLAGS="-R 64 -Z 2 -b 100000"
PROGRAM_ARGS="--protocol ps3i-xor --aggregation avg --group_by ab --values b --trunc-pr"
MPC_ARGS="replicated-ring-party.x 0 xtabs-avg-2 -h ${NODE_0}"
