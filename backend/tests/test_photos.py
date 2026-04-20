"""Tests for photo CRUD endpoints (routers/rolls.py photo section)."""
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _create_roll(client, roll_id="Roll-001"):
    resp = await client.post("/api/rolls", json={"roll_id": roll_id})
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def _create_photo(client, roll_db_id: int, frame_number: int = 1, **extra):
    payload = {"roll_id": roll_db_id, "frame_number": frame_number, **extra}
    resp = await client.post(f"/api/rolls/{roll_db_id}/photos", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _token(login_resp):
    return login_resp.json()["data"]["session"]["access_token"]


# ── GET /api/rolls/{roll_id}/photos ──────────────────────────────────────────

async def test_list_photos_empty_returns_empty_list(auth_client):
    roll = await _create_roll(auth_client, "Empty-Roll")
    resp = await auth_client.get(f"/api/rolls/{roll['id']}/photos")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_photos_ordered_by_frame_number(auth_client):
    roll = await _create_roll(auth_client, "Ordered-Roll")
    roll_id = roll["id"]

    await _create_photo(auth_client, roll_id, frame_number=3)
    await _create_photo(auth_client, roll_id, frame_number=1)
    await _create_photo(auth_client, roll_id, frame_number=2)

    resp = await auth_client.get(f"/api/rolls/{roll_id}/photos")
    assert resp.status_code == 200
    frames = [p["frame_number"] for p in resp.json()["items"]]
    assert frames == [1, 2, 3]


async def test_list_photos_roll_not_found_returns_404(auth_client):
    resp = await auth_client.get("/api/rolls/99999/photos")
    assert resp.status_code == 404


async def test_list_photos_other_users_roll_returns_404(client):
    await client.post("/api/auth/register", json={"username": "pOwner", "email": "po@x.com", "password": "pass1234"})
    rO = await client.post("/api/auth/login", json={"username": "pOwner", "password": "pass1234"})
    headers_owner = {"Authorization": f"Bearer {_token(rO)}"}

    await client.post("/api/auth/register", json={"username": "pThief", "email": "pt@x.com", "password": "pass1234"})
    rT = await client.post("/api/auth/login", json={"username": "pThief", "password": "pass1234"})
    headers_thief = {"Authorization": f"Bearer {_token(rT)}"}

    roll_resp = await client.post("/api/rolls", json={"roll_id": "PrivateRoll"}, headers=headers_owner)
    roll_id = roll_resp.json()["data"]["id"]

    resp = await client.get(f"/api/rolls/{roll_id}/photos", headers=headers_thief)
    assert resp.status_code == 404


async def test_list_photos_requires_authentication(client):
    resp = await client.get("/api/rolls/1/photos")
    assert resp.status_code == 401


# ── POST /api/rolls/{roll_id}/photos ─────────────────────────────────────────

async def test_create_photo_minimal_data_returns_201(auth_client):
    roll = await _create_roll(auth_client, "Photo-Roll")
    resp = await auth_client.post(
        f"/api/rolls/{roll['id']}/photos",
        json={"roll_id": roll["id"], "frame_number": 1},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["frame_number"] == 1
    assert data["roll_id"] == roll["id"]


async def test_create_photo_full_data_returns_201(auth_client):
    roll = await _create_roll(auth_client, "Full-Photo-Roll")
    roll_id = roll["id"]
    payload = {
        "roll_id": roll_id,
        "frame_number": 5,
        "note": "Great shot",
        "rating": 4,
        "tags": ["landscape", "golden-hour"],
        "exif_data": {"shutter": "1/250", "aperture": "f/2.8"},
        "image_url": "https://example.com/img.jpg",
        "thumbnail_url": "https://example.com/thumb.jpg",
    }
    resp = await auth_client.post(f"/api/rolls/{roll_id}/photos", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["note"] == "Great shot"
    assert data["rating"] == 4
    assert data["tags"] == ["landscape", "golden-hour"]
    assert data["exif_data"]["shutter"] == "1/250"


async def test_create_photo_duplicate_frame_number_returns_400(auth_client):
    roll = await _create_roll(auth_client, "Dup-Frame-Roll")
    roll_id = roll["id"]
    await _create_photo(auth_client, roll_id, frame_number=1)

    resp = await auth_client.post(
        f"/api/rolls/{roll_id}/photos",
        json={"roll_id": roll_id, "frame_number": 1},
    )
    assert resp.status_code == 400


async def test_create_photo_same_frame_different_roll_succeeds(auth_client):
    roll_a = await _create_roll(auth_client, "Roll-A-frame")
    roll_b = await _create_roll(auth_client, "Roll-B-frame")

    resp_a = await auth_client.post(
        f"/api/rolls/{roll_a['id']}/photos",
        json={"roll_id": roll_a["id"], "frame_number": 1},
    )
    resp_b = await auth_client.post(
        f"/api/rolls/{roll_b['id']}/photos",
        json={"roll_id": roll_b["id"], "frame_number": 1},
    )
    assert resp_a.status_code == 201
    assert resp_b.status_code == 201


async def test_create_photo_roll_not_found_returns_404(auth_client):
    resp = await auth_client.post(
        "/api/rolls/99999/photos",
        json={"roll_id": 99999, "frame_number": 1},
    )
    assert resp.status_code == 404


async def test_create_photo_other_users_roll_returns_404(client):
    await client.post("/api/auth/register", json={"username": "cpOwner", "email": "cpo@x.com", "password": "pass1234"})
    rO = await client.post("/api/auth/login", json={"username": "cpOwner", "password": "pass1234"})
    headers_owner = {"Authorization": f"Bearer {_token(rO)}"}

    await client.post("/api/auth/register", json={"username": "cpThief", "email": "cpt@x.com", "password": "pass1234"})
    rT = await client.post("/api/auth/login", json={"username": "cpThief", "password": "pass1234"})
    headers_thief = {"Authorization": f"Bearer {_token(rT)}"}

    roll_resp = await client.post("/api/rolls", json={"roll_id": "PvtRoll"}, headers=headers_owner)
    roll_id = roll_resp.json()["data"]["id"]

    resp = await client.post(
        f"/api/rolls/{roll_id}/photos",
        json={"roll_id": roll_id, "frame_number": 1},
        headers=headers_thief,
    )
    assert resp.status_code == 404


async def test_create_photo_frame_number_out_of_range_returns_422(auth_client):
    roll = await _create_roll(auth_client, "Range-Roll")
    roll_id = roll["id"]

    resp = await auth_client.post(
        f"/api/rolls/{roll_id}/photos",
        json={"roll_id": roll_id, "frame_number": 0},
    )
    assert resp.status_code == 422

    resp = await auth_client.post(
        f"/api/rolls/{roll_id}/photos",
        json={"roll_id": roll_id, "frame_number": 73},
    )
    assert resp.status_code == 422


async def test_create_photo_invalid_rating_returns_422(auth_client):
    roll = await _create_roll(auth_client, "Rating-Roll")
    resp = await auth_client.post(
        f"/api/rolls/{roll['id']}/photos",
        json={"roll_id": roll["id"], "frame_number": 1, "rating": 6},
    )
    assert resp.status_code == 422


async def test_create_photo_requires_authentication(client):
    resp = await client.post("/api/rolls/1/photos", json={"roll_id": 1, "frame_number": 1})
    assert resp.status_code == 401


# ── PUT /api/rolls/{roll_id}/photos/{photo_id} ────────────────────────────────

async def test_update_photo_note_succeeds(auth_client):
    roll = await _create_roll(auth_client, "Update-Note-Roll")
    photo = await _create_photo(auth_client, roll["id"], frame_number=1)

    resp = await auth_client.put(
        f"/api/rolls/{roll['id']}/photos/{photo['id']}",
        json={"note": "Updated note"},
    )
    assert resp.status_code == 200
    assert resp.json()["note"] == "Updated note"


async def test_update_photo_rating_succeeds(auth_client):
    roll = await _create_roll(auth_client, "Update-Rating-Roll")
    photo = await _create_photo(auth_client, roll["id"])

    resp = await auth_client.put(
        f"/api/rolls/{roll['id']}/photos/{photo['id']}",
        json={"rating": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["rating"] == 5


async def test_update_photo_tags_succeeds(auth_client):
    roll = await _create_roll(auth_client, "Update-Tags-Roll")
    photo = await _create_photo(auth_client, roll["id"])

    resp = await auth_client.put(
        f"/api/rolls/{roll['id']}/photos/{photo['id']}",
        json={"tags": ["portrait", "film"]},
    )
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["portrait", "film"]


async def test_update_photo_not_found_returns_404(auth_client):
    roll = await _create_roll(auth_client, "NoPhoto-Roll")
    resp = await auth_client.put(
        f"/api/rolls/{roll['id']}/photos/99999",
        json={"note": "ghost"},
    )
    assert resp.status_code == 404


async def test_update_photo_wrong_roll_returns_404(auth_client):
    roll_a = await _create_roll(auth_client, "WR-Roll-A")
    roll_b = await _create_roll(auth_client, "WR-Roll-B")
    photo = await _create_photo(auth_client, roll_a["id"])

    resp = await auth_client.put(
        f"/api/rolls/{roll_b['id']}/photos/{photo['id']}",
        json={"note": "mismatch"},
    )
    assert resp.status_code == 404


async def test_update_photo_other_users_photo_returns_404(client):
    await client.post("/api/auth/register", json={"username": "upOwner", "email": "upo@x.com", "password": "pass1234"})
    rO = await client.post("/api/auth/login", json={"username": "upOwner", "password": "pass1234"})
    headers_owner = {"Authorization": f"Bearer {_token(rO)}"}

    await client.post("/api/auth/register", json={"username": "upThief", "email": "upt@x.com", "password": "pass1234"})
    rT = await client.post("/api/auth/login", json={"username": "upThief", "password": "pass1234"})
    headers_thief = {"Authorization": f"Bearer {_token(rT)}"}

    roll_resp = await client.post("/api/rolls", json={"roll_id": "OwnedRoll"}, headers=headers_owner)
    roll_id = roll_resp.json()["data"]["id"]
    photo_resp = await client.post(
        f"/api/rolls/{roll_id}/photos",
        json={"roll_id": roll_id, "frame_number": 1},
        headers=headers_owner,
    )
    photo_id = photo_resp.json()["id"]

    resp = await client.put(
        f"/api/rolls/{roll_id}/photos/{photo_id}",
        json={"note": "stolen"},
        headers=headers_thief,
    )
    assert resp.status_code == 404


async def test_update_photo_requires_authentication(client):
    resp = await client.put("/api/rolls/1/photos/1", json={"note": "noauth"})
    assert resp.status_code == 401


# ── DELETE /api/rolls/{roll_id}/photos/{photo_id} ─────────────────────────────

async def test_delete_photo_succeeds(auth_client):
    roll = await _create_roll(auth_client, "Del-Photo-Roll")
    photo = await _create_photo(auth_client, roll["id"])

    resp = await auth_client.delete(f"/api/rolls/{roll['id']}/photos/{photo['id']}")
    assert resp.status_code == 200
    assert "message" in resp.json()

    photos_resp = await auth_client.get(f"/api/rolls/{roll['id']}/photos")
    assert photos_resp.json()["total"] == 0


async def test_delete_photo_not_found_returns_404(auth_client):
    roll = await _create_roll(auth_client, "DelNF-Roll")
    resp = await auth_client.delete(f"/api/rolls/{roll['id']}/photos/99999")
    assert resp.status_code == 404


async def test_delete_photo_wrong_roll_returns_404(auth_client):
    roll_a = await _create_roll(auth_client, "DelWR-A")
    roll_b = await _create_roll(auth_client, "DelWR-B")
    photo = await _create_photo(auth_client, roll_a["id"])

    resp = await auth_client.delete(f"/api/rolls/{roll_b['id']}/photos/{photo['id']}")
    assert resp.status_code == 404


async def test_delete_photo_other_users_photo_returns_404(client):
    await client.post("/api/auth/register", json={"username": "dpOwner", "email": "dpo@x.com", "password": "pass1234"})
    rO = await client.post("/api/auth/login", json={"username": "dpOwner", "password": "pass1234"})
    headers_owner = {"Authorization": f"Bearer {_token(rO)}"}

    await client.post("/api/auth/register", json={"username": "dpThief", "email": "dpt@x.com", "password": "pass1234"})
    rT = await client.post("/api/auth/login", json={"username": "dpThief", "password": "pass1234"})
    headers_thief = {"Authorization": f"Bearer {_token(rT)}"}

    roll_resp = await client.post("/api/rolls", json={"roll_id": "MyRoll"}, headers=headers_owner)
    roll_id = roll_resp.json()["data"]["id"]
    photo_resp = await client.post(
        f"/api/rolls/{roll_id}/photos",
        json={"roll_id": roll_id, "frame_number": 1},
        headers=headers_owner,
    )
    photo_id = photo_resp.json()["id"]

    resp = await client.delete(f"/api/rolls/{roll_id}/photos/{photo_id}", headers=headers_thief)
    assert resp.status_code == 404


async def test_delete_photo_requires_authentication(client):
    resp = await client.delete("/api/rolls/1/photos/1")
    assert resp.status_code == 401
