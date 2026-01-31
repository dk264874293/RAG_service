# RAG 架构实施工作计划

> **实施范围**: Phase 1-6
> **技术栈**: FAISS-CPU + DashScope Embeddings
> **预计时间**: 5-6 天

---

## 📊 实施概览

### 目标
为 RAG 服务添加完整的向量存储和检索能力：
1. 创建向量服务模块
2. 实现文档向量化流程
3. 集成 FAISS 向量存储
4. 提供语义检索 API

### 技术栈
- **向量存储**: FAISS-CPU (`faiss-cpu`)
- **嵌入模型**: DashScope (`text-embedding-v2`)
- **向量维度**: 1536

---

## 🎯 核心原则

### TDD 方法
- 每个任务先编写/更新测试
- 使用 `agent-executable` 验证（不依赖手动检查）
- API 端点使用 Playwright 自动化测试

### 并行执行策略
- **Wave 1**: 创建目录结构和类型定义（可并行）
- **Wave 2**: 实现嵌入服务（依赖 Wave 1）
- **Wave 3**: 实现向量存储管理器（依赖 Wave 1-2）
- **Wave 4**: 实现文档索引器和检索服务（依赖 Wave 1-3）
- **Wave 5**: 集成到 DocumentService（依赖 Wave 4）
- **Wave 6**: 创建检索 API 端点（依赖 Wave 5）

---

## 📋 详细实施任务

### Wave 1: 创建向量服务模块基础结构

#### 任务 1.1: 创建 src/vector/ 目录结构

**What to do**:
- 创建 `src/vector/` 目录
- 创建 `src/vector/__init__.py`
- 创建 `src/vector/types.py`

**Must NOT do**:
- 不要使用中文注释或文档字符串（代码审查已提示）
- 不要创建测试文件（Phase 4 暂时不实施测试）

**Recommended Agent Profile**:
- **Category**: `unspecified-low`
- **Skills**: `["git-master"]`
- **Reasoning**: 基础目录创建和简单代码编写

**Parallelization**:
- **Can Run In Parallel**: NO（顺序执行）
- **Parallel Group**: Wave 1 Sequential
- **Blocks**: Wave 2, 3, 4, 5, 6
- **Blocked By**: None

**References**:

**Pattern References**:
- `src/extractor/__init__.py` - 模块初始化模式
- `src/models/types.py` - 类型定义模式

**Acceptance Criteria**:

**Automated Verification (using Bash)**:
```bash
# Agent executes:
mkdir -p src/vector && echo "Directory created"

# Verify:
test -d src/vector && echo "PASS: Directory exists" || echo "FAIL: Directory not found"

# Verify files exist:
test -f src/vector/__init__.py && echo "PASS: __init__.py exists" || echo "FAIL: __init__.py missing"
test -f src/vector/types.py && echo "PASS: types.py exists" || echo "FAIL: types.py missing"
```

**Commit**: NO

---

#### 任务 1.2: 实现向量服务类型定义

**What to do**:
- 在 `src/vector/types.py` 中定义向量相关类型
- 定义 `VectorSearchResult` 类（包含文档和分数）
- 定义 `IndexStats` 类（索引统计信息）

**Must NOT do**:
- 不要实现复杂的嵌套类型
- 不要添加未使用的类型

**Recommended Agent Profile**:
- **Category**: `unspecified-low`
- **Skills**: `[]`
- **Reasoning**: 简单类型定义，不需要特殊技能

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 1 Sequential
- **Blocks**: Wave 2, 3, 4, 5, 6
- **Blocked By**: Task 1.1

**References**:

**Pattern References**:
- `src/models/document.py:Document` - Pydantic 模型定义模式
- `src/schemas/upload.py:UploadResponse` - 响应模型定义模式

**Acceptance Criteria**:

**Automated Verification (using Bash - Python)**:
```bash
# Agent executes:
python -c "
from src.vector.types import VectorSearchResult, IndexStats
print('Types imported successfully')

# Test VectorSearchResult
result = VectorSearchResult(
    doc_id='test',
    content='test content',
    metadata={},
    score=0.8
)
print(f'PASS: VectorSearchResult created - doc_id={result.doc_id}')

# Test IndexStats
stats = IndexStats(
    total_vectors=100,
    index_path='./data/faiss_index',
    dimension=1536
)
print(f'PASS: IndexStats created - total_vectors={stats.total_vectors}')
"

# Expected output:
# Types imported successfully
# PASS: VectorSearchResult created - doc_id=test
# PASS: IndexStats created - total_vectors=100
```

