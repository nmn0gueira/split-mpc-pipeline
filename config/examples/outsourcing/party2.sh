RUN_MATCH=false
RUN_IPREP=false

PROGRAM=xtabs.py
COMPILE_FLAGS="-R 64 -Z 2 -b 100000"
PROGRAM_ARGS="--rows 5000 --protocol psi --as-server --aggregation sum --group_by a --values b"
MPC_ARGS="replicated-ring-party.x 2 xtabs-sum-1 -h localhost"
