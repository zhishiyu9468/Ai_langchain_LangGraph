import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat_thread.exceptions import ChatThreadNotFoundError
from app.modules.chat_thread.models import ChatThread
from app.modules.chat_thread.repository import ChatThreadRepository


class ChatThreadService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ChatThreadRepository(session)

    async def add(self, user_id: int, title: str):
        async with self.session.begin():
            chat_thread = ChatThread(user_id=user_id, title=title)
            await self.repository.add(chat_thread)
            return chat_thread

    async def list_by_user(self,user_id:int)->list[ChatThread]:
        return await self.repository.list_by_user(user_id)

    async def rename(self, thread_id: uuid.UUID,user_id:int,title:str )->ChatThread:
        async with self.session.begin():
            thread=await self.repository.find_owned(thread_id,user_id)
            if not thread:
                raise ChatThreadNotFoundError
            thread.title=title
            await self.session.flush()
            await self.session.refresh(thread)
        return thread

    async def delete(self, thread_id: uuid.UUID, user_id:int)->None:
        async with self.session.begin():
            thread = await self.repository.find_owned(thread_id, user_id)
            if thread is None:
                raise ChatThreadNotFoundError
            await self.session.delete(thread)