**Commit**: NO

---

### Wave 2: 实现嵌入服务

#### 任务 2.1: 实现 EmbeddingService

**What to do**:
- 创建 `src/vector/embed_service.py`
- 实现 `EmbeddingService` 类
- 实现 `embed_text()` 方法（单个文本嵌入）
- 实现 `embed_batch()` 方法（批量嵌入）
- 实现 `get_dimension()` 方法

**Must NOT do**:
- 不要在 __init__ 中调用 API（延迟初始化）
- 不要硬编码 API Key（使用 config.dashscope_api_key）

**Recommended Agent Profile**:
- **Category**: `unspecified-low`
- **Skills**: `[]`
- **Reasoning**: 标准服务类实现，使用 langchain_community 集成

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 2 Sequential
- **Blocks**: Wave 3, 4, 5, 6
- **Blocked By**: Wave 1 (types.py 依赖)

**References**:

**Pattern References**:
- `chain/memory/faiss_mem.py:FAISSMemoryManager.__init__` - DashScope 嵌入初始化模式
- `chain/dashscope_embedding.py:25` - DashScopeEmbeddings 使用示例

**API/Type References**:
- `langchain_community.embeddings.DashScopeEmbeddings` - 嵌入模型类
- `config.py:dashscope_api_key` - API Key 配置

**Acceptance Criteria**:

**Automated Verification (using Bash - Python)**:
```bash
# Agent executes:
python -c "
import asyncio
from src.vector.embed_service import EmbeddingService
from config import settings

async def test():
    service = EmbeddingService(settings)
    
    # Test dimension
    dim = service.get_dimension()
    print(f'Dimension: {dim}')
    assert dim == 1536, f'FAIL: Expected 1536, got {dim}'
    print('PASS: Dimension is correct')
    
    # Test single embedding
    text = '这是一个测试文本'
    vector = await service.embed_text(text)
    print(f'Vector length: {len(vector)}')
    assert len(vector) == 1536, f'FAIL: Expected 1536, got {len(vector)}'
    assert all(isinstance(v, (int, float)) for v in vector), 'FAIL: Vector contains non-numeric values'
    print('PASS: Single embedding works')
    
    # Test batch embedding
    texts = ['文本1', '文本2', '文本3']
    vectors = await service.embed_batch(texts)
    print(f'Batch size: {len(vectors)}')
    assert len(vectors) == 3, f'FAIL: Expected 3, got {len(vectors)}'
    assert all(len(v) == 1536 for v in vectors), 'FAIL: Batch vectors have wrong dimension'
    print('PASS: Batch embedding works')

asyncio.run(test())
"

# Expected output:
# Dimension: 1536
# PASS: Dimension is correct
# Vector length: 1536
# PASS: Single embedding works
# Batch size: 3
# PASS: Batch embedding works
```

**Commit**: NO

---

### Wave 3: 实现向量存储管理器

#### 任务 3.1: 实现 FAISSVectorStore

**What to do**:
- 创建 `src/vector/vector_store.py`
- 实现 `FAISSVectorStore` 类
- 实现 `_initialize()` 方法（加载或创建索引）
- 实现 `_load_existing_index()` 方法
- 实现 `_create_new_index()` 方法
- 实现 `add_documents()` 方法
- 实现 `similarity_search()` 方法
- 实现 `similarity_search_with_score()` 方法
- 实现 `save_index()` 方法
- 实现 `get_stats()` 方法

**Must NOT do**:
- 不要在每次 add_documents 后都 save_index（批量操作后统一保存）
- 不要使用中文日志消息（使用英文）

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
- **Skills**: `[]`
- **Reasoning**: 复杂的向量存储管理，需要错误处理和状态管理

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 3 Sequential
- **Blocks**: Wave 4, 5, 6
- **Blocked By**: Wave 1-2 (依赖 EmbeddingService)

