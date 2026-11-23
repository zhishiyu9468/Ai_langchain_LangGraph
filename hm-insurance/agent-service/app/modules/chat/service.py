from collections.abc import AsyncIterator

from fastapi.sse import ServerSentEvent
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
    )-> AsyncIterator[ServerSentEvent]:
        thread=await self.repository.find_owned(request.thread_id,user_id)
        if not thread:
            raise ChatThreadNotFoundError
        _input={"messages":[HumanMessage(content=request.message)]}
        config = {"configurable": {"thread_id": str(request.thread_id)}}

        stream = await self.agent.astream_events(
            _input,
            config,
            version="v3",
        )

        # 2.3.只读取消息中的文本增量
        async for message in stream.messages:
            async for text in message.text:
                yield ServerSentEvent(data=text, event="message")
        # 2.4.返回结束标识
        yield ServerSentEvent(data="[DONE]", event="done")
