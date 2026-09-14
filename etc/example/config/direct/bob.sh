PARTY=1
INPUT=data/xtabs/bob.csv
MATCHED_OUTPUT=/tmp/bob_matched.csv
ADDRESS=127.0.0.1:10010
INPUT_COLUMNS=1
PROTOCOL=psi
PROTOCOL_ARGS=""

PROGRAM=xtabs.py
COMPILE_FLAGS="-R 64 -Z 2 -b 100000"
PROGRAM_ARGS="--rows 5000 --protocol psi --aggregation sum --group_by a --values b"
MPC_ARGS="semi2k-party.x 1 xtabs-sum-1 -h localhost"