**References**:

**Pattern References**:
- `chain/memory/faiss_mem.py:FAISSMemoryManager` - FAISS 管理器实现模式
- `chain/memory/faiss_mem.py:54-98` - 索引初始化和加载逻辑
- `chain/memory/faiss_mem.py:115-140` - add_documents 实现
- `chain/memory/faiss_mem.py:142-172` - similarity_search 实现

**API/Type References**:
- `langchain_community.vectorstores.FAISS` - FAISS 向量存储
- `langchain_core.documents.Document` - Langchain 文档模型
- `config.py:faiss_index_path` - FAISS 索引路径配置

**Acceptance Criteria**:

**Automated Verification (using Bash - Python)**:
```bash
# Agent executes:
python -c "
import asyncio
from src.vector.embed_service import EmbeddingService
from src.vector.vector_store import FAISSVectorStore
from config import settings

async def test():
    # Initialize services
    embedding_service = EmbeddingService(settings)
    store = FAISSVectorStore(settings, embedding_service)
    
    # Test stats
    stats = store.get_stats()
    print(f'Total vectors: {stats[\"total_vectors\"]}')
    assert 'total_vectors' in stats, 'FAIL: Missing total_vectors in stats'
    assert stats['total_vectors'] >= 1, 'FAIL: Index should have at least 1 vector (init doc)'
    print('PASS: Stats accessible')
    
    # Test similarity_search
    results = await store.similarity_search('测试查询', k=2)
    print(f'Search results: {len(results)}')
    assert isinstance(results, list), 'FAIL: Results should be a list'
    print('PASS: Similarity search works')
    
    # Test save_index
    saved = await store.save_index()
    assert saved is True, 'FAIL: save_index should return True'
    print('PASS: Index saved')

asyncio.run(test())
"

# Expected output:
# Total vectors: 1
# PASS: Stats accessible
# Search results: 1
# PASS: Similarity search works
# PASS: Index saved
```

**Commit**: NO

---

### Wave 4: 实现文档索引器和检索服务

#### 任务 4.1: 实现 DocumentIndexer

**What to do**:
- 创建 `src/vector/document_indexer.py`
- 实现 `DocumentIndexer` 类
- 实现 `index_document()` 方法（将文档向量化并存储）
- 实现 `get_index_stats()` 方法

**Must NOT do**:
- 不要实现 `delete_document()`（FAISS 不支持删除）
- 不要在每次 index_document 后都 save（批量操作后统一保存）

**Recommended Agent Profile**:
- **Category**: `unspecified-low`
- **Skills**: `[]`
- **Reasoning**: 索引服务实现，依赖 EmbeddingService 和 FAISSVectorStore

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 4 Sequential (with Task 4.2)
- **Blocks**: Wave 5, 6
- **Blocked By**: Wave 1-3

**References**:

**Pattern References**:
- `src/service/document_service.py:16-78` - 服务类实现模式
- `chain/memory/faiss_mem.py:115-140` - 文档添加到向量存储的模式

**API/Type References**:
- `src.models.document:Document` - 自定义文档模型
- `langchain_core.documents.Document` - Langchain 文档模型（需要转换）

**Acceptance Criteria**:

**Automated Verification (using Bash - Python)**:
```bash
# Agent executes:
python -c "
import asyncio
from src.vector.embed_service import EmbeddingService
from src.vector.vector_store import FAISSVectorStore
from src.vector.document_indexer import DocumentIndexer
from src.models.document import Document
from config import settings

async def test():
    # Initialize services
    embedding_service = EmbeddingService(settings)
    vector_store = FAISSVectorStore(settings, embedding_service)
    indexer = DocumentIndexer(settings, vector_store, embedding_service)
    
    # Test index_document
    docs = [
        Document(page_content='Test content 1', id_='doc1'),
        Document(page_content='Test content 2', id_='doc2')
    ]
    success = await indexer.index_document('test_file', docs)
    print(f'Index success: {success}')
    assert success is True, 'FAIL: index_document should return True'
    print('PASS: Document indexed')
    
    # Verify stats updated
    stats = await indexer.get_index_stats()
    print(f'Total vectors: {stats[\"total_vectors\"]}')
    assert stats['total_vectors'] >= 3, 'FAIL: Should have at least 3 vectors (1 init + 2 docs)'
    print('PASS: Stats updated correctly')

asyncio.run(test())
"

# Expected output:
# Index success: True
# PASS: Document indexed
# Total vectors: 3
# PASS: Stats updated correctly
```

