from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.category import CategoryListOut, CategoryOut
from app.services import product_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=CategoryListOut)
async def list_categories(
    locale: str = Query("fr"),
    top: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    items = await product_service.list_categories(db, locale, top=top)
    return CategoryListOut(items=items)


@router.get("/{slug}", response_model=CategoryOut)
async def get_category(slug: str, locale: str = Query("fr"), db: AsyncSession = Depends(get_db)):
    item = await product_service.get_category(db, slug, locale)
    if item is None:
        raise HTTPException(status_code=404, detail={"message": "Category not found", "code": "NOT_FOUND"})
    return item
