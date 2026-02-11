# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 提供项目指导。

## 项目概述

这是一个 **RAG (检索增强生成) 服务** - 面向环保合规检查的智能客服系统。支持文档上传、OCR处理、向量化、语义搜索和基于中国国家标准的自动化合规验证。

**技术栈：**
- **后端**: FastAPI (Python 3.8+), SQLAlchemy 异步 MySQL, FAISS 向量存储
- **前端**: React 18 + TypeScript, Vite, Monaco Editor, Tailwind CSS
- **LLM/嵌入**: OpenAI (gpt-3.5-turbo), DashScope (text-embedding-v2, 通义千问系列)
- **OCR**: PaddleOCR (远程 API), Tesseract (本地回退)
- **认证**: JWT + 可选 API 密钥认证
- **高级检索**: BM25 (rank-bm25), HyDE, Query2Doc, Reranker (sentence-transformers)
- **任务调度**: APScheduler 后台归档任务
- **中文 NLP**: jieba 分词
- **容器化**: Docker, Kubernetes
- **监控**: Prometheus, Grafana, OpenTelemetry, Jaeger
- **企业特性**: 多租户, RBAC权限系统, 审计日志

## 开发命令

### 后端

```bash
# 开发模式
pip install -r requirements.txt
python -m uvicorn src.app:app --reload --host 0.0.0.0 --port 8000

# 或使用脚本
./start.sh          # 开发服务器
./start-prod.sh     # 生产服务器
./stop.sh           # 停止服务
./restart.sh        # 重启服务
./status.sh         # 检查状态

# 测试
pytest                           # 所有测试
pytest tests/test_api.py         # 特定测试
pytest --cov=src                 # 覆盖率测试
```

### 前端

```bash
cd frontend
npm install
npm run dev        # 开发服务器 (localhost:3000)
npm run build      # 生产构建
npm run lint       # ESLint
```

### 部署

```bash
# Docker 部署
./deploy-v2.sh build     # 构建镜像
./deploy-v2.sh compose   # 启动 docker-compose
./deploy-v2.sh k8s       # 部署到 Kubernetes

# 数据库迁移
python migrations/002_create_rbac_tables.py

# 初始化 RBAC
python scripts/init_rbac.py
```

## 架构

### 分层架构

系统遵循清晰的分层架构：

```
API 层 (src/api/routes/)
    ↓
服务层 (src/service/)
    ↓
管道/处理层 (src/pipeline/, src/extractor/)
    ↓
向量/数据层 (src/vector/, src/models/)
```

### 核心组件

1. **文档处理管道** (`src/pipeline/document_processor.py`)
   - 所有文档处理的入口点
   - 编排: 提取 → OCR → 分块 → 向量化 → 存储
   - 通过传递给 `__init__()` 的配置字典进行配置

2. **服务** (`src/service/`)
   - 所有服务通过 `src/api/dependencies.py` 中的 `@lru_cache(maxsize=1)` 实现单例
   - `UploadService`: 文件验证，处理编排
   - `DocumentService`: 通过管道处理文档
   - `VectorService`: 通过 DocumentIndexer 进行文档索引
   - `MarkdownService`: Markdown 文件 CRUD 操作
   - `ComplianceService`: 环保法规检查
   - `RBACService`: 角色权限管理
   - `StorageService`: 存储抽象层（本地/OSS）

3. **向量组件** (`src/vector/`)
   - `EmbeddingService`: DashScope 文本嵌入 (1536 维)
   - `FAISSVectorStore`: 传统 FAISS 索引，软删除（遗留）
   - `OptimizedFAISSVectorStore`: 自适应索引选择 (Flat/IVF/IVF-PQ/HNSW)
   - `GenerationalIndexStore`: Hot/Cold 架构，支持物理删除
   - `ChromaVectorStore`: ChromaDB 向量存储实现
   - `MilvusVectorStore`: Milvus 分布式向量存储实现
   - `DocumentIndexer`: 文档索引和元数据追踪
   - `RetrievalService`: 传统语义搜索
   - `EnhancedRetrievalService`: 集成 Reranker 的高级检索

4. **检索策略** (`src/retrieval/strategies/`)
   - `VectorRetrievalStrategy`: 纯向量相似度搜索
   - `HybridRetrievalStrategy`: 向量 + BM25 融合
   - `ParentChildRetrievalStrategy`: 父子分块检索
   - `HyDEStrategy`: 假设文档嵌入
   - `Query2DocStrategy`: 查询扩展 + RRF 融合
   - `DecompositionStrategy`: 复杂查询分解