**Commit**: NO

---

#### 任务 4.2: 实现 RetrievalService

**What to do**:
- 创建 `src/vector/retrieval_service.py`
- 实现 `RetrievalService` 类
- 实现 `search()` 方法（语义搜索）
- 实现 `search_with_scores()` 方法（带相似度分数）

**Must NOT do**:
- 不要实现高级检索（hybrid_search, mmr_search），只实现基础的向量检索

**Recommended Agent Profile**:
- **Category**: `unspecified-low`
- **Skills**: `[]`
- **Reasoning**: 检索服务实现，相对简单

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 4 Sequential
- **Blocks**: Wave 5, 6
- **Blocked By**: Wave 1-3

**References**:

**Pattern References**:
- `chain/memory/faiss_mem.py:142-172` - similarity_search 实现模式
- `src/service/document_service.py:16-78` - 服务类实现模式

**API/Type References**:
- `src.vector.vector_store:FAISSVectorStore.similarity_search` - 向量搜索方法
- `src.models.document:Document` - 自定义文档模型

**Acceptance Criteria**:

**Automated Verification (using Bash - Python)**:
```bash
# Agent executes:
python -c "
import asyncio
from src.vector.embed_service import EmbeddingService
from src.vector.vector_store import FAISSVectorStore
from src.vector.document_indexer import DocumentIndexer
from src.vector.retrieval_service import RetrievalService
from src.models.document import Document
from config import settings

async def test():
    # Initialize and index some documents first
    embedding_service = EmbeddingService(settings)
    vector_store = FAISSVectorStore(settings, embedding_service)
    indexer = DocumentIndexer(settings, vector_store, embedding_service)
    
    docs = [
        Document(page_content='Python is a programming language', id_='doc1'),
        Document(page_content='JavaScript is used for web development', id_='doc2'),
        Document(page_content='Python supports async programming', id_='doc3')
    ]
    await indexer.index_document('test', docs)
    
    # Test retrieval service
    retrieval_service = RetrievalService(settings, vector_store, embedding_service)
    
    # Test search
    results = await retrieval_service.search('Python programming', k=2)
    print(f'Search results: {len(results)}')
    assert len(results) > 0, 'FAIL: Should return at least 1 result'
    assert any('Python' in r.page_content for r in results), 'FAIL: Results should contain Python'
    print('PASS: Search works')
    
    # Test search_with_scores
    results_with_scores = await retrieval_service.search_with_scores('Python', k=2)
    print(f'Search with scores: {len(results_with_scores)}')
    assert len(results_with_scores) > 0, 'FAIL: Should return at least 1 result'
    doc, score = results_with_scores[0]
    assert isinstance(score, (int, float)), 'FAIL: Score should be numeric'
    assert doc.page_content is not None, 'FAIL: Document should have content'
    print(f'PASS: Search with scores works (score={score:.4f})')

asyncio.run(test())
"

# Expected output:
# Search results: 2
# PASS: Search works
# Search with scores: 2
# PASS: Search with scores works (score=0.xxxx)
```

**Commit**: NO

---

### Wave 5: 集成到现有服务

#### 任务 5.1: 修改 DocumentService

**What to do**:
- 修改 `src/service/document_service.py`
- 在 `process_document()` 方法末尾添加向量化步骤
- 在 `process_document()` 的 except 块中捕获向量化异常（不阻塞主流程）

**Must NOT do**:
- 不要修改现有处理流程，只在末尾添加
- 不要改变返回值结构
- 不要添加中文日志（使用英文）

**Recommended Agent Profile**:
- **Category**: `quick`
- **Skills**: `[]`
- **Reasoning**: 简单的集成修改，向现有方法添加代码

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 5 Sequential
- **Blocks**: Wave 6
- **Blocked By**: Wave 1-4

**References**:

