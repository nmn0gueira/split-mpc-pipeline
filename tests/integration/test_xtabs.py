"""
Inputs are written as transposed CSVs: each get_input_from call reads
one space-separated line from Player-Data/Input-P{party}-0.

For sum-1 (single group-by column), group indices are 0-based.

Protocol input layouts (for --group_by a --values b):
  psi:  P0=[groups],        P1=[values]
  pid:  P0=[flags, groups], P1=[flags, values]  (flag=AND)
  ps3i: P0=[g_s0, v_s0],    P1=[g_s1, v_s1]  (reconstructed as s0+s1 mod 2^64)
  cpsi: P0=[f_s0, g_s0],    P1=[f_s1, g_s1, values] (flag=XOR, groups=add mod 2^32)
"""
from helpers import compile_program, parse_int_array, run_program, write_player_input

PSI_FLAGS  = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "psi"]
PID_FLAGS  = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "pid"]
PS3I_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "ps3i"]
CPSI_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "cpsi", "--share-type", "add32"]

XTABS_ARGS = ["--rows", "4", "--aggregation", "sum", "--group_by", "a", "--values", "b", "--n_cat_1", "2"]


class TestXtabsSum1Psi:
    def test_two_groups(self):
        write_player_input(0, [0, 1, 0, 1])
        write_player_input(1, [10, 20, 30, 40])
        compile_program("xtabs.py", *PSI_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [40, 60]

    def test_single_group_accumulates_all(self):
        write_player_input(0, [0, 0, 0, 0])
        write_player_input(1, [5, 10, 15, 20])
        compile_program("xtabs.py", *PSI_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        result = parse_int_array(output)
        assert result[0] == 50
        assert result[1] == 0

    def test_groups_from_bob(self):
        write_player_input(0, [100, 200, 300, 400])
        write_player_input(1, [0, 0, 1, 1])
        compile_program(
            "xtabs.py", *PSI_FLAGS,
            "--rows", "4", "--aggregation", "sum",
            "--group_by", "b", "--values", "a", "--n_cat_1", "2",
        )
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [300, 700]


class TestXtabsSum1Ps3i:
    def test_additive_share_reconstruction(self):
        write_player_input(0, [0, 1, 0, 1], [10, 20, 30, 40])
        write_player_input(1, [0, 0, 0, 0], [0, 0, 0, 0])
        compile_program("xtabs.py", *PS3I_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [40, 60]


class TestXtabsSum1Cpsi:
    def test_xor_flag_and_additive_alice_shares(self):
        write_player_input(0, [0, 0, 0, 0], [0, 1, 0, 1])
        write_player_input(1, [1, 1, 1, 1], [0, 0, 0, 0], [10, 20, 30, 40])
        compile_program("xtabs.py", *CPSI_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [40, 60]


class TestXtabsSum1Pid:
    def test_flag_masks_non_intersection_rows(self):
        write_player_input(0, [1, 1, 0, 0], [0, 1, 0, 1])
        write_player_input(1, [1, 1, 0, 0], [10, 20, 30, 40])
        compile_program("xtabs.py", *PID_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [10, 20]