5. **Memory 管理** (`src/memory/`)
   - `ConversationMemory`: 对话历史管理
   - `MemoryManager`: 统一 Memory 管理器
   - 支持自动总结、token 限制、会话隔离

6. **依赖注入** (`src/api/dependencies.py`)
   - 所有服务使用 FastAPI 的 `Depends()` 在此处连接
   - 三层向量存储选择: 分代索引 > 优化版 > 传统版
   - 通过 `enable_enhanced_retrieval` 标志启用增强检索服务
   - 循环导入处理: 函数内部本地导入

7. **中间件** (`src/middleware/`)
   - `TenantMiddleware`: 多租户上下文注入
   - `RBACAuthMiddleware`: 认证和权限检查
   - `PerformanceMiddleware`: 性能监控
   - `TelemetryMiddleware`: OpenTelemetry 链路追踪

### 数据流

```
用户上传 → UploadService.validate_file()
    ↓
UploadService.process_upload()
    ↓
DocumentService.process_document() → DocumentProcessingPipeline
    ↓
    ├─ Extractor (PDF/Word/OCR via src/extractor/)
    ├─ Chunker (AdaptiveChunker 多种策略)
    └─ VectorService.vectorize_document()
        ↓
        ├─ EmbeddingService.embed_documents()
        └─ FAISSVectorStore.add_documents()
```

## 配置

所有配置集中在 `config.py` 中使用 Pydantic Settings：
- 从 `.env` 文件加载环境变量
- 类型安全，带验证
- 初始化时自动创建所需目录

### 关键环境变量

```bash
# 必需配置
DASHSCOPE_API_KEY=your_key
OPENAI_API_KEY=your_key
SECRET_KEY=your_jwt_secret

# 数据库 (MySQL + SQLAlchemy async)
DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/rag_service
# 或独立的 MYSQL_* 变量

# OCR (远程 PaddleOCR API)
OCR_API_ENDPOINT=https://api.example.com/ocr
OCR_API_KEY=your_key
OCR_ENGINE=PP-OCRv5

# 多租户配置
ENABLE_MULTI_TENANT=true
TENANT_IDENTIFICATION=header
TENANT_HEADER_NAME=X-Tenant-ID

# RBAC 配置
ENABLE_RBAC=true
ENABLE_AUDIT_LOG=true
AUDIT_LOG_RETENTION_DAYS=90
```

### 重要设置

#### 向量存储配置
- `faiss_index_path`: "./data/faiss_index" - FAISS 向量存储路径
- `enable_generational_index`: 启用 Hot/Cold 分代索引架构
- `faiss_index_auto_select`: 启用自适应索引选择
- `faiss_index_type`: 强制指定索引类型 ("flat" | "ivf" | "ivf_pq" | "hnsw")

#### 文档处理配置
- `processed_dir`: "./output_dir" - OCR markdown 输出路径
- `upload_dir`: "./data/uploads" - 原始文件存储路径
- `chunking_strategy`: "hybrid" | "recursive" | "semantic" | "tabular"
- `pdf_parse_mode`: "text_layer" | "full_ocr" (影响提取策略)

#### 检索层配置
- `enable_enhanced_retrieval`: 使用 EnhancedRetrievalService
- `enable_reranker_by_default`: 默认启用 Reranker
- `enable_bm25`: 启用 BM25 关键词索引
- `retrieval_strategy`: 选择检索策略
- `enable_advanced_strategies`: 启用 HyDE 和 Query2Doc 策略

#### Memory 配置
- `enable_conversation_memory`: 启用对话记忆
- `conversation_max_messages`: 最大消息数量
- `conversation_max_tokens`: 最大 token 数
- `enable_summarization`: 启用自动总结

### FAISS 索引优化
- `faiss_index_auto_select`: 根据数据规模启用自适应索引选择
- `faiss_index_type`: 强制指定索引类型
- `faiss_index_config`: 每种索引类型的详细参数
  - 自动选择阈值: <10K→Flat, 10K-100K→IVF, 100K-1M→IVF-PQ, >1M→HNSW

