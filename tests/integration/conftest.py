import subprocess
from pathlib import Path

import pytest

from helpers import WORKSPACE


@pytest.fixture(scope="session", autouse=True)
def ensure_ssl():
    result = subprocess.run(
        ["Scripts/setup-ssl.sh", "3"],
        capture_output=True, text=True,
        cwd=str(Path(WORKSPACE) / "MP-SPDZ"),
    )
    if result.returncode != 0:
        pytest.fail(f"SSL setup failed:\n{result.stdout}\n{result.stderr}")
