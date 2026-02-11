# FAISS索引效率优化方案

## 一、问题分析

### 当前问题
```python
# src/vector/vector_store.py:66
faiss_index = faiss.IndexFlatL2(dimension)  # 硬编码，仅支持暴力搜索
```

**根本原因：**
1. 索引类型硬编码，未使用配置中的 `faiss_index_type`
2. 未使用已有的 `FAISSIndexFactory`
3. 没有自适应索引选择机制
4. 缺少索引性能监控

### 性能对比

| 索引类型 | 构建时间 | 内存占用 | 搜索速度 | 准确率 | 适用场景 |
|---------|---------|---------|---------|-------|---------|
| Flat (L2) | O(1) | 100% | O(n) 慢 | 100% | <10K 向量 |
| IVF | O(n) | 100% | O(√n) 中 | 95-99% | 10K-1M 向量 |
| IVF-PQ | O(n) | 25-50% | O(√n) 快 | 90-95% | 1M-10M 向量 |
| HNSW | O(n log n) | 150-200% | O(log n) 最快 | 98-99% | 所有规模 |

---

## 二、优化方案总览

```
┌─────────────────────────────────────────────────────────────────┐
│                  FAISS索引优化架构                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │            自适应索引选择器                              │  │
│  │  根据数据规模、查询模式、硬件资源自动选择最优索引         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                            ↓                                  │
│  ┌──────────────┬──────────────┬──────────────┬─────────────┐ │
│  │    Flat      │     IVF      │    IVF-PQ    │    HNSW     │ │
│  │  <10K 向量   │  10K-1M     │   1M-10M    │   所有规模   │ │
│  └──────────────┴──────────────┴──────────────┴─────────────┘ │
│                            ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │            索引迁移管理器                                │  │
│  │  支持在线索引类型切换，无需停机                          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                            ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │            性能监控与优化                                │  │
│  │  实时监控搜索性能，自动触发索引优化                      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、核心组件设计

### 3.1 增强版索引工厂

支持更多索引类型和自动选择：

```python
# 索引类型决策树
def select_optimal_index(vector_count: int, dimension: int,
                        memory_limit_mb: int) -> str:
    """
    根据数据规模自动选择最优索引

    决策逻辑:
    - <10K: Flat (精确搜索，足够快)
    - 10K-100K: IVF (平衡速度和准确性)
    - 100K-1M: IVF-PQ (节省内存)
    - >1M: HNSW (最快搜索)
    """
    if vector_count < 10000:
        return "flat"
    elif vector_count < 100000:
        return "ivf"
    elif vector_count < 1000000:
        # 检查内存限制
        estimated_memory = vector_count * dimension * 4 / (1024 * 1024)
        if estimated_memory > memory_limit_mb * 0.5:
            return "ivf_pq"  # 内存不足时使用压缩
        return "ivf"
    else:
        return "hnsw"  # 大规模使用HNSW
```

### 3.2 在线索引迁移

支持不停机切换索引类型：

```python
class IndexMigrator:
    """索引迁移管理器"""

    async def migrate_index(self,
                           from_type: str,
                           to_type: str,
                           batch_size: int = 10000) -> float:
        """
        在线迁移索引

        流程:
        1. 创建新类型索引
        2. 批量迁移向量数据
        3. 验证迁移准确性
        4. 原子切换索引
        5. 清理旧索引
        """
        # 迁移进度 (0.0 - 1.0)
        pass
```

### 3.3 性能监控

实时监控索引性能：

```python
class IndexPerformanceMonitor:
    """索引性能监控"""

    def record_search(self, latency_ms: float, k: int):
        """记录搜索性能"""

    def get_performance_report(self) -> dict:
        """获取性能报告"""
        return {
            "avg_latency_ms": 125.5,
            "p95_latency_ms": 234.2,
            "p99_latency_ms": 456.8,
            "queries_per_second": 850,
            "recommended_action": "Consider upgrading to HNSW"
        }
