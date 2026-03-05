import os
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

_test_db = os.path.join(tempfile.gettempdir(), "duodish_test.db")
os.environ["DB_PATH"] = _test_db

import pytest
from fastapi.testclient import TestClient
from app.main import app

IMAGE_DIR = os.path.join(TEST_DIR, "test_image")

_state: dict = {}


@pytest.fixture(scope="session")
def state():
    return _state


@pytest.fixture(scope="session")
def image_dir():
    return IMAGE_DIR


@pytest.fixture(scope="session", autouse=True)
def api():
    if os.path.exists(_test_db):
        os.remove(_test_db)
    wal = _test_db + "-wal"
    shm = _test_db + "-shm"
    for f in (wal, shm):
        if os.path.exists(f):
            os.remove(f)

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    for f in (_test_db, wal, shm):
        if os.path.exists(f):
            os.remove(f)
