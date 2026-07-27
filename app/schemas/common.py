from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    message: str
    code: str


class PaginatedMeta(BaseModel):
    total: int
    page: int
    limit: int
