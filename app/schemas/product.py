from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class OfferOut(BaseModel):
    id: UUID
    sku: str
    label: str
    price: Decimal
    compare_at_price: Decimal | None = None
    stock: int
    is_default: bool = False
    badge: str | None = None


class CategoryRefOut(BaseModel):
    slug: str
    name: str


class ProductListItemOut(BaseModel):
    id: UUID
    slug: str
    name: str
    headline: str = ""
    subheadline: str = ""
    rating: Decimal
    review_count: int
    primary_image: str | None = None
    default_offer: OfferOut | None = None
    category: CategoryRefOut | None = None


class ProductListOut(BaseModel):
    items: list[ProductListItemOut]
    total: int
    page: int
    limit: int


class ProductImageOut(BaseModel):
    url: str
    alt_text: str = ""
    is_lifestyle: bool = False
    sort_order: int = 0


class ProductSpecOut(BaseModel):
    key: str
    value: str


class ProductDetailOut(BaseModel):
    id: UUID
    slug: str
    name: str
    headline: str = ""
    subheadline: str = ""
    description: str = ""
    short_description: str = ""
    rating: Decimal
    review_count: int
    images: list[ProductImageOut] = []
    offers: list[OfferOut] = []
    specs: list[ProductSpecOut] = []
    cross_sells: list[ProductListItemOut] = []
    category: CategoryRefOut | None = None
