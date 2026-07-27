from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.order import OrderCreateIn, OrderOut
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderCreateIn, db: AsyncSession = Depends(get_db)):
    result = await order_service.create_order(db, payload)
    await db.commit()
    return result


@router.get("/by-number/{order_number}", response_model=OrderOut)
async def get_order_by_number(order_number: str, db: AsyncSession = Depends(get_db)):
    order = await order_service.get_order_by_number(db, order_number)
    if order is None:
        raise HTTPException(status_code=404, detail={"message": "Order not found", "code": "NOT_FOUND"})
    return order
