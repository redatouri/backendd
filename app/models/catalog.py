import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, UUIDTimestampMixin


class Admin(UUIDTimestampMixin, Base):
    __tablename__ = "admins"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Category(UUIDTimestampMixin, Base):
    __tablename__ = "categories"

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    parent: Mapped["Category | None"] = relationship(remote_side="Category.id")
    translations: Mapped[list["CategoryTranslation"]] = relationship(
        cascade="all, delete-orphan"
    )


class CategoryTranslation(UUIDTimestampMixin, Base):
    __tablename__ = "category_translations"
    __table_args__ = (UniqueConstraint("category_id", "locale"),)

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE")
    )
    locale: Mapped[str] = mapped_column(String(5))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    meta_title: Mapped[str] = mapped_column(String(255), default="")
    meta_description: Mapped[str] = mapped_column(Text, default="")


class Product(UUIDTimestampMixin, Base):
    __tablename__ = "products"

    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=Decimal("4.5"))
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    category: Mapped[Category] = relationship()
    translations: Mapped[list["ProductTranslation"]] = relationship(cascade="all, delete-orphan")
    images: Mapped[list["ProductImage"]] = relationship(cascade="all, delete-orphan")
    offers: Mapped[list["ProductOffer"]] = relationship(cascade="all, delete-orphan")
    specs: Mapped[list["ProductSpec"]] = relationship(cascade="all, delete-orphan")


class ProductTranslation(UUIDTimestampMixin, Base):
    __tablename__ = "product_translations"
    __table_args__ = (UniqueConstraint("product_id", "locale"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE")
    )
    locale: Mapped[str] = mapped_column(String(5))
    name: Mapped[str] = mapped_column(String(255))
    headline: Mapped[str] = mapped_column(String(255), default="")
    subheadline: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    short_description: Mapped[str] = mapped_column(String(500), default="")
    meta_title: Mapped[str] = mapped_column(String(255), default="")
    meta_description: Mapped[str] = mapped_column(Text, default="")


class ProductImage(UUIDTimestampMixin, Base):
    __tablename__ = "product_images"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE")
    )
    url: Mapped[str] = mapped_column(String(500))
    alt_text: Mapped[str] = mapped_column(String(255), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_lifestyle: Mapped[bool] = mapped_column(Boolean, default=False)


class ProductOffer(UUIDTimestampMixin, Base):
    __tablename__ = "product_offers"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE")
    )
    sku: Mapped[str] = mapped_column(String(50), unique=True)
    label: Mapped[str] = mapped_column(String(255))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    compare_at_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    badge: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class ProductSpec(UUIDTimestampMixin, Base):
    __tablename__ = "product_specs"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE")
    )
    locale: Mapped[str] = mapped_column(String(5))
    spec_key: Mapped[str] = mapped_column(String(100))
    spec_value: Mapped[str] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ProductCrossSell(UUIDTimestampMixin, Base):
    __tablename__ = "product_cross_sells"
    __table_args__ = (UniqueConstraint("product_id", "cross_sell_product_id"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE")
    )
    cross_sell_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE")
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)
