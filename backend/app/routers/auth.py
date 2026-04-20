from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse, UserLoginEmail
from app.auth import (
    authenticate_user_by_email,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    get_current_user
)
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")

    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password)
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    return {"data": {"user": UserResponse.model_validate(new_user).model_dump()}}


@router.post("/login")
async def login(credentials: UserLoginEmail, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user_by_email(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return {
        "data": {
            "session": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            },
            "user": UserResponse.model_validate(user).model_dump()
        }
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"data": {"user": UserResponse.model_validate(current_user).model_dump()}}


@router.post("/logout")
async def logout():
    return {"data": {"message": "Successfully logged out"}}
