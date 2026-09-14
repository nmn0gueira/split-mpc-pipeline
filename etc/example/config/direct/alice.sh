PARTY=0
INPUT=data/xtabs/alice.csv
MATCHED_OUTPUT=/tmp/alice_matched.csv
ADDRESS=0.0.0.0:10010
INPUT_COLUMNS=0
PROTOCOL=psi
PROTOCOL_ARGS=""

PROGRAM=xtabs.py
COMPILE_FLAGS="-R 64 -Z 2 -b 100000"
PROGRAM_ARGS="--rows 5000 --protocol psi --aggregation sum --group_by a --values b"
MPC_ARGS="semi2k-party.x 0 xtabs-sum-1 -h localhost"