```

---

## 四、索引类型详细设计

### 4.1 Flat (精确搜索)

**特点：**
- 100% 召回率
- 内存占用：100%
- 速度：O(n)
- 适用：<10K 向量

**配置：**
```python
{
    "index_type": "flat",
    "metric": "L2"  # 或 "IP" (内积)
}
```

### 4.2 IVF (倒排文件)

**特点：**
- 95-99% 召回率
- 内存占用：100%
- 速度：O(√n)
- 适用：10K-1M 向量

**核心参数：**
```python
{
    "index_type": "ivf",
    "nlist": 100,      # 聚类中心数 (建议: sqrt(n))
    "nprobe": 10,      # 搜索时探测的聚类数 (影响速度/准确率)
    "metric": "L2"
}

# 参数自动计算公式:
nlist = min(100, int(sqrt(vector_count)))
nprobe = max(1, int(nlist * 0.1))  # 探测10%的聚类
```

### 4.3 IVF-PQ (乘积量化)

**特点：**
- 90-95% 召回率
- 内存占用：25-50%
- 速度：O(√n)
- 适用：1M-10M 向量

**核心参数：**
```python
{
    "index_type": "ivf_pq",
    "nlist": 100,      # 聚类中心数
    "m": 64,           # PQ子量化器数 (影响压缩比)
    "nbits": 8,        # 每个量化器的位数
    "nprobe": 10,
    "metric": "L2"
}

# 内存计算:
# 原始: dimension * 4 bytes
# PQ后: m * nbits / 8 bytes
# 压缩比: (dimension * 4) / (m * nbits / 8)
```

### 4.4 HNSW (分层导航小世界图)

**特点：**
- 98-99% 召回率
- 内存占用：150-200%
- 速度：O(log n)
- 适用：所有规模（尤其是大规模）

**核心参数：**
```python
{
    "index_type": "hnsw",
    "M": 32,              # 每个节点的连接数 (影响召回率和内存)
    "efConstruction": 200, # 构建时的候选数 (影响质量)
    "efSearch": 64,       # 搜索时的候选数 (影响召回率)
    "metric": "L2"
}

# 参数建议:
# M = 16-64 (大: 高召回，慢构建)
# efConstruction = 200-800
# efSearch = k * 2-10
```

---

## 五、实施计划

### Phase 1: 集成索引工厂 (1天)

- [ ] 修改 `FAISSVectorStore` 使用 `FAISSIndexFactory`
- [ ] 支持配置驱动索引类型
- [ ] 添加索引参数验证

### Phase 2: 自适应索引选择 (1天)

- [ ] 实现 `AdaptiveIndexSelector`
- [ ] 根据数据规模自动选择
- [ ] 添加手动覆盖选项

### Phase 3: 性能监控 (1天)

- [ ] 实现 `IndexPerformanceMonitor`
- [ ] 记录搜索延迟和吞吐量
- [ ] 生成性能报告和优化建议

### Phase 4: 在线索引迁移 (2天)

- [ ] 实现 `IndexMigrator`
- [ ] 支持批量迁移
- [ ] 原子切换机制
- [ ] 回滚支持

### Phase 5: 高级优化 (可选)

- [ ] GPU 加速支持
- [ ] 分布式索引
- [ ] 混合索引 (Flat + HNSW)

---

## 六、配置更新

### 6.1 自动选择模式（推荐）

```python
# config.py
faiss_index_auto_select: bool = True  # 自动选择最优索引
faiss_index_memory_limit_mb: int = 4096  # 内存限制（MB）
faiss_index_target_latency_ms: int = 100  # 目标延迟
```

### 6.2 手动指定模式

```python
# config.py
faiss_index_type: str = "hnsw"  # flat, ivf, ivf_pq, hnsw

# 索引类型特定配置
faiss_index_config: Dict[str, Any] = {
    # IVF/IVF-PQ 配置
    "nlist": 100,
    "nprobe": 10,

    # IVF-PQ 额外配置
    "m": 64,
    "nbits": 8,

    # HNSW 配置
    "M": 32,
    "efConstruction": 200,
    "efSearch": 64,
}
```

---

## 七、预期效果

### 性能提升

| 数据规模 | 当前 (Flat) | 优化后 (HNSW) | 提升 |
|---------|------------|--------------|------|
| 10K | 50ms | 5ms | 10x |
| 100K | 500ms | 8ms | 62x |
| 1M | 5000ms | 15ms | 333x |
| 10M | 50000ms | 30ms | 1666x |

### 内存优化

| 索引类型 | 1M向量 (1536维) | 内存占用 |
|---------|----------------|---------|
| Flat | 1M × 1536 × 4B | 5.8 GB |
| IVF | 1M × 1536 × 4B | 5.8 GB |
| IVF-PQ (m=64) | 1M × 64 × 1B | 64 MB (99%↓) |
| HNSW (M=32) | 1M × 1536 × 4B × 1.5 | 8.7 GB |

### 准确率

| 索引类型 | Recall@10 | Recall@100 |
|---------|-----------|------------|
| Flat | 100% | 100% |
| IVF (nprobe=10) | 95-98% | 98-99% |
| IVF-PQ | 90-95% | 95-98% |
| HNSW (efSearch=64) | 97-99% | 99%+ |

---

## 八、API 设计

### 8.1 查看当前索引

```bash
GET /api/vector/index/info

