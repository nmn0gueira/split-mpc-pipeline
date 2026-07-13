"""
Verifies the client-input.x and ClientManager socket path for all protocol input types.

xtabs sum is used as the test program. Data is delivered via client-input.x over sockets rather than read from Player-Data by the MPC parties directly.
"""
import time

import pytest

from helpers import (
    compile_program, parse_client_int_outputs, parse_client_sfix_outputs,
    run_client, run_program_background,
    start_client_background, write_player_input,
)

MPC_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000"]
XTABS_ARGS = ["--rows", "4", "--aggregation", "sum", "--group_by", "a", "--values", "b", "--n_cat_1", "2"]


class TestAsServer:
    def _run(self, protocol, client0_rows, client1_rows, *extra_compile_args):
        write_player_input(0, *client0_rows)
        write_player_input(1, *client1_rows)
        compile_program("xtabs.py", *MPC_FLAGS, "--protocol", protocol, *XTABS_ARGS, "--as-server", *extra_compile_args)

        mpc = run_program_background("ring.sh", "xtabs-sum-1")
        time.sleep(2)

        client0 = start_client_background(0, nparties=3)
        run_client(1, nparties=3, finish=True)

        mpc_out, mpc_err = mpc.communicate(timeout=60)
        client0_out, client0_err = client0.communicate(timeout=10)

        if mpc.returncode != 0:
            pytest.fail(f"MPC run failed:\n{mpc_out}\n{mpc_err}")
        if client0.returncode != 0:
            pytest.fail(f"client-input.x failed:\n{client0_out}\n{client0_err}")

        return client0_out

    def test_psi_int(self):
        out = self._run("psi",
            [[1, 2, 1, 2]],
            [[10, 20, 30, 40]],
        )
        assert parse_client_int_outputs(out) == [40, 60]

    def test_psi_float(self):
        out = self._run("psi",
            [[1, 2, 1, 2]],
            [[1.5, 2.5, 3.5, 4.5]],
            "fix",
        )
        result = parse_client_sfix_outputs(out)
        assert abs(result[0] - 5.0) < 0.01
        assert abs(result[1] - 7.0) < 0.01

    def test_pid(self):
        out = self._run("pid",
            [[1, 1, 1, 1], [1, 2, 1, 2]],
            [[1, 1, 0, 1], [10, 20, 30, 40]]
        )
        assert parse_client_int_outputs(out) == [10, 60]

    def test_ps3i(self):
        out = self._run("ps3i",
            [[8765432109876543210, 3456789012345678901, 7890123456789012345, 2345678901234567890],
            [6789012345678901234, 1234567890123456789, 9012345678901234567, 4567890123456789012]],
            [[9681311963833008407, 14989955061363872717, 10556620616920539272, 16101065172474983728],
            [11657731728030650392, 17212176183586094847, 9434398394808317079, 13878853950252762644]]
        )
        assert parse_client_int_outputs(out) == [40, 60]

    def test_ps3i_xor(self):
        out = self._run("ps3i-xor",
            [[3000000000000000000, 4000000000000000000, 5000000000000000000, 6000000000000000000],
            [1000000000000000000, 2000000000000000000, 3000000000000000000, 4000000000000000000]],
            [[3000000000000000001, 4000000000000000002, 5000000000000000001, 6000000000000000002],
            [1000000000000000010, 2000000000000000020, 3000000000000000030, 4000000000000000040]]
        )
        assert parse_client_int_outputs(out) == [40, 60]

    def test_cpsi_add32(self):
        out = self._run("cpsi",
            [[1, 0, 1, 1], [2847392156, 1923847561, 3912847561, 847392156]],
            [[0, 1, 1, 0], [1447575141, 2371119737, 382119735, 3447575142], [10, 20, 30, 40]],
            "--share-type", "add32"
        )
        assert parse_client_int_outputs(out) == [10, 60]

    def test_cpsi_xor(self):
        out = self._run("cpsi",
            [[1, 0, 1, 1], [2847392156, 1923847561, 3912847561, 847392156]],
            [[0, 1, 1, 0], [2847392157, 1923847563, 3912847561, 847392158], [10, 20, 30, 40]],
            "--share-type", "xor",
        )
        assert parse_client_int_outputs(out) == [10, 60]
