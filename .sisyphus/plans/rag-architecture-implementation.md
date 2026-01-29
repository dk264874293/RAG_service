# RAG 服务完整架构实施计划

> **规划日期**: 2026-01-29
> **架构选型**: FAISS + DashScope Embeddings
> **实施方案**: 完整重构（统一架构）
> **规划者**: Prometheus (Plan Builder)

---

## 📊 架构概览

### 当前问题诊断

#### ✅ 已有组件
- 文档处理流程完整（上传→提取→分块→JSON 存储）
- Document 模型已定义 `vector` 字段
- `chain/` 目录有独立的向量存储实现（FAISS、Chroma、InMemory）
- DashScope 嵌入服务已配置

#### ❌ 核心缺失
1. **文档处理流程中缺少向量化步骤**
   - `document_service.py` 处理完文档后只保存 JSON
   - 没有调用嵌入 API
   - 没有存入向量数据库

2. **Chain 模块与文档处理完全隔离**
   - `chain/` 目录有 FAISS 向量存储
   - `src/` 服务层完全没有集成
   - 两个部分无法互通数据

3. **缺少检索能力**
   - 无法通过语义搜索文档
   - 没有相似度匹配功能
   - 无法实现真正的 RAG

---

### 目标架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户上传文档                              │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│           文档提取器 (PDF/Word/Excel/PPT)                     │
│           src/extractor/ (已实现)                            │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│           文档分块 (AdaptiveChunker)                          │
│           src/pipeline/adaptive_chunker.py (已实现)           │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│      【新增】文本嵌入服务 (DashScope Embeddings)              │
│      src/vector/embed_service.py                             │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│      【新增】向量存储管理器 (FAISS)                           │
│      src/vector/vector_store.py                              │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│      【新增】FAISS 向量索引 (磁盘持久化)                       │
│      ./data/faiss_index/                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    用户查询                                  │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│      【新增】查询嵌入 (DashScope Embeddings)                  │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│      【新增】向量检索 (FAISS similarity_search)              │
│      返回相关文档片段 + 相似度分数                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 核心组件规划

### 新增模块：src/vector/

| 文件 | 功能 | 关键类/方法 |
|-------|-------|------------|
| `__init__.py` | 模块初始化 | 导出所有向量服务 |
| `embed_service.py` | DashScope 嵌入服务 | `EmbeddingService.embed_text()` |
| `vector_store.py` | FAISS 向量存储管理 | `FAISSVectorStore.similarity_search()` |
| `document_indexer.py` | 文档索引服务 | `DocumentIndexer.index_document()` |
| `retrieval_service.py` | 检索服务 | `RetrievalService.search()` |
| `types.py` | 类型定义 | 向量相关数据类型 |

### 修改模块：src/service/

| 文件 | 修改内容 |
|-------|-----------|
| `document_service.py` | 在 `process_document()` 末尾添加向量化步骤 |

### 新增 API：src/api/routes/

| 文件 | 端点 | 功能 |
|-------|------|------|
| `retrieval.py` | `POST /api/retrieval/search` | 语义搜索文档 |
| | `GET /api/retrieval/similar` | 查找相似文档 |

---

## 📋 详细实施计划

### Phase 1: 基础设施搭建（2-3 天）

#### 任务 1.1: 创建向量服务模块结构
- [ ] 创建 `src/vector/` 目录
- [ ] 创建 `src/vector/__init__.py`
- [ ] 创建 `src/vector/types.py`（定义向量相关类型）

#### 任务 1.2: 实现嵌入服务 (`embed_service.py`)

**文件**: `src/vector/embed_service.py`

```python
"""
DashScope 文本嵌入服务
负责将文本转换为向量表示
"""

from typing import List
from langchain_community.embeddings import DashScopeEmbeddings
from config import settings
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    """DashScope 文本嵌入服务"""

    def __init__(self, config_obj):
        self.embedding_model = DashScopeEmbeddings(
            model=config_obj.dashscope_embedding_model,
            dashscope_api_key=config_obj.dashscope_api_key
        )
        self.dimension = 1536  # text-embedding-v2 的维度
        logger.info(f"初始化 DashScope 嵌入服务: {config_obj.dashscope_embedding_model}")

    async def embed_text(self, text: str) -> List[float]:
        """
        嵌入单个文本

        Args:
            text: 待嵌入的文本

        Returns:
            向量表示（1536 维）
        """
        try:
            vector = await self.embedding_model.aembed_query(text)
            logger.debug(f"文本嵌入成功: 长度={len(text)}, 向量维度={len(vector)}")
            return vector
        except Exception as e:
            logger.error(f"文本嵌入失败: {e}")
            raise

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量嵌入文本

        Args:
            texts: 待嵌入的文本列表

        Returns:
            向量列表
        """
        try:
            vectors = await self.embedding_model.aembed_documents(texts)
            logger.info(f"批量嵌入成功: 数量={len(texts)}, 向量维度={len(vectors[0]) if vectors else 0}")
            return vectors
        except Exception as e:
            logger.error(f"批量嵌入失败: {e}")
            raise

    def get_dimension(self) -> int:
        """获取向量维度"""
        return self.dimension
```

