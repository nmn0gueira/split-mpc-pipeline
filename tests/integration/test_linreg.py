"""
Uses small datasets with known linear relationships to verify that
the SGD solver learns approximately correct weights.

Protocol input layouts (for --features a1b0 --label b):
  psi: P0=[features],           P1=[labels]
  pid: P0=[flags, features],    P1=[flags, labels]  (flag=AND)
"""
from helpers import compile_program, parse_labeled_float, run_program, write_player_input

PSI_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "psi"]
PID_FLAGS = ["-R", "64", "-Z", "2", "-b", "100000", "--protocol", "pid"]
FIT_FLAGS = ["--n_epochs", "200", "--batch_size", "4", "--test_size", "0"]


class TestLinregPsi:
    def test_slope_two(self):
        write_player_input(0, [1, 2, 3, 4])
        write_player_input(1, [2, 4, 6, 8])
        compile_program(
            "linreg.py", *PSI_FLAGS,
            "--rows", "4", "--features", "a1b0", "--label", "b",
            *FIT_FLAGS,
        )
        output = run_program("ring.sh", "linreg")
        weight = parse_labeled_float(output, "Model Weights")
        bias = parse_labeled_float(output, "Model Bias")
        assert abs(weight - 2.0) < 0.1, f"weight={weight}"
        assert abs(bias) < 0.1, f"bias={bias}"

    def test_slope_half(self):
        write_player_input(0, [2, 4, 6, 8])
        write_player_input(1, [1, 2, 3, 4])
        compile_program(
            "linreg.py", *PSI_FLAGS,
            "--rows", "4", "--features", "a1b0", "--label", "b",
            *FIT_FLAGS,
        )
        output = run_program("ring.sh", "linreg")
        weight = parse_labeled_float(output, "Model Weights")
        bias = parse_labeled_float(output, "Model Bias")
        assert abs(weight - 0.5) < 0.1, f"weight={weight}"
        assert abs(bias) < 0.1, f"bias={bias}"


class TestLinregPid:
    """Private-ID: verify that sample_mask excludes non-intersection rows from training.

    Rows 2 and 3 carry outlier labels (100, 200 instead of 6, 8).
    With flag=[1,1,0,0] only rows 0,1 train, so the model should still
    learn y=2x despite the outliers being present in the input arrays.
    """

    def test_outlier_rows_masked_by_flag(self):
        write_player_input(0, [1, 1, 0, 0], [1, 2, 3, 4])
        write_player_input(1, [1, 1, 0, 0], [2, 4, 100, 200])
        # sample_mask halves the effective gradient (2 of 4 rows masked), so more epochs are needed for the same convergence as the PSI tests
        compile_program(
            "linreg.py", *PID_FLAGS,
            "--rows", "4", "--features", "a1b0", "--label", "b",
            "--n_epochs", "600", "--batch_size", "4", "--test_size", "0",
        )
        output = run_program("ring.sh", "linreg")
        weight = parse_labeled_float(output, "Model Weights")
        bias = parse_labeled_float(output, "Model Bias")

        assert abs(weight - 2.0) < 0.2, f"weight={weight}"
        assert abs(bias) < 0.2, f"bias={bias}"
