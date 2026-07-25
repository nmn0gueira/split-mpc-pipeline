INPUT="${INPUT_BASE_DIR}/alice.csv"
MATCHED_OUTPUT=/tmp/alice_matched.csv
RUN_COMPILE=false

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

MPC_ARGS="client-input.x --client_id 0 --nparties 3 --hosts ${NODE_2},${NODE_3},${NODE_4}"