#### 任务 1.3: 实现向量存储管理器 (`vector_store.py`)

**文件**: `src/vector/vector_store.py`

```python
"""
FAISS 向量存储管理器
负责 FAISS 索引的创建、加载、保存和查询
"""

import os
from typing import List, Tuple, Dict, Any, Optional
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LangchainDocument
from config import settings
import logging

logger = logging.getLogger(__name__)

class FAISSVectorStore:
    """FAISS 向量存储管理器"""

    def __init__(self, config_obj, embedding_service):
        self.index_path = config_obj.faiss_index_path
        self.embedding_service = embedding_service
        self.vector_store = None
        self._initialize()

    def _initialize(self):
        """初始化或加载 FAISS 索引"""
        try:
            if os.path.exists(self.index_path):
                self._load_existing_index()
            else:
                self._create_new_index()
        except Exception as e:
            logger.error(f"初始化 FAISS 存储失败: {e}")
            self._create_new_index()

    def _load_existing_index(self):
        """加载现有的 FAISS 索引"""
        try:
            self.vector_store = FAISS.load_local(
                self.index_path,
                self.embedding_service.embedding_model,
                allow_dangerous_deserialization=True
            )
            vector_count = self.vector_store.index.ntotal
            logger.info(f"成功加载 FAISS 索引: {vector_count} 个向量")
        except Exception as e:
            logger.error(f"加载 FAISS 索引失败: {e}，将创建新索引")
            raise e

    def _create_new_index(self):
        """创建新的 FAISS 索引"""
        try:
            init_text = "系统初始化 - RAG 向量数据库已就绪"
            self.vector_store = FAISS.from_texts(
                [init_text],
                self.embedding_service.embedding_model,
                metadatas=[{"type": "system_init"}]
            )
            logger.info("创建新的 FAISS 索引")
        except Exception as e:
            logger.error(f"创建 FAISS 索引失败: {e}")
            raise e

    async def add_documents(self, documents: List[LangchainDocument]) -> bool:
        """
        添加文档到向量存储

        Args:
            documents: Langchain 文档列表

        Returns:
            是否添加成功
        """
        try:
            self.vector_store.add_documents(documents)
            logger.info(f"成功添加 {len(documents)} 个文档到向量存储")
            return True
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False

    async def similarity_search(self, query: str, k: int = 5, filter_dict: Optional[Dict] = None) -> List[LangchainDocument]:
        """
        相似度搜索

        Args:
            query: 查询文本
            k: 返回结果数量
            filter_dict: 元数据过滤条件

        Returns:
            相关文档列表
        """
        try:
            if filter_dict:
                results = self.vector_store.similarity_search(
                    query, k=k, filter=filter_dict
                )
            else:
                results = self.vector_store.similarity_search(query, k=k)

            logger.info(f"相似度搜索: query='{query[:50]}...', 返回 {len(results)} 个结果")
            return results
        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            return []

    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 5
    ) -> List[Tuple[LangchainDocument, float]]:
        """
        相似度搜索（带分数）

        Args:
            query: 查询文本
            k: 返回结果数量

        Returns:
            (文档, 相似度分数) 列表
        """
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            logger.info(f"相似度搜索（带分数）: 返回 {len(results)} 个结果")
            return results
        except Exception as e:
            logger.error(f"相似度搜索（带分数）失败: {e}")
            return []

    async def save_index(self) -> bool:
        """保存 FAISS 索引到磁盘"""
        try:
            self.vector_store.save_local(self.index_path)
            vector_count = self.vector_store.index.ntotal
            logger.info(f"成功保存 FAISS 索引: {vector_count} 个向量")
            return True
        except Exception as e:
            logger.error(f"保存 FAISS 索引失败: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取向量存储统计信息"""
        try:
            total_vectors = self.vector_store.index.ntotal
            return {
                "total_vectors": total_vectors,
                "index_path": self.index_path,
                "dimension": self.embedding_service.get_dimension(),
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "total_vectors": 0,
                "index_path": self.index_path,
                "dimension": 0
            }
```

