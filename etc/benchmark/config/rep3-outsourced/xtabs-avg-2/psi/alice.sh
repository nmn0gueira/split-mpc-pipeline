INPUT="${INPUT_BASE_DIR}/alice.csv"
MATCHED_OUTPUT=/tmp/alice_matched.csv
RUN_COMPILE=false

PARTY=0
ADDRESS=${NODE_1}:10010
INPUT_COLUMNS=0
PROTOCOL=psi
PROTOCOL_ARGS="-nt 8"

MPC_ARGS="client-input.x --client_id 0 --nparties 3 --hosts ${NODE_2},${NODE_3},${NODE_4}"