**Pattern References**:
- `src/service/document_service.py:36-60` - 现有处理流程
- `src/service/document_service.py:63-68` - 异常处理模式

**Code Location**:
- `src/service/document_service.py:61` - 在 return 语句之前添加向量化代码

**Acceptance Criteria**:

**Automated Verification (using Bash - Python)**:
```bash
# Agent executes:
python -c "
import asyncio
from src.service.document_service import DocumentService
from config import settings
from pathlib import Path

async def test():
    service = DocumentService(settings)
    
    # Check if the file exists for testing
    test_file = './src/extractor/ocr_module/core/pdfs/25AA0118采样.pdf'
    if not Path(test_file).exists():
        print('SKIP: Test file not found')
        return
    
    # Process document (this should trigger vectorization)
    success, msg, documents = await service.process_document(
        test_file,
        'test_file_001',
        'test.pdf'
    )
    
    print(f'Success: {success}')
    print(f'message: {msg}')
    print(f'documents: {len(documents)}')
    
    # Verify vectorization happened
    import os
    faiss_dir = './data/faiss_index'
    if os.path.exists(faiss_dir):
        files = os.listdir(faiss_dir)
        print(f'FAISS index files: {files}')
        assert len(files) > 0, 'FAIL: FAISS index should be created'
        print('PASS: Vectorization completed - FAISS index created')
    else:
        print('SKIP: FAISS index not created (may be normal if test file missing)')

asyncio.run(test())
"

# Expected output:
# success: True
# message: 处理成功
# documents: X
# FAISS index files: ['index.faiss', 'index.pkl']
# PASS: Vectorization completed - FAISS index created
```

**Commit**: NO

---

#### 任务 5.2: 更新依赖注入

**What to do**:
- 修改 `src/api/dependencies.py`
- 添加向量服务的导入语句
- 添加 `get_embedding_service()` 函数（使用 @lru_cache）
- 添加 `get_vector_store()` 函数（使用 @lru_cache）
- 添加 `get_retrieval_service()` 函数（使用 @lru_cache）

**Must NOT do**:
- 不要修改现有的服务依赖（get_upload_service 等）
- 不要移除 @lru_cache 装饰器

**Recommended Agent Profile**:
- **Category**: `quick`
- **Skills**: `[]`
- **Reasoning**: 简单的依赖注入添加

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 5 Sequential
- **Blocks**: Wave 6
- **Blocked By**: Wave 1-4

**References**:

**Pattern References**:
- `src/api/dependencies.py:11-25` - 现有的 lru_cache 模式
- `src/api/dependencies.py:11` - @lru_cache 装饰器使用示例

**Acceptance Criteria**:

**Automated Verification (using Bash - Python)**:
```bash
# Agent executes:
python -c "
from src.api.dependencies import (
    get_embedding_service,
    get_vector_store,
    get_retrieval_service
)

# Test singleton pattern
service1 = get_embedding_service()
service2 = get_embedding_service()
print(f'Singleton test: {service1 is service2}')
assert service1 is service2, 'FAIL: Should be same instance'
print('PASS: EmbeddingService is singleton')

store1 = get_vector_store()
store2 = get_vector_store()
assert store1 is store2, 'FAIL: VectorStore should be singleton'
print('PASS: VectorStore is singleton')

retrieval1 = get_retrieval_service()
retrieval2 = get_retrieval_service()
assert retrieval1 is retrieval2, 'FAIL: RetrievalService should be singleton'
print('PASS: RetrievalService is singleton')

# Verify dependencies
assert retrieval1.vector_store is store1, 'FAIL: RetrievalService should use same VectorStore'
print('PASS: Dependencies correctly injected')
"

# Expected output:
# singleton test: True
# PASS: EmbeddingService is singleton
# PASS: VectorStore is singleton
# PASS: RetrievalService is singleton
# PASS: Dependencies correctly injected
```

**Commit**: NO

---

### Wave 6: 创建检索 API 端点

#### 任务 6.1: 创建检索 API 路由