#### 任务 1.4: 实现文档索引器 (`document_indexer.py`)

**文件**: `src/vector/document_indexer.py`

```python
"""
文档索引服务
负责将文档块向量化并存储到 FAISS
"""

from typing import List, Dict, Any
from langchain_core.documents import Document as LangchainDocument
from ..models.document import Document
from .embed_service import EmbeddingService
from .vector_store import FAISSVectorStore
import logging

logger = logging.getLogger(__name__)

class DocumentIndexer:
    """文档索引服务"""

    def __init__(self, config_obj, vector_store: FAISSVectorStore, embedding_service: EmbeddingService):
        self.config = config_obj
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    async def index_document(self, file_id: str, documents: List[Document]) -> bool:
        """
        索引单个文档的所有块

        Args:
            file_id: 文件 ID
            documents: 文档块列表

        Returns:
            是否索引成功
        """
        try:
            # 转换为 Langchain Document 格式
            langchain_docs = []
            for doc in documents:
                lc_doc = LangchainDocument(
                    page_content=doc.page_content,
                    metadata={
                        **doc.metadata,
                        "file_id": file_id,
                        "doc_id": doc.id_
                    }
                )
                langchain_docs.append(lc_doc)

            # 添加到向量存储
            success = await self.vector_store.add_documents(langchain_docs)

            if success:
                # 保存索引
                await self.vector_store.save_index()
                logger.info(f"文档索引成功: file_id={file_id}, 块数={len(documents)}")

            return success

        except Exception as e:
            logger.error(f"文档索引失败: file_id={file_id}, error={e}")
            return False

    async def delete_document(self, file_id: str) -> bool:
        """
        删除文档的所有索引

        注意: FAISS 不支持删除单个向量，需要重建索引

        Args:
            file_id: 文件 ID

        Returns:
            是否删除成功
        """
        logger.warning(f"FAISS 不支持删除操作: file_id={file_id}")
        return False

    async def get_index_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        return self.vector_store.get_stats()
```

#### 任务 1.5: 实现检索服务 (`retrieval_service.py`)

**文件**: `src/vector/retrieval_service.py`

```python
"""
检索服务
提供向量相似度搜索和高级检索功能
"""

from typing import List, Tuple, Dict, Any, Optional
from langchain_core.documents import Document as LangchainDocument
from ..models.document import Document
from .embed_service import EmbeddingService
from .vector_store import FAISSVectorStore
import logging

logger = logging.getLogger(__name__)

class RetrievalService:
    """检索服务"""

    def __init__(self, config_obj, vector_store: FAISSVectorStore, embedding_service: EmbeddingService):
        self.config = config_obj
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    async def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """
        语义搜索

        Args:
            query: 查询文本
            k: 返回结果数量
            filter_dict: 元数据过滤条件

        Returns:
            相关文档列表
        """
        try:
            langchain_docs = await self.vector_store.similarity_search(
                query, k=k, filter_dict=filter_dict
            )

            # 转换为我们的 Document 格式
            documents = []
            for lc_doc in langchain_docs:
                doc = Document(
                    page_content=lc_doc.page_content,
                    id_=lc_doc.metadata.get("doc_id", ""),
                    metadata=lc_doc.metadata
                )
                documents.append(doc)

            logger.info(f"检索成功: query='{query[:50]}...', 返回 {len(documents)} 个结果")
            return documents

        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []

    async def search_with_scores(
        self,
        query: str,
        k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        搜索并返回相似度分数

        Args:
            query: 查询文本
            k: 返回结果数量

        Returns:
            (文档, 相似度分数) 列表
        """
        try:
            results = await self.vector_store.similarity_search_with_score(query, k=k)

            # 转换格式
            documents_with_scores = []
            for lc_doc, score in results:
                doc = Document(
                    page_content=lc_doc.page_content,
                    id_=lc_doc.metadata.get("doc_id", ""),
                    metadata=lc_doc.metadata
                )
                documents_with_scores.append((doc, score))

            logger.info(f"检索（带分数）成功: 返回 {len(documents_with_scores)} 个结果")
            return documents_with_scores

        except Exception as e:
            logger.error(f"检索（带分数）失败: {e}")
            return []
```

