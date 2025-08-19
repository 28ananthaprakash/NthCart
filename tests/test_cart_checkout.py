import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from main import app
from utils import load_data, save_data

client = TestClient(app)


def login_as(username, password):
    # map known usernames to their emails in data.json
    if username == 'ananth':
        email = 'ananth@gmail.com'
    elif username == 'bob':
        email = 'bob@gmail.com'
    else:
        email = f"{username}@quicktest.com"
    resp = client.post("/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.headers.get("x-token")


@pytest.fixture(autouse=True)
def reset_data(tmp_path, monkeypatch):
    # copy original data.json to temp and point DATA_PATH to it
    repo = Path(__file__).resolve().parent.parent
    src = repo / "data.json"
    dst = tmp_path / "data.json"
    dst.write_bytes(src.read_bytes())
    # monkeypatch the DATA_PATH in utils
    import utils
    monkeypatch.setattr(utils, 'DATA_PATH', dst)
    yield


def test_items_list_requires_auth_and_returns_items():
    token = login_as('alex', '11111111')
    resp = client.get("/items", headers={"X-Token": token})
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert any(i.get('id') == 1 for i in items)


def test_add_to_cart_and_view():
    token = login_as('alex', '11111111')
    # add 2 of item 1
    resp = client.post("/cart/add", json={"item_id": 1, "qty": 2}, headers={"X-Token": token})
    assert resp.status_code == 200
    # view cart
    resp2 = client.get("/cart", headers={"X-Token": token})
    assert resp2.status_code == 200
    body = resp2.json()
    assert body.get('total') == 499.0 * 2
    assert len(body.get('items')) == 1


def test_checkout_without_coupon_and_stock_decrement():
    token = login_as('alex', '11111111')
    # add 1 of item 2
    resp = client.post("/cart/add", json={"item_id": 2, "qty": 1}, headers={"X-Token": token})
    assert resp.status_code == 200
    # checkout
    resp2 = client.post("/cart/checkout", json={}, headers={"X-Token": token})
    assert resp2.status_code == 200
    order = resp2.json()
    assert order.get('subtotal') == 349.0
    assert order.get('discount') == 0.0
    assert order.get('total') == 349.0
    # verify stock decremented
    data = load_data()
    item = next(i for i in data['items'] if i['id'] == 2)
    assert item['stock'] == 499


def test_checkout_with_invalid_coupon_fails():
    token = login_as('alex', '11111111')
    client.post("/cart/add", json={"item_id": 1, "qty": 1}, headers={"X-Token": token})
    resp = client.post("/cart/checkout", json={"discount_code": "NOPE"}, headers={"X-Token": token})
    assert resp.status_code == 400


def test_coupon_must_belong_to_user_and_be_unused():
    # Bob has a coupon in data.json CB0B1234
    token = login_as('bob', '33333333')
    client.post("/cart/add", json={"item_id": 4, "qty": 1}, headers={"X-Token": token})
    resp = client.post("/cart/checkout", json={"discount_code": "CB0B1234"}, headers={"X-Token": token})
    assert resp.status_code == 200
    order = resp.json()
    assert order.get('discount') > 0
    # second use should fail
    token2 = login_as('bob', '33333333')
    client.post("/cart/add", json={"item_id": 4, "qty": 1}, headers={"X-Token": token2})
    resp2 = client.post("/cart/checkout", json={"discount_code": "CB0B1234"}, headers={"X-Token": token2})
    assert resp2.status_code == 400
        # Removed stray end patch marker
