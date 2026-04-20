from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import uuid


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
    # Accept either username or email
    username: Optional[str] = None
    email: Optional[EmailStr] = None
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


# Supabase-compatible login response: {data: {user, session}}
class SessionData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginData(BaseModel):
    user: UserResponse
    session: SessionData


class LoginResponse(BaseModel):
    data: LoginData


# Supabase-compatible /auth/me response: {data: {user}}
class MeData(BaseModel):
    user: UserResponse


class MeResponse(BaseModel):
    data: MeData


# ============= Roll Schemas =============

class RollBase(BaseModel):
    roll_id: Optional[str] = Field(default=None, max_length=50)
    film_stock: Optional[str] = None
    camera: Optional[str] = None
    iso: Optional[int] = None
    total_frames: int = Field(default=36, ge=1, le=72)
    status: str = Field(default="shooting")
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
    date_created: Optional[datetime] = None
    date_finished: Optional[datetime] = None
    date_developed: Optional[datetime] = None
    custom_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    photo_count: int = 0

    class Config:
        from_attributes = True


# Legacy list response (kept for backward compat with existing tests)
class RollListResponse(BaseModel):
    items: List[RollResponse]
    total: int


# Supabase-compatible: {data: [...]}
class RollsDataResponse(BaseModel):
    data: List[RollResponse]


class RollDataResponse(BaseModel):
    data: RollResponse


# ============= Photo Schemas =============

class PhotoBase(BaseModel):
    frame_number: Optional[int] = Field(default=None, ge=1, le=72)
    note: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    tags: Optional[List[str]] = None


class PhotoCreate(PhotoBase):
    roll_id: Union[int, str]  # DB integer id or user-visible string (e.g. "Roll-001")
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    exif_data: Optional[Dict[str, Any]] = None


# Flat photo creation for /photos endpoint (roll_id is string or int)
class PhotoCreateFlat(BaseModel):
    roll_id: Any  # string roll_id or integer DB id
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    note: Optional[str] = None
    frame_number: Optional[int] = Field(default=None, ge=1, le=72)
    exif_data: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class PhotoUpdate(BaseModel):
    frame_number: Optional[int] = Field(default=None, ge=1, le=72)
    note: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    tags: Optional[List[str]] = None
    exif_data: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None


class PhotoResponse(PhotoBase):
    id: int
    user_id: int
    roll_id: int
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    exif_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PhotoListResponse(BaseModel):
    items: List[PhotoResponse]
    total: int


# Supabase-compatible: {data: [...]}
class PhotosDataResponse(BaseModel):
    data: List[PhotoResponse]


class PhotoDataResponse(BaseModel):
    data: PhotoResponse


# ============= Sync Schemas =============

class SyncData(BaseModel):
    rolls: List[Dict[str, Any]]
    photos: List[Dict[str, Any]]
    last_sync: Optional[datetime] = None


# Legacy response (kept for backward compat with existing tests)
class SyncResponse(BaseModel):
    success: bool
    message: str
    synced_rolls: int = 0
    synced_photos: int = 0


# Supabase-compatible: {data: {rolls, photos, errors}}
class SyncResultData(BaseModel):
    rolls: int
    photos: int
    errors: List[str] = []


class SyncDataResponse(BaseModel):
    data: SyncResultData


# ============= Search & Stats Schemas =============

class SearchResultData(BaseModel):
    rolls: List[RollResponse]
    photos: List[PhotoResponse]


class SearchResponse(BaseModel):
    data: SearchResultData


class StatsData(BaseModel):
    rollCount: int
    photoCount: int
    filmStocks: Dict[str, int]


class StatsResponse(BaseModel):
    data: StatsData
