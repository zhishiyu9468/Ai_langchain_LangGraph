from langchain_milvus import Milvus
from pymilvus import Function, FunctionType

from app.main import logger


def create_reranker(query: str) -> Function:
    """milvus的reranker function，这里采用ali的重排模型"""
    return Function(
        name="dashscope_semantic_ranker",
        input_field_names=["text"],
        function_type=FunctionType.RERANK,
        params={
            "reranker": "model",
            "provider": "ali",
            "model_name": "gte-rerank-v2",
            "queries": [query],
            "max_client_batch_size": 5,
        },
    )
class ParentChunkRetriever:
    def __init__(self, vector_store:Milvus):
        self.vector_store = vector_store
        logger.info("RAG Retriever 初始化完成✅️")