---

### Phase 2: 集成现有服务（1 天）

#### 任务 2.1: 修改 DocumentService

**文件**: `src/service/document_service.py`

在 `process_document` 方法末尾添加向量化步骤：

```python
async def process_document(
    self, file_path: str, file_id: str, file_name: str
) -> tuple[bool, str, List]:
    try:
        config = {...}  # 现有配置
        pipeline = DocumentProcessingPipeline(config)
        documents = await pipeline.process_document(file_path)

        # 现有代码：保存 JSON
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        result_file = self.processed_dir / f"{file_id}.json"
        result_data = {...}
        async with aiofiles.open(result_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(result_data, ensure_ascii=False, indent=2))

        # 【新增】向量化并索引
        try:
            from src.vector.embed_service import EmbeddingService
            from src.vector.vector_store import FAISSVectorStore
            from src.vector.document_indexer import DocumentIndexer

            # 初始化向量服务
            embedding_service = EmbeddingService(self.settings)
            vector_store = FAISSVectorStore(self.settings, embedding_service)
            indexer = DocumentIndexer(self.settings, vector_store, embedding_service)

            # 索引文档
            await indexer.index_document(file_id, documents)
            logger.info(f"文档向量化成功: file_id={file_id}")

        except Exception as e:
            logger.error(f"文档向量化失败: file_id={file_id}, error={e}")
            # 向量化失败不影响主流程，继续返回

        return True, "处理成功", documents

    except OCRError as e:
        logger.error(f"OCR处理失败: {e}")
        return False, f"OCR处理失败: {e}", []
    except Exception as e:
        logger.error(f"文档处理失败: {e}")
        return False, f"处理失败: {e}", []
```

#### 任务 2.2: 更新依赖注入

**文件**: `src/api/dependencies.py`

添加向量服务的依赖注入：

```python
from functools import lru_cache

from config import settings
from src.service.upload_service import UploadService
from src.service.document_service import DocumentService
from src.service.markdown_service import MarkdownService

# 【新增】向量服务依赖
from src.vector.embed_service import EmbeddingService
from src.vector.vector_store import FAISSVectorStore
from src.vector.retrieval_service import RetrievalService

@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """获取嵌入服务实例（单例模式）"""
    return EmbeddingService(get_settings())

@lru_cache(maxsize=1)
def get_vector_store() -> FAISSVectorStore:
    """获取向量存储实例（单例模式）"""
    embedding_service = get_embedding_service()
    return FAISSVectorStore(get_settings(), embedding_service)

@lru_cache(maxsize=1)
def get_retrieval_service() -> RetrievalService:
    """获取检索服务实例（单例模式）"""
    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    return RetrievalService(get_settings(), vector_store, embedding_service)
```

---

### Phase 3: API 端点开发（1 天）

#### 任务 3.1: 创建检索 API

**文件**: `src/api/routes/retrieval.py` (新建)

```python
"""
检索 API 路由
提供语义搜索和相似度匹配功能
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.dependencies import get_retrieval_service
from src.vector.retrieval_service import RetrievalService
from src.models.document import Document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/retrieval", tags=["检索服务"])


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索查询", min_length=1)
    k: int = Field(default=5, description="返回结果数量", ge=1, le=20)
    filters: Optional[Dict[str, Any]] = Field(None, description="元数据过滤条件")

    class Config:
        schema_extra = {
            "example": {
                "query": "Python 异步编程的最佳实践",
                "k": 5,
                "filters": {"file_type": ".pdf"}
            }
        }


class SearchResult(BaseModel):
    """搜索结果模型"""
    doc_id: str = Field(..., description="文档 ID")
    content: str = Field(..., description="文档内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    score: Optional[float] = Field(None, description="相似度分数")


class SearchResponse(BaseModel):
    """搜索响应模型"""
    query: str = Field(..., description="搜索查询")
    total: int = Field(..., description="结果总数")
    results: List[SearchResult] = Field(..., description="搜索结果列表")


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service)
):
    """
    语义搜索文档

    根据查询文本，使用向量相似度搜索相关文档片段。
    """
    try:
        logger.info(f"收到搜索请求: query='{request.query}', k={request.k}")

        # 执行搜索
        documents = await retrieval_service.search(
            query=request.query,
            k=request.k,
            filter_dict=request.filters
        )

        # 转换为响应格式
        results = []
        for doc in documents:
            results.append(SearchResult(
                doc_id=doc.id_,
                content=doc.page_content[:500],  # 限制预览长度
                metadata=doc.metadata,
                score=None
            ))

        logger.info(f"搜索完成: 返回 {len(results)} 个结果")

        return SearchResponse(
            query=request.query,
            total=len(results),
            results=results
        )

    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/search-with-scores")
async def search_documents_with_scores(
    query: str = Query(..., description="搜索查询", min_length=1),
    k: int = Query(default=5, description="返回结果数量", ge=1, le=20),
    retrieval_service: RetrievalService = Depends(get_retrieval_service)
):
    """
    搜索文档（带相似度分数）

    返回带有相似度分数的搜索结果。
    """
    try:
        logger.info(f"收到搜索请求（带分数）: query='{query}', k={k}")

        # 执行搜索
        documents_with_scores = await retrieval_service.search_with_scores(
            query=query,
            k=k
        )

        # 转换为响应格式
        results = []
        for doc, score in documents_with_scores:
            results.append(SearchResult(
                doc_id=doc.id_,
                content=doc.page_content[:500],
                metadata=doc.metadata,
                score=score
            ))

        logger.info(f"搜索完成: 返回 {len(results)} 个结果")

        return {
            "query": query,
            "total": len(results),
            "results": results
        }

    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/stats")
async def get_index_stats(
    retrieval_service: RetrievalService = Depends(get_retrieval_service)
):
    """
    获取向量索引统计信息

    返回 FAISS 索引的状态和统计信息。
    """
    try:
        stats = await retrieval_service.vector_store.get_stats()
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
```

