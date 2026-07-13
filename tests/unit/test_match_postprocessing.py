import pandas as pd
import pytest

from match import (
    get_effective_input_path,
    post_process_cpsi,
    post_process_pid,
    post_process_ps3i_xor,
    post_process_psi,
)


def write_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False, header=False)


def read_csv(path):
    return pd.read_csv(path, header=None)


class TestPostProcessPsi:
    def test_resolves_intersection_ids_to_data(self, tmp_path):
        input_file = tmp_path / "alice.csv"
        output_file = tmp_path / "output.csv"

        write_csv(input_file, [["carol", 50, "x"], ["frank", 20, "y"], ["alice", 10, "z"]])
        write_csv(output_file, [["carol"], ["frank"]])

        post_process_psi(str(input_file), str(output_file))

        result = read_csv(output_file)
        assert result.shape == (2, 2)
        assert result[0].tolist() == [50, 20]
        assert result[1].tolist() == ["x", "y"]

    def test_id_column_is_dropped(self, tmp_path):
        input_file = tmp_path / "alice.csv"
        output_file = tmp_path / "output.csv"

        write_csv(input_file, [["carol", 50]])
        write_csv(output_file, [["carol"]])

        post_process_psi(str(input_file), str(output_file))

        result = read_csv(output_file)

        assert result.shape == (1, 1)
        assert result[0].tolist() == [50]

    def test_output_order_follows_psi_result(self, tmp_path):
        input_file = tmp_path / "alice.csv"
        output_file = tmp_path / "output.csv"

        write_csv(input_file, [["carol", 50], ["frank", 20]])
        write_csv(output_file, [["frank"], ["carol"]])

        post_process_psi(str(input_file), str(output_file))

        result = read_csv(output_file)
        assert result[0].tolist() == [20, 50]

    def test_single_match(self, tmp_path):
        input_file = tmp_path / "alice.csv"
        output_file = tmp_path / "output.csv"

        write_csv(input_file, [["carol", 50], ["frank", 20], ["alice", 10]])
        write_csv(output_file, [["alice"]])

        post_process_psi(str(input_file), str(output_file))

        result = read_csv(output_file)
        assert result.shape == (1, 1)
        assert result[0].tolist() == [10]


HEX_10 = "0" * 24 + "0000000A"
HEX_99 = "0" * 24 + "00000063"
HEX_77 = "0" * 24 + "0000004D"


class TestPostProcessCpsi:
    def test_receiver_converts_hex_shares_to_int(self, tmp_path):
        output_file = tmp_path / "output.csv"

        write_csv(output_file, [[0, HEX_10], [1, HEX_99]])

        post_process_cpsi("unused", str(output_file), is_server=False, temp_files=[])

        result = read_csv(output_file)
        assert result[0].tolist() == [0, 1]
        assert result[1].tolist() == [10, 99]

    def test_receiver_multiple_share_columns(self, tmp_path):
        output_file = tmp_path / "output.csv"

        write_csv(output_file, [[0, HEX_10, HEX_77], [1, HEX_99, HEX_10]])

        post_process_cpsi("unused", str(output_file), is_server=False, temp_files=[])

        result = read_csv(output_file)
        assert result[1].tolist() == [10, 99]
        assert result[2].tolist() == [77, 10]

    def test_server_appends_own_data_at_mapped_positions(self, tmp_path):
        input_file = tmp_path / "bob.csv"
        output_file = tmp_path / "output.csv"
        mapping_file = tmp_path / "mapping.out"

        write_csv(input_file, [["carol", 99], ["frank", 77]])
        write_csv(output_file, [[0, HEX_10], [1, HEX_10], [0, HEX_10], [1, HEX_10]])
        mapping_file.write_text("1\n3")

        post_process_cpsi(str(input_file), str(output_file), is_server=True, temp_files=[])

        result = read_csv(output_file)
        assert result.shape == (4, 3)  # flag col, share col, bob's value col
        assert result[2].tolist() == [0, 99, 0, 77]

    def test_server_non_intersection_rows_stay_zero(self, tmp_path):
        input_file = tmp_path / "bob.csv"
        output_file = tmp_path / "output.csv"
        mapping_file = tmp_path / "mapping.out"

        write_csv(input_file, [["alice", 42]])
        write_csv(output_file, [[0, HEX_10], [1, HEX_10], [0, HEX_10]])
        mapping_file.write_text("2")

        post_process_cpsi(str(input_file), str(output_file), is_server=True, temp_files=[])

        result = read_csv(output_file)
        assert result[2].tolist() == [0, 0, 42]


