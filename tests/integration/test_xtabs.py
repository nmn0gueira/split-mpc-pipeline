"""
Inputs are written as transposed CSVs: each get_input_from call reads
one space-separated line from Player-Data/Input-P{party}-0.

Group indices are 1-based and 0 is the sentinel for excluded rows (masked by the flag).

Protocol input layouts (for --group_by a --values b):
  psi:  P0=[groups],        P1=[values]
  pid:  P0=[flags, groups], P1=[flags, values]  (flag=AND)
  ps3i: P0=[g_s0, v_s0],    P1=[g_s1, v_s1]  (reconstructed as s0+s1 mod 2^64)
  cpsi: P0=[f_s0, g_s0],    P1=[f_s1, g_s1, values] (flag=XOR, groups=add mod 2^32)
"""
from helpers import compile_program, parse_float_array, parse_float_matrix, parse_int_array, parse_int_matrix, run_program, write_player_input

PSI_FLAGS  = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "psi"]
PID_FLAGS  = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "pid"]
PS3I_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "ps3i"]
CPSI_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "cpsi", "--share-type", "add32"]

XTABS_1D = ["--group_by", "a", "--values", "b", "--n_cat_1", "2"]
XTABS_2D = ["--group_by", "ab", "--values", "b", "--n_cat_1", "2", "--n_cat_2", "2"]
XTABS_2D_NOVALS = ["--group_by", "ab", "--n_cat_1", "2", "--n_cat_2", "2"]

XTABS_ARGS = ["--rows", "4", "--aggregation", "sum", *XTABS_1D]