#### 任务 3.2: 注册路由

**文件**: `src/api/routes/__init__.py`

```python
from .upload import router as upload_router
from .markdown import router as markdown_router
from .health import router as health_router
from .retrieval import router as retrieval_router  # 【新增】

__all__ = ["upload_router", "markdown_router", "health_router", "retrieval_router"]
```

**文件**: `src/app.py`

```python
from src.api.routes import upload_router, markdown_router, health_router, retrieval_router

app.include_router(upload_router)
app.include_router(markdown_router)
app.include_router(health_router)
app.include_router(retrieval_router)  # 【新增】
```

---

### Phase 4: 配置和测试（1-2 天）

#### 任务 4.1: 更新配置文件

**文件**: `config.py`

添加 FAISS 和检索相关配置：

```python
class Settings(BaseSettings):
    # ... 现有配置 ...

    # 【新增】FAISS 配置
    faiss_index_path: str = "./data/faiss_index"
    faiss_index_type: str = "IndexFlatIP"
    faiss_dimension: int = 1536

    # 【新增】DashScope 嵌入配置
    dashscope_api_key: str = Field(..., description="DashScope API Key")
    dashscope_embedding_model: str = "text-embedding-v2"

    # 【新增】检索配置
    default_search_k: int = 5
    max_search_k: int = 20

    class Config:
        env_file = ".env"
        extra = "allow"
```

#### 任务 4.2: 创建单元测试

**文件**: `tests/test_vector_services.py` (新建)

```python
"""
向量服务单元测试
"""

import pytest
from src.vector.embed_service import EmbeddingService
from src.vector.vector_store import FAISSVectorStore
from src.vector.document_indexer import DocumentIndexer
from src.vector.retrieval_service import RetrievalService
from config import settings

@pytest.mark.asyncio
async def test_embedding_service():
    """测试嵌入服务"""
    service = EmbeddingService(settings)

    # 测试单个文本嵌入
    text = "这是一个测试文本"
    vector = await service.embed_text(text)

    assert len(vector) == 1536
    assert all(isinstance(v, float) for v in vector)

@pytest.mark.asyncio
async def test_vector_store():
    """测试向量存储"""
    embedding_service = EmbeddingService(settings)
    store = FAISSVectorStore(settings, embedding_service)

    # 测试统计信息
    stats = store.get_stats()
    assert "total_vectors" in stats

@pytest.mark.asyncio
async def test_document_indexer():
    """测试文档索引器"""
    embedding_service = EmbeddingService(settings)
    vector_store = FAISSVectorStore(settings, embedding_service)
    indexer = DocumentIndexer(settings, vector_store, embedding_service)

    # 创建测试文档
    from src.models.document import Document
    docs = [
        Document(page_content="测试内容1", id_="doc1"),
        Document(page_content="测试内容2", id_="doc2")
    ]

    # 测试索引
    success = await indexer.index_document("test_file", docs)
    assert success is True

@pytest.mark.asyncio
async def test_retrieval_service():
    """测试检索服务"""
    # 先索引一些文档
    # 然后测试检索

    embedding_service = EmbeddingService(settings)
    vector_store = FAISSVectorStore(settings, embedding_service)
    retrieval_service = RetrievalService(settings, vector_store, embedding_service)

    # 测试搜索
    results = await retrieval_service.search("测试查询", k=3)
    assert isinstance(results, list)
```