### 分代索引 (Hot/Cold 架构)
- `enable_generational_index`: 启用 Hot/Cold 索引架构
- `hot_index_max_size`: 归档前 Hot 索引最大向量数
- `hot_index_type`: Hot 索引类型 (推荐 IVFPQ)
- `cold_index_type`: Cold 索引类型 (HNSW 用于读优化归档)
- `archive_age_days`: 文档归档到 Cold 索引前的天数
- `archive_schedule`: 归档任务的 Cron 调度

## API 结构

所有路由在 `src/api/routes/` 中：
- `/api/upload/` - 单个/批量文件上传
- `/api/retrieval/search` - 语义搜索
- `/api/compliance/check` - 环保合规检查
- `/api/markdown/` - Markdown 文件管理 (OCR 输出)
- `/api/auth/` - JWT 认证
- `/api/storage/` - 存储操作 (本地/OSS)
- `/api/maintenance/` - 索引维护和归档操作
- `/api/index_optimization/` - FAISS 索引优化控制
- `/api/admin/` - 管理员接口 (需要 RBAC 权限)
- `/api/tenant/` - 多租户管理
- `/api/memory/` - 对话记忆管理
- `/health/` - 健康检查
- `/metrics` - Prometheus 指标

FastAPI 自动文档: `http://localhost:8000/docs`

## 数据库

- **ORM**: SQLAlchemy 异步支持 (aiomysql)
- **模型**: `src/models/model.py` - SQLAlchemy 模型
- **RBAC 模型**: `src/models/rbac.py` - 角色权限模型
- **租户模型**: `src/models/tenant.py` - 多租户模型
- **Schema**: `src/schemas/` - Pydantic 请求/响应模型
- **向量存储**: FAISS (磁盘持久化)

## 容器化部署

### Docker 部署

```bash
# 构建镜像
docker build -t rag-service:latest .

# 运行容器
docker run -p 8000:8000 --env-file .env rag-service:latest
```

### Docker Compose

```bash
# 启动完整服务栈 (包括 MySQL, Redis, Prometheus, Grafana, Jaeger)
./deploy-v2.sh compose

# 查看日志
docker-compose logs -f rag-service

# 停止服务
./deploy-v2.sh stop
```

### Kubernetes 部署

```bash
# 部署到 Kubernetes
./deploy-v2.sh k8s

# 查看状态
kubectl get pods -n rag-service

# 查看日志
kubectl logs -f deployment/rag-service -n rag-service
```

### 部署架构

- **副本数**: 3 个 Pod (可配置 HPA 2-10)
- **资源限制**: 500m CPU, 1Gi RAM 请求; 2 CPU, 4Gi RAM 限制
- **健康检查**: `/health` 端点
- **持久化**: PVC 挂载到 `/app/data`
- **配置**: ConfigMap + Secret

## 监控和可观测性

### Prometheus 指标

系统内置自定义 Prometheus 指标：

- **HTTP 请求**: `http_requests_total`, `http_request_duration_seconds`
- **文档处理**: `document_processing_duration_seconds`, `documents_processed_total`
- **检索性能**: `search_duration_seconds`, `retrieval_relevance_score`
- **Reranker**: `reranker_requests_total`, `reranker_score_delta`
- **向量存储**: `faiss_index_size`, `hot_index_size`, `cold_index_size`
- **系统资源**: CPU, 内存, 磁盘使用

访问指标: `http://localhost:9090` (Prometheus)

### Grafana 仪表板

预配置仪表板位于 `monitoring/grafana/dashboards/`：
- **RAG Service Overview**: 服务概览、QPS、延迟、错误率
- **Retrieval Quality**: 检索质量监控
- **System Resources**: 系统资源监控

访问仪表板: `http://localhost:3000` (默认 admin/admin)

### OpenTelemetry 链路追踪

- **Jaeger**: 分布式链路追踪
- **自动插桩**: FastAPI, HTTPX, SQLAlchemy
- **手动追踪**: `TraceOperation` 上下文管理器

访问 Jaeger UI: `http://localhost:16686`

### 告警规则

告警规则位于 `monitoring/alerts/rag-service-alerts.yml`：
- 服务可用性告警
- 错误率告警
- 延迟告警
- 资源使用告警
- 业务指标告警

## 特殊模式

### 服务单例模式

