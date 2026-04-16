"""Tests for film roll CRUD endpoints (routers/rolls.py)."""
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _create_roll(client, roll_id="Roll-001", status="shooting", **extra):
    payload = {"roll_id": roll_id, "status": status, **extra}
    resp = await client.post("/api/rolls", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_photo(client, roll_db_id: int, frame_number: int = 1):
    resp = await client.post(
        f"/api/rolls/{roll_db_id}/photos",
        json={"roll_id": roll_db_id, "frame_number": frame_number},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── GET /api/rolls ────────────────────────────────────────────────────────────

async def test_list_rolls_empty_returns_empty_list(auth_client):
    resp = await auth_client.get("/api/rolls")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_rolls_returns_created_rolls(auth_client):
    await _create_roll(auth_client, "Roll-001")
    await _create_roll(auth_client, "Roll-002")
    resp = await auth_client.get("/api/rolls")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_list_rolls_returns_own_rolls_only(client):
    # Register and log in as user A
    await client.post("/api/auth/register", json={"username": "userA", "email": "a@x.com", "password": "pass1234"})
    resp_a = await client.post("/api/auth/login", json={"username": "userA", "password": "pass1234"})
    headers_a = {"Authorization": f"Bearer {resp_a.json()['access_token']}"}

    # Register and log in as user B
    await client.post("/api/auth/register", json={"username": "userB", "email": "b@x.com", "password": "pass1234"})
    resp_b = await client.post("/api/auth/login", json={"username": "userB", "password": "pass1234"})
    headers_b = {"Authorization": f"Bearer {resp_b.json()['access_token']}"}

    # User A creates 2 rolls, user B creates 1 roll
    await client.post("/api/rolls", json={"roll_id": "A-1"}, headers=headers_a)
    await client.post("/api/rolls", json={"roll_id": "A-2"}, headers=headers_a)
    await client.post("/api/rolls", json={"roll_id": "B-1"}, headers=headers_b)

    resp = await client.get("/api/rolls", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


async def test_list_rolls_photo_count_is_accurate(auth_client):
    """Bug Fix 3 regression: photo_count is computed in one query, not N+1."""
    roll = await _create_roll(auth_client, "Roll-photo-count")
    roll_id = roll["id"]

    await _create_photo(auth_client, roll_id, frame_number=1)
    await _create_photo(auth_client, roll_id, frame_number=2)
    await _create_photo(auth_client, roll_id, frame_number=3)

    resp = await auth_client.get("/api/rolls")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["photo_count"] == 3


async def test_list_rolls_filter_by_status(auth_client):
    await _create_roll(auth_client, "R-shoot", status="shooting")
    await _create_roll(auth_client, "R-finish", status="finished")
    await _create_roll(auth_client, "R-dev", status="developed")

    resp = await auth_client.get("/api/rolls?status=shooting")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "shooting"


async def test_list_rolls_ordered_newest_first(auth_client):
    r1 = await _create_roll(auth_client, "Roll-first")
    r2 = await _create_roll(auth_client, "Roll-second")
    r3 = await _create_roll(auth_client, "Roll-third")

    resp = await auth_client.get("/api/rolls")
    ids = [item["id"] for item in resp.json()["items"]]
    # Newest roll should appear first
    assert ids[0] == r3["id"]
    assert ids[-1] == r1["id"]


async def test_list_rolls_requires_authentication(client):
    resp = await client.get("/api/rolls")
    assert resp.status_code == 401


# ── POST /api/rolls ───────────────────────────────────────────────────────────

async def test_create_roll_minimal_data_returns_201(auth_client):
    resp = await auth_client.post("/api/rolls", json={"roll_id": "Min-Roll"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["roll_id"] == "Min-Roll"
    assert data["photo_count"] == 0
    assert data["total_frames"] == 36  # default


async def test_create_roll_full_data_returns_201(auth_client):
    payload = {
        "roll_id": "Full-Roll",
        "film_stock": "Kodak Portra 400",
        "camera": "Nikon F3",
        "iso": 400,
        "total_frames": 36,
        "status": "shooting",
        "note": "Test roll",
        "custom_data": {"key": "value"},
    }
    resp = await auth_client.post("/api/rolls", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["film_stock"] == "Kodak Portra 400"
    assert data["camera"] == "Nikon F3"
    assert data["iso"] == 400
    assert data["custom_data"] == {"key": "value"}


async def test_create_roll_duplicate_roll_id_returns_400(auth_client):
    await _create_roll(auth_client, "Dup-Roll")
    resp = await auth_client.post("/api/rolls", json={"roll_id": "Dup-Roll"})
    assert resp.status_code == 400


async def test_create_roll_duplicate_roll_id_different_user_succeeds(client):
    """roll_id uniqueness is per user, not global."""
    await client.post("/api/auth/register", json={"username": "userX", "email": "userx@example.com", "password": "pass1234"})
    rX = await client.post("/api/auth/login", json={"username": "userX", "password": "pass1234"})
    headers_x = {"Authorization": f"Bearer {rX.json()['access_token']}"}

    await client.post("/api/auth/register", json={"username": "userY", "email": "usery@example.com", "password": "pass1234"})
    rY = await client.post("/api/auth/login", json={"username": "userY", "password": "pass1234"})
    headers_y = {"Authorization": f"Bearer {rY.json()['access_token']}"}

    resp_x = await client.post("/api/rolls", json={"roll_id": "Shared-001"}, headers=headers_x)
    resp_y = await client.post("/api/rolls", json={"roll_id": "Shared-001"}, headers=headers_y)
    assert resp_x.status_code == 201
    assert resp_y.status_code == 201


async def test_create_roll_missing_roll_id_returns_422(auth_client):
    resp = await auth_client.post("/api/rolls", json={"film_stock": "Kodak"})
    assert resp.status_code == 422


async def test_create_roll_invalid_total_frames_returns_422(auth_client):
    resp = await auth_client.post("/api/rolls", json={"roll_id": "Bad-Frames", "total_frames": 0})
    assert resp.status_code == 422

    resp = await auth_client.post("/api/rolls", json={"roll_id": "Bad-Frames2", "total_frames": 73})
    assert resp.status_code == 422


async def test_create_roll_requires_authentication(client):
    resp = await client.post("/api/rolls", json={"roll_id": "NoAuth"})
    assert resp.status_code == 401


# ── GET /api/rolls/{roll_id} ──────────────────────────────────────────────────

async def test_get_roll_returns_correct_data(auth_client):
    created = await _create_roll(auth_client, "Get-Me", film_stock="Fuji")
    roll_id = created["id"]

    resp = await auth_client.get(f"/api/rolls/{roll_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == roll_id
    assert data["roll_id"] == "Get-Me"
    assert data["film_stock"] == "Fuji"
    assert "photo_count" in data


async def test_get_roll_nonexistent_returns_404(auth_client):
    resp = await auth_client.get("/api/rolls/99999")
    assert resp.status_code == 404


async def test_get_roll_other_users_roll_returns_404(client):
    await client.post("/api/auth/register", json={"username": "ownerU", "email": "owner@x.com", "password": "pass1234"})
    rO = await client.post("/api/auth/login", json={"username": "ownerU", "password": "pass1234"})
    headers_owner = {"Authorization": f"Bearer {rO.json()['access_token']}"}

    await client.post("/api/auth/register", json={"username": "thiefU", "email": "thief@x.com", "password": "pass1234"})
    rT = await client.post("/api/auth/login", json={"username": "thiefU", "password": "pass1234"})
    headers_thief = {"Authorization": f"Bearer {rT.json()['access_token']}"}

    roll_resp = await client.post("/api/rolls", json={"roll_id": "Owners-Roll"}, headers=headers_owner)
    roll_id = roll_resp.json()["id"]

    resp = await client.get(f"/api/rolls/{roll_id}", headers=headers_thief)
    assert resp.status_code == 404


async def test_get_roll_requires_authentication(client):
    resp = await client.get("/api/rolls/1")
    assert resp.status_code == 401


# ── PUT /api/rolls/{roll_id} ──────────────────────────────────────────────────

async def test_update_roll_partial_update_succeeds(auth_client):
    roll = await _create_roll(auth_client, "Update-Me", film_stock="Kodak")
    roll_id = roll["id"]

    resp = await auth_client.put(f"/api/rolls/{roll_id}", json={"camera": "Leica M6"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["camera"] == "Leica M6"
    assert data["film_stock"] == "Kodak"  # unchanged


async def test_update_roll_status_succeeds(auth_client):
    roll = await _create_roll(auth_client, "Status-Update", status="shooting")
    roll_id = roll["id"]

    resp = await auth_client.put(f"/api/rolls/{roll_id}", json={"status": "finished"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "finished"


async def test_update_roll_nonexistent_returns_404(auth_client):
    resp = await auth_client.put("/api/rolls/99999", json={"camera": "Nikon"})
    assert resp.status_code == 404


async def test_update_roll_other_users_roll_returns_404(client):
    await client.post("/api/auth/register", json={"username": "owner2", "email": "owner2@x.com", "password": "pass1234"})
    rO = await client.post("/api/auth/login", json={"username": "owner2", "password": "pass1234"})
    headers_owner = {"Authorization": f"Bearer {rO.json()['access_token']}"}

    await client.post("/api/auth/register", json={"username": "thief2", "email": "thief2@x.com", "password": "pass1234"})
    rT = await client.post("/api/auth/login", json={"username": "thief2", "password": "pass1234"})
    headers_thief = {"Authorization": f"Bearer {rT.json()['access_token']}"}

    roll_resp = await client.post("/api/rolls", json={"roll_id": "Protected"}, headers=headers_owner)
    roll_id = roll_resp.json()["id"]

    resp = await client.put(f"/api/rolls/{roll_id}", json={"camera": "Attacker"}, headers=headers_thief)
    assert resp.status_code == 404


async def test_update_roll_requires_authentication(client):
    resp = await client.put("/api/rolls/1", json={"camera": "NoAuth"})
    assert resp.status_code == 401


# ── DELETE /api/rolls/{roll_id} ───────────────────────────────────────────────

async def test_delete_roll_succeeds(auth_client):
    roll = await _create_roll(auth_client, "Delete-Me")
    roll_id = roll["id"]

    resp = await auth_client.delete(f"/api/rolls/{roll_id}")
    assert resp.status_code == 200
    assert "message" in resp.json()

    # Confirm it's gone
    resp = await auth_client.get(f"/api/rolls/{roll_id}")
    assert resp.status_code == 404


async def test_delete_roll_cascades_to_photos(auth_client):
    roll = await _create_roll(auth_client, "Roll-With-Photos")
    roll_id = roll["id"]
    await _create_photo(auth_client, roll_id, frame_number=1)
    await _create_photo(auth_client, roll_id, frame_number=2)

    await auth_client.delete(f"/api/rolls/{roll_id}")

    # Photos should also be gone (cascade)
    resp = await auth_client.get(f"/api/rolls/{roll_id}/photos")
    assert resp.status_code == 404


async def test_delete_roll_nonexistent_returns_404(auth_client):
    resp = await auth_client.delete("/api/rolls/99999")
    assert resp.status_code == 404


async def test_delete_roll_other_users_roll_returns_404(client):
    await client.post("/api/auth/register", json={"username": "owner3", "email": "owner3@x.com", "password": "pass1234"})
    rO = await client.post("/api/auth/login", json={"username": "owner3", "password": "pass1234"})
    headers_owner = {"Authorization": f"Bearer {rO.json()['access_token']}"}

    await client.post("/api/auth/register", json={"username": "thief3", "email": "thief3@x.com", "password": "pass1234"})
    rT = await client.post("/api/auth/login", json={"username": "thief3", "password": "pass1234"})
    headers_thief = {"Authorization": f"Bearer {rT.json()['access_token']}"}

    roll_resp = await client.post("/api/rolls", json={"roll_id": "Mine"}, headers=headers_owner)
    roll_id = roll_resp.json()["id"]

    resp = await client.delete(f"/api/rolls/{roll_id}", headers=headers_thief)
    assert resp.status_code == 404


async def test_delete_roll_requires_authentication(client):
    resp = await client.delete("/api/rolls/1")
    assert resp.status_code == 401
