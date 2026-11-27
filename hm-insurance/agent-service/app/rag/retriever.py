from langchain_milvus import Milvus
from langchain_core.documents import Document
from pymilvus import Function, FunctionType
from pymilvus.exceptions import MilvusException

from app.infra.database import AsyncSessionFactory
from app.core.logging import get_logger
from app.rag.models import ParentChunk
from app.rag.repository import ParentChunkRepository

logger = get_logger(__name__)


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

    async def retrieve(self,query:str,k:int,product_id:int)->list[ParentChunk]:
        #1.向量库查询字块
        try:
            child_chunks=await self.vector_store.asimilarity_search(
                query=query,
                k=k,
                fetch_k=10,
                expr=f"product_id == {product_id}",
                reranker=create_reranker(query),
            )
        except MilvusException as exc:
            if exc.code != 5 or "unsupported ID type" not in str(exc):
                raise
            logger.warning("混合检索失败，改用稠密向量检索", product_id=product_id)
            embedding = await self.vector_store.embeddings.aembed_query(query)
            results = await self.vector_store.aclient.search(
                collection_name=self.vector_store.collection_name,
                data=[embedding],
                anns_field="dense",
                filter=f"product_id == {product_id}",
                limit=k,
                output_fields=["text", "parent_id", "product_id"],
            )
            child_chunks = [
                Document(
                    page_content=hit["entity"]["text"],
                    metadata={
                        "parent_id": hit["entity"]["parent_id"],
                        "product_id": hit["entity"]["product_id"],
                    },
                )
                for hit in results[0]
            ]
        #2.获取父块id
        parent_ids=list(
            dict.fromkeys(child.metadata["parent_id"] for child in child_chunks)
        )
        if not parent_ids:
            return []
        #3.数据库查询父块
        async with AsyncSessionFactory() as session:
            repository=ParentChunkRepository(session)
            parent_chunks=await repository.list_by_ids(parent_ids)

        parent_chunk_map={
            str(parent_chunk.id):parent_chunk
            for parent_chunk in parent_chunks
        }

        return [
            parent_chunk_map[parent_id]
            for parent_id in parent_ids
        ]
