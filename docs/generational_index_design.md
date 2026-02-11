# 方案C：分代索引架构设计

## 一、核心思想

```
传统软删除问题：
┌─────────────────────────────────────────────────────────────┐
│  FAISS索引 = 活跃数据 + 已删除数据（但标记为deleted）          │
│  → 索引膨胀、搜索变慢、需要全量重建                            │
└─────────────────────────────────────────────────────────────┘

分代索引方案：
┌─────────────────────────────────────────────────────────────┐
│  活跃索引 (Hot Index)   → 频繁增删，支持物理删除              │
│  归档索引 (Cold Index)  → 只读查询，不维护删除状态             │
│  → 增量维护、无需全量重建、搜索性能稳定                        │
└─────────────────────────────────────────────────────────────┘
```

## 二、架构设计

### 2.1 双层索引结构

```
┌──────────────────────────────────────────────────────────────────┐
│                         分代索引架构                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐    ┌─────────────────────┐             │
│  │   活跃索引 (Hot)     │    │   归档索引 (Cold)    │             │
│  ├─────────────────────┤    ├─────────────────────┤             │
│  │ • 最近30天文档        │    │ • 30天以上文档        │             │
│  │ • 支持物理删除         │    │ • 只读，不维护删除     │             │
│  │ • 使用IVF-PQ加速      │    │ • 使用HNSW高召回      │             │
│  │ • 大小：< 100万向量   │    │ • 大小：无限制        │             │
│  │ • 文件：hot.index     │    │ • 文件：cold.index    │             │
│  └─────────────────────┘    └─────────────────────┘             │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              元数据路由表 (Routing Table)                │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  doc_id → index_type (hot/cold) + location              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
├──────────────────────────────────────────────────────────────────┤
│                        搜索流程                                   │
│                                                                   │
│  用户查询 ──→ 路由器 ──→ Hot Index (70%权重) ──┐                │
│                   └──→ Cold Index (30%权重) ───┤                │
│                                                   ↓               │
│                                           RRF融合排序             │
│                                                   ↓               │
│                                           返回Top-K结果           │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 数据生命周期

```
┌─────────────────────────────────────────────────────────────────┐
│                    文档生命周期管理                               │
└─────────────────────────────────────────────────────────────────┘

   新文档上传
       ↓
   ┌──────────────────┐
   │   活跃索引        │  ← 热数据阶段（频繁访问）
   │   (Hot Index)     │
   └──────────────────┘
       ↓
   定期归档任务（每天凌晨）
       ↓
   ┌──────────────────┐
   │   归档索引        │  ← 冷数据阶段（归档存储）
   │   (Cold Index)    │
   └──────────────────┘
       ↓
   长期存储（可选迁移到对象存储）


删除操作：
   • Hot Index中的文档 → 直接物理删除（IDRemover）
   • Cold Index中的文档 → 软删除标记（定期重建）
```

## 三、核心组件设计

### 3.1 GenerationalIndexStore

```python
"""
分代索引存储
核心职责：
1. 管理Hot和Cold两个FAISS索引
2. 处理文档的路由和迁移
3. 统一的搜索接口
"""