Response:
{
  "index_type": "hnsw",
  "vector_count": 125000,
  "dimension": 1536,
  "memory_usage_mb": 1024,
  "performance": {
    "avg_latency_ms": 12.5,
    "p95_latency_ms": 23.4,
    "qps": 850
  }
}
```

### 8.2 触发索引优化

```bash
POST /api/vector/index/optimize

Request:
{
  "target_index_type": "hnsw",  # 或 "auto" 自动选择
  "force": false
}

Response:
{
  "migration_id": "mig_123456",
  "estimated_time_sec": 300,
  "status": "in_progress"
}
```

### 8.3 查询迁移进度

```bash
GET /api/vector/index/migration/{migration_id}

Response:
{
  "status": "in_progress",
  "progress": 0.65,  # 65%
  "current_phase": "migrating_vectors",
  "estimated_remaining_sec": 105
}
```

---

## 九、监控指标

### Prometheus 指标

```python
# 索引性能指标
faiss_search_latency_ms{index_type="hnsw"}
faiss_search_qps{index_type="hnsw"}
faiss_recall_rate{index_type="hnsw",k="10"}
faiss_memory_usage_mb{index_type="hnsw"}
faiss_vector_count{index_type="hnsw"}

# 迁移指标
faiss_migration_progress{migration_id="123"}
faiss_migration_status{from_type="flat",to_type="hnsw"}
```

### 告警规则

```yaml
# 搜索延迟告警
- alert: HighSearchLatency
  expr: faiss_search_latency_ms > 500
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Search latency too high"
    description: "Consider upgrading to HNSW index"

# 召回率告警
- alert: LowRecallRate
  expr: faiss_recall_rate{k="10"} < 0.90
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Recall rate below 90%"
```

---

## 十、向后兼容

### 渐进式迁移

```python
# 默认保持 Flat 索引（向后兼容）
faiss_index_auto_select: bool = False  # 默认关闭

# 用户可以选择启用
# 1. 设置 faiss_index_auto_select = True
# 2. 或手动指定 faiss_index_type = "hnsw"
```

### 灰度发布

```python
# 按租户灰度
def get_index_type_for_tenant(tenant_id: str) -> str:
    if tenant_id in experimental_tenants:
        return "hnsw"
    return "flat"  # 默认
```

---

## 十一、故障恢复

### 索引损坏恢复

```python
class IndexRecoveryManager:
    """索引恢复管理器"""

    async def recover_from_backup(self, backup_path: str) -> bool:
        """从备份恢复索引"""

    async def validate_index(self) -> bool:
        """验证索引完整性"""

    async def rebuild_from_source(self) -> bool:
        """从源数据重建索引"""
```

---

## 十二、总结

### 核心改进

1. **集成索引工厂**: 使用已有 `FAISSIndexFactory`
2. **自适应选择**: 根据数据规模自动选择最优索引
3. **在线迁移**: 支持不停机切换索引类型
4. **性能监控**: 实时监控和自动优化建议

### 实施优先级

| 优先级 | 任务 | 工作量 | 影响 |
|--------|------|--------|------|
| P0 | 集成索引工厂 | 1天 | 启用配置驱动 |
| P0 | 自适应选择 | 1天 | 自动化优化 |
| P1 | 性能监控 | 1天 | 可观测性 |
| P1 | 在线迁移 | 2天 | 零停机升级 |
| P2 | GPU加速 | 3天 | 极致性能 |

### 预期收益

- **性能**: 10-1000x 搜索加速
- **内存**: 最高节省 99% 内存 (IVF-PQ)
- **成本**: 减少硬件需求
- **体验**: 更快的响应速度
