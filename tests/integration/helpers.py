import os
import re
import subprocess
from pathlib import Path

import pytest

WORKSPACE = str(Path(__file__).parents[2])
PLAYER_DATA = os.path.join(WORKSPACE, "MP-SPDZ", "Player-Data")


def write_player_input(party, *rows):
    path = os.path.join(PLAYER_DATA, f"Input-P{party}-0")
    with open(path, "w") as f:
        for row in rows:
            f.write(" ".join(str(v) for v in row) + "\n")


def compile_program(program, *args):
    result = subprocess.run(
        ["scripts/compile.sh", program, *args],
        capture_output=True, text=True, cwd=WORKSPACE,
    )
    if result.returncode != 0:
        pytest.fail(f"Compile failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout + result.stderr


def run_program(script, name):
    result = subprocess.run(
        ["scripts/run.sh", script, name],
        capture_output=True, text=True, cwd=WORKSPACE,
    )
    if result.returncode != 0:
        pytest.fail(f"Run failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout + result.stderr


def parse_int_array(output):
    m = re.search(r'\[([^\[\]]+)\]', output)
    assert m, f"No array found in output:\n{output}"
    return [int(x.strip()) for x in m.group(1).split(",")]


def parse_float_array(output):
    m = re.search(r'\[([^\[\]]+)\]', output)
    assert m, f"No array found in output:\n{output}"
    return [float(x.strip()) for x in m.group(1).split(",")]


def parse_labeled_float(output, label):
    m = re.search(rf'{re.escape(label)}:\s*(\S+)', output)
    assert m, f"Label '{label}' not found in output:\n{output}"
    return float(m.group(1))
