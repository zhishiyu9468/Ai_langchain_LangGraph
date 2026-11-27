from langchain_community.embeddings import DashScopeEmbeddings
from langchain_milvus import Milvus, BM25BuiltInFunction

from app.core.config import settings
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import ParentChunkRetriever

_embeddings = DashScopeEmbeddings(
    model="text-embedding-v4",
    dashscope_api_key=settings.rag.dashscope_api_key,
)
# 2.初始化VectorStore
_vector_store = Milvus(
    embedding_function=_embeddings,
    collection_name="insurance_collection",
    builtin_function=BM25BuiltInFunction(
        analyzer_params={"type": "chinese"}
    ),
    vector_field=["dense", "sparse"],
    connection_args={"uri": settings.rag.milvus_url},
    auto_id=True,
)
pipeline=RAGPipeline(_vector_store)
retriever=ParentChunkRetriever(_vector_store)

def close_rag() -> None:
    """关闭RAG组件"""
    pipeline.close()
    _vector_store.client.close()

__all__ = ['pipeline', 'retriever', 'close_rag']