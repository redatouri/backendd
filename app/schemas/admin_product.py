from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer


class AdminTranslationIn(BaseModel):
    locale: str
    name: str
    headline: str = ""
    subheadline: str = "Équipement professionnel, original et garanti."
    description: str = ""
    short_description: str = ""
    meta_title: str = ""
    meta_description: str = ""


class AdminOfferIn(BaseModel):
    id: UUID | None = None
    sku: str
    label: str = "Neuf"
    price: Decimal = Field(gt=0)
    compare_at_price: Decimal | None = None
    stock: int = Field(default=6, ge=0)
    is_default: bool = True
    badge: str | None = None
    sort_order: int = 0

    @field_serializer("price", "compare_at_price")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        return float(value) if value is not None else None


class AdminImageIn(BaseModel):
    url: str
    alt_text: str = ""
    sort_order: int = 0
    is_lifestyle: bool = False


class AdminSpecIn(BaseModel):
    locale: str = "fr"
    spec_key: str
    spec_value: str
    sort_order: int = 0


class AdminProductCreateIn(BaseModel):
    slug: str
    category_id: UUID
    is_active: bool = True
    is_featured: bool = False
    sort_order: int = 0
    translations: list[AdminTranslationIn]
    offers: list[AdminOfferIn]
    images: list[AdminImageIn] = Field(default_factory=list)
    specs: list[AdminSpecIn] = Field(default_factory=list)
    cross_sell_ids: list[UUID] = Field(default_factory=list)


class AdminProductUpdateIn(BaseModel):
    slug: str | None = None
    category_id: UUID | None = None
    is_active: bool | None = None
    is_featured: bool | None = None
    sort_order: int | None = None
    translations: list[AdminTranslationIn] | None = None
    offers: list[AdminOfferIn] | None = None
    images: list[AdminImageIn] | None = None
    specs: list[AdminSpecIn] | None = None
    cross_sell_ids: list[UUID] | None = None


class AdminProductListItemOut(BaseModel):
    id: UUID
    slug: str
    name: str
    category_id: UUID
    category_slug: str | None = None
    category_name: str | None = None
    price: Decimal | None = None
    stock: int | None = None
    offer_id: UUID | None = None
    is_active: bool
    is_featured: bool
    primary_image: str | None = None

    @field_serializer("price")
    def serialize_price(self, value: Decimal | None) -> float | None:
        return float(value) if value is not None else None


class AdminProductListOut(BaseModel):
    items: list[AdminProductListItemOut]
    total: int
    page: int
    limit: int


class AdminCategoryOptionOut(BaseModel):
    id: UUID
    slug: str
    name: str


class AdminProductDetailOut(BaseModel):
    id: UUID
    slug: str
    category_id: UUID
    category_slug: str | None = None
    is_active: bool
    is_featured: bool
    sort_order: int
    translations: list[AdminTranslationIn]
    offers: list[AdminOfferIn]
    images: list[AdminImageIn]
    specs: list[AdminSpecIn]
    cross_sell_ids: list[UUID] = Field(default_factory=list)