所有服务使用 `@lru_cache(maxsize=1)` 实现单例行为：
```python
@lru_cache(maxsize=1)
def get_upload_service() -> UploadService:
    vector_service = get_vector_service()
    return UploadService(get_settings(), vector_service)
```

### 异步管道

文档处理完全异步：
- OCR 调用是异步的
- 文件 I/O 使用 `aiofiles`
- 数据库查询通过 SQLAlchemy 异步执行

### OCR 策略
- **主要方式**: 远程 PaddleOCR API（可配置端点）
- **回退方式**: 本地 Tesseract（如果 `fallback_to_cloud=True`）
- **置信度过滤**: 低于 `ocr_confidence_threshold` 的结果被丢弃

### 分块策略

通过 `AdaptiveChunker` 支持多种策略：
- `hybrid`: 组合 recursive, tabular, fixed, semantic
- `recursive`: LangChain RecursiveCharacterTextSplitter
- `tabular`: 保留表格结构
- `semantic`: LlamaIndex 语义分块
- `fixed`: 固定大小分块

### Markdown 编辑器
- OCR 输出保存为 `processed_dir` 中的 Markdown 文件
- 通过 `/api/markdown/` 端点提供
- 前端使用 Monaco Editor 进行编辑
- 文件按 `filename` 索引（从原始文件名派生）

### 高级检索功能

**BM25 索引管理器** (`src/retrieval/bm25_index_manager.py`):
- 使用 jieba 分词从向量存储自动构建
- 支持与向量存储变更的增量同步
- pickle 序列化的持久化磁盘存储
- 用于混合检索（向量 + 关键词融合）

**HyDE 策略** (`src/retrieval/strategies/hyde_strategy.py`):
- 使用 LLM 生成假设文档
- 向量化假设文档以获得更好的语义匹配
- 适合问答类查询（"什么是...?"）
- 需要 LLM 服务（DashScope/OpenAI）

**Query2Doc 策略** (`src/retrieval/strategies/query2doc_strategy.py`):
- 使用 LLM 将查询扩展为多个相关查询
- 对每个查询执行并行检索
- 使用倒数排名融合 (RRF) 融合结果
- 适合模糊或短查询

**Decomposition 策略** (`src/retrieval/strategies/decomposition_strategy.py`):
- 将复杂查询分解为多个子问题
- 并行检索每个子问题的结果
- 整合和去重返回最终结果
- 适合多步骤推理查询（"比较 A 和 B 的优缺点"）

**Reranker** (`src/retrieval/reranker.py`):
- 用于结果重排序的交叉编码器模型
- 默认模型: BAAI/bge-reranker-large
- 延迟初始化以减少启动开销
- 集成到 EnhancedRetrievalService

### 向量存储选择优先级

系统自动选择最佳向量存储实现：

1. **GenerationalIndexStore** (如果 `enable_generational_index=True`)
   - Hot Index: IVF-PQ，支持物理删除
   - Cold Index: HNSW，用于归档数据（>30 天）
   - Hot + Cold 结果的 RRF 融合

2. **OptimizedFAISSVectorStore** (如果 `faiss_index_auto_select=True` 或 `faiss_index_type != "flat"`)
   - 根据数据规模自动选择索引类型
   - 性能监控和升级建议

3. **FAISSVectorStore** (默认，传统)
   - IndexFlatL2 暴力搜索
   - 通过 deleted_ids 追踪实现软删除

4. **ChromaVectorStore** (通过配置选择)
   - 持久化存储（DuckDB + Parquet）
   - 内置元数据过滤
   - 自动持久化，无需手动保存

5. **MilvusVectorStore** (通过配置选择)
   - 分布式架构支持
   - IVF_FLAT 索引默认
   - 表达式过滤

### Vector Store 抽象

通过 `BaseVectorStore` 接口统一访问不同向量存储：
- `add_documents()`: 添加文档
- `search()`: 相似度搜索
- `search_with_score()`: 带分数的搜索
- `delete_documents()`: 删除文档
- `update_document()`: 更新文档
- `count_documents()`: 统计文档数

工厂模式创建：`VectorStoreFactory.create()`

## 多租户支持

### 租户识别

系统支持三种租户识别方式：
1. **HTTP Header**: `X-Tenant-ID` (默认)
2. **子域名**: `tenant.yourdomain.com`
3. **查询参数**: `?tenant_id=xxx`

### 租户隔离级别

