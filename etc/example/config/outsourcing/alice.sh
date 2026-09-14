RUN_COMPILE=false

PARTY=0
INPUT=data/xtabs/alice.csv
MATCHED_OUTPUT=/tmp/alice_matched.csv
ADDRESS=0.0.0.0:10010
INPUT_COLUMNS=0
PROTOCOL=psi
PROTOCOL_ARGS=""

# --hosts is unecessary in localhost (just to exemplify)
MPC_ARGS="client-input.x --client_id 0 --nparties 3 --hosts localhost,localhost,localhost"
