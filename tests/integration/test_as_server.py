"""
Verifies the client-input.x and ClientManager socket path.

xtabs is used as the test program: the same inputs and expected output as the
PSI file-mode test, but data is delivered via client-input.x over sockets
rather than read from Player-Data by the MPC parties directly.
"""
import time

import pytest

from helpers import (
    compile_program, parse_client_int_outputs, parse_client_sfix_outputs,
    run_client, run_program_background,
    start_client_background, write_player_input,
)

PSI_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "psi"]
XTABS_ARGS = ["--rows", "4", "--aggregation", "sum", "--group_by", "a", "--values", "b", "--n_cat_1", "2"]


class TestAsServer:
    def test_client_io_int(self):
        write_player_input(0, [0, 1, 0, 1])
        write_player_input(1, [10, 20, 30, 40])
        compile_program("xtabs.py", *PSI_FLAGS, *XTABS_ARGS, "--as-server")

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

        assert parse_client_int_outputs(client0_out) == [40, 60]

    def test_client_io_float(self):
        write_player_input(0, [0, 1, 0, 1])
        write_player_input(1, [1.5, 2.5, 3.5, 4.5])
        compile_program("xtabs.py", *PSI_FLAGS, *XTABS_ARGS, "--as-server", "fix")

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

        result = parse_client_sfix_outputs(client0_out)
        assert abs(result[0] - 5.0) < 0.01
        assert abs(result[1] - 7.0) < 0.01