- **行级隔离**: 通过 `tenant_id` 字段过滤数据（默认）
- **Schema 隔离**: 每个租户独立数据库 Schema（未来支持）
- **数据库隔离**: 每个租户独立数据库（未来支持）

### 配额管理

每个租户可配置配额：
- API 调用限制
- 文档上传数量
- 存储空间限制
- 检索 QPS 限制

### 中间件

`TenantMiddleware` 自动：
- 从请求中提取租户 ID
- 注入到请求状态 (`request.state.tenant_id`)
- 追踪 API 调用用于配额强制
- 跳过公开端点

## RBAC 权限系统

### 角色定义

**系统级角色**：
- `system:admin`: 系统管理员 - 所有权限
- `system:operator`: 系统操作员 - 监控和只读权限

**租户级角色**：
- `tenant:owner`: 租户所有者 - 租户内所有权限
- `tenant:admin`: 租户管理员 - 租户管理权限
- `tenant:member`: 租户成员 - 基本权限

### 权限定义

19 个细粒度权限：
- **文档操作**: `document:create`, `document:read`, `document:update`, `document:delete`
- **检索操作**: `search:execute`, `search:advanced`
- **合规检查**: `compliance:execute`
- **用户管理**: `user:create`, `user:read`, `user:update`, `user:delete`, `user:assign_role`
- **租户管理**: `tenant:read`, `tenant:update`, `tenant:delete`
- **系统管理**: `system:admin`, `system:monitor`

### 使用示例

```python
from fastapi import Depends
from src.api.rbac_dependencies import require_document_read, require_document_delete

@app.get("/api/documents/{doc_id}")
async def get_document(
    doc_id: str,
    _: bool = Depends(require_document_read())
):
    # 只有拥有 document:read 权限的用户才能访问
    ...

@app.delete("/api/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    _: bool = Depends(require_document_delete())
):
    # 只有拥有 document:delete 权限的用户才能访问
    ...
```

### 审计日志

所有敏感操作自动记录：
- 用户操作（登录、登出）
- 权限变更
- 数据访问
- 配置修改

日志包含：
- 用户 ID、租户 ID
- 操作类型、资源类型、资源 ID
- 操作结果、错误信息
- IP 地址、User Agent
- 请求 ID（链路追踪）
- 变更前后的值

## Memory 管理

### 对话记忆

`ConversationMemory` 提供对话历史管理：
- 按 `conversation_id` 隔离会话
- Token 限制强制执行
- 自动总结（超过阈值时）
- 消息搜索功能

### Memory Manager

统一管理多种 Memory 类型：
- **CONVERSATION**: 对话历史（当前支持）
- **SHORT_TERM**: 短期记忆（Redis，未来支持）
- **LONG_TERM**: 长期记忆（向量数据库，未来支持）
- **EPISODIC**: 情景记忆（未来支持）
- **SEMANTIC**: 语义记忆（未来支持）

### 使用示例

```python
from src.api.dependencies import get_memory_manager

memory_manager = get_memory_manager()

# 添加对话消息
await memory_manager.add_conversation_message(
    content="用户的问题",
    role="user",
    conversation_id="conv_123",
    user_id="user_456"
)

# 获取对话历史
history = await memory_manager.get_conversation_history(
    conversation_id="conv_123",
    limit=10
)

# 搜索对话
results = await memory_manager.search_conversations(
    query="环保标准",
    conversation_id="conv_123",
    k=5
)
```

## 熔断和重试

### 熔断器

防止级联故障：
```python
from src.utils.resilience import CircuitBreaker, circuit_breaker

@circuit_breaker(failure_threshold=5, recovery_timeout=60)
async def call_external_api():
    ...
```

### 重试策略

多种退避策略：
- **FIXED**: 固定延迟
- **LINEAR**: 线性增长
- **EXPONENTIAL**: 指数退避
- **FIBONACCI**: 斐波那契序列

```python
from src.utils.resilience_retry import retry, async_retry

@async_retry(max_attempts=3, backoff="exponential", base_delay=1)
async def call_with_retry():
    ...
```

### 超时控制

```python
from src.utils.resilience_retry import timeout, async_timeout

@async_timeout(timeout_seconds=30)
async def operation_with_timeout():
    ...
```

### 服务降级

