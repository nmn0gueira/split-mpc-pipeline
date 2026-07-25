RUN_MATCH=false
RUN_IPREP=false

PROGRAM=linreg.py
COMPILE_FLAGS="-R 64 -Z 2 -b 100000"
case $(basename "$INPUT_BASE_DIR") in
    1024)    _batch_size=128 ;;
    8192)    _batch_size=1024 ;;
    131072)  _batch_size=16384 ;;
    1048576) _batch_size=131072 ;;
    8388608) _batch_size=1048576 ;;
    *) echo "ERROR: unknown PID size $(basename "$INPUT_BASE_DIR")" >&2; exit 1 ;;
esac

PROGRAM_ARGS="--protocol pid --as-server --features a5b5 --label b --test_size 0.0 --n_epochs 10 --batch_size $_batch_size --trunc-pr"
MPC_ARGS="replicated-ring-party.x 0 linreg -h ${NODE_2}"
