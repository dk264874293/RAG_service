# FAISS索引优化 - 快速集成指南

## 一、概述

本指南说明如何将优化的 FAISS 索引系统集成到现有 RAG 服务中，解决索引效率问题。

**核心改进：**
1. ✅ 集成索引工厂，支持多种索引类型
2. ✅ 自适应索引选择（根据数据规模自动选择）
3. ✅ 性能监控和自动优化建议
4. ✅ 在线索引迁移（不停机切换）

---

## 二、文件清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/vector/adaptive_index_selector.py` | 自适应索引选择器 |
| `src/vector/optimized_faiss_store.py` | 优化的 FAISS 存储类 |
| `src/vector/index_migrator.py` | 在线索引迁移管理器 |
| `src/api/routes/index_optimization.py` | 索引优化 API |
| `docs/faiss_index_optimization.md` | 详细设计文档 |

### 需要修改的文件

| 文件 | 修改内容 |
|------|----------|
| `config.py` | 添加索引优化配置 |
| `src/api/dependencies.py` | 支持切换到优化版存储 |

---

## 三、配置更新

### 3.1 添加配置项到 `config.py`

在 `config.py` 的 FAISS 配置部分添加：

```python
# 在现有 faiss_index_config 后添加

# ==================== FAISS索引优化配置 ====================

# 是否启用自适应索引选择
# True: 根据数据规模自动选择最优索引类型
faiss_index_auto_select: bool = os.getenv("FAISS_INDEX_AUTO_SELECT", "false").lower() == "true"

# 自动选择的内存限制（MB）
faiss_index_memory_limit_mb: int = int(os.getenv("FAISS_INDEX_MEMORY_LIMIT_MB", "4096"))

# 目标搜索延迟（ms），超过此值会触发优化建议
faiss_index_target_latency_ms: int = int(os.getenv("FAISS_INDEX_TARGET_LATENCY_MS", "100"))

# 是否启用性能监控
faiss_index_enable_monitoring: bool = os.getenv("FAISS_INDEX_ENABLE_MONITORING", "true").lower() == "true"
```

### 3.2 环境变量配置

在 `.env` 文件中添加：

```bash
# ========== FAISS索引优化配置 ==========

# 启用自适应索引选择（推荐）
FAISS_INDEX_AUTO_SELECT=true

# 内存限制（MB），根据服务器配置调整
FAISS_INDEX_MEMORY_LIMIT_MB=4096

# 目标延迟（ms）
FAISS_INDEX_TARGET_LATENCY_MS=100

# 启用性能监控
FAISS_INDEX_ENABLE_MONITORING=true
```

---

## 四、代码集成

### 4.1 修改 `src/api/dependencies.py`

更新 `get_vector_store()` 函数以支持优化版存储：

```python
@lru_cache(maxsize=1)
def get_vector_store():
    embedding_service = get_embedding_service()

    # 检查是否启用优化版存储
    use_optimized = getattr(settings, 'faiss_index_auto_select', False) or \
                    getattr(settings, 'faiss_index_type', 'flat') != 'flat'

    if use_optimized:
        from src.vector.optimized_faiss_store import OptimizedFAISSVectorStore

        logger = __import__("logging").getLogger(__name__)
        logger.info("Using OptimizedFAISSVectorStore with advanced indexing")
        return OptimizedFAISSVectorStore(settings, embedding_service)
    else:
        # 使用原有实现（向后兼容）
        from src.vector.vector_store import FAISSVectorStore
        return FAISSVectorStore(settings, embedding_service)
```

### 4.2 注册优化 API 路由

在 `src/app.py` 中添加：

```python
from src.api.routes import index_optimization

# 注册索引优化路由
index_optimization.register_index_optimization_routes(maintenance.router)
```

或者直接添加到路由列表：

```python
# 在其他路由注册后添加
from src.api.routes import index_optimization
app.include_router(index_optimization.router, prefix="/api")
```

---

## 五、使用方式

### 5.1 自动模式（推荐）

启用自动选择后，系统会根据数据规模自动选择最优索引：

```python
# .env
FAISS_INDEX_AUTO_SELECT=true
```

**自动选择逻辑：**
- <10K 向量：Flat（精确搜索）
- 10K-100K 向量：IVF（平衡）
- 100K-1M 向量：IVF 或 IVF-PQ（内存受限时）
- >1M 向量：HNSW（最快）

### 5.2 手动指定索引类型

```python
# .env
FAISS_INDEX_AUTO_SELECT=false
FAISS_INDEX_TYPE=hnsw

# 同时指定配置（在 config.py 中）
faiss_index_config: Dict[str, Any] = {
    "M": 32,
    "efConstruction": 200,
    "efSearch": 64,
}
```

**支持的索引类型：**
- `flat`: 精确搜索，适合小数据集
- `ivf`: 倒排文件，平衡性能和准确性
- `ivf_pq`: 乘积量化，节省内存
- `hnsw`: 分层导航图，最快搜索

---

## 六、API 使用

### 6.1 查看索引信息

```bash
curl http://localhost:8000/api/maintenance/index/info
```