class GenerationalIndexStore:
    def __init__(self, config, embedding_service):
        self.config = config
        self.embedding = embedding_service

        # Hot Index: 活跃数据，支持物理删除
        self.hot_index = HotFAISSIndex(
            index_path=f"{config.faiss_index_path}/hot",
            embedding_service=embedding_service,
            max_size=config.hot_index_max_size,  # 默认100万
            index_type="IVFPQ",  # 使用IVF-PQ加速
        )

        # Cold Index: 归档数据，只读
        self.cold_index = ColdFAISSIndex(
            index_path=f"{config.faiss_index_path}/cold",
            embedding_service=embedding_service,
            index_type="HNSW",  # 高召回率
        )

        # 路由表：doc_id → index_type
        self.routing_table = RoutingTable(
            db_path=f"{config.faiss_index_path}/routing.db"
        )

        # 归档管理器
        self.archive_manager = ArchiveManager(
            hot_index=self.hot_index,
            cold_index=self.cold_index,
            routing_table=self.routing_table,
            archive_age_days=config.archive_age_days,  # 默认30天
        )

    async def add_documents(self, docs: List[Document]) -> bool:
        """添加文档到活跃索引"""
        # 新文档始终添加到Hot Index
        doc_ids = await self.hot_index.add_documents(docs)

        # 更新路由表
        for doc_id in doc_ids:
            self.routing_table.set_location(doc_id, "hot")

        return True

    async def delete_documents(self, file_id: str) -> int:
        """删除文档"""
        # 1. 查询该file_id的doc_id及其位置
        locations = self.routing_table.get_by_file_id(file_id)

        deleted_count = 0
        for doc_id, index_type in locations:
            if index_type == "hot":
                # Hot Index: 物理删除
                deleted_count += await self.hot_index.remove_doc(doc_id)
            else:
                # Cold Index: 软删除（因为重建成本高）
                deleted_count += await self.cold_index.soft_delete(doc_id)

            # 更新路由表
            self.routing_table.delete(doc_id)

        return deleted_count

    async def search(self, query: str, k: int = 10) -> List[Document]:
        """统一搜索接口"""
        # 计算每个索引的召回数量
        hot_k = int(k * 0.7)  # Hot Index召回70%
        cold_k = int(k * 0.5)  # Cold Index召回50%（留余量）

        # 并行搜索两个索引
        hot_results, cold_results = await asyncio.gather(
            self.hot_index.search(query, k=hot_k),
            self.cold_index.search(query, k=cold_k)
        )

        # RRF融合
        fused_results = self._reciprocal_rank_fusion(
            hot_results=hot_results,
            cold_results=cold_results,
            k=k
        )

        return fused_results[:k]

    def _reciprocal_rank_fusion(self, hot_results, cold_results, k: int):
        """RRF融合算法"""
        scores = {}

        # Hot Index权重: 0.7
        for rank, doc in enumerate(hot_results):
            doc_id = doc.metadata["doc_id"]
            scores[doc_id] = scores.get(doc_id, 0) + 0.7 / (rank + 60)

        # Cold Index权重: 0.3
        for rank, doc in enumerate(cold_results):
            doc_id = doc.metadata["doc_id"]
            scores[doc_id] = scores.get(doc_id, 0) + 0.3 / (rank + 60)

        # 按分数排序
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in sorted_docs]

    async def archive_old_documents(self):
        """归档旧文档（定期任务）"""
        return await self.archive_manager.run_archive_task()

    async def rebuild_cold_index(self):
        """重建Cold Index（删除软删除的文档）"""
        return await self.cold_index.rebuild()
```

### 3.2 HotFAISSIndex（支持物理删除）

```python
"""
活跃索引：支持物理删除的FAISS索引
使用IVF-PQ索引类型，支持IDRemover进行物理删除
"""

class HotFAISSIndex:
    def __init__(self, index_path, embedding_service, max_size=1000000, index_type="IVFPQ"):
        self.index_path = index_path
        self.embedding = embedding_service
        self.max_size = max_size
        self.index_type = index_type

        self.vector_store = None
        self.id_remover = None  # FAISS IDRemover，支持物理删除

        self._initialize()

    def _initialize(self):
        """初始化索引"""
        if os.path.exists(self.index_path):
            self._load()
        else:
            self._create_new()

    def _create_new(self):
        """创建新索引"""
        dimension = self.embedding.get_dimension()

        if self.index_type == "IVFPQ":
            # IVF-PQ: 适合大规模，速度快
            quantizer = faiss.IndexFlatL2(dimension)
            index = faiss.IndexIVFPQ(
                quantizer,
                dimension,
                nlist=100,      # 聚类中心数
                m=64,           # PQ压缩维度
                nbits=8         # 每个量化器的位数
            )
            # 需要训练
            index.nprobe = 10  # 搜索时探测的聚类数

        elif self.index_type == "HNSW":
            # HNSW: 高召回率，但内存占用大
            index = faiss.IndexHNSWFlat(dimension, M=32)
            index.efSearch = 64

        else:
            # Fallback to Flat
            index = faiss.IndexFlatL2(dimension)

        # 包装IDRemover，支持物理删除
        self.id_remover = faiss.IDRemover(index)

        self.vector_store = FAISS(
            embedding_function=self.embedding.embedding_model,
            index=self.id_remover,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={},
        )

        self._save()

    async def add_documents(self, docs: List[Document]) -> List[str]:
        """添加文档"""
        # 检查容量
        current_size = self.vector_store.index.ntotal
        if current_size + len(docs) > self.max_size:
            # 触发归档
            await self._trigger_archive()

        doc_ids = [f"doc_{uuid.uuid4().hex}" for _ in docs]
        langchain_docs = [
            LangchainDocument(page_content=doc.content, metadata={**doc.metadata, "doc_id": doc_id})
            for doc, doc_id in zip(docs, doc_ids)
        ]

        self.vector_store.add_documents(langchain_docs)
        self._save()

        return doc_ids

    async def remove_doc(self, doc_id: str) -> int:
        """物理删除文档"""
        # FAISS IDRemover.remove_ids()
        try:
            # 获取FAISS内部ID
            faiss_id = self._get_faiss_id(doc_id)
            if faiss_id is None:
                return 0

            # 物理删除
            self.id_remover.remove_ids(faiss_id)

            # 从docstore删除
            self.vector_store.docstore.delete({doc_id})

            self._save()
            logger.info(f"Physically removed doc_id={doc_id} from hot index")
            return 1

        except Exception as e:
            logger.error(f"Failed to remove doc_id={doc_id}: {e}")
            return 0

    async def search(self, query: str, k: int) -> List[Document]:
        """搜索"""
        results = self.vector_store.similarity_search(query, k=k)
        return results

    def _get_faiss_id(self, doc_id: str) -> Optional[int]:
        """获取FAISS内部ID"""
        for faiss_id, stored_doc_id in self.vector_store.index_to_docstore_id.items():
            if stored_doc_id == doc_id:
                return faiss_id
        return None