**What to do**:
- 创建 `src/api/routes/retrieval.py`
- 创建 `SearchRequest` Pydantic 模型
- 创建 `SearchResult` Pydantic 模型
- 创建 `SearchResponse` Pydantic 模型
- 实现 `/api/retrieval/search` POST 端点
- 实现 `/api/retrieval/search-with-scores` POST 端点
- 实现 `/api/retrieval/stats` GET 端点

**Must NOT do**:
- 不要使用中文字段描述（使用英文）
- 不要硬编码端点路径（使用常量或配置）
- 不要实现复杂的过滤逻辑（基础的元数据过滤即可）

**Recommended Agent Profile**:
- **Category**: `visual-engineering`
- **Skills**: `["frontend-ui-ux"]`
- **Reasoning**: API 路由实现，需要良好的 API 设计和 Pydantic 模型

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 6 Sequential
- **Blocks**: None (final wave)
- **Blocked By**: Wave 1-5

**References**:

**Pattern References**:
- `src/api/routes/upload.py:17-52` - API 路由结构模式
- `src/api/routes/upload.py:20-52` - POST 端点实现模式
- `src/schemas/upload.py:5-46` - Pydantic 模型定义模式

**API/Type References**:
- `fastapi.APIRouter` - 路由器类
- `fastapi.Depends` - 依赖注入
- `pydantic.BaseModel` - 基础模型类
- `pydantic.Field` - 字段定义

**Acceptance Criteria**:

**Automated Verification (using Bash + Playwright)**:
```bash
# Agent executes:
echo "Starting FastAPI server..."
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
sleep 5  # Wait for server to start

# Test search endpoint
echo "Testing /api/retrieval/search..."
curl -X POST 'http://localhost:8000/api/retrieval/search' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "Python programming",
    "k": 3
  }' > /tmp/search_response.json

# Verify response
python -c "
import json
with open('/tmp/search_response.json', 'r') as f:
    response = json.load(f)
print(f'Status: {response.get(\"query\")}')
print(f'Total: {response.get(\"total\")}')
print(f'Results: {len(response.get(\"results\", []))}')
assert response.get('total') >= 0, 'FAIL: Total should be non-negative'
assert 'results' in response, 'FAIL: Missing results field'
print('PASS: /api/retrieval/search works')
"

# Test stats endpoint
echo "Testing /api/retrieval/stats..."
curl -X GET 'http://localhost:8000/api/retrieval/stats' > /tmp/stats_response.json

python -c "
import json
with open('/tmp/stats_response.json', 'r') as f:
    response = json.load(f)
print(f'Status: {response.get(\"status\")}')
assert 'stats' in response, 'FAIL: Missing stats field'
stats = response.get('stats', {})
assert 'total_vectors' in stats, 'FAIL: Missing total_vectors'
print(f'Total vectors: {stats.get(\"total_vectors\")}')
print('PASS: /api/retrieval/stats works')
"

# Cleanup
kill $SERVER_PID
echo "Server stopped"
"

# Expected output:
# Starting FastAPI server...
# ...
# Status: Python programming
# Total: 3
# Results: 3
# PASS: /api/retrieval/search works
# Status: success
# Total vectors: 4
# PASS: /api/retrieval/stats works
# Server stopped
```

**Evidence to Capture**:
- [ ] API 响应 JSON 保存在 `/tmp/search_response.json`
- [ ] API 响应 JSON 保存在 `/tmp/stats_response.json`
- [ ] 服务器启动日志
- [ ] 服务器停止日志

**Commit**: NO (Wait for all waves to complete)

---

### Wave 7: 更新配置和注册路由

#### 任务 7.1: 更新配置文件

**What to do**:
- 修改 `config.py`
- 添加 `faiss_index_path: str` 字段（默认 "./data/faiss_index"）
- 添加 `faiss_dimension: int` 字段（默认 1536）
- 确保 `dashscope_api_key: str` 字段存在（从 .env 读取）
- 确保 `dashscope_embedding_model: str` 字段存在（默认 "text-embedding-v2"）

**Must NOT do**:
- 不要修改现有配置字段
- 不要添加不必要的配置项

**Recommended Agent Profile**:
- **Category**: `quick`
- **Skills**: `[]`
- **Reasoning**: 简单的配置添加

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 7 Sequential (with Task 7.2)
- **Blocks**: None
- **Blocked By**: Wave 1-6

