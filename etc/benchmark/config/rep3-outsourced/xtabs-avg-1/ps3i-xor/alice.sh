INPUT="${INPUT_BASE_DIR}/alice.csv"
MATCHED_OUTPUT=/tmp/alice_matched.csv
RUN_COMPILE=false

PARTY=0
ADDRESS=0.0.0.0:10010
INPUT_COLUMNS=0,3
PROTOCOL=ps3i-xor
PROTOCOL_ARGS="--no-tls"
export RUST_LOG=info
export RAYON_NUM_THREADS=16

MPC_ARGS="client-input.x --client_id 0 --nparties 3 --hosts ${NODE_2},${NODE_3},${NODE_4}"
