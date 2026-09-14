INPUT="${INPUT_BASE_DIR}/alice.csv"
MATCHED_OUTPUT=/tmp/alice_matched.csv

PARTY=0
ADDRESS=0.0.0.0:10010
INPUT_COLUMNS=0,1,2,3,4,5
PROTOCOL=pid
case $(basename "$INPUT_BASE_DIR") in
    1024)    _log2=10 ;;
    8192)    _log2=13 ;;
    131072)  _log2=17 ;;
    1048576) _log2=20 ;;
    8388608) _log2=23 ;;
    *) echo "ERROR: unknown PID size $(basename "$INPUT_BASE_DIR")" >&2; exit 1 ;;
esac
PROTOCOL_ARGS="--log_receiver $_log2 --log_sender $_log2"

PROGRAM=linreg.py
COMPILE_FLAGS="-R 128 -Z 2 -b 100000"
case $(basename "$INPUT_BASE_DIR") in
    1024)    _batch_size=128 ;;
    8192)    _batch_size=1024 ;;
    131072)  _batch_size=16384 ;;
    1048576) _batch_size=131072 ;;
    8388608) _batch_size=1048576 ;;
    *) echo "ERROR: unknown PID size $(basename "$INPUT_BASE_DIR")" >&2; exit 1 ;;
esac
PROGRAM_ARGS="--protocol pid --features a5b5 --label b --test_size 0.0 --n_epochs 10 --batch_size $_batch_size --trunc-pr"
MPC_ARGS="semi2k-party.x 0 linreg -h ${NODE_0}"
