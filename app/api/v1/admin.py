from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models import Order, OrderItem, Product, ProductOffer
from app.schemas.admin_product import (
    AdminCategoryOptionOut,
    AdminProductCreateIn,
    AdminProductDetailOut,
    AdminProductListOut,
    AdminProductUpdateIn,
)
from app.schemas.order import OrderStatusPatchIn
from app.services import admin_product_service
from app.services.order_service import order_to_out

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


@router.get("/stats")
async def admin_stats(db: AsyncSession = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    orders_today = await db.scalar(
        select(func.count()).select_from(Order).where(func.date(Order.created_at) == today)
    )
    orders_pending = await db.scalar(
        select(func.count()).select_from(Order).where(Order.status == "pending")
    )
    week_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    revenue_week = await db.scalar(
        select(func.coalesce(func.sum(Order.total), 0)).where(Order.created_at >= week_start)
    )
    low_stock = (
        await db.scalars(
            select(ProductOffer)
            .where(ProductOffer.stock < 5)
            .options(selectinload(ProductOffer.product).selectinload(Product.translations))
            .limit(10)
        )
    ).all()
    return {
        "orders_today": int(orders_today or 0),
        "orders_pending": int(orders_pending or 0),
        "revenue_week": float(revenue_week or 0),
        "low_stock_products": [
            {
                "id": str(o.product_id),
                "name": o.product.translations[0].name if o.product.translations else o.sku,
                "stock": o.stock,
            }
            for o in low_stock
        ],
    }


@router.get("/categories", response_model=list[AdminCategoryOptionOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await admin_product_service.list_admin_categories(db)


@router.get("/products", response_model=AdminProductListOut)
async def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await admin_product_service.list_admin_products(
        db, page=page, limit=limit, search=search
    )
    return AdminProductListOut(items=items, total=total, page=page, limit=limit)


@router.post("/products", response_model=AdminProductDetailOut, status_code=201)
async def create_product(payload: AdminProductCreateIn, db: AsyncSession = Depends(get_db)):
    return await admin_product_service.create_admin_product(db, payload)


@router.get("/products/{product_id}", response_model=AdminProductDetailOut)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    product = await admin_product_service.load_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail={"message": "Product not found", "code": "NOT_FOUND"})
    return admin_product_service.product_to_admin_detail(product)


@router.put("/products/{product_id}", response_model=AdminProductDetailOut)
async def update_product(
    product_id: UUID,
    payload: AdminProductUpdateIn,
    db: AsyncSession = Depends(get_db),
):
    return await admin_product_service.update_admin_product(db, product_id, payload)


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    await admin_product_service.delete_admin_product(db, product_id)


@router.get("/orders")
async def list_orders(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Order).order_by(Order.created_at.desc())
    if status_filter:
        query = query.where(Order.status == status_filter)
    orders = (await db.scalars(query)).all()
    total = len(orders)
    start = (page - 1) * limit
    page_orders = orders[start : start + limit]
    results = []
    for order in page_orders:
        items = (await db.scalars(select(OrderItem).where(OrderItem.order_id == order.id))).all()
        out = order_to_out(order, list(items))
        results.append({**out.model_dump(), "customer": order.customer})
    return {"items": results, "total": total, "page": page, "limit": limit}


@router.get("/orders/{order_id}")
async def get_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail={"message": "Order not found", "code": "NOT_FOUND"})
    items = (await db.scalars(select(OrderItem).where(OrderItem.order_id == order.id))).all()
    out = order_to_out(order, list(items))
    return {**out.model_dump(), "customer": order.customer, "admin_notes": order.admin_notes}


@router.patch("/orders/{order_id}")
async def patch_order(order_id: UUID, payload: OrderStatusPatchIn, db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail={"message": "Order not found", "code": "NOT_FOUND"})
    if payload.status:
        order.status = payload.status
    if payload.admin_notes is not None:
        order.admin_notes = payload.admin_notes
    await db.commit()
    items = (await db.scalars(select(OrderItem).where(OrderItem.order_id == order.id))).all()
    out = order_to_out(order, list(items))
    return {**out.model_dump(), "customer": order.customer, "admin_notes": order.admin_notes}
