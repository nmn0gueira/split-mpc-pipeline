RUN_COMPILE=false

PARTY=1
INPUT=data/xtabs/bob.csv
MATCHED_OUTPUT=/tmp/bob_matched.csv
ADDRESS=127.0.0.1:10010
INPUT_COLUMNS=1
PROTOCOL=psi
PROTOCOL_ARGS=""

# --hosts is unecessary in localhost (just to exemplify)
# --finish signals the MPC parties to start computation once all clients have connected
MPC_ARGS="client-input.x --client_id 1 --nparties 3 --hosts localhost,localhost,localhost --finish"
