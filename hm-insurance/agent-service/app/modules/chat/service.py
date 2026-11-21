from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.schemas import ChatRequest
from app.modules.chat_thread.exceptions import ChatThreadNotFoundError
from app.modules.chat_thread.repository import ChatThreadRepository


class ChatService:
    def __init__(self,session:AsyncSession,agent:CompiledStateGraph):
        self.repository=ChatThreadRepository(session)
        self.agent=agent

    async def chat_stream(
            self,
            user_id:int,
            request:ChatRequest
    )->str:
        thread=await self.repository.find_owned(request.thread_id,user_id)
        if not thread:
            raise ChatThreadNotFoundError
        _input={"messages":[HumanMessage(content=request.message)]}
        config = {"configurable": {"thread_id": str(request.thread_id)}}
        result = await self.agent.ainvoke(_input, config)
        ai_message = result["messages"][-1]
        return ai_message.content
