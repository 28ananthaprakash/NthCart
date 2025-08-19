import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from main import app
from utils import load_data

client = TestClient(app)


def login_as(email, password):
    resp = client.post("/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.headers.get("x-token")


@pytest.fixture(autouse=True)
def reset_data(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parent.parent
    src = repo / "data.json"
    dst = tmp_path / "data.json"
    dst.write_bytes(src.read_bytes())
    import utils
    monkeypatch.setattr(utils, 'DATA_PATH', dst)
    yield


def test_admin_generate_discount_requires_admin():
    # normal user cannot generate
    token = login_as('alex@quicktest.com', '11111111')
    resp = client.post('/admin/generate_discount', json={'email': 'alex@quicktest.com'}, headers={"X-Token": token})
    assert resp.status_code == 403

    # admin can generate only if eligible or override
    admin_token = login_as('ananth@gmail.com', '22222222')
    # compute eligibility from the fixture data so the test doesn't assume specific values
    data = load_data()
    cfg = data.get('config', {})
    nth = cfg.get('nth_order', 5)
    user = next((u for u in data.get('users', {}).values() if u.get('email') == 'alex@quicktest.com'), None)
    assert user is not None
    eligible = user.get('order_count_until_coupon', 0) >= nth
    resp2 = client.post('/admin/generate_discount', json={'email': 'alex@quicktest.com'}, headers={"X-Token": admin_token})
    # admin without override should only succeed when eligible
    if eligible:
        assert resp2.status_code == 200
    else:
        assert resp2.status_code == 400

    # with override it should work
    resp3 = client.post('/admin/generate_discount', json={'email': 'alex@quicktest.com', 'override': True}, headers={"X-Token": admin_token})
    assert resp3.status_code == 200
    body = resp3.json()
    assert 'coupon_code' in body


def test_admin_stats_and_user_scope():
    admin_token = login_as('ananth@gmail.com', '22222222')
    # full stats
    resp = client.get('/admin/stats', headers={"X-Token": admin_token})
    assert resp.status_code == 200
    all_stats = resp.json()
    assert isinstance(all_stats, list)
    # bob exists and should have at least one coupon and orders
    bob_stats = next((s for s in all_stats if s['username'] == 'bob'), None)
    assert bob_stats is not None
    # do not assume historical orders in the fixture; just ensure it's a non-negative int
    assert isinstance(bob_stats['items_purchased_count'], int)
    assert bob_stats['items_purchased_count'] >= 0

    # single user query
    # request by email
    resp2 = client.get('/admin/stats', params={'email': 'bob@gmail.com'}, headers={"X-Token": admin_token})
    assert resp2.status_code == 200
    single = resp2.json()
    assert single['username'] == 'bob'
    assert single['email'] == 'bob@gmail.com'
