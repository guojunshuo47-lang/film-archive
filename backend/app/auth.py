from datetime import datetime, timedelta
from typing import Optional, Union
import hashlib
import secrets
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import TokenPayload

settings = get_settings()
security = HTTPBearer(auto_error=False)


def _hash_with_salt(password: str, salt: str) -> str:
    """使用 SHA256 + Salt 哈希密码"""
    return hashlib.sha256((password + salt).encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # 格式: hash:salt
    if ":" not in hashed_password:
        return False
    stored_hash, salt = hashed_password.rsplit(":", 1)
    computed_hash = _hash_with_salt(plain_password, salt)
    return secrets.compare_digest(stored_hash, computed_hash)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    # 生成随机 salt
    salt = secrets.token_hex(16)
    hash_value = _hash_with_salt(password, salt)
    return f"{hash_value}:{salt}"


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenPayload]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None:
            return None
        return TokenPayload(sub=int(user_id), type=token_type)
    except JWTError:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None or payload.sub is None or payload.type != "access":
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def authenticate_user_by_email(db: AsyncSession, email: str, password: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
