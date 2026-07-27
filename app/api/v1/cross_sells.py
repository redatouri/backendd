from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.product import ProductListItemOut
from app.services import product_service

router = APIRouter(prefix="/cross-sells", tags=["cross-sells"])


@router.get("", response_model=list[ProductListItemOut])
async def get_cross_sells(
    product_ids: list[UUID] = Query(default=[]),
    locale: str = Query("fr"),
    limit: int = Query(4, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.get_cross_sells(db, product_ids, locale, limit)
