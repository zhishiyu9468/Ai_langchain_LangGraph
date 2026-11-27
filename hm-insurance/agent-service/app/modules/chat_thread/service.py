import uuid
from uuid import UUID

from langchain_core.messages import HumanMessage, ChatMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from mcp.server.fastmcp.prompts.base import AssistantMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat_thread.exceptions import ChatThreadNotFoundError
from app.modules.chat_thread.models import ChatThread
from app.modules.chat_thread.repository import ChatThreadRepository
from app.modules.chat.schemas import ChatHistoryResponse,ChatMessageResponse

class ChatThreadService:
    def __init__(self, session: AsyncSession,agent:CompiledStateGraph):
        self.session = session
        self.repository = ChatThreadRepository(session)
        self.agent=agent


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
            await self.agent.checkpointer.adelete_thread(str(thread_id))
            await self.session.delete(thread)

    async def get_history(
            self,
            thread_id: UUID,
            user_id: int,
    ) -> ChatHistoryResponse:
        # 1.校验会话归属
        thread = await self.repository.find_owned(thread_id, user_id)
        if thread is None:
            raise ChatThreadNotFoundError

        # 2.读取Agent最新状态
        config = {"configurable": {"thread_id": str(thread_id)}}
        snapshot = await self.agent.aget_state(config)

        # 3.读取additional_info
        additional_infos = snapshot.values.get("additional_info", {})

        # 4.处理消息历史
        messages = []
        for message in snapshot.values.get("messages", []):
            # 4.1.只保留用户消息和AI消息
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                continue

            # 4.2.组装信息
            if message.text:
                messages.append(
                    ChatMessageResponse(
                        role=role,
                        content=message.text,
                        additional_info=additional_infos.get(message.id),
                    )
                )

        # 5.处理interrupt
        interrupts = None
        if hasattr(snapshot, 'interrupts') and snapshot.interrupts:
            interrupts = snapshot.interrupts
        elif hasattr(snapshot, 'tasks') and snapshot.tasks:
            for task in snapshot.tasks:
                if hasattr(task, 'interrupts') and task.interrupts:
                    interrupts = task.interrupts
                    break

        return ChatHistoryResponse(
            thread_id=thread_id,
            messages=messages,
            interrupt=interrupts[0].value if interrupts else None
        )
