from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar, List, Any

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: Optional[T] = None


class PageData(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int


class PageResponse(ResponseBase[PageData[T]]):
    pass


class ErrorResponse(BaseModel):
    code: int
    message: str
    data: None = None
