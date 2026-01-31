# Phase 1 Draft

## 用户需求
根据Phase 1内容制定完整计划，要求系统可以灵活切换不同检索能力，保持高扩展性。

## 核心设计决策

### 1. 架构模式
- **策略模式（Strategy Pattern）**: 统一的检索策略接口
- **工厂模式（Factory Pattern）**: 动态创建策略和索引
- **依赖注入**: 通过配置驱动，不硬编码

### 2. 检索策略接口
```python
class BaseRetrievalStrategy(ABC):
    @abstractmethod
    async def search(self, query: str, k: int = 5, **kwargs) -> List[Document]:
        pass

    @abstractmethod
    async def search_with_scores(self, query: str, k: int = 5, **kwargs) -> List[tuple]:
        pass
```

### 3. FAISS索引工厂
支持的索引类型：
- FlatL2（精确搜索，适合小规模）
- IVF-PQ（平衡精度和性能，适合中等规模）
- HNSW（最高性能，适合大规模）

### 4. 检索策略
- VectorRetrievalStrategy（基础向量检索）
- HybridRetrievalStrategy（向量+BM25混合检索）
- ParentChildRetrievalStrategy（父子索引检索）

### 5. 配置驱动
```python
# 配置文件切换策略
retrieval_strategy = "vector"  # 或 "hybrid", "parent_child"
faiss_index_type = "ivf_pq"  # 或 "flat", "hnsw"
```

## 实施分解

### Wave 1: 核心接口和工厂（3-4天）
1. 创建BaseRetrievalStrategy接口
2. 实现FAISSIndexFactory（支持3种索引类型）
3. 实现RetrievalStrategyFactory（策略注册和创建）

### Wave 2: 实现核心策略（5-6天）
1. VectorRetrievalStrategy（向量检索）
2. HybridRetrievalStrategy（混合检索+RRF）
3. ParentChildRetrievalStrategy（父子索引）

### Wave 3: 集成和配置（3-4天）
1. 更新config.py添加配置项
2. 更新依赖注入，支持动态策略创建

### Wave 4: API更新（2-3天）
1. 更新检索API，支持策略参数
2. 添加策略信息返回

## 预期收益

### 性能提升
| 场景 | 当前 | 优化后 | 提升 |
|------|------|--------|------|
| 小规模（<1K文档） | 80ms | 20ms | -75% |
| 中等规模（1K-10K文档） | 800ms | 40ms | -95% |
| 大规模（10K-100K文档） | 8s | 100ms | -98.75% |

### 扩展性
- 新策略添加：无需修改核心代码，只需实现接口
- 运行时切换：通过配置或API参数切换
- 插件化：支持第三方策略扩展

## 待确认问题
1. BM25库选择：Rank BM25 vs Whoosh vs 自实现
2. 索引迁移策略：渐进式迁移还是一次性重建
3. 性能基准：需要实际的测试数据集
