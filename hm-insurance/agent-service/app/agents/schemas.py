from dataclasses import dataclass


@dataclass(frozen=True)
class InsuranceAgentContext:
    """Agent运行时上下文"""
    user_id:int