```python
from src.utils.resilience_retry import FallbackResult

result = await service.call_with_fallback(
    primary=primary_operation,
    fallback=fallback_operation,
    fallback_result=FallbackResult(value="默认值")
)
```

## 测试

- **后端**: `tests/` 目录中的 pytest
- **前端**: npm test（单元测试）, npm run test:e2e（E2E 测试）
- 测试文件镜像源结构: `tests/test_api.py`, `tests/test_compliance.py`

### 集成测试

最近的优化添加包括全面的集成测试：

- **test_generational_index.py**: 测试 Hot/Cold 索引架构 (6/6 测试)
  - 路由表操作
  - Hot 索引物理删除
  - Cold 索引归档
  - RRF 融合

- **test_faiss_optimization.py**: 测试自适应索引选择 (5/5 测试)
  - 索引类型选择逻辑
  - 索引类型间的在线迁移
  - 性能监控

- **test_retrieval_optimization.py**: 测试检索层增强 (7/7 测试)
  - BM25 索引构建和搜索
  - HyDE 和 Query2Doc 策略
  - EnhancedRetrievalService 与 Reranker
  - 策略自动选择
  - RRF 融合算法

## 常见陷阱

1. **循环导入**: `src/api/dependencies.py` 中的服务使用本地导入避免循环依赖
2. **FAISS 反序列化**: 加载 FAISS 索引需要 `allow_dangerous_deserialization=True`
3. **异步数据库**: 使用 `async with session:` 进行数据库操作
4. **文件上传验证**: `UploadService.validate_file()` 中验证文件类型和大小
5. **OCR 输出路径**: Markdown 文件保存到 `processed_dir`，不是 `upload_dir`
6. **中文语言**: 所有 UI 文本为中文，但代码/API 响应为英文
7. **向量维度**: 必须使用 DashScope v2（1536 维），不是 v3（384 维）
8. **FAISS IDRemover**: 并非所有 FAISS 版本都可用；HotIndex 有软删除回退
9. **BM25 get_top_n()**: 返回文档内容，不是元组；分数需要单独计算
10. **OpenMP 警告**: 多个 OpenMP 运行时可能导致警告；如需要设置 `KMP_DUPLICATE_LIB_OK=TRUE`
11. **向量存储兼容性**: 代码必须处理直接 FAISS 和包装的 FAISSVectorStore 结构
12. **租户隔离**: 查询数据库时必须添加 `tenant_id` 过滤条件
13. **权限检查**: 所有受保护的端点必须使用 RBAC 依赖注入
14. **审计日志**: 敏感操作必须记录审计日志
15. **Memory 过期**: 长时间运行的对话会触发总结，可能丢失细节

## 文件组织