class TestXtabsSum1Psi:
    def test_two_groups(self):
        write_player_input(0, [1, 2, 1, 2])
        write_player_input(1, [10, 20, 30, 40])
        compile_program("xtabs.py", *PSI_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [40, 60]

    def test_single_group_accumulates_all(self):
        write_player_input(0, [1, 1, 1, 1])
        write_player_input(1, [5, 10, 15, 20])
        compile_program("xtabs.py", *PSI_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        result = parse_int_array(output)
        assert result[0] == 50
        assert result[1] == 0

    def test_groups_from_bob(self):
        write_player_input(0, [100, 200, 300, 400])
        write_player_input(1, [1, 1, 2, 2])
        compile_program(
            "xtabs.py", *PSI_FLAGS,
            "--rows", "4", "--aggregation", "sum",
            "--group_by", "b", "--values", "a", "--n_cat_1", "2",
        )
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [300, 700]


class TestXtabsSum1Ps3i:
    def test_additive_share_reconstruction(self):
        write_player_input(0,
            [8765432109876543210, 3456789012345678901, 7890123456789012345, 2345678901234567890],
            [6789012345678901234, 1234567890123456789, 9012345678901234567, 4567890123456789012],
        )
        write_player_input(1,
            [9681311963833008407, 14989955061363872717, 10556620616920539272, 16101065172474983728],
            [11657731728030650392, 17212176183586094847, 9434398394808317079, 13878853950252762644],
        )
        compile_program("xtabs.py", *PS3I_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [40, 60]


class TestXtabsSum1Cpsi:
    def test_xor_flag_and_additive_alice_shares(self):
        write_player_input(0, [1, 0, 1, 0], [2847392156, 1923847561, 3912847561, 847392156])
        write_player_input(1, [0, 1, 0, 1], [1447575141, 2371119737, 382119736, 3447575142], [10, 20, 30, 40])
        compile_program("xtabs.py", *CPSI_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [40, 60]


class TestXtabsSum1Pid:
    def test_flag_masks_non_intersection_rows(self):
        write_player_input(0, [1, 1, 0, 0], [1, 2, 1, 2])
        write_player_input(1, [1, 1, 0, 0], [10, 20, 30, 40])
        compile_program("xtabs.py", *PID_FLAGS, *XTABS_ARGS)
        output = run_program("ring.sh", "xtabs-sum-1")
        assert parse_int_array(output) == [10, 20]


class TestXtabsSum2Psi:
    def test_two_groups_two_columns(self):
        write_player_input(0, [1, 1, 2, 2])
        write_player_input(1, [1, 2, 1, 2], [10, 20, 30, 40])
        compile_program("xtabs.py", *PSI_FLAGS, "--rows", "4", "--aggregation", "sum", *XTABS_2D)
        output = run_program("ring.sh", "xtabs-sum-2")
        assert parse_int_matrix(output) == [[10, 20], [30, 40]]


class TestXtabsAvg1Psi:
    def test_average_per_group(self):
        write_player_input(0, [1, 1, 2, 2])
        write_player_input(1, [10, 30, 20, 40])
        compile_program("xtabs.py", *PSI_FLAGS, "--rows", "4", "--aggregation", "avg", *XTABS_1D)
        output = run_program("ring.sh", "xtabs-avg-1")
        result = parse_float_array(output)
        assert abs(result[0] - 20.0) < 0.5
        assert abs(result[1] - 30.0) < 0.5


class TestXtabsAvg2Psi:
    def test_average_per_group_pair(self):
        write_player_input(0, [1, 1, 1, 2, 2, 2])
        write_player_input(1, [1, 2, 1, 2, 1, 2], [10, 20, 30, 40, 50, 60])
        compile_program("xtabs.py", *PSI_FLAGS, "--rows", "6", "--aggregation", "avg", *XTABS_2D)
        output = run_program("ring.sh", "xtabs-avg-2")
        result = parse_float_matrix(output)
        assert abs(result[0][0] - 20.0) < 0.5
        assert abs(result[0][1] - 20.0) < 0.5
        assert abs(result[1][0] - 50.0) < 0.5
        assert abs(result[1][1] - 50.0) < 0.5


class TestXtabsStd1Psi:
    def test_std_per_group(self):
        write_player_input(0, [1, 1, 2, 2])
        write_player_input(1, [10, 30, 20, 40])
        compile_program("xtabs.py", *PSI_FLAGS, "--rows", "4", "--aggregation", "std", *XTABS_1D)
        output = run_program("ring.sh", "xtabs-std-1")
        result = parse_float_array(output)
        assert abs(result[0] - 10.0) < 0.5
        assert abs(result[1] - 10.0) < 0.5


class TestXtabsStd2Psi:
    def test_std_per_group_pair(self):
        write_player_input(0, [1, 1, 1, 1, 2, 2, 2, 2])
        write_player_input(1, [1, 1, 2, 2, 1, 1, 2, 2], [10, 30, 20, 40, 50, 70, 60, 80])
        compile_program("xtabs.py", *PSI_FLAGS, "--rows", "8", "--aggregation", "std", *XTABS_2D)
        output = run_program("ring.sh", "xtabs-std-2")
        result = parse_float_matrix(output)
        for row in result:
            for val in row:
                assert abs(val - 10.0) < 0.5


class TestXtabsFreq2Psi:
    def test_frequency_count(self):
        write_player_input(0, [1, 1, 2, 2])
        write_player_input(1, [1, 2, 1, 2])
        compile_program("xtabs.py", *PSI_FLAGS, "--rows", "4", "--aggregation", "freq", *XTABS_2D_NOVALS)
        output = run_program("ring.sh", "xtabs-freq-2")
        assert parse_int_matrix(output) == [[1, 1], [1, 1]]


class TestXtabsMode2Psi:
    def test_mode_per_group(self):
        write_player_input(0, [1, 1, 1, 2, 2, 2])
        write_player_input(1, [1, 1, 2, 2, 2, 1])
        compile_program("xtabs.py", *PSI_FLAGS, "--rows", "6", "--aggregation", "mode", *XTABS_2D_NOVALS)
        output = run_program("ring.sh", "xtabs-mode-2")
        assert parse_int_array(output) == [1, 2]
