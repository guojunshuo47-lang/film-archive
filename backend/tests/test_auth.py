"""Tests for auth utilities (app/auth.py) and auth endpoints (routers/auth.py)."""
import pytest
from sqlalchemy import select

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models import User


# ── Auth utility unit tests ───────────────────────────────────────────────────

def test_get_password_hash_returns_hash_colon_salt_format():
    hashed = get_password_hash("mypassword")
    parts = hashed.split(":")
    assert len(parts) == 2
    assert all(len(p) > 0 for p in parts)


def test_verify_password_correct_password_returns_true():
    hashed = get_password_hash("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_wrong_password_returns_false():
    hashed = get_password_hash("mypassword")
    assert verify_password("wrongpassword", hashed) is False


def test_verify_password_malformed_hash_returns_false():
    assert verify_password("anypassword", "nocolonseparator") is False


def test_create_access_token_returns_decodable_jwt():
    token = create_access_token(user_id=42)
    payload = decode_token(token)
    assert payload is not None
    assert payload.sub == 42
    assert payload.type == "access"


def test_create_refresh_token_returns_decodable_jwt():
    token = create_refresh_token(user_id=99)
    payload = decode_token(token)
    assert payload is not None
    assert payload.sub == 99
    assert payload.type == "refresh"


def test_decode_token_returns_none_for_invalid_token():
    assert decode_token("not.a.real.token") is None


def test_decode_token_returns_none_for_empty_string():
    assert decode_token("") is None


# ── POST /api/auth/register ───────────────────────────────────────────────────

async def test_register_success_returns_201(client):
    resp = await client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "securepass"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "hashed_password" not in data


async def test_register_duplicate_username_returns_400(client):
    payload = {"username": "bob", "email": "bob@example.com", "password": "pass123"}
    await client.post("/api/auth/register", json=payload)
    resp = await client.post(
        "/api/auth/register",
        json={"username": "bob", "email": "bob2@example.com", "password": "pass123"},
    )
    assert resp.status_code == 400
    assert "Username" in resp.json()["detail"]


async def test_register_duplicate_email_returns_400(client):
    await client.post(
        "/api/auth/register",
        json={"username": "carol", "email": "carol@example.com", "password": "pass123"},
    )
    resp = await client.post(
        "/api/auth/register",
        json={"username": "carol2", "email": "carol@example.com", "password": "pass123"},
    )
    assert resp.status_code == 400
    assert "Email" in resp.json()["detail"]


async def test_register_short_password_returns_422(client):
    resp = await client.post(
        "/api/auth/register",
        json={"username": "dave", "email": "dave@example.com", "password": "abc"},
    )
    assert resp.status_code == 422


async def test_register_invalid_email_returns_422(client):
    resp = await client.post(
        "/api/auth/register",
        json={"username": "eve", "email": "not-an-email", "password": "pass123"},
    )
    assert resp.status_code == 422


async def test_register_short_username_returns_422(client):
    resp = await client.post(
        "/api/auth/register",
        json={"username": "ab", "email": "ab@example.com", "password": "pass123"},
    )
    assert resp.status_code == 422


# ── POST /api/auth/login ──────────────────────────────────────────────────────

async def test_login_success_returns_token_bundle(client):
    await client.post(
        "/api/auth/register",
        json={"username": "frank", "email": "frank@example.com", "password": "pass123"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "frank", "password": "pass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["expires_in"], int)


async def test_login_wrong_password_returns_401(client):
    await client.post(
        "/api/auth/register",
        json={"username": "grace", "email": "grace@example.com", "password": "pass123"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "grace", "password": "wrongpass"},
    )
    assert resp.status_code == 401


async def test_login_nonexistent_user_returns_401(client):
    resp = await client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "pass123"},
    )
    assert resp.status_code == 401


# ── POST /api/auth/refresh ────────────────────────────────────────────────────

async def test_refresh_with_valid_refresh_token_returns_new_tokens(client):
    await client.post(
        "/api/auth/register",
        json={"username": "hank", "email": "hank@example.com", "password": "pass123"},
    )
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "hank", "password": "pass123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_refresh_with_access_token_returns_401(client):
    await client.post(
        "/api/auth/register",
        json={"username": "ivy", "email": "ivy@example.com", "password": "pass123"},
    )
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "ivy", "password": "pass123"},
    )
    # Use access token where refresh token is expected
    access_token = login_resp.json()["access_token"]
    resp = await client.post("/api/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


async def test_refresh_with_invalid_token_returns_401(client):
    resp = await client.post("/api/auth/refresh", json={"refresh_token": "garbage.token.value"})
    assert resp.status_code == 401


async def test_refresh_for_deleted_user_returns_401(client, db_session):
    """Bug Fix 2 regression: token refresh must fail for deleted users."""
    await client.post(
        "/api/auth/register",
        json={"username": "jack", "email": "jack@example.com", "password": "pass123"},
    )
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "jack", "password": "pass123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Delete the user from the database
    result = await db_session.execute(select(User).where(User.username == "jack"))
    user = result.scalar_one()
    await db_session.delete(user)
    await db_session.commit()

    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


async def test_refresh_for_inactive_user_returns_401(client, db_session):
    """Bug Fix 2 regression: token refresh must fail for deactivated users."""
    await client.post(
        "/api/auth/register",
        json={"username": "kate", "email": "kate@example.com", "password": "pass123"},
    )
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "kate", "password": "pass123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Deactivate the user
    result = await db_session.execute(select(User).where(User.username == "kate"))
    user = result.scalar_one()
    user.is_active = False
    await db_session.commit()

    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


# ── GET /api/auth/me ──────────────────────────────────────────────────────────

async def test_get_me_returns_current_user(auth_client):
    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data


async def test_get_me_without_token_returns_401(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_get_me_with_invalid_token_returns_401(client):
    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer badtoken"})
    assert resp.status_code == 401


# ── POST /api/auth/logout ─────────────────────────────────────────────────────

async def test_logout_returns_success_message(client):
    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert "message" in resp.json()
