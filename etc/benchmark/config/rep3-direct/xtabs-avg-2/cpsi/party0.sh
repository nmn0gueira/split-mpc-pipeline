INPUT="${INPUT_BASE_DIR}/alice.csv"
MATCHED_OUTPUT=/tmp/alice_matched.csv

PARTY=0
ADDRESS=${NODE_1}:10010
INPUT_COLUMNS=0,1
PROTOCOL=cpsi
PROTOCOL_ARGS="-add32"

PROGRAM=xtabs.py
COMPILE_FLAGS="-R 64 -Z 2 -b 100000"
PROGRAM_ARGS="--protocol cpsi --share-type add32 --aggregation avg --group_by ab --values b --trunc-pr"
MPC_ARGS="replicated-ring-party.x 0 xtabs-avg-2 -h ${NODE_0}"