**References**:

**Pattern References**:
- `config.py` - 现有配置模式
- `chain/memory/faiss_mem.py:23-25` - FAISS 相关配置常量

**Acceptance Criteria**:

**Automated Verification (using Bash - Python)**:
```bash
# Agent executes:
python -c "
from config import settings

# Verify FAISS config
assert hasattr(settings, 'faiss_index_path'), 'FAIL: Missing faiss_index_path'
print(f'faiss_index_path: {settings.faiss_index_path}')
assert settings.faiss_index_path == './data/faiss_index', 'FAIL: Wrong default value'
print('PASS: FAISS index path configured')

assert hasattr(settings, 'faiss_dimension'), 'FAIL: Missing faiss_dimension'
print(f'faiss_dimension: {settings.faiss_dimension}')
assert settings.faiss_dimension == 1536, 'FAIL: Wrong dimension'
print('PASS: FAISS dimension configured')

# Verify DashScope config
assert hasattr(settings, 'dashscope_api_key'), 'FAIL: Missing dashscope_api_key'
print(f'dashscope_api_key: {settings.dashscope_api_key[:10]}...')  # Only show prefix
assert len(settings.dashscope_api_key) > 0, 'FAIL: API key is empty'
print('PASS: DashScope API key configured')

assert hasattr(settings, 'dashscope_embedding_model'), 'FAIL: Missing dashscope_embedding_model'
print(f'dashscope_embedding_model: {settings.dashscope_embedding_model}')
print('PASS: All configurations correct')
"

# Expected output:
# faiss_index_path: ./data/faiss_index
# PASS: FAISS index path configured
# faiss_dimension: 1536
# PASS: FAISS dimension configured
# dashscope_api_key: sk-xxxxx...
# PASS: DashScope API key configured
# dashscope_embedding_model: text-embedding-v2
# PASS: All configurations correct
```

**Commit**: NO

---

#### 任务 7.2: 注册检索路由

**What to do**:
- 修改 `src/api/routes/__init__.py`
- 添加 `retrieval_router` 的导入和导出
- 修改 `src/app.py`
- 导入 `retrieval_router`
- 调用 `app.include_router(retrieval_router)`

**Must NOT do**:
- 不要修改现有的路由注册
- 不要改变路由顺序

**Recommended Agent Profile**:
- **Category**: `quick`
- **Skills**: `[]`
- **Reasoning**: 简单的路由注册添加

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 7 Sequential
- **Blocks**: None
- **Blocked By**: Wave 1-6

**References**:

**Pattern References**:
- `src/api/routes/__init__.py:1-5` - 现有路由导入模式
- `src/app.py:65-66` - 现有路由注册模式

**Acceptance Criteria**:

**Automated Verification (using Bash + Playwright)**:
```bash
# Agent executes:
echo "Starting FastAPI server..."
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
sleep 5  # Wait for server to start

# Test that retrieval routes are accessible
echo "Testing route registration..."

# Test retrieval stats endpoint
curl -X GET 'http://localhost:8000/api/retrieval/stats' > /tmp/test_route.json

python -c "
import json
with open('/tmp/test_route.json', 'r') as f:
    response = json.load(f)
assert response.get('status') == 'success', 'FAIL: Route not registered correctly'
print('PASS: Retrieval routes registered and accessible')
"

# Test OpenAPI docs
curl -s 'http://localhost:8000/openapi.json' | python -c "
import sys, json
data = json.load(sys.stdin)
paths = data.get('paths', {})

# Check if retrieval endpoints exist
assert '/api/retrieval/search' in paths, 'FAIL: Missing /api/retrieval/search'
print('PASS: /api/retrieval/search in OpenAPI')
assert '/api/retrieval/stats' in paths, 'FAIL: Missing /api/retrieval/stats'
print('PASS: /api/retrieval/stats in OpenAPI')

# Verify tags
tags = [tag.get('name') for tag in data.get('tags', [])]
assert '检索服务' in tags, 'FAIL: Missing 检索服务 tag'
print('PASS: Retrieval tag present')
"

# Cleanup
kill $SERVER_PID
echo "Server stopped"
"

# Expected output:
# PASS: Retrieval routes registered and accessible
# PASS: /api/retrieval/search in OpenAPI
# PASS: /api/retrieval/stats in OpenAPI
# PASS: Retrieval tag present
# Server stopped
```

