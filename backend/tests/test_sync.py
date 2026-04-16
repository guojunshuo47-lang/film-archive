"""Tests for sync endpoints (routers/sync.py).

Bug Fix 1 regression tests are marked with comments: the operator precedence
bug caused snake_case keys to never match in WHERE clauses.
"""
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_export(client):
    resp = await client.get("/api/sync/export")
    assert resp.status_code == 200
    return resp.json()


# ── POST /api/sync ────────────────────────────────────────────────────────────

async def test_sync_empty_payload_succeeds(auth_client):
    resp = await auth_client.post("/api/sync", json={"rolls": [], "photos": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["synced_rolls"] == 0
    assert data["synced_photos"] == 0


async def test_sync_creates_new_roll_camelcase_keys(auth_client):
    """Bug Fix 1: camelCase keys (rollId, filmStock) must be matched correctly."""
    payload = {
        "rolls": [{"rollId": "R-camel-1", "filmStock": "Kodak", "iso": 400, "status": "shooting"}],
        "photos": [],
    }
    resp = await auth_client.post("/api/sync", json=payload)
    assert resp.status_code == 200
    assert resp.json()["synced_rolls"] == 1

    export = await _get_export(auth_client)
    roll_ids = [r["roll_id"] for r in export["rolls"]]
    assert "R-camel-1" in roll_ids


async def test_sync_creates_new_roll_snake_case_keys(auth_client):
    """Bug Fix 1 regression: snake_case keys (roll_id, film_stock) must also work."""
    payload = {
        "rolls": [{"roll_id": "R-snake-1", "film_stock": "Fuji", "iso": 200, "status": "finished"}],
        "photos": [],
    }
    resp = await auth_client.post("/api/sync", json=payload)
    assert resp.status_code == 200
    assert resp.json()["synced_rolls"] == 1

    export = await _get_export(auth_client)
    roll_ids = [r["roll_id"] for r in export["rolls"]]
    assert "R-snake-1" in roll_ids


async def test_sync_updates_existing_roll(auth_client):
    """Syncing the same roll_id twice should update, not duplicate."""
    # First sync — create
    await auth_client.post(
        "/api/sync",
        json={"rolls": [{"rollId": "R-update", "filmStock": "Kodak"}], "photos": []},
    )
    # Second sync — update with new film_stock
    resp = await auth_client.post(
        "/api/sync",
        json={"rolls": [{"rollId": "R-update", "filmStock": "Fuji 400H"}], "photos": []},
    )
    assert resp.json()["synced_rolls"] == 1

    export = await _get_export(auth_client)
    rolls = [r for r in export["rolls"] if r["roll_id"] == "R-update"]
    assert len(rolls) == 1
    assert rolls[0]["film_stock"] == "Fuji 400H"


async def test_sync_creates_photo_camelcase_keys(auth_client):
    """Bug Fix 1: camelCase photo keys (rollId, frameNumber) must work."""
    # First create a roll so the photo has a parent
    await auth_client.post(
        "/api/sync",
        json={"rolls": [{"rollId": "R-photo-camel"}], "photos": []},
    )
    payload = {
        "rolls": [],
        "photos": [{"rollId": "R-photo-camel", "frameNumber": 3, "note": "camel photo"}],
    }
    resp = await auth_client.post("/api/sync", json=payload)
    assert resp.status_code == 200
    assert resp.json()["synced_photos"] == 1


async def test_sync_creates_photo_snake_case_keys(auth_client):
    """Bug Fix 1 regression: snake_case photo keys (roll_id, frame_number) must also work."""
    await auth_client.post(
        "/api/sync",
        json={"rolls": [{"roll_id": "R-photo-snake"}], "photos": []},
    )
    payload = {
        "rolls": [],
        "photos": [{"roll_id": "R-photo-snake", "frame_number": 5, "note": "snake photo"}],
    }
    resp = await auth_client.post("/api/sync", json=payload)
    assert resp.status_code == 200
    assert resp.json()["synced_photos"] == 1


async def test_sync_updates_existing_photo(auth_client):
    """Syncing same roll+frame twice should update the photo."""
    # Create roll and photo
    await auth_client.post(
        "/api/sync",
        json={
            "rolls": [{"rollId": "R-photo-update"}],
            "photos": [{"rollId": "R-photo-update", "frameNumber": 1, "note": "original"}],
        },
    )
    # Update the photo
    resp = await auth_client.post(
        "/api/sync",
        json={
            "rolls": [],
            "photos": [{"rollId": "R-photo-update", "frameNumber": 1, "note": "updated"}],
        },
    )
    assert resp.json()["synced_photos"] == 1

    export = await _get_export(auth_client)
    photos = [p for p in export["photos"] if p.get("note") == "updated"]
    assert len(photos) == 1


async def test_sync_photo_for_unknown_roll_is_skipped(auth_client):
    """Photos referencing a non-existent roll_id are silently skipped."""
    payload = {
        "rolls": [],
        "photos": [{"rollId": "NonExistentRoll", "frameNumber": 1}],
    }
    resp = await auth_client.post("/api/sync", json=payload)
    assert resp.status_code == 200
    assert resp.json()["synced_photos"] == 0


async def test_sync_rolls_and_photos_together(auth_client):
    """Rolls and photos can be synced in a single request."""
    payload = {
        "rolls": [{"rollId": "R-together"}],
        "photos": [{"rollId": "R-together", "frameNumber": 7, "rating": 5}],
    }
    resp = await auth_client.post("/api/sync", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["synced_rolls"] == 1
    assert data["synced_photos"] == 1


async def test_sync_mixed_camelcase_and_snake_case(auth_client):
    """Some rolls use camelCase, others use snake_case — all must sync."""
    payload = {
        "rolls": [
            {"rollId": "R-mixed-camel", "filmStock": "Kodak"},
            {"roll_id": "R-mixed-snake", "film_stock": "Fuji"},
        ],
        "photos": [],
    }
    resp = await auth_client.post("/api/sync", json=payload)
    assert resp.status_code == 200
    assert resp.json()["synced_rolls"] == 2

    export = await _get_export(auth_client)
    roll_ids = [r["roll_id"] for r in export["rolls"]]
    assert "R-mixed-camel" in roll_ids
    assert "R-mixed-snake" in roll_ids


async def test_sync_requires_authentication(client):
    resp = await client.post("/api/sync", json={"rolls": [], "photos": []})
    assert resp.status_code == 401


# ── GET /api/sync/export ──────────────────────────────────────────────────────

async def test_export_empty_returns_empty_lists(auth_client):
    export = await _get_export(auth_client)
    assert export["rolls"] == []
    assert export["photos"] == []
    assert "export_time" in export


async def test_export_returns_only_own_data(client):
    """User isolation: export must not include other users' data."""
    await client.post("/api/auth/register", json={"username": "expA", "email": "expA@x.com", "password": "pass1234"})
    rA = await client.post("/api/auth/login", json={"username": "expA", "password": "pass1234"})
    headers_a = {"Authorization": f"Bearer {rA.json()['access_token']}"}

    await client.post("/api/auth/register", json={"username": "expB", "email": "expB@x.com", "password": "pass1234"})
    rB = await client.post("/api/auth/login", json={"username": "expB", "password": "pass1234"})
    headers_b = {"Authorization": f"Bearer {rB.json()['access_token']}"}

    await client.post("/api/sync", json={"rolls": [{"rollId": "A-1"}, {"rollId": "A-2"}], "photos": []}, headers=headers_a)
    await client.post("/api/sync", json={"rolls": [{"rollId": "B-1"}], "photos": []}, headers=headers_b)

    resp_a = await client.get("/api/sync/export", headers=headers_a)
    assert resp_a.status_code == 200
    assert len(resp_a.json()["rolls"]) == 2

    resp_b = await client.get("/api/sync/export", headers=headers_b)
    assert resp_b.status_code == 200
    assert len(resp_b.json()["rolls"]) == 1


async def test_export_roll_fields_present(auth_client):
    await auth_client.post(
        "/api/sync",
        json={"rolls": [{"rollId": "Field-Check", "filmStock": "Kodak", "iso": 400, "status": "shooting"}], "photos": []},
    )
    export = await _get_export(auth_client)
    roll = export["rolls"][0]
    for field in ("id", "roll_id", "film_stock", "camera", "iso", "total_frames", "status", "note", "custom_data"):
        assert field in roll, f"Missing field: {field}"


async def test_export_photo_fields_present(auth_client):
    # Create via rolls API (not sync) to ensure the roll has an integer pk
    roll_resp = await auth_client.post("/api/rolls", json={"roll_id": "Photo-Fields-Roll"})
    roll_id = roll_resp.json()["id"]
    await auth_client.post(
        f"/api/rolls/{roll_id}/photos",
        json={"roll_id": roll_id, "frame_number": 1, "rating": 3, "tags": ["test"]},
    )
    export = await _get_export(auth_client)
    photo = export["photos"][0]
    for field in ("id", "roll_id", "frame_number", "image_url", "thumbnail_url", "note", "rating", "tags", "exif_data"):
        assert field in photo, f"Missing field: {field}"


async def test_export_requires_authentication(client):
    resp = await client.get("/api/sync/export")
    assert resp.status_code == 401
