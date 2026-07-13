import time

import pytest

from conftest import ALICE_ROWS, BOB_ROWS
from helpers import (
    compile_program,
    parse_int_array,
    run_iprep,
    run_match,
    run_match_background,
    run_program,
    write_csv,
)

PS3I_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "ps3i"]
PS3I_XOR_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "ps3i-xor"]
XTABS_ARGS = ["--rows", "4", "--aggregation", "sum", "--group_by", "a", "--values", "b", "--n_cat_1", "2"]

SERVER_ADDR = "0.0.0.0:10010"
CLIENT_ADDR = "http://127.0.0.1:10010"


@pytest.mark.requires_privateid
class TestPs3iE2E:
    def test_xtabs_sum(self, tmp_path):
        alice_csv = str(tmp_path / "alice.csv")
        bob_csv = str(tmp_path / "bob.csv")
        alice_out = str(tmp_path / "alice_matched.csv")
        bob_out = str(tmp_path / "bob_matched.csv")
        write_csv(alice_csv, ALICE_ROWS)
        write_csv(bob_csv, BOB_ROWS)

        server = run_match_background("ps3i", bob_csv, bob_out, SERVER_ADDR, ["--no-tls"])
        time.sleep(1)
        run_match("ps3i", alice_csv, alice_out, CLIENT_ADDR, ["--no-tls"])
        server.join(timeout=60)

        run_iprep(alice_out, party=0, columns=[0, 1])
        run_iprep(bob_out, party=1, columns=[0, 1])

        compile_program("xtabs.py", *PS3I_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [30, 70]


@pytest.mark.requires_privateid
class TestPs3iXorE2E:
    def test_xtabs_sum(self, tmp_path):
        alice_csv = str(tmp_path / "alice.csv")
        bob_csv = str(tmp_path / "bob.csv")
        alice_out = str(tmp_path / "alice_matched.csv")
        bob_out = str(tmp_path / "bob_matched.csv")
        write_csv(alice_csv, ALICE_ROWS)
        write_csv(bob_csv, BOB_ROWS)

        server = run_match_background("ps3i-xor", bob_csv, bob_out, SERVER_ADDR, ["--no-tls"])
        time.sleep(1)
        run_match("ps3i-xor", alice_csv, alice_out, CLIENT_ADDR, ["--no-tls"])
        server.join(timeout=60)

        run_iprep(alice_out, party=0, columns=[1, 0])
        run_iprep(bob_out, party=1, columns=[1, 0])

        compile_program("xtabs.py", *PS3I_XOR_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [30, 70]
