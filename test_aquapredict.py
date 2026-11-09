import os
import shutil
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

PROJECT_FOLDER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_FOLDER)


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    work_folder = tmp_path_factory.mktemp("work")
    shutil.copy(os.path.join(PROJECT_FOLDER, "model.pkl"), work_folder)
    old_folder = os.getcwd()
    os.chdir(work_folder)
    import main
    with TestClient(main.app) as test_client:
        yield test_client
    os.chdir(old_folder)


def make_user(client):
    email = uuid.uuid4().hex[:8] + "@test.com"
    client.post("/auth/register", json={"name": "Test", "email": email, "password": "pass123"})
    login = client.post("/auth/login", json={"email": email, "password": "pass123"})
    return login.json()["user_id"]


def make_tank(client, capacity=500):
    user_id = make_user(client)
    response = client.post("/tanks", json={"user_id": user_id, "name": "Test tank", "capacity": capacity})
    return response.json()["tank_id"]


def send_level(client, tank_id, level):
    return client.post("/readings", json={"tank_id": tank_id, "level": level})


# ---------- Functional tests ----------

def test_register_new_user(client):
    email = uuid.uuid4().hex[:8] + "@test.com"
    response = client.post("/auth/register", json={"name": "Test", "email": email, "password": "pass123"})
    assert response.status_code == 200


def test_register_duplicate_email(client):
    email = uuid.uuid4().hex[:8] + "@test.com"
    body = {"name": "Test", "email": email, "password": "pass123"}
    client.post("/auth/register", json=body)
    response = client.post("/auth/register", json=body)
    assert response.status_code == 400


def test_login_correct(client):
    email = uuid.uuid4().hex[:8] + "@test.com"
    client.post("/auth/register", json={"name": "Test", "email": email, "password": "pass123"})
    response = client.post("/auth/login", json={"email": email, "password": "pass123"})
    assert response.status_code == 200
    assert "user_id" in response.json()


def test_login_wrong_password(client):
    email = uuid.uuid4().hex[:8] + "@test.com"
    client.post("/auth/register", json={"name": "Test", "email": email, "password": "pass123"})
    response = client.post("/auth/login", json={"email": email, "password": "wrong"})
    assert response.status_code == 401


def test_tank_capacity_must_be_positive(client):
    user_id = make_user(client)
    response = client.post("/tanks", json={"user_id": user_id, "name": "Bad", "capacity": 0})
    assert response.status_code in (400, 422)


def test_first_reading_is_idle(client):
    tank_id = make_tank(client)
    response = send_level(client, tank_id, 100)
    assert response.status_code == 200
    assert response.json()["status"] == "Idle"
    assert response.json()["fill_speed"] == 0


def test_warning_then_critical(client):
    tank_id = make_tank(client)
    send_level(client, tank_id, 400)
    warning = send_level(client, tank_id, 430).json()
    assert warning["fill_speed"] == 30
    assert warning["status"] == "Warning"
    assert warning["ring"] == 0
    critical = send_level(client, tank_id, 460).json()
    assert critical["status"] == "Critical"
    assert critical["ring"] == 1


def test_full_tank(client):
    tank_id = make_tank(client)
    response = send_level(client, tank_id, 499)
    assert response.json()["status"] == "Full"


def test_level_above_capacity_rejected(client):
    tank_id = make_tank(client)
    response = send_level(client, tank_id, 900)
    assert response.status_code == 400


def test_history_newest_first_and_notifications(client):
    tank_id = make_tank(client)
    send_level(client, tank_id, 400)
    send_level(client, tank_id, 430)
    send_level(client, tank_id, 460)
    history = client.get("/history", params={"tank_id": tank_id}).json()
    assert len(history) == 3
    assert history[0]["level"] == 460
    notifications = client.get("/notifications", params={"tank_id": tank_id}).json()
    assert len(notifications) == 2


# ---------- Database tests ----------

def test_all_four_tables_exist(client):
    from database import get_connection
    connection = get_connection()
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    connection.close()
    names = {row["name"] for row in rows}
    assert {"users", "tanks", "readings", "notifications"}.issubset(names)


def test_password_is_stored_as_hash(client):
    from database import get_connection
    email = uuid.uuid4().hex[:8] + "@test.com"
    client.post("/auth/register", json={"name": "Test", "email": email, "password": "pass123"})
    connection = get_connection()
    row = connection.execute("SELECT password_hash FROM users WHERE email = ?", (email,)).fetchone()
    connection.close()
    assert row["password_hash"] != "pass123"
    assert "$" in row["password_hash"]


def test_reading_is_saved_in_database(client):
    from database import get_connection
    tank_id = make_tank(client)
    send_level(client, tank_id, 250)
    connection = get_connection()
    row = connection.execute("SELECT level FROM readings WHERE tank_id = ?", (tank_id,)).fetchone()
    connection.close()
    assert row["level"] == 250


def test_critical_alert_saved_with_ring(client):
    from database import get_connection
    tank_id = make_tank(client)
    send_level(client, tank_id, 400)
    send_level(client, tank_id, 430)
    send_level(client, tank_id, 460)
    connection = get_connection()
    row = connection.execute(
        "SELECT ring FROM notifications WHERE tank_id = ? ORDER BY id DESC LIMIT 1", (tank_id,)
    ).fetchone()
    connection.close()
    assert row["ring"] == 1