```

### 3.3 ColdFAISSIndex（归档索引）

```python
"""
归档索引：只读索引，使用HNSW高召回率
"""
class ColdFAISSIndex:
    def __init__(self, index_path, embedding_service, index_type="HNSW"):
        self.index_path = index_path
        self.embedding = embedding_service
        self.index_type = index_type

        self.vector_store = None
        self.soft_deleted_ids = set()  # 软删除集合

        self._initialize()

    def _initialize(self):
        """初始化"""
        if os.path.exists(self.index_path):
            self._load()
        else:
            self._create_empty()

    def _create_empty(self):
        """创建空索引"""
        dimension = self.embedding.get_dimension()

        if self.index_type == "HNSW":
            index = faiss.IndexHNSWFlat(dimension, M=32)
            index.efSearch = 64
        else:
            index = faiss.IndexFlatL2(dimension)

        self.vector_store = FAISS(
            embedding_function=self.embedding.embedding_model,
            index=index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={},
        )

        self._save()

    async def add_documents(self, docs: List[Document]) -> List[str]:
        """添加文档（从Hot迁移过来）"""
        langchain_docs = [
            LangchainDocument(page_content=doc.content, metadata=doc.metadata)
            for doc in docs
        ]

        self.vector_store.add_documents(langchain_docs)
        self._save()
        return [doc.metadata.get("doc_id") for doc in docs]

    async def soft_delete(self, doc_id: str) -> int:
        """软删除"""
        self.soft_deleted_ids.add(doc_id)
        self._save_deleted_ids()
        return 1

    async def search(self, query: str, k: int) -> List[Document]:
        """搜索，过滤软删除"""
        # 召回k*3倍，过滤后返回k
        search_k = k * 3
        results = self.vector_store.similarity_search(query, k=search_k)

        # 过滤软删除
        filtered = [
            doc for doc in results
            if doc.metadata.get("doc_id") not in self.soft_deleted_ids
        ][:k]

        return filtered

    async def rebuild(self) -> bool:
        """重建索引（移除软删除的文档）"""
        try:
            # 收集活跃文档
            active_docs = []
            for doc_id in self.vector_store.index_to_docstore_id.values():
                if doc_id not in self.soft_deleted_ids:
                    doc = self.vector_store.docstore.search(doc_id)
                    if doc:
                        active_docs.append(doc)

            # 重建索引
            self._create_empty()
            if active_docs:
                self.vector_store.add_documents(active_docs)

            # 清空软删除集合
            self.soft_deleted_ids.clear()

            self._save()
            logger.info(f"Rebuilt cold index with {len(active_docs)} docs")
            return True

        except Exception as e:
            logger.error(f"Failed to rebuild cold index: {e}")
            return False
