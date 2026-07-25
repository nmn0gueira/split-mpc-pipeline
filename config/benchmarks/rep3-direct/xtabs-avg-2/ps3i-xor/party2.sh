RUN_MATCH=false
RUN_IPREP=false

PROGRAM=xtabs.py
COMPILE_FLAGS="-R 64 -Z 2 -b 100000"
PROGRAM_ARGS="--protocol ps3i-xor --aggregation avg --group_by ab --values b --trunc-pr"
MPC_ARGS="replicated-ring-party.x 2 xtabs-avg-2 -h ${NODE_0}"
