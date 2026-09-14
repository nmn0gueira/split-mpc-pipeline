INPUT="${INPUT_BASE_DIR}/bob.csv"
MATCHED_OUTPUT=/tmp/bob_matched.csv

PARTY=1
ADDRESS=0.0.0.0:10010
INPUT_COLUMNS=0,1,2,3,4,5
PROTOCOL=psi
PROTOCOL_ARGS="-nt 8"

PROGRAM=linreg.py
COMPILE_FLAGS="-R 64 -Z 2 -b 100000"
case $(basename "$INPUT_BASE_DIR") in
    1000)     _batch_size=128 ;;
    10000)    _batch_size=1024 ;;
    100000)   _batch_size=16384 ;;
    1000000)  _batch_size=131072 ;;
    10000000) _batch_size=1048576 ;;
    *) echo "ERROR: unknown size $(basename "$INPUT_BASE_DIR")" >&2; exit 1 ;;
esac
PROGRAM_ARGS="--protocol psi --features a5b5 --label b --test_size 0.0 --n_epochs 10 --batch_size $_batch_size --trunc-pr"
MPC_ARGS="replicated-ring-party.x 1 linreg -h ${NODE_0}"
