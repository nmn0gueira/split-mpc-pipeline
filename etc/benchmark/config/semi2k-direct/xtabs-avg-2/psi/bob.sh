INPUT="${INPUT_BASE_DIR}/bob.csv"
MATCHED_OUTPUT=/tmp/bob_matched.csv

PARTY=1
ADDRESS=0.0.0.0:10010
INPUT_COLUMNS=0,1
PROTOCOL=psi
PROTOCOL_ARGS="-nt 8"

PROGRAM=xtabs.py
COMPILE_FLAGS="-R 64 -Z 2 -b 100000"
PROGRAM_ARGS="--protocol psi --aggregation avg --group_by ab --values b"
MPC_ARGS="semi2k-party.x 1 xtabs-avg-2 -h ${NODE_0}"
