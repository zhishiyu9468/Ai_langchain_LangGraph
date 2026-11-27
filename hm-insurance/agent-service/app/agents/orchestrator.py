from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.types import Command

from app.agents.insurance_advisor import init_insurance_advisor
from app.agents.chitchat import init_chitchat_agent
from app.agents.intent_router import intent_router
from app.agents.schemas import InsuranceAgentState, Intent


# 一、定义节点

# 1.路由节点
async def route_node(
        state: InsuranceAgentState,
) -> Command[Intent]:
    """意图识别节点，后续再完善"""

    # 1.获取active_workflow，也就是上一轮会话的工作流
    previous_workflow = state.get("active_workflow", "")
    previous_ai_message=find_previous_ai_message(state['messages'])
    context=f"上一轮对话工作流:{previous_workflow}\n上一轮对话AI回复:{previous_ai_message}"
    result = await intent_router.route(state['messages'][-1].content, context)
    if isinstance(result,str):
        return Command(
            update={
                "messages":[AIMessage(content=result)],
                "previous_workflow":previous_workflow,
                "active_flow":"chitchat",

            },
            goto=END
        )
    return Command(
        update={
            "previous_workflow": previous_workflow,
            "active_flow": result.intent,
        },
        goto=result.intent
    )


def find_previous_ai_message(messages:list[BaseMessage])->str:
    """查找本轮用户消息之前最近一条可展示的AI回复"""
    for message in reversed(messages[:-1]):
        if not isinstance(message,AIMessage):
            continue
        if message.tool_calls:
            continue
        if message.text:
            return message.text
    return ""




async def chitchat_node(state:InsuranceAgentState)->dict:
    return {"messages":[AIMessage("你好,今天想聊点什么?")]}

async def recommendation_node(state:InsuranceAgentState)->dict:
    return {"messages":[AIMessage("保险推荐工作流尚未接入。")]}

async def claim_node(state:InsuranceAgentState)->dict:
    return {"messages":[AIMessage("理赔工作流尚未接入。")]}

async def human_handoff_node(state:InsuranceAgentState)->dict:
    return {"messages":[AIMessage("已记录转人工请求，后续可接入人工客服系统。")]}

def fallback_node(state:InsuranceAgentState)->dict:
    return {"messages":[AIMessage("我还不确定你的需求,请说明你是想咨询保险、推荐方案还是办理理赔")]}

def init_insurance_orchestrator(checkpointer:AsyncPostgresSaver):
    """初始化保险顾问主Graph"""
    builder = StateGraph(InsuranceAgentState)

    builder.add_node("route", route_node)
    builder.add_node("chitchat", init_chitchat_agent())
    builder.add_node("recommendation_plan",init_insurance_advisor())
    builder.add_node("claim", claim_node)
    builder.add_node("human_handoff", human_handoff_node)
    builder.add_node("fallback", fallback_node)

    builder.add_edge(START, "route")
    builder.add_edge("chitchat", END)
    builder.add_edge("recommendation_plan", END)
    builder.add_edge("claim", END)
    builder.add_edge("human_handoff", END)
    builder.add_edge("fallback", END)

    return builder.compile(checkpointer=checkpointer)