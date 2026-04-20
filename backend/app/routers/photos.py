from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.database import get_db
from app.models import User, Roll, Photo
from app.schemas import PhotoCreate, PhotoUpdate, PhotoResponse
from app.auth import get_current_user

router = APIRouter(prefix="/photos", tags=["photos"])


async def _resolve_roll(db: AsyncSession, roll_id, user_id: int) -> Roll:
    """Accept either an integer DB id or a string roll_id like 'Roll-001'."""
    roll_id_str = str(roll_id)
    if roll_id_str.isdigit():
        cond = or_(Roll.id == int(roll_id_str), Roll.roll_id == roll_id_str)
    else:
        cond = Roll.roll_id == roll_id_str
    result = await db.execute(select(Roll).where(and_(cond, Roll.user_id == user_id)))
    return result.scalar_one_or_none()


@router.get("")
async def list_photos(
    roll_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Photo).where(Photo.user_id == current_user.id)
    if roll_id is not None:
        roll = await _resolve_roll(db, roll_id, current_user.id)
        if not roll:
            return {"data": []}
        query = query.where(Photo.roll_id == roll.id)
    query = query.order_by(Photo.roll_id, Photo.frame_number)
    result = await db.execute(query)
    photos = result.scalars().all()
    return {"data": [PhotoResponse.model_validate(p).model_dump(mode="json") for p in photos]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_photo(
    photo_data: PhotoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    roll = await _resolve_roll(db, photo_data.roll_id, current_user.id)
    if not roll:
        raise HTTPException(status_code=404, detail="Roll not found")

    existing = await db.execute(
        select(Photo).where(
            and_(Photo.roll_id == roll.id, Photo.frame_number == photo_data.frame_number)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Frame {photo_data.frame_number} already exists in this roll")

    new_photo = Photo(
        user_id=current_user.id,
        roll_id=roll.id,
        frame_number=photo_data.frame_number,
        image_url=photo_data.image_url,
        thumbnail_url=photo_data.thumbnail_url,
        note=photo_data.note,
        rating=photo_data.rating,
        tags=photo_data.tags or [],
        exif_data=photo_data.exif_data or {}
    )
    db.add(new_photo)
    await db.flush()
    await db.refresh(new_photo)
    return {"data": PhotoResponse.model_validate(new_photo).model_dump(mode="json")}


@router.put("/{photo_id}")
async def update_photo(
    photo_id: int,
    photo_data: PhotoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Photo).where(and_(Photo.id == photo_id, Photo.user_id == current_user.id))
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    for field, value in photo_data.model_dump(exclude_unset=True).items():
        setattr(photo, field, value)
    await db.flush()
    await db.refresh(photo)
    return {"data": PhotoResponse.model_validate(photo).model_dump(mode="json")}


@router.delete("/{photo_id}")
async def delete_photo(
    photo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Photo).where(and_(Photo.id == photo_id, Photo.user_id == current_user.id))
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    await db.delete(photo)
    await db.flush()
    return {"data": {"message": "Photo deleted successfully"}}
