RUN_MATCH=false
RUN_IPREP=false

PROGRAM=xtabs.py
COMPILE_FLAGS="-R 64 -Z 2 -b 100000"
PROGRAM_ARGS="--protocol pid --aggregation avg --group_by a --values b --trunc-pr"
MPC_ARGS="replicated-ring-party.x 2 xtabs-avg-1 -h ${NODE_0}"
