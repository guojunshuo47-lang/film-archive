from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models import User, Roll, Photo
from app.schemas import (
    PhotoCreateFlat, PhotoUpdate, PhotoResponse,
    PhotosDataResponse, PhotoDataResponse
)
from app.auth import get_current_user

router = APIRouter(prefix="/photos", tags=["photos"])


async def _resolve_roll(db: AsyncSession, roll_id_value, user_id: int) -> Roll:
    """Resolve roll by integer DB id or string roll_id field."""
    try:
        rid = int(roll_id_value)
        result = await db.execute(
            select(Roll).where(and_(Roll.id == rid, Roll.user_id == user_id))
        )
    except (ValueError, TypeError):
        result = await db.execute(
            select(Roll).where(and_(Roll.roll_id == str(roll_id_value), Roll.user_id == user_id))
        )
    roll = result.scalar_one_or_none()
    if not roll:
        raise HTTPException(status_code=404, detail="Roll not found")
    return roll


@router.get("", response_model=PhotosDataResponse)
async def list_photos(
    roll_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有照片，可按 roll_id 过滤"""
    query = select(Photo).where(Photo.user_id == current_user.id)

    if roll_id is not None:
        roll = await _resolve_roll(db, roll_id, current_user.id)
        query = query.where(Photo.roll_id == roll.id)

    query = query.order_by(Photo.roll_id, Photo.frame_number)
    result = await db.execute(query)
    photos = result.scalars().all()

    return PhotosDataResponse(data=[PhotoResponse.model_validate(p) for p in photos])


@router.post("", response_model=PhotoDataResponse, status_code=status.HTTP_201_CREATED)
async def create_photo(
    photo_data: PhotoCreateFlat,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建照片（平铺接口）"""
    roll = await _resolve_roll(db, photo_data.roll_id, current_user.id)

    # Auto-assign frame_number if not provided
    frame_number = photo_data.frame_number
    if frame_number is None:
        count_result = await db.execute(
            select(func.count()).where(Photo.roll_id == roll.id)
        )
        frame_number = (count_result.scalar() or 0) + 1

    new_photo = Photo(
        user_id=current_user.id,
        roll_id=roll.id,
        frame_number=frame_number,
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

    return PhotoDataResponse(data=PhotoResponse.model_validate(new_photo))


@router.put("/{photo_id}", response_model=PhotoDataResponse)
async def update_photo(
    photo_id: int,
    photo_data: PhotoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新照片"""
    result = await db.execute(
        select(Photo).where(and_(Photo.id == photo_id, Photo.user_id == current_user.id))
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    update_data = photo_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(photo, field, value)

    await db.flush()
    await db.refresh(photo)

    return PhotoDataResponse(data=PhotoResponse.model_validate(photo))


@router.delete("/{photo_id}")
async def delete_photo(
    photo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除照片"""
    result = await db.execute(
        select(Photo).where(and_(Photo.id == photo_id, Photo.user_id == current_user.id))
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    await db.delete(photo)
    await db.flush()

    return {"success": True}
