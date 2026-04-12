from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, Roll, Photo
from app.schemas import (
    RollCreate, RollUpdate, RollResponse, RollListResponse,
    PhotoCreate, PhotoUpdate, PhotoResponse, PhotoListResponse,
    SyncData, SyncResponse
)
from app.auth import get_current_user

router = APIRouter(prefix="/rolls", tags=["rolls"])


@router.get("", response_model=RollListResponse)
async def list_rolls(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的所有胶卷"""
    query = select(Roll).where(Roll.user_id == current_user.id)

    if status:
        query = query.where(Roll.status == status)

    query = query.order_by(Roll.created_at.desc())

    result = await db.execute(query)
    rolls = result.scalars().all()

    # 计算每个胶卷的照片数量
    roll_responses = []
    for roll in rolls:
        photo_count_result = await db.execute(
            select(func.count()).where(Photo.roll_id == roll.id)
        )
        photo_count = photo_count_result.scalar()

        roll_dict = {
            "id": roll.id,
            "user_id": roll.user_id,
            "roll_id": roll.roll_id,
            "film_stock": roll.film_stock,
            "camera": roll.camera,
            "iso": roll.iso,
            "total_frames": roll.total_frames,
            "status": roll.status,
            "date_created": roll.date_created,
            "date_finished": roll.date_finished,
            "date_developed": roll.date_developed,
            "note": roll.note,
            "custom_data": roll.custom_data or {},
            "created_at": roll.created_at,
            "updated_at": roll.updated_at,
            "photo_count": photo_count
        }
        roll_responses.append(RollResponse(**roll_dict))

    return RollListResponse(items=roll_responses, total=len(roll_responses))


@router.post("", response_model=RollResponse, status_code=status.HTTP_201_CREATED)
async def create_roll(
    roll_data: RollCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新胶卷"""
    # 检查 roll_id 是否已存在
    result = await db.execute(
        select(Roll).where(
            and_(Roll.user_id == current_user.id, Roll.roll_id == roll_data.roll_id)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Roll with ID '{roll_data.roll_id}' already exists"
        )

    new_roll = Roll(
        user_id=current_user.id,
        roll_id=roll_data.roll_id,
        film_stock=roll_data.film_stock,
        camera=roll_data.camera,
        iso=roll_data.iso,
        total_frames=roll_data.total_frames,
        status=roll_data.status,
        note=roll_data.note,
        custom_data=roll_data.custom_data or {}
    )
    db.add(new_roll)
    await db.flush()
    await db.refresh(new_roll)

    return RollResponse(
        id=new_roll.id,
        user_id=new_roll.user_id,
        roll_id=new_roll.roll_id,
        film_stock=new_roll.film_stock,
        camera=new_roll.camera,
        iso=new_roll.iso,
        total_frames=new_roll.total_frames,
        status=new_roll.status,
        date_created=new_roll.date_created,
        date_finished=new_roll.date_finished,
        date_developed=new_roll.date_developed,
        note=new_roll.note,
        custom_data=new_roll.custom_data or {},
        created_at=new_roll.created_at,
        updated_at=new_roll.updated_at,
        photo_count=0
    )


@router.get("/{roll_id}", response_model=RollResponse)
async def get_roll(
    roll_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个胶卷详情"""
    result = await db.execute(
        select(Roll).where(and_(Roll.id == roll_id, Roll.user_id == current_user.id))
    )
    roll = result.scalar_one_or_none()

    if not roll:
        raise HTTPException(status_code=404, detail="Roll not found")

    # 获取照片数量
    photo_count_result = await db.execute(
        select(func.count()).where(Photo.roll_id == roll.id)
    )
    photo_count = photo_count_result.scalar()

    return RollResponse(
        id=roll.id,
        user_id=roll.user_id,
        roll_id=roll.roll_id,
        film_stock=roll.film_stock,
        camera=roll.camera,
        iso=roll.iso,
        total_frames=roll.total_frames,
        status=roll.status,
        date_created=roll.date_created,
        date_finished=roll.date_finished,
        date_developed=roll.date_developed,
        note=roll.note,
        custom_data=roll.custom_data or {},
        created_at=roll.created_at,
        updated_at=roll.updated_at,
        photo_count=photo_count
    )


@router.put("/{roll_id}", response_model=RollResponse)
async def update_roll(
    roll_id: int,
    roll_data: RollUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新胶卷信息"""
    result = await db.execute(
        select(Roll).where(and_(Roll.id == roll_id, Roll.user_id == current_user.id))
    )
    roll = result.scalar_one_or_none()

    if not roll:
        raise HTTPException(status_code=404, detail="Roll not found")

    # 更新字段
    update_data = roll_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(roll, field, value)

    await db.flush()
    await db.refresh(roll)

    # 获取照片数量
    photo_count_result = await db.execute(
        select(func.count()).where(Photo.roll_id == roll.id)
    )
    photo_count = photo_count_result.scalar()

    return RollResponse(
        id=roll.id,
        user_id=roll.user_id,
        roll_id=roll.roll_id,
        film_stock=roll.film_stock,
        camera=roll.camera,
        iso=roll.iso,
        total_frames=roll.total_frames,
        status=roll.status,
        date_created=roll.date_created,
        date_finished=roll.date_finished,
        date_developed=roll.date_developed,
        note=roll.note,
        custom_data=roll.custom_data or {},
        created_at=roll.created_at,
        updated_at=roll.updated_at,
        photo_count=photo_count
    )


@router.delete("/{roll_id}")
async def delete_roll(
    roll_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除胶卷及其所有照片"""
    result = await db.execute(
        select(Roll).where(and_(Roll.id == roll_id, Roll.user_id == current_user.id))
    )
    roll = result.scalar_one_or_none()

    if not roll:
        raise HTTPException(status_code=404, detail="Roll not found")

    await db.delete(roll)
    await db.flush()

    return {"message": "Roll deleted successfully"}


# ============= Photo Endpoints =============

@router.get("/{roll_id}/photos", response_model=PhotoListResponse)
async def list_photos(
    roll_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取胶卷中的所有照片"""
    # 验证胶卷归属
    result = await db.execute(
        select(Roll).where(and_(Roll.id == roll_id, Roll.user_id == current_user.id))
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Roll not found")

    result = await db.execute(
        select(Photo)
        .where(and_(Photo.roll_id == roll_id, Photo.user_id == current_user.id))
        .order_by(Photo.frame_number)
    )
    photos = result.scalars().all()

    return PhotoListResponse(
        items=[PhotoResponse.model_validate(p) for p in photos],
        total=len(photos)
    )


@router.post("/{roll_id}/photos", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def create_photo(
    roll_id: int,
    photo_data: PhotoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """添加照片到胶卷"""
    # 验证胶卷归属
    result = await db.execute(
        select(Roll).where(and_(Roll.id == roll_id, Roll.user_id == current_user.id))
    )
    roll = result.scalar_one_or_none()
    if not roll:
        raise HTTPException(status_code=404, detail="Roll not found")

    # 检查帧号是否已存在
    result = await db.execute(
        select(Photo).where(
            and_(
                Photo.roll_id == roll_id,
                Photo.frame_number == photo_data.frame_number
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Frame {photo_data.frame_number} already exists in this roll"
        )

    new_photo = Photo(
        user_id=current_user.id,
        roll_id=roll_id,
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

    return PhotoResponse.model_validate(new_photo)


@router.put("/{roll_id}/photos/{photo_id}", response_model=PhotoResponse)
async def update_photo(
    roll_id: int,
    photo_id: int,
    photo_data: PhotoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新照片信息"""
    result = await db.execute(
        select(Photo).where(
            and_(
                Photo.id == photo_id,
                Photo.roll_id == roll_id,
                Photo.user_id == current_user.id
            )
        )
    )
    photo = result.scalar_one_or_none()

    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # 更新字段
    update_data = photo_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(photo, field, value)

    await db.flush()
    await db.refresh(photo)

    return PhotoResponse.model_validate(photo)


@router.delete("/{roll_id}/photos/{photo_id}")
async def delete_photo(
    roll_id: int,
    photo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除照片"""
    result = await db.execute(
        select(Photo).where(
            and_(
                Photo.id == photo_id,
                Photo.roll_id == roll_id,
                Photo.user_id == current_user.id
            )
        )
    )
    photo = result.scalar_one_or_none()

    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    await db.delete(photo)
    await db.flush()

    return {"message": "Photo deleted successfully"}
