from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models import User, Roll, Photo
from app.schemas import PhotoCreate, PhotoUpdate, PhotoResponse
from app.auth import get_current_user

router = APIRouter(prefix="/photos", tags=["photos"])


@router.get("")
async def list_photos(
    roll_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Photo).where(Photo.user_id == current_user.id)
    if roll_id is not None:
        query = query.where(Photo.roll_id == roll_id)
    query = query.order_by(Photo.roll_id, Photo.frame_number)
    result = await db.execute(query)
    photos = result.scalars().all()
    return {"data": [PhotoResponse.model_validate(p).model_dump() for p in photos]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_photo(
    photo_data: PhotoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Roll).where(and_(Roll.id == photo_data.roll_id, Roll.user_id == current_user.id))
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Roll not found")

    existing = await db.execute(
        select(Photo).where(
            and_(Photo.roll_id == photo_data.roll_id, Photo.frame_number == photo_data.frame_number)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Frame {photo_data.frame_number} already exists in this roll")

    new_photo = Photo(
        user_id=current_user.id,
        roll_id=photo_data.roll_id,
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
    return {"data": PhotoResponse.model_validate(new_photo).model_dump()}


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
    return {"data": PhotoResponse.model_validate(photo).model_dump()}


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