```
src/
├── api/
│   ├── routes/                 # API 端点
│   │   ├── upload.py           # 文件上传端点
│   │   ├── retrieval.py        # 搜索端点
│   │   ├── compliance.py       # 合规检查
│   │   ├── markdown.py         # Markdown 文件管理
│   │   ├── auth.py             # JWT 认证
│   │   ├── storage.py          # 存储操作 (本地/OSS)
│   │   ├── maintenance.py      # 索引维护和归档
│   │   ├── index_optimization.py # FAISS 优化控制
│   │   ├── admin.py            # 管理员接口
│   │   └── tenant.py           # 多租户管理
│   ├── dependencies.py         # 服务 DI 容器（关键）
│   └── rbac_dependencies.py    # RBAC 依赖注入
├── service/                    # 业务逻辑层
│   ├── llm_service.py          # LLM 服务包装器
│   ├── storage_service.py      # 存储抽象 (本地/OSS)
│   ├── upload_service.py       # 文件上传编排
│   ├── document_service.py     # 文档处理
│   ├── vector_service.py       # 文档索引
│   ├── markdown_service.py     # Markdown CRUD 操作
│   ├── rbac_service.py         # RBAC 权限服务
│   └── memory_manager.py       # Memory 管理
├── vector/
│   ├── base.py                 # 向量存储基础接口
│   ├── embed_service.py        # DashScope 嵌入 (1536d)
│   ├── vector_store.py         # 传统 FAISS (软删除)
│   ├── optimized_faiss_store.py # 自适应索引选择
│   ├── generational_index_store.py # Hot/Cold 架构
│   ├── chroma_store.py         # ChromaDB 实现
│   ├── milvus_store.py         # Milvus 实现
│   ├── adaptive_index_selector.py # 自动索引类型选择
│   ├── index_migrator.py       # 在线索引迁移
│   ├── routing_table.py        # doc_id → 索引映射 (Hot/Cold)
│   ├── hot_faiss_index.py      # Hot 索引 (IVF-PQ, 物理删除)
│   ├── cold_faiss_index.py     # Cold 索引 (HNSW, 归档)
│   ├── enhanced_retrieval_service.py # 增强检索 + Reranker
│   └── faiss_index_factory.py  # FAISS 索引工厂
├── retrieval/
│   ├── bm25_index_manager.py   # BM25 索引 (jieba 分词)
│   ├── reranker.py             # 交叉编码器重排序
│   └── strategies/             # 检索策略
│       ├── base.py             # 基础策略接口
│       ├── factory.py          # 策略工厂
│       ├── vector_strategy.py  # 纯向量搜索
│       ├── hybrid_strategy.py  # 向量 + BM25 融合
│       ├── parent_child_strategy.py # 父子检索
│       ├── hyde_strategy.py    # 假设文档嵌入
│       ├── query2doc_strategy.py # 查询扩展 + RRF
│       └── decomposition_strategy.py # 查询分解
├── memory/                     # Memory 管理
│   ├── base.py                 # Memory 基础接口
│   ├── conversation_memory.py  # 对话历史
│   └── memory_manager.py       # Memory 管理器
├── tasks/
│   └── archive_task.py         # 定时 Hot→Cold 归档
├── pipeline/                   # 文档处理编排
├── extractor/                  # 文档提取器
│   └── ocr_module/             # OCR 引擎
├── models/                     # SQLAlchemy 模型
│   ├── base.py                 # 基础模型类
│   ├── model.py                # 主要模型
│   ├── rbac.py                 # RBAC 模型
│   ├── tenant.py               # 租户模型
│   ├── enums.py                # 枚举定义
│   └── custom_types.py         # 自定义数据库类型
├── schemas/                    # Pydantic schemas
├── compliance/                 # 环保合规检查
├── middleware/                 # 中间件
│   ├── tenant_middleware.py    # 租户中间件
│   ├── rbac_auth_middleware.py # RBAC 认证中间件
│   ├── performance_middleware.py # 性能监控
│   ├── telemetry.py            # OpenTelemetry
│   ├── metrics.py              # Prometheus 指标
│   └── rbac.py                 # RBAC 定义
├── utils/                      # 工具类
│   ├── resilience.py           # 熔断器
│   └── resilience_retry.py     # 重试和超时
└── app.py                      # FastAPI 应用入口

集成测试:
├── test_generational_index.py  # Hot/Cold 索引测试
├── test_faiss_optimization.py  # 自适应索引测试
└── test_retrieval_optimization.py # 检索层测试

frontend/src/
├── components/          # React 组件
├── pages/               # 页面级组件
├── services/            # API 客户端 (axios)
└── main.tsx             # React 入口点

监控配置:
monitoring/
├── prometheus/
│   └── prometheus.yml   # Prometheus 配置
├── alerts/
│   └── rag-service-alerts.yml # 告警规则
└── grafana/
    ├── provisioning/    # 数据源配置
    └── dashboards/      # 仪表板 JSON

部署文件:
├── Dockerfile           # Docker 镜像
├── docker-compose.yml   # Docker Compose
├── k8s/                 # Kubernetes 清单
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── hpa.yaml
└── deploy-v2.sh         # 部署脚本

迁移脚本:
migrations/
└── 002_create_rbac_tables.py # RBAC 表迁移

初始化脚本:
scripts/
└── init_rbac.py         # RBAC 初始化
```

## 添加新功能

1. **新 API 端点**: 添加路由到 `src/api/routes/`，在 `src/app.py` 中注册
2. **新服务**: 添加到 `src/service/`，在 `src/api/dependencies.py` 中连接，通过 `Depends()` 注入
3. **新文档格式**: 添加提取器到 `src/extractor/`，在 DocumentProcessingPipeline 中注册
4. **新分块策略**: 添加到 `src/pipeline/chunkers/`，更新 `chunking_strategy` 配置
5. **数据库模型**: 添加到 `src/models/model.py`，创建迁移脚本
6. **新检索策略**:
   - 继承 `src/retrieval/strategies/base.py` 中的 `BaseRetrievalStrategy`
   - 实现 `search()` 和 `search_with_scores()` 方法
   - 在 `RetrievalStrategyFactory` 中注册