```

### 3.4 ArchiveManager（归档管理器）

```python
"""
归档管理器：负责将旧文档从Hot迁移到Cold
"""
class ArchiveManager:
    def __init__(self, hot_index, cold_index, routing_table, archive_age_days=30):
        self.hot_index = hot_index
        self.cold_index = cold_index
        self.routing_table = routing_table
        self.archive_age_days = archive_age_days

    async def run_archive_task(self) -> Dict[str, int]:
        """执行归档任务"""
        logger.info("Starting archive task...")

        # 1. 找出需要归档的文档
        docs_to_archive = await self._find_docs_to_archive()

        if not docs_to_archive:
            logger.info("No documents to archive")
            return {"archived_count": 0, "freed_space": 0}

        # 2. 从Hot Index读取
        docs = await self._fetch_from_hot_index(docs_to_archive)

        # 3. 添加到Cold Index
        await self.cold_index.add_documents(docs)

        # 4. 从Hot Index删除
        for doc_id in docs_to_archive:
            await self.hot_index.remove_doc(doc_id)

        # 5. 更新路由表
        for doc_id in docs_to_archive:
            self.routing_table.set_location(doc_id, "cold")

        logger.info(f"Archived {len(docs_to_archive)} documents")
        return {
            "archived_count": len(docs_to_archive),
            "freed_space": len(docs_to_archive) * self.estimate_doc_size()
        }

    async def _find_docs_to_archive(self) -> List[str]:
        """找出需要归档的文档"""
        cutoff_date = datetime.now() - timedelta(days=self.archive_age_days)

        # 从路由表找出超过归档期限的文档
        # 这里简化处理，实际应该查询元数据表
        all_doc_ids = self.routing_table.get_all_by_type("hot")
        docs_to_archive = []

        for doc_id in all_doc_ids:
            # 查询文档创建时间（从metadata）
            doc = self.hot_index.vector_store.docstore.search(doc_id)
            if doc:
                created_at = doc.metadata.get("created_at")
                if created_at and created_at < cutoff_date:
                    docs_to_archive.append(doc_id)

        return docs_to_archive

    async def _fetch_from_hot_index(self, doc_ids: List[str]) -> List[Document]:
        """从Hot Index获取文档"""
        docs = []
        for doc_id in doc_ids:
            doc = self.hot_index.vector_store.docstore.search(doc_id)
            if doc:
                docs.append(Document(
                    content=doc.page_content,
                    metadata=doc.metadata
                ))
        return docs

    def estimate_doc_size(self) -> int:
        """估算单个文档的索引大小（字节）"""
        # 简化估算
        return 1024  # 1KB
```

### 3.5 RoutingTable（路由表）

```python
"""
路由表：维护doc_id到索引类型的映射
使用SQLite持久化
"""
import sqlite3
from contextlib import contextmanager

class RoutingTable:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS routing (
                    doc_id TEXT PRIMARY KEY,
                    index_type TEXT NOT NULL,
                    file_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_id ON routing(file_id)
            """)
            conn.commit()

    def set_location(self, doc_id: str, index_type: str, file_id: str = None):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO routing (doc_id, index_type, file_id) VALUES (?, ?, ?)",
                (doc_id, index_type, file_id)
            )
            conn.commit()

    def get_location(self, doc_id: str) -> Optional[str]:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT index_type FROM routing WHERE doc_id = ?",
                (doc_id,)
            )
            row = cursor.fetchone()
            return row["index_type"] if row else None

    def get_by_file_id(self, file_id: str) -> List[Tuple[str, str]]:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT doc_id, index_type FROM routing WHERE file_id = ?",
                (file_id,)
            )
            return [(row["doc_id"], row["index_type"]) for row in cursor.fetchall()]

    def get_all_by_type(self, index_type: str) -> List[str]:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT doc_id FROM routing WHERE index_type = ?",
                (index_type,)
            )
            return [row["doc_id"] for row in cursor.fetchall()]

    def delete(self, doc_id: str):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM routing WHERE doc_id = ?", (doc_id,))
            conn.commit()

    def get_stats(self) -> Dict:
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT index_type, COUNT(*) as count
                FROM routing
                GROUP BY index_type
            """)
            return {row["index_type"]: row["count"] for row in cursor.fetchall()}
```

## 四、配置管理

```python
# config.py 添加配置

class Settings(BaseSettings):
    # ... 现有配置 ...

    # ========== 分代索引配置 ==========
    enable_generational_index: bool = True  # 是否启用分代索引

    # Hot Index 配置
    hot_index_max_size: int = 1000000  # Hot Index最大容量（向量数）
    hot_index_type: str = "IVFPQ"  # Hot Index类型: IVFPQ, HNSW, Flat
    hot_index_nlist: int = 100  # IVF聚类中心数
    hot_index_nprobe: int = 10  # IVF搜索探测数

    # Cold Index 配置
    cold_index_type: str = "HNSW"  # Cold Index类型: HNSW, Flat
    cold_index_m: int = 32  # HNSW连接数
    cold_index_ef_search: int = 64  # HNSW搜索参数

    # 归档配置
    archive_age_days: int = 30  # 归档天数（超过此天数的文档归档）
    archive_schedule: str = "0 2 * * *"  # 归档任务cron表达式（每天凌晨2点）

    # 搜索权重配置
    hot_search_weight: float = 0.7  # Hot Index搜索权重
    cold_search_weight: float = 0.3  # Cold Index搜索权重
