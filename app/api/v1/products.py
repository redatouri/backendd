from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.product import ProductDetailOut, ProductListOut
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListOut)
async def list_products(
    locale: str = Query("fr"),
    category: str | None = None,
    featured: bool | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("popular"),
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    in_stock: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await product_service.list_products(
        db,
        locale,
        category=category,
        featured=featured,
        page=page,
        limit=limit,
        sort=sort,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
    )
    return ProductListOut(items=items, total=total, page=page, limit=limit)


@router.get("/{slug}", response_model=ProductDetailOut)
async def get_product(slug: str, locale: str = Query("fr"), db: AsyncSession = Depends(get_db)):
    item = await product_service.get_product(db, slug, locale)
    if item is None:
        raise HTTPException(status_code=404, detail={"message": "Product not found", "code": "PRODUCT_NOT_FOUND"})
    return item
