from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from app.database import get_db
from app.models import User, Roll, Photo
from app.schemas import SyncData, SyncDataResponse, SyncResultData
from app.auth import get_current_user

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", response_model=SyncDataResponse)
async def sync_data(
    sync_data: SyncData,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量同步数据（从 localStorage 迁移或离线同步）"""
    synced_rolls = 0
    synced_photos = 0
    errors: List[str] = []

    try:
        # 处理胶卷数据
        for roll_dict in sync_data.rolls:
            try:
                roll_id_val = roll_dict.get("rollId") or roll_dict.get("roll_id")
                result = await db.execute(
                    select(Roll).where(
                        and_(Roll.user_id == current_user.id, Roll.roll_id == roll_id_val)
                    )
                )
                existing_roll = result.scalar_one_or_none()

                if existing_roll:
                    existing_roll.film_stock = roll_dict.get("filmStock") or roll_dict.get("film_stock")
                    existing_roll.camera = roll_dict.get("camera")
                    existing_roll.iso = roll_dict.get("iso")
                    existing_roll.total_frames = roll_dict.get("totalFrames") or roll_dict.get("total_frames", 36)
                    existing_roll.status = roll_dict.get("status", "shooting")
                    existing_roll.note = roll_dict.get("note")
                    existing_roll.custom_data = roll_dict.get("customData") or roll_dict.get("custom_data", {})
                else:
                    new_roll = Roll(
                        user_id=current_user.id,
                        roll_id=roll_id_val,
                        film_stock=roll_dict.get("filmStock") or roll_dict.get("film_stock"),
                        camera=roll_dict.get("camera"),
                        iso=roll_dict.get("iso"),
                        total_frames=roll_dict.get("totalFrames") or roll_dict.get("total_frames", 36),
                        status=roll_dict.get("status", "shooting"),
                        note=roll_dict.get("note"),
                        custom_data=roll_dict.get("customData") or roll_dict.get("custom_data", {})
                    )
                    db.add(new_roll)
                    await db.flush()

                synced_rolls += 1
            except Exception as e:
                errors.append(f"Roll sync error: {str(e)}")

        # 处理照片数据
        for photo_dict in sync_data.photos:
            try:
                roll_result = await db.execute(
                    select(Roll).where(
                        and_(
                            Roll.user_id == current_user.id,
                            Roll.roll_id == (photo_dict.get("rollId") or photo_dict.get("roll_id"))
                        )
                    )
                )
                roll = roll_result.scalar_one_or_none()

                if roll:
                    frame_num = photo_dict.get("frameNumber") or photo_dict.get("frame_number")
                    photo_result = await db.execute(
                        select(Photo).where(
                            and_(
                                Photo.user_id == current_user.id,
                                Photo.roll_id == roll.id,
                                Photo.frame_number == frame_num
                            )
                        )
                    )
                    existing_photo = photo_result.scalar_one_or_none()

                    if existing_photo:
                        existing_photo.image_url = photo_dict.get("imageUrl") or photo_dict.get("image_url")
                        existing_photo.thumbnail_url = photo_dict.get("thumbnailUrl") or photo_dict.get("thumbnail_url")
                        existing_photo.note = photo_dict.get("note")
                        existing_photo.rating = photo_dict.get("rating")
                        existing_photo.tags = photo_dict.get("tags", [])
                        existing_photo.exif_data = photo_dict.get("exifData") or photo_dict.get("exif_data", {})
                    else:
                        new_photo = Photo(
                            user_id=current_user.id,
                            roll_id=roll.id,
                            frame_number=frame_num or 1,
                            image_url=photo_dict.get("imageUrl") or photo_dict.get("image_url"),
                            thumbnail_url=photo_dict.get("thumbnailUrl") or photo_dict.get("thumbnail_url"),
                            note=photo_dict.get("note"),
                            rating=photo_dict.get("rating"),
                            tags=photo_dict.get("tags", []),
                            exif_data=photo_dict.get("exifData") or photo_dict.get("exif_data", {})
                        )
                        db.add(new_photo)

                    synced_photos += 1
            except Exception as e:
                errors.append(f"Photo sync error: {str(e)}")

        await db.commit()

        return SyncDataResponse(
            data=SyncResultData(rolls=synced_rolls, photos=synced_photos, errors=errors)
        )

    except Exception as e:
        await db.rollback()
        return SyncDataResponse(
            data=SyncResultData(rolls=synced_rolls, photos=synced_photos, errors=[str(e)])
        )


@router.get("/export")
async def export_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导出用户所有数据（备份用）"""
    roll_result = await db.execute(
        select(Roll).where(Roll.user_id == current_user.id)
    )
    rolls = roll_result.scalars().all()

    photo_result = await db.execute(
        select(Photo).where(Photo.user_id == current_user.id)
    )
    photos = photo_result.scalars().all()

    return {
        "rolls": [
            {
                "id": r.id,
                "roll_id": r.roll_id,
                "film_stock": r.film_stock,
                "camera": r.camera,
                "iso": r.iso,
                "total_frames": r.total_frames,
                "status": r.status,
                "note": r.note,
                "custom_data": r.custom_data,
                "date_created": r.date_created.isoformat() if r.date_created else None,
                "date_finished": r.date_finished.isoformat() if r.date_finished else None,
                "date_developed": r.date_developed.isoformat() if r.date_developed else None,
            }
            for r in rolls
        ],
        "photos": [
            {
                "id": p.id,
                "roll_id": p.roll_id,
                "frame_number": p.frame_number,
                "image_url": p.image_url,
                "thumbnail_url": p.thumbnail_url,
                "note": p.note,
                "rating": p.rating,
                "tags": p.tags,
                "exif_data": p.exif_data,
            }
            for p in photos
        ],
        "export_time": datetime.utcnow().isoformat()
    }
