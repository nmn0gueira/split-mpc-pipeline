INPUT="${INPUT_BASE_DIR}/bob.csv"
MATCHED_OUTPUT=/tmp/bob_matched.csv
RUN_COMPILE=false

PARTY=1
ADDRESS=http://${NODE_0}:10010
INPUT_COLUMNS=0,3
PROTOCOL=ps3i-xor
PROTOCOL_ARGS="--no-tls"
export RUST_LOG=info
export RAYON_NUM_THREADS=16

MPC_ARGS="--delay 2 client-input.x --client_id 1 --nparties 3 --hosts ${NODE_2},${NODE_3},${NODE_4} --finish"
