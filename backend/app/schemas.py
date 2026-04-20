from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============= User Schemas =============

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class UserLoginEmail(BaseModel):
    email: str
    password: str


# ============= Token Schemas =============

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: Optional[int] = None
    type: Optional[str] = None


class TokenRefresh(BaseModel):
    refresh_token: str


# ============= Roll Schemas =============

class RollBase(BaseModel):
    roll_id: str = Field(..., min_length=1, max_length=50)
    film_stock: Optional[str] = None
    camera: Optional[str] = None
    iso: Optional[int] = None
    total_frames: int = Field(default=36, ge=1, le=72)
    status: str = Field(default="shooting")  # shooting, finished, developed
    note: Optional[str] = None


class RollCreate(RollBase):
    custom_data: Optional[Dict[str, Any]] = None


class RollUpdate(BaseModel):
    roll_id: Optional[str] = None
    film_stock: Optional[str] = None
    camera: Optional[str] = None
    iso: Optional[int] = None
    total_frames: Optional[int] = Field(default=None, ge=1, le=72)
    status: Optional[str] = None
    date_finished: Optional[datetime] = None
    date_developed: Optional[datetime] = None
    note: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = None


class RollResponse(RollBase):
    id: int
    user_id: int
    date_created: datetime
    date_finished: Optional[datetime] = None
    date_developed: Optional[datetime] = None
    custom_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    photo_count: int = 0

    class Config:
        from_attributes = True


class RollListResponse(BaseModel):
    items: List[RollResponse]
    total: int


# ============= Photo Schemas =============

class PhotoBase(BaseModel):
    frame_number: int = Field(..., ge=1, le=72)
    note: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    tags: Optional[List[str]] = None


class PhotoCreate(PhotoBase):
    roll_id: int
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    exif_data: Optional[Dict[str, Any]] = None


class PhotoUpdate(BaseModel):
    frame_number: Optional[int] = Field(default=None, ge=1, le=72)
    note: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    tags: Optional[List[str]] = None
    exif_data: Optional[Dict[str, Any]] = None


class PhotoResponse(PhotoBase):
    id: int
    user_id: int
    roll_id: int
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    exif_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PhotoListResponse(BaseModel):
    items: List[PhotoResponse]
    total: int


# ============= Sync Schemas =============

class SyncData(BaseModel):
    rolls: List[Dict[str, Any]]
    photos: List[Dict[str, Any]]
    last_sync: Optional[datetime] = None


class SyncResponse(BaseModel):
    success: bool
    message: str
    synced_rolls: int = 0
    synced_photos: int = 0
