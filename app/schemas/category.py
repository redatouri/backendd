from uuid import UUID

from pydantic import BaseModel


class CategoryChildOut(BaseModel):
    slug: str
    name: str
    product_count: int = 0


class CategoryOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str = ""
    image_url: str | None = None
    product_count: int = 0
    children: list[CategoryChildOut] = []


class CategoryListOut(BaseModel):
    items: list[CategoryOut]
