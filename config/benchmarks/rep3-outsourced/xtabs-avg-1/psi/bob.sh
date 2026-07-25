INPUT="${INPUT_BASE_DIR}/bob.csv"
MATCHED_OUTPUT=/tmp/bob_matched.csv
RUN_COMPILE=false

PARTY=1
ADDRESS=0.0.0.0:10010
INPUT_COLUMNS=1
PROTOCOL=psi
PROTOCOL_ARGS="-nt 8"

MPC_ARGS="--delay 2 client-input.x --client_id 1 --nparties 3 --hosts ${NODE_2},${NODE_3},${NODE_4} --finish"
