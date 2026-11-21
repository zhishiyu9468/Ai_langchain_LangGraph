from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat_thread.models import ChatThread


class ChatThreadRepository:
    def __init__(self,session:AsyncSession):
        self.session=session

    async def add(self,chat_thread:ChatThread):
        self.session.add(chat_thread)

    async def list_by_user(self,user_id:int)->list[ChatThread]:
        results=await self.session.scalars(
            select(ChatThread)
            .where(ChatThread.user_id==user_id)
            .order_by(
                ChatThread.updated_at.desc(),
                ChatThread.created_at.desc()
            )
        )
        return list(results.all())

    async def find_owned(self,thread_id:UUID,user_id:int)->ChatThread|None:
        return await self.session.scalar(
            select(ChatThread)
            .where(ChatThread.id==thread_id,
                   ChatThread.user_id==user_id
                   )
        )

    async def delete(self,thread:ChatThread)->None:
        await self.session.delete(thread)


