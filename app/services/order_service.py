from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import Order, OrderItem, OrderSequence, Product, ProductOffer, ProductTranslation
from app.schemas.order import OrderCreateIn, OrderItemOut, OrderOut
from app.services.product_service import pick_translation


async def next_order_number(db: AsyncSession) -> str:
    year = datetime.now(timezone.utc).year
    seq = await db.get(OrderSequence, year)
    if seq is None:
        seq = OrderSequence(year=year, last_number=0)
        db.add(seq)
        await db.flush()
    seq.last_number += 1
    await db.flush()
    prefix = settings.order_number_prefix
    return f"{prefix}-{year}-{seq.last_number:06d}"


def calc_shipping(subtotal: Decimal) -> Decimal:
    if subtotal >= settings.free_shipping_threshold:
        return Decimal("0.00")
    return settings.shipping_flat_rate


def order_to_out(order: Order, items: list[OrderItem]) -> OrderOut:
    return OrderOut(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        payment_method=order.payment_method,
        subtotal=order.subtotal,
        shipping_fee=order.shipping_fee,
        total=order.total,
        items=[
            OrderItemOut(
                product_name=i.product_name,
                offer_label=i.offer_label,
                unit_price=i.unit_price,
                quantity=i.quantity,
                line_total=i.line_total,
            )
            for i in items
        ],
        created_at=order.created_at.isoformat(),
    )


async def create_order(db: AsyncSession, payload: OrderCreateIn) -> OrderOut:
    subtotal = Decimal("0.00")
    line_data: list[dict] = []

    for item in payload.items:
        offer = await db.scalar(
            select(ProductOffer)
            .where(ProductOffer.id == item.offer_id)
            .options(selectinload(ProductOffer.product).selectinload(Product.translations))
        )
        if offer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Offer not found", "code": "OFFER_NOT_FOUND"},
            )
        if offer.stock < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Insufficient stock",
                    "code": "STOCK_INSUFFICIENT",
                    "offer_id": str(offer.id),
                    "available": offer.stock,
                },
            )
        product = offer.product
        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Product not found", "code": "PRODUCT_NOT_FOUND"},
            )
        tr = pick_translation(product.translations, payload.customer.locale)
        name = tr.name if tr else product.slug
        line_total = offer.price * item.quantity
        subtotal += line_total
        line_data.append(
            {
                "offer": offer,
                "product": product,
                "name": name,
                "quantity": item.quantity,
                "line_total": line_total,
            }
        )

    shipping_fee = calc_shipping(subtotal)
    total = subtotal + shipping_fee
    order_number = await next_order_number(db)
    order = Order(
        order_number=order_number,
        status="pending",
        payment_method="cod",
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        total=total,
        customer=payload.customer.model_dump(),
        notes=payload.notes,
    )
    db.add(order)
    await db.flush()
    order_items: list[OrderItem] = []
    for line in line_data:
        offer: ProductOffer = line["offer"]
        offer.stock -= line["quantity"]
        order_items.append(
            OrderItem(
                order_id=order.id,
                product_id=line["product"].id,
                offer_id=offer.id,
                product_name=line["name"],
                offer_label=offer.label,
                unit_price=offer.price,
                quantity=line["quantity"],
                line_total=line["line_total"],
            )
        )
    db.add_all(order_items)
    await db.flush()
    return order_to_out(order, order_items)


async def get_order_by_number(db: AsyncSession, order_number: str) -> OrderOut | None:
    order = await db.scalar(select(Order).where(Order.order_number == order_number))
    if order is None:
        return None
    items = (await db.scalars(select(OrderItem).where(OrderItem.order_id == order.id))).all()
    return order_to_out(order, list(items))


async def delete_order(db: AsyncSession, order_id: UUID) -> None:
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Order not found", "code": "NOT_FOUND"},
        )
    await db.execute(delete(OrderItem).where(OrderItem.order_id == order_id))
    await db.delete(order)
    await db.commit()
