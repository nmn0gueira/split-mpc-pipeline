import os

import pytest

from helpers import WORKSPACE

ALICE_ROWS = [
    ("alice001", 1),
    ("alice002", 2),
    ("shared001", 1),
    ("shared002", 1),
    ("shared003", 2),
    ("shared004", 2),
]

BOB_ROWS = [
    ("bob001", 100),
    ("bob002", 200),
    ("shared001", 10),
    ("shared002", 20),
    ("shared003", 30),
    ("shared004", 40),
]

VOLEPSI_BIN = os.path.join(WORKSPACE, "match/volepsi/out/build/linux/frontend/frontend")
PRIVATEID_BIN = os.path.join(WORKSPACE, "match/Private-ID/target/release/cross-psi-server")
KUNLUN_BIN = os.path.join(WORKSPACE, "match/Kunlun/build/main_pid")


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_volepsi: skip if volepsi binary not built")
    config.addinivalue_line("markers", "requires_privateid: skip if Private-ID binaries not built")
    config.addinivalue_line("markers", "requires_kunlun: skip if Kunlun binary not built")


@pytest.fixture(autouse=True)
def skip_missing_binaries(request):
    checks = {
        "requires_volepsi": VOLEPSI_BIN,
        "requires_privateid": PRIVATEID_BIN,
        "requires_kunlun": KUNLUN_BIN,
    }
    for mark, path in checks.items():
        if request.node.get_closest_marker(mark) and not os.path.exists(path):
            pytest.skip(f"{mark.removeprefix('requires_')} binary not found at {path}")