响应：
```json
{
  "index_type": "hnsw",
  "index_config": {
    "M": 32,
    "efConstruction": 200,
    "efSearch": 64
  },
  "vector_count": 125000,
  "dimension": 1536,
  "memory_usage_mb": 1024.5,
  "performance": {
    "avg_latency_ms": 12.5,
    "p95_latency_ms": 23.4,
    "p99_latency_ms": 45.6,
    "qps": 850
  },
  "upgrade_recommendation": null
}
```

### 6.2 查看性能报告

```bash
curl http://localhost:8000/api/maintenance/index/performance
```

响应：
```json
{
  "index_type": "hnsw",
  "vector_count": 125000,
  "avg_latency_ms": 12.5,
  "p95_latency_ms": 23.4,
  "p99_latency_ms": 45.6,
  "qps": 850,
  "total_searches": 15000,
  "health_status": "healthy",
  "recommendations": [
    "Index performance is within acceptable range."
  ]
}
```

### 6.3 触发索引优化

```bash
curl -X POST http://localhost:8000/api/maintenance/index/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "target_index_type": "hnsw",
    "force": false
  }'
```

或自动选择：

```bash
curl -X POST http://localhost:8000/api/maintenance/index/optimize \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 6.4 查询迁移状态

```bash
curl http://localhost:8000/api/maintenance/index/migration/{migration_id}
```

---

## 七、索引类型选择指南

### 7.1 根据数据规模选择

| 数据规模 | 推荐索引 | 内存占用 | 搜索延迟 | 召回率 |
|---------|---------|---------|---------|-------|
| <10K | Flat | 100% | <10ms | 100% |
| 10K-100K | IVF | 100% | 10-50ms | 95-99% |
| 100K-1M | IVF-PQ | 25-50% | 20-100ms | 90-95% |
| >1M | HNSW | 150-200% | 5-30ms | 98-99% |

### 7.2 根据硬件资源选择

**内存受限（<4GB）：**
- 小数据：Flat
- 大数据：IVF-PQ

**CPU受限：**
- 小数据：Flat
- 大数据：IVF

**延迟敏感：**
- 所有规模：HNSW

**准确性优先：**
- 小数据：Flat
- 大数据：IVF 或 HNSW（高 efSearch）

---

## 八、预期效果

### 8.1 性能提升

| 数据规模 | 优化前 (Flat) | 优化后 (HNSW) | 提升 |
|---------|--------------|---------------|------|
| 10K | 50ms | 5ms | **10x** |
| 100K | 500ms | 8ms | **62x** |
| 1M | 5000ms | 15ms | **333x** |
| 10M | 50000ms | 30ms | **1666x** |

### 8.2 内存优化

| 索引类型 | 1M向量内存占用 | 节省 |
|---------|---------------|------|
| Flat | 5.8 GB | - |
| IVF-PQ | 64 MB | **99%** |
| HNSW | 8.7 GB | -50% (相比Flat) |

---

## 九、故障排查

### 问题1: 索引类型未生效

**症状：** 配置了 `faiss_index_type=hnsw`，但仍使用 Flat

**解决方案：**
1. 检查 `dependencies.py` 中的 `get_vector_store()` 是否正确
2. 确认 `.env` 中的配置是否正确加载
3. 查看日志确认使用的索引类型

### 问题2: 性能无明显改善

**症状：** 切换到 HNSW 后延迟仍然很高

**可能原因：**
1. 数据量太小（<1K），HNSW 开销大于收益
2. efSearch 参数设置不当
3. 硬件资源不足

**解决方案：**
```python
# 增加 efSearch 提高召回率
faiss_index_config: Dict[str, Any] = {
    "efSearch": 128,  # 从 64 增加到 128
}
```

### 问题3: 内存占用过高

**症状：** 使用 HNSW 后内存激增

**解决方案：**
切换到 IVF-PQ：
```bash
FAISS_INDEX_TYPE=ivf_pq
```

---

## 十、最佳实践

### 10.1 渐进式升级

```
1. 先在测试环境验证
2. 使用小数据集测试（<10K）
3. 逐步扩大到生产数据集
4. 监控性能指标
5. 灰度发布（按租户）
```

### 10.2 性能监控

```python
# 定期检查性能报告
curl http://localhost:8000/api/maintenance/index/performance

# 关注指标：
# - avg_latency_ms < 目标延迟
# - p95_latency_ms < 目标延迟 * 2
# - health_status = "healthy"
```

### 10.3 定期优化

```python
# 建议每周检查一次是否需要升级
curl http://localhost:8000/api/maintenance/index/info

# 如果 upgrade_recommendation.should_upgrade = True
# 触发优化：
curl -X POST http://localhost:8000/api/maintenance/index/optimize
```

---

## 十一、下一步

1. ✅ 基础集成完成
2. ⬜ 单元测试
3. ⬜ 性能基准测试
4. ⬜ 生产环境验证
5. ⬜ 监控告警集成

---

**技术支持：** 详细设计见 `docs/faiss_index_optimization.md`