```

## 五、集成到现有系统

### 5.1 修改 dependencies.py

```python
# src/api/dependencies.py

@lru_cache(maxsize=1)
def get_vector_store():
    embedding_service = get_embedding_service()

    if settings.enable_generational_index:
        from src.vector.generational_index_store import GenerationalIndexStore
        return GenerationalIndexStore(settings, embedding_service)
    else:
        # 保持原有实现，向后兼容
        from src.vector.vector_store import FAISSVectorStore
        return FAISSVectorStore(settings, embedding_service)
```

### 5.2 添加归档任务

```python
# src/tasks/archive_task.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.api.dependencies import get_vector_store

scheduler = AsyncIOScheduler()

async def archive_task():
    """定期归档任务"""
    vector_store = get_vector_store()
    if hasattr(vector_store, 'archive_old_documents'):
        result = await vector_store.archive_old_documents()
        logger.info(f"Archive task completed: {result}")

def start_scheduler():
    schedule = settings.archive_schedule  # "0 2 * * *"
    scheduler.add_job(archive_task, 'cron', hour=2, minute=0)
    scheduler.start()
```

## 六、监控和维护

### 6.1 监控指标

```python
# src/metrics/index_metrics.py

class IndexMetrics:
    def get_metrics(self) -> Dict:
        vector_store = get_vector_store()

        return {
            "hot_index_size": vector_store.hot_index.get_size(),
            "cold_index_size": vector_store.cold_index.get_size(),
            "routing_table_stats": vector_store.routing_table.get_stats(),
            "last_archive_time": vector_store.archive_manager.last_archive_time,
            "deletion_rate_hot": vector_store.hot_index.get_deletion_rate(),
            "deletion_rate_cold": vector_store.cold_index.get_deletion_rate(),
        }
```

### 6.2 维护API

```python
# src/api/routes/maintenance.py

@router.post("/index/archive")
async def trigger_archive():
    """手动触发归档"""
    vector_store = get_vector_store()
    if hasattr(vector_store, 'archive_old_documents'):
        result = await vector_store.archive_old_documents()
        return result
    return {"error": "Generational index not enabled"}

@router.post("/index/rebuild-cold")
async def rebuild_cold_index():
    """重建Cold Index"""
    vector_store = get_vector_store()
    if hasattr(vector_store, 'rebuild_cold_index'):
        result = await vector_store.rebuild_cold_index()
        return result
    return {"error": "Generational index not enabled"}

@router.get("/index/stats")
async def get_index_stats():
    """获取索引统计"""
    vector_store = get_vector_store()
    if hasattr(vector_store, 'get_stats'):
        return vector_store.get_stats()
    return {"error": "Stats not available"}
```

## 七、优势总结

| 指标 | 传统软删除 | 分代索引 |
|------|-----------|----------|
| 内存泄漏 | deleted_ids持续增长 | Hot Index物理删除，无泄漏 |
| 搜索性能 | 随删除率下降而下降 | Hot Index稳定，Cold Index高效 |
| 维护成本 | 需要全量重建 | 仅需归档迁移，增量维护 |
| 召回准确性 | 需要k*3补偿 | 双索引融合，召回更准确 |
| 数据可用性 | 重建期间不可用 | 归档不影响查询 |
| 扩展性 | 单索引限制 | 冷热分离，无限扩展 |

## 八、实施路径

### Phase 1: 基础实现（2周）
- [ ] 实现 HotFAISSIndex 和 ColdFAISSIndex
- [ ] 实现 RoutingTable（SQLite）
- [ ] 实现基础搜索和融合逻辑

### Phase 2: 归档机制（1周）
- [ ] 实现 ArchiveManager
- [ ] 添加归档定时任务
- [ ] 实现归档监控

### Phase 3: 集成和优化（1周）
- [ ] 集成到现有系统
- [ ] 添加监控指标
- [ ] 添加维护API

### Phase 4: 测试和上线（1周）
- [ ] 单元测试
- [ ] 性能测试
- [ ] 灰度上线