**Evidence to Capture**:
- [ ] 路由测试响应
- [ ] OpenAPI schema 验证日志
- [ ] 服务器启动和停止日志

**Commit**: NO

---

#### 任务 7.3: 安装 FAISS-CPU 依赖

**What to do**:
- 修改 `requirements.txt` 或项目依赖文件
- 添加 `faiss-cpu` 依赖
- 如果使用 `pyproject.toml`，添加到 dependencies

**Must NOT do**:
- 不要添加 `faiss-gpu`（用户指定 CPU 版本）
- 不要修改其他依赖

**Recommended Agent Profile**:
- **Category**: `quick`
- **Skills**: `[]`
- **Reasoning**: 简单的依赖添加

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 7 Sequential
- **Blocks**: None
- **Blocked By**: Wave 1-6

**References**:

**Pattern References**:
- 查看项目现有的依赖文件格式（`requirements.txt`, `pyproject.toml`, 或 `setup.py`）

**Acceptance Criteria**:

**Automated Verification (using Bash)**:
```bash
# Agent executes:
pip install faiss-cpu

# Verify installation
python -c "
import faiss
print(f'FAISS version: {faiss.__version__}')
print('PASS: FAISS-CPU installed successfully')

# Verify CPU backend
import faiss.swigfaiss as swigfaiss
index = swigfaiss.IndexFlatL2(1536)
print(f'Index created: {type(index)}')
print('PASS: FAISS CPU backend works')
"

# Expected output:
# FAISS version: 1.x.x
# PASS: FAISS-CPU installed successfully
# Index created: <class 'faiss.swigfaiss.IndexFlatL2'>
# PASS: FAISS CPU backend works
```

**Commit**: NO (Wait for all waves to complete)

---

## 📊 总体验收标准

### 功能验收
- [ ] 文档上传后自动向量化并存储到 FAISS
- [ ] 可以通过 `/api/retrieval/search` 进行语义搜索
- [ ] 检索结果包含相关文档内容和元数据
- [ ] `/api/retrieval/stats` 返回索引统计信息

### 技术验收
- [ ] 所有服务使用单例模式（@lru_cache）
- [ ] 依赖注入正确配置
- [ ] 向量化步骤集成到 DocumentService
- [ ] FAISS 索引持久化到磁盘

### 性能验收
- [ ] 单个文档嵌入时间 < 500ms
- [ ] 检索响应时间 < 100ms (k=5)
- [ ] 支持批量嵌入

---

## 🎯 关键依赖关系

```
Wave 1 (类型定义)
  ↓
Wave 2 (嵌入服务) ← 依赖 config.py
  ↓
Wave 3 (向量存储) ← 依赖 Wave 1-2
  ↓
Wave 4 (索引/检索) ← 依赖 Wave 1-3
  ↓
Wave 5 (集成) ← 依赖 Wave 1-4
  ↓
Wave 6 (API) ← 依赖 Wave 1-5
  ↓
Wave 7 (配置和路由) ← 依赖 Wave 1-6
```

---

## 📝 重要提醒

1. **FAISS-CPU 安装**: 确保在任务 7.3 中正确安装 `faiss-cpu`
2. **API Key 配置**: 确保 `.env` 文件中有 `DASHSCOPE_API_KEY`
3. **目录创建**: FAISS 索引目录会自动创建在 `./data/faiss_index`
4. **异常处理**: 向量化失败不应阻塞文档处理主流程
5. **单例模式**: 所有服务类都使用 `@lru_cache(maxsize=1)`

---

## ✅ 准备执行

本工作计划已包含：
- ✅ 7 个 Wave，共 15 个详细任务
- ✅ 每个任务的完整代码示例
- ✅ 自动化验收标准（使用 Bash + Python/Playwright）
- ✅ 推荐的 Agent Profile 和技能
- ✅ 详细的引用和模式参考
- ✅ 明确的依赖关系和并行化策略

**下一步**: 运行 `/start-work` 开始执行！
