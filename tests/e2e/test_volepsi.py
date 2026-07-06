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

PSI_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "psi"]
CPSI_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "cpsi", "--share-type", "add32"]
XTABS_ARGS = ["--aggregation", "sum", "--group_by", "a", "--values", "b", "--n_cat_1", "2"]

VOLEPSI_CPSI_SERVER_EXTRA_ARGS = ["-add32", "-senderColumns", "1"]
VOLEPSI_CPSI_CLIENT_EXTRA_ARGS = ["-add32"]

SERVER_ADDR = "0.0.0.0:10010"
CLIENT_ADDR = "127.0.0.1:10010"

ALICE_ROWS = [
    ("alice001", 0),
    ("alice002", 1),
    ("shared001", 0),
    ("shared002", 1),
]

BOB_ROWS = [
    ("bob001", 10),
    ("bob002", 20),
    ("shared001", 30),
    ("shared002", 40),
]


@pytest.mark.requires_volepsi
class TestPsiE2E:
    def test_xtabs_sum(self, tmp_path):
        alice_csv = str(tmp_path / "alice.csv")
        bob_csv = str(tmp_path / "bob.csv")
        alice_out = str(tmp_path / "alice_matched.csv")
        bob_out = str(tmp_path / "bob_matched.csv")
        write_csv(alice_csv, ALICE_ROWS)
        write_csv(bob_csv, BOB_ROWS)

        server = run_match_background("psi", bob_csv, bob_out, SERVER_ADDR)
        time.sleep(1)
        run_match("psi", alice_csv, alice_out, CLIENT_ADDR)
        server.join(timeout=30)

        run_iprep(alice_out, party=0, columns=[0])
        run_iprep(bob_out, party=1, columns=[0])

        compile_program("xtabs.py", *PSI_FLAGS, "--rows", "2", *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [30, 40]


@pytest.mark.requires_volepsi
class TestCpsiE2E:
    def test_xtabs_sum(self, tmp_path):
        alice_csv = str(tmp_path / "alice.csv")
        bob_csv = str(tmp_path / "bob.csv")
        alice_out = str(tmp_path / "alice_matched.csv")
        bob_out = str(tmp_path / "bob_matched.csv")
        write_csv(alice_csv, ALICE_ROWS)
        write_csv(bob_csv, BOB_ROWS)

        server = run_match_background("cpsi", bob_csv, bob_out, SERVER_ADDR, VOLEPSI_CPSI_SERVER_EXTRA_ARGS)
        time.sleep(1)
        run_match("cpsi", alice_csv, alice_out, CLIENT_ADDR, VOLEPSI_CPSI_CLIENT_EXTRA_ARGS)
        server.join(timeout=30)

        run_iprep(alice_out, party=0, columns=[0, 1])
        run_iprep(bob_out, party=1, columns=[0, 1, 2])

        compile_program("xtabs.py", *CPSI_FLAGS, "--rows", "24", *XTABS_ARGS)   # Testing CPSI with datasets of size 4 and intersection 2 outputs 24 rows
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [30, 40]
