from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.database import get_db
from app.models import User, Roll, Photo
from app.schemas import RollResponse, PhotoResponse
from app.auth import get_current_user

router = APIRouter(tags=["search"])


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    roll_result = await db.execute(
        select(Roll).where(
            Roll.user_id == current_user.id,
            or_(
                Roll.roll_id.ilike(f"%{q}%"),
                Roll.film_stock.ilike(f"%{q}%"),
                Roll.camera.ilike(f"%{q}%"),
                Roll.note.ilike(f"%{q}%"),
            )
        )
    )
    rolls = roll_result.scalars().all()

    photo_result = await db.execute(
        select(Photo).where(
            Photo.user_id == current_user.id,
            Photo.note.ilike(f"%{q}%")
        )
    )
    photos = photo_result.scalars().all()

    return {
        "data": {
            "rolls": [
                RollResponse(
                    id=r.id, user_id=r.user_id, roll_id=r.roll_id,
                    film_stock=r.film_stock, camera=r.camera, iso=r.iso,
                    total_frames=r.total_frames, status=r.status, note=r.note,
                    date_created=r.date_created, date_finished=r.date_finished,
                    date_developed=r.date_developed, custom_data=r.custom_data or {},
                    created_at=r.created_at, updated_at=r.updated_at, photo_count=0
                ).model_dump(mode="json")
                for r in rolls
            ],
            "photos": [PhotoResponse.model_validate(p).model_dump(mode="json") for p in photos]
        }
    }


@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_rolls = (await db.execute(
        select(func.count()).where(Roll.user_id == current_user.id)
    )).scalar()

    total_photos = (await db.execute(
        select(func.count()).where(Photo.user_id == current_user.id)
    )).scalar()

    status_rows = (await db.execute(
        select(Roll.status, func.count()).where(Roll.user_id == current_user.id).group_by(Roll.status)
    )).all()
    rolls_by_status = {row[0]: row[1] for row in status_rows}

    return {
        "data": {
            "rolls": total_rolls,
            "photos": total_photos,
            "rolls_by_status": rolls_by_status
        }
    }