class TestPostProcessPs3iXor:
    def test_concatenates_company_and_partner_horizontally(self, tmp_path):
        output_path = str(tmp_path / "output.csv")

        write_csv(output_path + "_company_feature.csv", [[10, 20], [30, 40]])
        write_csv(output_path + "_partner_feature.csv", [[1, 2], [3, 4]])

        post_process_ps3i_xor(output_path, [])

        result = read_csv(output_path)
        assert result.shape == (2, 4)
        assert result.iloc[0].tolist() == [10, 20, 1, 2]
        assert result.iloc[1].tolist() == [30, 40, 3, 4]

    def test_single_column_each_side(self, tmp_path):
        output_path = str(tmp_path / "output.csv")

        write_csv(output_path + "_company_feature.csv", [[5], [6]])
        write_csv(output_path + "_partner_feature.csv", [[7], [8]])

        post_process_ps3i_xor(output_path, [])

        result = read_csv(output_path)
        assert result.shape == (2, 2)
        assert result.iloc[0].tolist() == [5, 7]
        assert result.iloc[1].tolist() == [6, 8]


class TestPostProcessPid:
    def test_sets_flag_and_data_at_mapped_positions(self, tmp_path):
        """
        Private-ID output has all UIDs in col 0 (shuffled, shared by both parties)
        and this party's UIDs in col 1 (in input order). The function places flag=1
        and the party's data at the rows where their UIDs appear in the global list.
        """
        input_file = tmp_path / "alice.csv"
        output_file = tmp_path / "output.csv"

        write_csv(input_file, [["carol", 50], ["frank", 20]])

        # Global UID list (col 0): uid_c at row 0, uid_a at row 1, uid_b at row 2, uid_d at row 3
        # Alice's UIDs (col 1): carol corresponds to uid_a, and frank corresponds to uid_b
        write_csv(output_file, [
            ["uid_c", "uid_a"],
            ["uid_a", "uid_b"],
            ["uid_b", "extra"],
            ["uid_d", "extra"],
        ])

        post_process_pid(str(input_file), str(output_file), [])

        result = read_csv(output_file)
        assert result.shape == (4, 2)
        assert result[0].tolist() == [0, 1, 1, 0]
        assert result[1].tolist() == [0, 50, 20, 0]

    def test_output_size_matches_union(self, tmp_path):
        input_file = tmp_path / "alice.csv"
        output_file = tmp_path / "output.csv"

        write_csv(input_file, [["alice", 1]])
        write_csv(output_file, [
            ["uid_x", "uid_x"],
            ["uid_y", "extra"],
            ["uid_z", "extra"],
        ])

        post_process_pid(str(input_file), str(output_file), [])

        result = read_csv(output_file)
        assert len(result) == 3

    def test_single_item_intersection(self, tmp_path):
        input_file = tmp_path / "alice.csv"
        output_file = tmp_path / "output.csv"

        write_csv(input_file, [["alice", 42]])
        write_csv(output_file, [
            ["uid_b", "uid_a"],
            ["uid_a", "extra"],
        ])

        post_process_pid(str(input_file), str(output_file), [])

        result = read_csv(output_file)
        # alice→uid_a is at row 1
        assert result[0].tolist() == [0, 1]
        assert result[1].tolist() == [0, 42]


class TestGetEffectiveInputPath:
    def test_psi_uses_provided_id_path(self, tmp_path):
        id_file = tmp_path / "ids.csv"
        id_file.touch()
        result = get_effective_input_path("psi", "full.csv", str(id_file), [])
        assert result == str(id_file)

    def test_psi_extracts_ids_when_no_id_path(self, tmp_path):
        input_file = tmp_path / "alice.csv"
        write_csv(input_file, [["carol", 50, "x"], ["frank", 20, "y"]])

        result = get_effective_input_path("psi", str(input_file), None, [])

        extracted = read_csv(result)
        assert extracted.shape == (2, 1)
        assert extracted[0].tolist() == ["carol", "frank"]

    def test_cpsi_server_uses_ids_only(self, tmp_path):
        id_file = tmp_path / "ids.csv"
        id_file.touch()
        result = get_effective_input_path("cpsi", "full.csv", str(id_file), [], is_server=True)
        assert result == str(id_file)

    def test_cpsi_client_uses_full_input_regardless(self, tmp_path):
        id_file = tmp_path / "ids.csv"
        id_file.touch()
        result = get_effective_input_path("cpsi", "full.csv", str(id_file), [], is_server=False)
        assert result == "full.csv"

    def test_ps3i_always_uses_full_input(self, tmp_path):
        result = get_effective_input_path("ps3i", "full.csv", None, [])
        assert result == "full.csv"

    def test_ps3i_xor_always_uses_full_input(self, tmp_path):
        result = get_effective_input_path("ps3i-xor", "full.csv", "ids.csv", [])
        assert result == "full.csv"

    def test_pid_uses_provided_id_path(self, tmp_path):
        id_file = tmp_path / "ids.csv"
        id_file.touch()
        result = get_effective_input_path("pid", "full.csv", str(id_file), [])
        assert result == str(id_file)
