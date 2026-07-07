import time

import pytest

from helpers import (
    compile_program,
    parse_int_array,
    run_iprep,
    run_match,
    run_match_background,
    run_program,
    write_csv,
)

PID_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "pid"]
XTABS_ARGS = ["--rows", "252", "--aggregation", "sum", "--group_by", "a", "--values", "b", "--n_cat_1", "2"]

SERVER_ADDR = "0.0.0.0:10010"
CLIENT_ADDR = "127.0.0.1:10010"

ALICE_ROWS = [
    ("alice001", 0),
    ("alice002", 1),
    ("shared001", 0),
    ("shared002", 0),
    ("shared003", 1),
    ("shared004", 1),
]

BOB_ROWS = [
    ("bob001", 100),
    ("bob002", 200),
    ("shared001", 10),
    ("shared002", 20),
    ("shared003", 30),
    ("shared004", 40),
]


@pytest.mark.requires_kunlun
class TestPidE2E:
    def test_xtabs_sum(self, tmp_path):
        alice_csv = str(tmp_path / "alice.csv")
        bob_csv = str(tmp_path / "bob.csv")
        alice_out = str(tmp_path / "alice_matched.csv")
        bob_out = str(tmp_path / "bob_matched.csv")
        write_csv(alice_csv, ALICE_ROWS)
        write_csv(bob_csv, BOB_ROWS)

        server = run_match_background("pid", bob_csv, bob_out, SERVER_ADDR, ["--log_sender", "7", "--log_receiver", "7"])
        time.sleep(2)
        run_match("pid", alice_csv, alice_out, CLIENT_ADDR, ["--log_sender", "7", "--log_receiver", "7"])
        server.join(timeout=60)

        run_iprep(alice_out, party=0, columns=[0, 1])
        run_iprep(bob_out, party=1, columns=[0, 1])

        compile_program("xtabs.py", *PID_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [30, 70]
