from pathlib import Path
from uuid import uuid4

from langchain.chat_models import init_chat_model
from langchain_core.documents import Document
from langchain_milvus import Milvus
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from mineru import MinerU
from app.rag.repository import ParentChunkRepository
from app.core.config import settings, APP_ROOT
from app.core.logging import get_logger
from app.infra.database import AsyncSessionFactory
from app.modules.product.models import Product
from app.rag.models import ParentChunk

logger = get_logger(__name__)


MARKDOWN_OPTIMIZATION_PROMPT = """
下面这份 Markdown 文档是从保险条款 PDF 解析得来，由于 PDF 中的各个小节是以表格形式存在，所以解析时出现错乱。你分析内容，帮我转为格式正确的 Markdown，特别是标题编号要正确。
- 标题等级要从 1 级标题开始，逐层增加，目录和文档名不计入标题等级。
- 输出结果中不要包含正文开始之前的部分。
- 输出结果只包含 Markdown 正文，不要解释或代码围栏。
- 不要修改保险条款。
""".strip()

class RAGPipeline:
    def __init__(self,vector_store:Milvus)->None:
        self._vector_store = vector_store
        self._mineru=MinerU(settings.rag.mineru_token)
        self._model=init_chat_model(
            settings.llm.chat_model,
            api_key=settings.llm.api_key,
            extra_body={"thinking":{"type":"disabled"}},
            max_tokens=10000
        )
        self._markdown_splitter=MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "h1"),
                ("##", "h2"),
                ("###", "h3"),
                ("####", "h4"),
            ],
            strip_headers=True,
        )
        self._child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "；", ";", "，", ","],
            keep_separator="end",
        )
        logger.info("RAG Pipeline 初始化完成✅️")
    async def ingest(self,product:Product)->None:
        markdown=self._parse_and_optimize(product.clause_name)
        parent_chunks,child_chunks = self._chunk(product=product, markdown=markdown)
        self._save_child_chunks(product_id=product.id,child_chunks=child_chunks)
        await self._save_parent_chunks(product_id=product.id,parent_chunks=parent_chunks)

    def _parse_and_optimize(self,clause_name:str)->str:
        file_path=Path(APP_ROOT/"data"/"raw"/"kb"/clause_name)
        result=self._mineru.extract(str(file_path), timeout=1200)
        # 2.使用大模型优化Markdown
        response = self._model.invoke(
            [
                {"role": "system", "content": MARKDOWN_OPTIMIZATION_PROMPT},
                {"role": "user", "content": result.markdown},
            ]
        )
        return response.content
    def _chunk(
            self,
            markdown:str,
            product:Product
    )->tuple[list[ParentChunk],list[Document]]:
        sections=self._markdown_splitter.split_text(markdown)
        parent_chunks:list[ParentChunk]=[]
        child_chunks:list[Document]=[]
        for section in sections:
            section_path=list(section.metadata.values())
            parent=ParentChunk(
                id=uuid4(),
                product_id=product.id,
                clause_name=product.clause_name,
                section_path=section_path,
                content=section.page_content
            )
            parent_chunks.append(parent)

            section.metadata={
                "product_id":product.id,
                "parent_id":str(parent.id),
            }
            children=self._child_splitter.split_documents([section])
            # 把章节路径拼接到子块正文中，补充语义上下文
            section_header = "\n".join(section_path) + "\n"
            for child in children:
                child.page_content = section_header + child.page_content
            child_chunks.extend(children)
        return parent_chunks,child_chunks
    def _save_child_chunks(self,product_id:int,child_chunks:list[Document])->None:
        if self._vector_store.client.has_collection(
            self._vector_store.collection_name
        ):
            self._vector_store.delete(expr=f"product_id == {product_id}")
        self._vector_store.add_documents(child_chunks)

    async def _save_parent_chunks(self,product_id:int,parent_chunks:list[ParentChunk])->None:
        async with AsyncSessionFactory() as session:
            async with session.begin():
                repository=ParentChunkRepository(session)
                await repository.delete_by_product_id(product_id)
                repository.add_all(parent_chunks)
    def close(self):
        self._mineru.close()