7. **新向量存储类型**:
   - 实现 `BaseVectorStore` 接口
   - 在 `VectorStoreFactory` 中注册
8. **新权限**:
   - 在 `Permission` 枚举中添加
   - 更新 `ROLE_PERMISSIONS` 映射
   - 在路由中使用相应的依赖注入

## 功能开关

主要功能可以通过 `.env` 中的环境变量启用/禁用：

```bash
# ==================== 向量存储选择 ====================
# 优先级: 分代索引 > 优化版 > 传统版
ENABLE_GENERATIONAL_INDEX=false     # Hot/Cold 架构
FAISS_INDEX_AUTO_SELECT=false       # 自适应索引选择
FAISS_INDEX_TYPE=flat               # 强制指定索引类型

# ==================== 检索增强 ====================
ENABLE_ENHANCED_RETRIEVAL=true      # 使用 EnhancedRetrievalService
ENABLE_RERANKER_BY_DEFAULT=true     # 默认启用 Reranker
ENABLE_BM25=true                     # BM25 关键词索引
ENABLE_ADVANCED_STRATEGIES=true      # HyDE, Query2Doc, Decomposition

# ==================== 索引参数 ====================
HOT_INDEX_MAX_SIZE=1000000          # Hot 索引容量
ARCHIVE_AGE_DAYS=30                 # 归档前天数
BM25_K1=1.2                         # BM25 k1 参数
BM25_B=0.75                         # BM25 b 参数

# ==================== 多租户 ====================
ENABLE_MULTI_TENANT=true            # 启用多租户
TENANT_IDENTIFICATION=header        # 租户识别方式
TENANT_HEADER_NAME=X-Tenant-ID      # 租户 Header 名称

# ==================== RBAC ====================
ENABLE_RBAC=true                    # 启用 RBAC
ENABLE_AUDIT_LOG=true               # 启用审计日志
AUDIT_LOG_RETENTION_DAYS=90         # 审计日志保留天数

# ==================== Memory ====================
ENABLE_CONVERSATION_MEMORY=true     # 启用对话记忆
CONVERSATION_MAX_MESSAGES=100       # 最大消息数
CONVERSATION_MAX_TOKENS=4000        # 最大 token 数
ENABLE_SUMMARIZATION=true           # 启用自动总结

# ==================== 监控 ====================
ENABLE_TELEMETRY=true               # 启用 OpenTelemetry
ENABLE_METRICS=true                 # 启用 Prometheus 指标
JAEGER_HOST=localhost               # Jaeger 主机
JAEGER_PORT=6831                    # Jaeger 端口

# ==================== 存储 ====================
STORAGE_TYPE=local                  # 存储类型: local 或 oss
OSS_ACCESS_KEY_ID=xxx               # OSS 访问密钥
OSS_ACCESS_KEY_SECRET=xxx           # OSS 访问密钥 Secret
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET_NAME=rag-service
```

## 系统架构优势

1. **分代索引架构**（行业首创）
   - 解决了 FAISS 软删除的根本问题
   - 支持高频删除场景（用户文档管理）
   - 搜索性能稳定，不受软删除累积影响

2. **检索策略丰富**（行业领先）
   - 6+ 种检索策略
   - Reranker 深度集成
   - 向量 + 关键词混合检索

3. **文档处理完善**（垂直领域领先）
   - PDF 双模式处理
   - OCR 双重引擎
   - 自适应分块

4. **性能优化深度**
   - 自适应索引选择
   - 在线索引迁移
   - 全链路异步

5. **企业级特性**
   - 多租户支持
   - RBAC 权限系统
   - 审计日志
   - 完整监控体系

6. **生产就绪**
   - 容器化部署
   - 熔断降级
   - 可观测性完善
   - 自动扩缩容

## 未来规划

### 短期（3个月）
- 完善 RBAC 权限系统初始化脚本
- 添加更多单元测试和集成测试
- 优化性能瓶颈
- 完善文档

### 中期（6个月）
- SelfQuery 检索策略
- ContextualCompression
- 知识图谱集成
- 智能路由

### 长期（12个月）
- 插件市场
- SDK 开放
- 多语言支持
- 企业级 SLA
