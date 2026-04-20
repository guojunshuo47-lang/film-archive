from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import User, Roll, Photo
from app.schemas import (
    RollResponse, PhotoResponse,
    SearchResponse, SearchResultData,
    StatsResponse, StatsData
)
from app.auth import get_current_user

router = APIRouter(tags=["data"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """搜索胶卷和照片"""
    term = f"%{q}%"

    roll_result = await db.execute(
        select(Roll).where(
            Roll.user_id == current_user.id,
            (Roll.film_stock.ilike(term) | Roll.camera.ilike(term) | Roll.note.ilike(term))
        )
    )
    rolls = roll_result.scalars().all()

    photo_result = await db.execute(
        select(Photo).where(
            Photo.user_id == current_user.id,
            Photo.note.ilike(term)
        )
    )
    photos = photo_result.scalars().all()

    return SearchResponse(
        data=SearchResultData(
            rolls=[RollResponse.model_validate({**r.__dict__, "photo_count": 0}) for r in rolls],
            photos=[PhotoResponse.model_validate(p) for p in photos]
        )
    )


@router.get("/stats", response_model=StatsResponse)
async def stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取统计数据"""
    roll_count_result = await db.execute(
        select(func.count()).where(Roll.user_id == current_user.id)
    )
    roll_count = roll_count_result.scalar() or 0

    photo_count_result = await db.execute(
        select(func.count()).where(Photo.user_id == current_user.id)
    )
    photo_count = photo_count_result.scalar() or 0

    # Film stock breakdown
    stocks_result = await db.execute(
        select(Roll.film_stock, func.count(Roll.id))
        .where(Roll.user_id == current_user.id, Roll.film_stock.isnot(None))
        .group_by(Roll.film_stock)
    )
    film_stocks = {stock: count for stock, count in stocks_result.all()}

    return StatsResponse(
        data=StatsData(
            rollCount=roll_count,
            photoCount=photo_count,
            filmStocks=film_stocks
        )
    )
