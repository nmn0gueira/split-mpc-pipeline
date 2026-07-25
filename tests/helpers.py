import os
import re
import subprocess
import threading
from pathlib import Path

import pytest

from iprep import transform_csv
from match import run_protocol

WORKSPACE = str(Path(__file__).parents[1])
PLAYER_DATA = os.path.join(WORKSPACE, "MP-SPDZ", "Player-Data")


def compile_program(program, *args):
    result = subprocess.run(
        ["bash", "scripts/compile.sh", program, *args],
        capture_output=True, text=True, cwd=WORKSPACE,
    )
    if result.returncode != 0:
        pytest.fail(f"Compile failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout + result.stderr


def run_program(script, name):
    result = subprocess.run(
        ["bash", "scripts/run.sh", script, name],
        capture_output=True, text=True, cwd=WORKSPACE,
    )
    if result.returncode != 0:
        pytest.fail(f"Run failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout + result.stderr


def run_program_background(script, name):
    return subprocess.Popen(
        ["bash", "scripts/run.sh", script, name],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=WORKSPACE,
    )


def parse_int_array(output):
    m = re.search(r'\[([^\[\]]+)\]', output)
    assert m, f"No array found in output:\n{output}"
    return [int(x.strip()) for x in m.group(1).split(",")]


def parse_float_array(output):
    m = re.search(r'\[([^\[\]]+)\]', output)
    assert m, f"No array found in output:\n{output}"
    return [float(x.strip()) for x in m.group(1).split(",")]


def parse_int_matrix(output):
    arrays = re.findall(r'\[([^\[\]]+)\]', output)
    assert arrays, f"No matrix found in output:\n{output}"
    return [[int(x.strip()) for x in a.split(",")] for a in arrays]


def parse_float_matrix(output):
    arrays = re.findall(r'\[([^\[\]]+)\]', output)
    assert arrays, f"No matrix found in output:\n{output}"
    return [[float(x.strip()) for x in a.split(",")] for a in arrays]


def parse_labeled_float(output, label):
    m = re.search(rf'{re.escape(label)}:\s*(\S+)', output)
    assert m, f"Label '{label}' not found in output:\n{output}"
    return float(m.group(1))


def write_player_input(party, *rows):
    path = os.path.join(PLAYER_DATA, f"Input-P{party}-0")
    with open(path, "w") as f:
        for row in rows:
            f.write(" ".join(str(v) for v in row) + "\n")


def start_client_background(client_id, nparties):
    return subprocess.Popen(
        ["bash", "scripts/run.sh", "client-input.x",
         "--client_id", str(client_id),
         "--nparties", str(nparties)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=WORKSPACE,
    )


def run_client(client_id, nparties, finish=False):
    args = [
        "bash", "scripts/run.sh", "client-input.x",
        "--client_id", str(client_id),
        "--nparties", str(nparties),
    ]
    if finish:
        args.append("--finish")
    result = subprocess.run(args, capture_output=True, text=True, cwd=WORKSPACE)
    if result.returncode != 0:
        pytest.fail(f"client-input.x failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout + result.stderr


def parse_client_int_outputs(output):
    return [int(m.group(1)) for m in re.finditer(r'Output:\s*(-?\d+)', output)]


def parse_client_sfix_outputs(output):
    return [float(m.group(1)) for m in re.finditer(r'Output:\s*(-?[\d.]+)', output)]


def write_csv(path, rows):
    with open(path, "w") as f:
        for row in rows:
            f.write(",".join(str(v) for v in row) + "\n")


def run_match_background(protocol, input_csv, output_csv, address, extra_args=None):
    t = threading.Thread(
        target=run_protocol,
        args=(protocol, input_csv, None, output_csv, address, extra_args or []),
        daemon=True,
    )
    t.start()
    return t


def run_match(protocol, input_csv, output_csv, address, extra_args=None):
    run_protocol(protocol, input_csv, None, output_csv, address, extra_args or [])


def run_iprep(input_csv, party, columns, player_data_dir=None):
    transform_csv(
        input_csv,
        player_data_dir or PLAYER_DATA,
        party,
        columns=columns,
    )