#### 任务 4.3: 创建集成测试

**文件**: `tests/test_rag_integration.py` (新建)

```python
"""
RAG 系统集成测试
端到端测试：上传→处理→索引→检索
"""

import pytest
import asyncio
from pathlib import Path
from src.service.upload_service import UploadService
from src.vector.retrieval_service import RetrievalService
from config import settings

@pytest.mark.asyncio
async def test_end_to_end_rag():
    """端到端 RAG 测试"""

    # 1. 上传并处理文档
    upload_service = UploadService(settings)

    # 模拟文件上传
    test_file_path = "./tests/test_document.pdf"

    # 假设文件已上传，处理文档
    success, msg, documents = await upload_service.document_service.process_document(
        test_file_path,
        "test_file_001",
        "test_document.pdf"
    )

    assert success is True
    assert len(documents) > 0

    # 2. 等待向量化完成
    await asyncio.sleep(1)

    # 3. 测试检索
    retrieval_service = RetrievalService(settings)
    results = await retrieval_service.search("测试查询", k=3)

    assert len(results) > 0

    # 验证检索结果相关性
    for result in results:
        assert result.page_content is not None
        assert len(result.page_content) > 0
```

---

## 📊 性能优化建议

### 1. 批量嵌入优化
```python
# ❌ 慢：逐个嵌入
for chunk in chunks:
    vector = await embed_service.embed_text(chunk)

# ✅ 快：批量嵌入
vectors = await embed_service.embed_batch(chunks)
```

### 2. FAISS 索引优化
- 使用 `IndexFlatIP` 进行内积搜索
- 预分配索引空间
- 定期保存索引到磁盘

### 3. 检索优化
- 实现元数据过滤
- 实现混合检索（向量 + BM25）
- 实现结果重排序

---

## 🎯 成功指标

| 指标 | 目标值 | 测试方法 |
|-------|-------|----------|
| 嵌入延迟 | < 500ms | 单个文档嵌入时间 |
| 检索延迟 | < 100ms | k=5 检索时间 |
| 索引容量 | > 10K 文档 | FAISS 索引向量数 |
| 检索准确性 | > 0.7 相关度分数 | 人工评估 |
| 并发性能 | > 100 QPS | 负载测试 |

---

## 📅 实施时间表

| 阶段 | 任务 | 预计时间 | 依赖 |
|------|-------|-----------|------|
| **Phase 1** | 基础设施搭建 | 2-3 天 | 无 |
| **Phase 2** | 集成现有服务 | 1 天 | Phase 1 |
| **Phase 3** | API 端点开发 | 1 天 | Phase 2 |
| **Phase 4** | 配置和测试 | 1-2 天 | Phase 3 |
| **总计** | | **5-7 天** | |

---

## ✅ 验收标准

### 功能验收
- [ ] 文档上传后自动向量化并存储到 FAISS
- [ ] 可以通过语义搜索查询相关文档
- [ ] 检索结果按相似度排序
- [ ] 支持元数据过滤（按文件类型、日期等）
- [ ] FAISS 索引持久化到磁盘

### 性能验收
- [ ] 单个文档嵌入时间 < 500ms
- [ ] 检索响应时间 < 100ms (k=5)
- [ ] 支持 10K+ 文档索引

### 质量验收
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过
- [ ] 代码符合项目规范
- [ ] 日志记录完整

---

## 🚀 开始实施

本计划已准备好交付执行。

**下一步**：运行 `/start-work` 命令，让 Sisyphus 执行这个计划。

实施顺序：
1. **Wave 1**: 创建向量服务模块（`src/vector/` 目录结构和基础服务）
2. **Wave 2**: 实现嵌入服务和向量存储管理器
3. **Wave 3**: 实现文档索引器和检索服务
4. **Wave 4**: 集成到 DocumentService
5. **Wave 5**: 创建检索 API 端点
6. **Wave 6**: 更新配置文件，添加单元测试
7. **Wave 7**: 创建集成测试，验证端到端流程

所有优化完成后，你将拥有一个完整的 RAG 系统！
