from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.schemas import (
    UserCreate, UserResponse, UserLogin, Token, TokenRefresh, TokenPayload,
    LoginResponse, LoginData, SessionData, MeResponse, MeData
)
from app.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    get_current_user
)
from app.config import get_settings


router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    return new_user


@router.post("/login", response_model=LoginResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录 — 支持 email 或 username"""
    identifier = credentials.email or credentials.username
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username is required"
        )

    user = await authenticate_user(db, identifier, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return LoginResponse(
        data=LoginData(
            user=UserResponse.model_validate(user),
            session=SessionData(
                access_token=access_token,
                refresh_token=refresh_token,
            )
        )
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """刷新访问令牌"""
    payload = decode_token(refresh_data.refresh_token)

    if payload is None or payload.sub is None or payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(payload.sub)
    new_refresh_token = create_refresh_token(payload.sub)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=MeResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return MeResponse(
        data=MeData(user=UserResponse.model_validate(current_user))
    )


@router.post("/logout")
async def logout():
    """登出"""
    return {"success": True}
