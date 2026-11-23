from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Header
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response
from starlette.status import HTTP_204_NO_CONTENT

from app.infra.database import get_session
from app.modules.chat_thread.schemas import ChatThreadResponse, ChatThreadCreate
from app.modules.chat.schemas import ChatHistoryResponse,ChatMessageResponse
from app.modules.chat_thread.service import ChatThreadService

router = APIRouter(prefix="/api/v1/chat-threads",tags=["chat-threads"])

def get_service(
        request:Request,
        session:AsyncSession=Depends(get_session)

):
    return ChatThreadService(session,request.app.state.agent)

@router.post("",response_model=ChatThreadResponse)
async def create_chat_thread(
        request:ChatThreadCreate,
        user_id: Annotated[int, Header(alias="x-user-id")],
        service:ChatThreadService=Depends(get_service),
)->ChatThreadResponse:
    response= await service.add(user_id,request.title)
    ChatThreadResponse.model_validate(response)
    return response

@router.get("",response_model=list[ChatThreadResponse])
async def list_chat_threads(
        user_id: Annotated[int, Header(alias="x-user-id")],
        service:ChatThreadService=Depends(get_service)
)->list[ChatThreadResponse]:
    threads=await service.list_by_user(user_id)
    return [
        ChatThreadResponse.model_validate(thread)
        for thread in threads
    ]

@router.patch("/{thread_id}",response_model=ChatThreadResponse)
async def rename(
        request: ChatThreadCreate,
        thread_id:UUID,
        user_id: Annotated[int, Header(alias="x-user-id")],
        service:ChatThreadService=Depends(get_service),
)->ChatThreadResponse:
    result= await service.rename(thread_id,user_id,request.title)
    return ChatThreadResponse.model_validate(result)

@router.delete("/{thread_id}",status_code=HTTP_204_NO_CONTENT)
async def delete_chat_thread(
        thread_id:UUID,
        user_id: Annotated[int, Header(alias="x-user-id")],
        service:ChatThreadService=Depends(get_service)
)->Response:
    await service.delete(thread_id,user_id)
    return Response(status_code=HTTP_204_NO_CONTENT)

@router.get("/{thread_id}/messages",response_model=ChatHistoryResponse)
async def get_chat_history(
        thread_id:UUID,
        user_id:Annotated[int,Header(alias="x-user-id")],
        service=Depends(get_service)
):
    return await service.get_history(thread_id,user_id)
