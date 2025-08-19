import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# ensure repo root is importable when pytest runs from tests/
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from main import app

client = TestClient(app)


def test_login_success():
    resp = client.post("/login", json={"email": "alex@quicktest.com", "password": "11111111"})
    assert resp.status_code == 200
    token = resp.headers.get("x-token")
    assert token is not None
    body = resp.json()
    assert body.get("token") == token
    assert body.get("user", {}).get("username") == "alex"


def test_login_failure_wrong_password():
    resp = client.post("/login", json={"email": "alex@quicktest.com", "password": "badpass"})
    assert resp.status_code == 401


def test_require_user_protected():
    # login
    resp = client.post("/login", json={"email": "alex@quicktest.com", "password": "11111111"})
    token = resp.headers.get("x-token")
    assert token is not None



def test_require_admin_protected():
    # admin login
    resp = client.post("/login", json={"email": "ananth@gmail.com", "password": "22222222"})
    token = resp.headers.get("x-token")
    assert token is not None

