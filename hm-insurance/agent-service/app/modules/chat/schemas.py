from typing import Literal, Any
from uuid import UUID

from pydantic import Field, BaseModel

from app.common.schemas import BaseSchema


class ChatRequest(BaseModel):
    """基础对话请求"""

    thread_id: UUID
    message: str | None = Field(default=None, min_length=1)
    decision: dict[str, Any] | None = None

class ChatMessageResponse(BaseSchema):
    role:Literal["user","assistant"]
    content:str

class ChatHistoryResponse(BaseSchema):
    thread_id:UUID
    messages:list[ChatMessageResponse]