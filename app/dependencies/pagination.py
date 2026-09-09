from pydantic import BaseModel, Field
from typing import Generic, TypeVar

T = TypeVar('T')

class PaginationParams(BaseModel):
    skip: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(10, ge=1, le=100, description="Number of items to return (max 100)")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int
    pages: int = 0
    
    def __init__(self, items: list[T], total: int, skip: int, limit: int):
        pages = (total + limit - 1) // limit if limit > 0 else 0
        super().__init__(items=items, total=total, skip=skip, limit=limit, pages=pages)

def get_pagination_params(skip: int = 0, limit: int = 10) -> PaginationParams:
    if skip < 0:
        skip = 0
    if limit < 1:
        limit = 10
    if limit > 100:
        limit = 100
    
    return PaginationParams(skip=skip, limit=limit)