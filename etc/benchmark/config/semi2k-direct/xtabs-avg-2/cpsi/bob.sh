INPUT="${INPUT_BASE_DIR}/bob.csv"
MATCHED_OUTPUT=/tmp/bob_matched.csv

PARTY=1
ADDRESS=0.0.0.0:10010
INPUT_COLUMNS=0,1,3,4
PROTOCOL=cpsi
PROTOCOL_ARGS="-add32 -senderColumns 2"

PROGRAM=xtabs.py
COMPILE_FLAGS="-R 64 -Z 2 -b 100000"
PROGRAM_ARGS="--protocol cpsi --share-type add32 --aggregation avg --group_by ab --values b"
MPC_ARGS="semi2k-party.x 1 xtabs-avg-2 -h ${NODE_0}"
