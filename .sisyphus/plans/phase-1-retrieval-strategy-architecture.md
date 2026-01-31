# Phase 1: 高扩展性检索架构实施计划

> **目标**: 设计并实现一个灵活、可扩展的检索策略架构，支持多种检索能力的动态切换
> **版本**: 1.0.0
> **预计时间**: 2-3周
> **状态**: 📋 待执行

---

## 📋 目录

- [项目概述](#项目概述)
- [架构设计](#架构设计)
- [核心接口设计](#核心接口设计)
- [实施任务](#实施任务)
- [验证策略](#验证策略)

---

## 项目概述

### 目标

将当前硬编码的检索服务重构为高扩展性的策略架构，支持：

1. **检索策略动态切换**: 通过配置文件切换不同的检索策略（向量、混合、父子索引等）
2. **FAISS索引类型切换**: 运行时切换不同的FAISS索引类型（Flat、IVF、HNSW）
3. **检索策略组合**: 支持多个检索策略的组合使用（链式调用）
4. **插件化扩展**: 新增检索策略只需实现接口，无需修改核心代码

### 核心原则

- **开闭原则**: 对扩展开放，对修改关闭
- **单一职责**: 每个策略只负责一种检索逻辑
- **依赖倒置**: 依赖抽象接口，不依赖具体实现
- **配置驱动**: 通过配置控制行为，不硬编码

---

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  POST /api/retrieval/search                        │  │
│  │  {                                                 │  │
│  │    "query": "...",                                │  │
│  │    "strategy": "hybrid"                            │  │
│  │  }                                                │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Retrieval Strategy Factory                    │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  get_retrieval_strategy(strategy_name, config)      │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  Vector  │    │  Hybrid  │    │  Parent  │
    │ Strategy │    │ Strategy │    │  Strategy│
    └──────────┘    └──────────┘    └──────────┘
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │FAISS Store│    │Vector+BM25│    │Child     │
    │(Config)  │    │          │    │Indexer   │
    └──────────┘    └──────────┘    └──────────┘
```

### 核心设计模式

#### 1. 策略模式（Strategy Pattern）

定义统一的检索策略接口，不同策略实现相同接口：

```python
# 抽象基类
class BaseRetrievalStrategy(ABC):
    @abstractmethod
    async def search(self, query: str, k: int = 5, **kwargs) -> List[Document]:
        pass

# 具体策略
class VectorRetrievalStrategy(BaseRetrievalStrategy):
    async def search(self, query: str, k: int = 5, **kwargs) -> List[Document]:
        # 向量检索逻辑
        pass

class HybridRetrievalStrategy(BaseRetrievalStrategy):
    async def search(self, query: str, k: int = 5, **kwargs) -> List[Document]:
        # 混合检索逻辑（向量+BM25）
        pass
```

#### 2. 工厂模式（Factory Pattern）

根据配置创建对应的检索策略：

```python
class RetrievalStrategyFactory:
    @staticmethod
    def create(strategy_name: str, config: Dict) -> BaseRetrievalStrategy:
        strategies = {
            "vector": VectorRetrievalStrategy,
            "hybrid": HybridRetrievalStrategy,
            "parent_child": ParentChildRetrievalStrategy,
        }

        strategy_class = strategies.get(strategy_name)
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        return strategy_class(config)
```

#### 3. 策略链模式（Chain of Responsibility）

支持多个策略的链式调用：

```python
class RetrievalStrategyChain:
    def __init__(self):
        self.strategies = []

    def add_strategy(self, strategy: BaseRetrievalStrategy):
        self.strategies.append(strategy)
        return self  # 支持链式调用

    async def execute(self, query: str, k: int = 5) -> List[Document]:
        all_results = []
        for strategy in self.strategies:
            results = await strategy.search(query, k=k)
            all_results.extend(results)
        return self._deduplicate_and_rank(all_results, k)
```

---

## 核心接口设计

### 1. 检索策略接口（`src/retrieval/strategies/base.py`）

```python
"""
Base retrieval strategy interface
All retrieval strategies must inherit from this interface
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from src.models.document import Document


class BaseRetrievalStrategy(ABC):
    """
    Abstract base class for retrieval strategies

    All retrieval strategies must implement this interface to ensure
    consistency and enable dynamic switching.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize retrieval strategy with configuration

        Args:
            config: Strategy-specific configuration
        """
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[Document]:
        """
        Execute search with this strategy

        Args:
            query: Search query text
            k: Number of results to return
            filter_dict: Optional metadata filters
            **kwargs: Additional strategy-specific parameters

        Returns:
            List of retrieved documents sorted by relevance
        """
        pass

    @abstractmethod
    async def search_with_scores(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[tuple[Document, float]]:
        """
        Execute search and return scores

        Args:
            query: Search query text
            k: Number of results to return
            filter_dict: Optional metadata filters
            **kwargs: Additional strategy-specific parameters

        Returns:
            List of (document, score) tuples
        """
        pass

    def get_config(self) -> Dict[str, Any]:
        """Get strategy configuration"""
        return self.config

    def get_name(self) -> str:
        """Get strategy name"""
        return self.name

    async def warmup(self) -> None:
        """
        Warmup strategy (optional)

        Called after initialization to prepare resources.
        Override if strategy needs warmup (e.g., loading models).
        """
        pass

    async def cleanup(self) -> None:
        """
        Cleanup resources (optional)

        Called when strategy is no longer needed.
        Override if strategy needs to cleanup resources.
        """
        pass
```

### 2. FAISS索引接口（`src/vector/faiss_index_factory.py`）

```python
"""
FAISS index factory for creating different index types
Supports dynamic index type switching
"""

import faiss
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseFAISSIndex(ABC):
    """Abstract base class for FAISS index wrappers"""

    def __init__(self, dimension: int, config: Dict[str, Any]):
        self.dimension = dimension
        self.config = config
        self.index = None

    @abstractmethod
    def create_index(self) -> faiss.Index:
        """Create FAISS index"""
        pass

    @abstractmethod
    def train_index(self, vectors: list) -> None:
        """Train index (if needed)"""
        pass

    def get_index(self) -> faiss.Index:
        """Get FAISS index"""
        if self.index is None:
            self.index = self.create_index()
        return self.index


class FlatL2Index(BaseFAISSIndex):
    """Flat L2 index (exact search, no training)"""

    def create_index(self) -> faiss.Index:
        logger.info("Creating FlatL2 index for exact search")
        return faiss.IndexFlatL2(self.dimension)

    def train_index(self, vectors: list) -> None:
        # Flat index doesn't need training
        pass


class IVFPQIndex(BaseFAISSIndex):
    """
    IVF-PQ index (approximate search, needs training)

    Parameters:
        - nlist: Number of clusters (default: 100)
        - m: Number of subquantizers (default: 64)
        - nbits: Bits per subquantizer (default: 8)
    """

    def create_index(self) -> faiss.Index:
        nlist = self.config.get("nlist", 100)
        m = self.config.get("m", 64)
        nbits = self.config.get("nbits", 8)

        logger.info(
            f"Creating IVF-PQ index: nlist={nlist}, m={m}, nbits={nbits}"
        )

        quantizer = faiss.IndexFlatL2(self.dimension)
        index = faiss.IndexIVFPQ(quantizer, self.dimension, nlist, m, nbits)
        return index

    def train_index(self, vectors: list) -> None:
        if self.index.is_trained:
            logger.info("Index already trained, skipping")
            return

        logger.info(f"Training IVF-PQ index with {len(vectors)} vectors")
        import numpy as np

        train_vectors = np.array(vectors).astype('float32')
        self.index.train(train_vectors)
        logger.info("IVF-PQ index training completed")


class HNSWIndex(BaseFAISSIndex):
    """
    HNSW index (graph-based approximate search)

    Parameters:
        - M: Number of connections per node (default: 32)
        - efConstruction: Build-time ef (default: 200)
        - efSearch: Search-time ef (default: 64)
    """

    def create_index(self) -> faiss.Index:
        M = self.config.get("M", 32)

        logger.info(f"Creating HNSW index: M={M}")
        return faiss.IndexHNSWFlat(self.dimension, M)

    def train_index(self, vectors: list) -> None:
        # HNSW doesn't need explicit training
        pass

    def configure_search(self, ef_search: int):
        """Configure search-time ef parameter"""
        ef_search = self.config.get("efSearch", 64)
        self.index.hnsw.efSearch = ef_search
        logger.info(f"HNSW efSearch configured: {ef_search}")


class FAISSIndexFactory:
    """Factory for creating FAISS indexes"""

    _index_types = {
        "flat": FlatL2Index,
        "ivf_pq": IVFPQIndex,
        "hnsw": HNSWIndex,
    }

    @classmethod
    def create_index(
        self,
        index_type: str,
        dimension: int,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseFAISSIndex:
        """
        Create FAISS index

        Args:
            index_type: Index type (flat, ivf_pq, hnsw)
            dimension: Vector dimension
            config: Index-specific configuration

        Returns:
            FAISS index wrapper instance

        Raises:
            ValueError: If index_type is unknown
        """
        config = config or {}
        index_class = self._index_types.get(index_type.lower())

        if not index_class:
            available = ", ".join(self._index_types.keys())
            raise ValueError(
                f"Unknown index type: {index_type}. "
                f"Available types: {available}"
            )

        logger.info(f"Creating FAISS index type: {index_type}")
        return index_class(dimension, config)

    @classmethod
    def get_available_types(cls) -> list:
        """Get list of available index types"""
        return list(cls._index_types.keys())
```

### 3. 检索策略工厂（`src/retrieval/strategies/factory.py`）

```python
"""
Retrieval strategy factory
Creates retrieval strategies based on configuration
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class RetrievalStrategyFactory:
    """
    Factory for creating retrieval strategies

    Supports dynamic strategy creation based on configuration.
    """

    # Registry of available strategies
    _strategies = {}

    @classmethod
    def register(cls, name: str, strategy_class):
        """
        Register a retrieval strategy

        Args:
            name: Strategy name
            strategy_class: Strategy class
        """
        cls._strategies[name] = strategy_class
        logger.info(f"Registered retrieval strategy: {name}")

    @classmethod
    def create(
        cls,
        strategy_name: str,
        config: Dict[str, Any],
        dependencies: Optional[Dict[str, Any]] = None
    ):
        """
        Create a retrieval strategy

        Args:
            strategy_name: Name of strategy to create
            config: Strategy configuration
            dependencies: Required dependencies (vector_store, embedding_service, etc.)

        Returns:
            Strategy instance

        Raises:
            ValueError: If strategy_name is unknown
        """
        strategy_class = cls._strategies.get(strategy_name)

        if not strategy_class:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unknown strategy: {strategy_name}. "
                f"Available strategies: {available}"
            )

        logger.info(f"Creating retrieval strategy: {strategy_name}")

        # Merge config with dependencies
        full_config = {**config}
        if dependencies:
            full_config.update(dependencies)

        return strategy_class(full_config)

    @classmethod
    def get_available_strategies(cls) -> list:
        """Get list of available strategies"""
        return list(cls._strategies.keys())

    @classmethod
    def auto_register(cls):
        """
        Auto-register all strategy classes in the strategies module

        This method scans the strategies module and registers all
        classes that inherit from BaseRetrievalStrategy.
        """
        import importlib
        import inspect
        from .base import BaseRetrievalStrategy

        # Import all modules in strategies package
        modules = []
        try:
            from . import vector_strategy
            modules.append(vector_strategy)
        except ImportError:
            pass

        try:
            from . import hybrid_strategy
            modules.append(hybrid_strategy)
        except ImportError:
            pass

        try:
            from . import parent_child_strategy
            modules.append(parent_child_strategy)
        except ImportError:
            pass

        # Register all strategy classes
        for module in modules:
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BaseRetrievalStrategy) and
                    obj is not BaseRetrievalStrategy):
                    strategy_name = name.replace("Strategy", "").lower()
                    cls.register(strategy_name, obj)
```

---

## 实施任务

### Wave 1: 核心接口和工厂（3-4天）

#### 任务 1.1: 创建基础接口

**What to do**:
- 创建 `src/retrieval/strategies/` 目录
- 创建 `src/retrieval/strategies/__init__.py`
- 创建 `src/retrieval/strategies/base.py`（BaseRetrievalStrategy接口）

**Recommended Agent Profile**:
- Category: `unspecified-low`
- Skills: `[]`

**Parallelization**:
- Can Run In Parallel: NO
- Parallel Group: Wave 1 Sequential
- Blocks: Wave 2

**Acceptance Criteria**:
```python
# Test: BaseRetrievalStrategy can be imported
from src.retrieval.strategies.base import BaseRetrievalStrategy

# Test: Abstract methods are defined
import inspect
methods = inspect.getmembers(BaseRetrievalStrategy, predicate=inspect.ismethod)
abstract_methods = [
    name for name, method in methods
    if getattr(method, '__isabstractmethod__', False)
]
assert 'search' in abstract_methods
assert 'search_with_scores' in abstract_methods
print("PASS: BaseRetrievalStrategy interface defined")
```

#### 任务 1.2: 实现FAISS索引工厂

**What to do**:
- 创建 `src/vector/faiss_index_factory.py`
- 实现BaseFAISSIndex抽象类
- 实现FlatL2Index、IVFPQIndex、HNSWIndex
- 实现FAISSIndexFactory工厂类

**Recommended Agent Profile**:
- Category: `unspecified-low`
- Skills: `[]`

**Parallelization**:
- Can Run In Parallel: YES (with 1.1)
- Parallel Group: Wave 1
- Blocks: Wave 2

**Acceptance Criteria**:
```python
# Test: Create different index types
from src.vector.faiss_index_factory import FAISSIndexFactory

# Flat index
flat_index = FAISSIndexFactory.create_index("flat", 1536, {})
assert flat_index.get_index() is not None
print("PASS: Flat index created")

# IVF-PQ index
ivf_config = {"nlist": 100, "m": 64, "nbits": 8}
ivf_index = FAISSIndexFactory.create_index("ivf_pq", 1536, ivf_config)
assert ivf_index.get_index() is not None
print("PASS: IVF-PQ index created")

# HNSW index
hnsw_config = {"M": 32, "efSearch": 64}
hnsw_index = FAISSIndexFactory.create_index("hnsw", 1536, hnsw_config)
assert hnsw_index.get_index() is not None
print("PASS: HNSW index created")

# Test: Get available types
types = FAISSIndexFactory.get_available_types()
assert "flat" in types
assert "ivf_pq" in types
assert "hnsw" in types
print("PASS: All index types available")
```

#### 任务 1.3: 实现检索策略工厂

**What to do**:
- 创建 `src/retrieval/strategies/factory.py`
- 实现RetrievalStrategyFactory类
- 实现策略注册机制
- 实现自动注册功能

**Recommended Agent Profile**:
- Category: `unspecified-low`
- Skills: `[]`

**Parallelization**:
- Can Run In Parallel: NO
- Parallel Group: Wave 1 Sequential (depends on 1.1)
- Blocks: Wave 2

**Acceptance Criteria**:
```python
# Test: Factory can be imported
from src.retrieval.strategies.factory import RetrievalStrategyFactory

# Test: Get available strategies
strategies = RetrievalStrategyFactory.get_available_strategies()
assert len(strategies) > 0
print(f"PASS: Available strategies: {strategies}")

# Test: Create strategy (after implementation in Wave 2)
try:
    strategy = RetrievalStrategyFactory.create(
        "vector",
        {"test": True},
        {"vector_store": None}
    )
    print("PASS: Strategy created via factory")
except Exception as e:
    print(f"SKIP: Strategy not yet implemented: {e}")
```

---

### Wave 2: 实现核心策略（5-6天）

#### 任务 2.1: 实现向量检索策略

**What to do**:
- 创建 `src/retrieval/strategies/vector_strategy.py`
- 实现VectorRetrievalStrategy类
- 继承BaseRetrievalStrategy
- 集成FAISSVectorStore和FAISS索引工厂

**Recommended Agent Profile**:
- Category: `unspecified-low`
- Skills: `[]`

**Parallelization**:
- Can Run In Parallel: NO
- Parallel Group: Wave 2 Sequential
- Blocks: Wave 3

**Acceptance Criteria**:
```python
# Test: Vector strategy can be imported and instantiated
from src.retrieval.strategies.vector_strategy import VectorRetrievalStrategy
from src.vector.faiss_index_factory import FAISSIndexFactory

# Create index
index = FAISSIndexFactory.create_index("flat", 1536, {})

# Create strategy
strategy = VectorRetrievalStrategy({
    "index": index,
    "embedding_service": None,
    "use_reranking": False
})

# Test: Search method exists
assert hasattr(strategy, 'search')
assert hasattr(strategy, 'search_with_scores')
print("PASS: VectorRetrievalStrategy implemented")
```

#### 任务 2.2: 实现混合检索策略

**What to do**:
- 创建 `src/retrieval/strategies/hybrid_strategy.py`
- 实现HybridRetrievalStrategy类
- 集成BM25+向量检索
- 实现RRF（Reciprocal Rank Fusion）融合算法

**Recommended Agent Profile**:
- Category: `unspecified-low`
- Skills: `[]`

**Parallelization**:
- Can Run In Parallel: NO
- Parallel Group: Wave 2 Sequential
- Blocks: Wave 3

**Acceptance Criteria**:
```python
# Test: Hybrid strategy can be imported
from src.retrieval.strategies.hybrid_strategy import HybridRetrievalStrategy

# Create strategy
strategy = HybridRetrievalStrategy({
    "vector_store": None,
    "bm25_index": None,
    "alpha": 0.7  # Vector weight
})

# Test: Search method exists
assert hasattr(strategy, 'search')
assert hasattr(strategy, 'reciprocal_rank_fusion')
print("PASS: HybridRetrievalStrategy implemented")
```

#### 任务 2.3: 实现父子索引策略

**What to do**:
- 创建 `src/retrieval/strategies/parent_child_strategy.py`
- 实现ParentChildRetrievalStrategy类
- 实现父子分块逻辑
- 实现检索去重策略

**Recommended Agent Profile**:
- Category: `unspecified-low`
- Skills: `[]`

**Parallelization**:
- Can Run In Parallel: YES (with 2.1)
- Parallel Group: Wave 2
- Blocks: Wave 3

**Acceptance Criteria**:
```python
# Test: Parent-child strategy can be imported
from src.retrieval.strategies.parent_child_strategy import ParentChildRetrievalStrategy

# Create strategy
strategy = ParentChildRetrievalStrategy({
    "vector_store": None,
    "parent_chunk_size": 2000,
    "child_chunk_size": 400
})

# Test: Search and index methods exist
assert hasattr(strategy, 'search')
assert hasattr(strategy, 'index_document')
print("PASS: ParentChildRetrievalStrategy implemented")
```

---

### Wave 3: 集成和配置（3-4天）

#### 任务 3.1: 更新配置文件

**What to do**:
- 修改 `config.py`
- 添加检索策略配置
- 添加FAISS索引类型配置
- 添加混合检索权重配置

**配置项**:
```python
# 检索策略配置
retrieval_strategy: str = "vector"  # vector, hybrid, parent_child
retrieval_strategy_config: Dict[str, Any] = Field(
    default_factory=lambda: {
        "use_reranking": True,
        "reranker_top_k": 20,
    }
)

# FAISS索引配置
faiss_index_type: str = "ivf_pq"  # flat, ivf_pq, hnsw
faiss_index_config: Dict[str, Any] = Field(
    default_factory=lambda: {
        "nlist": 100,
        "m": 64,
        "nbits": 8,
        "M": 32,
        "efSearch": 64,
    }
)

# 混合检索配置
hybrid_retrieval_config: Dict[str, Any] = Field(
    default_factory=lambda: {
        "alpha": 0.7,  # Vector weight
        "bm25_k1": 1.2,
        "bm25_b": 0.75,
    }
)

# 父子索引配置
parent_child_config: Dict[str, Any] = Field(
    default_factory=lambda: {
        "parent_chunk_size": 2000,
        "child_chunk_size": 400,
        "chunk_overlap": 50,
    }
)
```

**Recommended Agent Profile**:
- Category: `quick`
- Skills: `[]`

**Parallelization**:
- Can Run In Parallel: NO
- Parallel Group: Wave 3 Sequential
- Blocks: Wave 4

**Acceptance Criteria**:
```python
# Test: Config can be imported
from config import settings

# Test: New config fields exist
assert hasattr(settings, 'retrieval_strategy')
assert hasattr(settings, 'faiss_index_type')
assert hasattr(settings, 'hybrid_retrieval_config')
assert hasattr(settings, 'parent_child_config')

# Test: Default values
assert settings.retrieval_strategy == "vector"
assert settings.faiss_index_type == "ivf_pq"
print("PASS: Configuration updated")
```

#### 任务 3.2: 更新依赖注入

**What to do**:
- 修改 `src/api/dependencies.py`
- 添加 `get_retrieval_strategy()` 函数
- 更新 `get_vector_store()` 使用FAISS索引工厂
- 支持策略的动态切换

**Recommended Agent Profile**:
- Category: `quick`
- Skills: `[]`

**Parallelization**:
- Can Run In Parallel: YES (with 3.1)
- Parallel Group: Wave 3
- Blocks: Wave 4

**Acceptance Criteria**:
```python
# Test: New dependency function exists
from src.api.dependencies import get_retrieval_strategy

# Test: Strategy can be retrieved
strategy = get_retrieval_strategy()
assert strategy is not None
assert hasattr(strategy, 'search')
print(f"PASS: Retrieval strategy injected: {strategy.get_name()}")
```

---

### Wave 4: API更新（2-3天）

#### 任务 4.1: 更新检索API

**What to do**:
- 修改 `src/api/routes/retrieval.py`
- 添加策略切换支持
- 添加策略信息返回
- 更新API文档

**API更新**:
```python
@router.post("/search")
async def search(
    request: SearchRequest,
    strategy: str = None,  # Optional strategy override
    strategy_factory: RetrievalStrategyFactory = Depends(get_strategy_factory),
):
    """
    Search with configurable strategy

    Args:
        request: Search request with query and parameters
        strategy: Optional strategy name to override default

    Returns:
        Search results with strategy info
    """
    # Use strategy from request or default from config
    strategy_name = strategy or settings.retrieval_strategy

    # Get strategy
    strategy = strategy_factory.create(
        strategy_name,
        settings.retrieval_strategy_config,
        {
            "vector_store": vector_store,
            "embedding_service": embedding_service
        }
    )

    # Execute search
    results = await strategy.search(
        query=request.query,
        k=request.k,
        filter_dict=request.filter_dict
    )

    return {
        "query": request.query,
        "strategy": strategy_name,
        "total": len(results),
        "results": results
    }
```

**Recommended Agent Profile**:
- Category: `visual-engineering`
- Skills: `["frontend-ui-ux"]`

**Parallelization**:
- Can Run In Parallel: NO
- Parallel Group: Wave 4 Sequential
- Blocks: None

**Acceptance Criteria**:
```python
# Test: API supports strategy parameter
# (Detailed API testing with Playwright)
```

---

## 验证策略

### 单元测试

```python
# tests/test_strategies.py
import pytest
from src.retrieval.strategies.base import BaseRetrievalStrategy
from src.retrieval.strategies.factory import RetrievalStrategyFactory


class TestRetrievalStrategies:

    def test_base_strategy_interface(self):
        """Test BaseRetrievalStrategy interface"""
        # Cannot instantiate abstract class
        with pytest.raises(TypeError):
            BaseRetrievalStrategy({})

    def test_vector_strategy_search(self):
        """Test vector retrieval strategy"""
        from src.retrieval.strategies.vector_strategy import VectorRetrievalStrategy

        # Implementation test
        strategy = VectorRetrievalStrategy({})

        # Should have search methods
        assert hasattr(strategy, 'search')
        assert hasattr(strategy, 'search_with_scores')

    def test_hybrid_strategy_rrf(self):
        """Test hybrid strategy RRF fusion"""
        from src.retrieval.strategies.hybrid_strategy import HybridRetrievalStrategy

        strategy = HybridRetrievalStrategy({})

        # Should have RRF method
        assert hasattr(strategy, 'reciprocal_rank_fusion')

    def test_strategy_factory(self):
        """Test strategy factory"""
        # Get available strategies
        strategies = RetrievalStrategyFactory.get_available_strategies()
        assert len(strategies) > 0


class TestFAISSIndexFactory:

    def test_create_flat_index(self):
        """Test creating Flat index"""
        from src.vector.faiss_index_factory import FAISSIndexFactory

        index = FAISSIndexFactory.create_index("flat", 1536, {})
        assert index is not None
        assert index.get_index() is not None

    def test_create_ivf_pq_index(self):
        """Test creating IVF-PQ index"""
        from src.vector.faiss_index_factory import FAISSIndexFactory

        config = {"nlist": 100, "m": 64, "nbits": 8}
        index = FAISSIndexFactory.create_index("ivf_pq", 1536, config)
        assert index is not None

    def test_create_hnsw_index(self):
        """Test creating HNSW index"""
        from src.vector.faiss_index_factory import FAISSIndexFactory

        config = {"M": 32, "efSearch": 64}
        index = FAISSIndexFactory.create_index("hnsw", 1536, config)
        assert index is not None
```

### 集成测试

```python
# tests/test_retrieval_integration.py
import pytest
from src.api.dependencies import get_retrieval_strategy


class TestRetrievalIntegration:

    @pytest.mark.asyncio
    async def test_vector_retrieval(self):
        """Test vector retrieval end-to-end"""
        strategy = get_retrieval_strategy()

        # Execute search
        results = await strategy.search("test query", k=5)

        # Verify results
        assert isinstance(results, list)
        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_strategy_switching(self):
        """Test strategy switching via config"""
        # Test with vector strategy
        # (Setup config for vector)
        strategy = get_retrieval_strategy()
        assert strategy.get_name() == "VectorRetrievalStrategy"

        # Test with hybrid strategy
        # (Setup config for hybrid)
        strategy = get_retrieval_strategy()
        assert strategy.get_name() == "HybridRetrievalStrategy"
```

### 性能测试

```python
# tests/test_performance.py
import pytest
import time


class TestRetrievalPerformance:

    @pytest.mark.asyncio
    async def test_flat_index_performance(self):
        """Test Flat index performance"""
        from src.vector.faiss_index_factory import FAISSIndexFactory

        # Create index
        index = FAISSIndexFactory.create_index("flat", 1536, {})

        # Measure search time
        start = time.time()
        # (Execute search)
        end = time.time()

        # Should be fast (< 100ms for small index)
        assert (end - start) < 0.1

    @pytest.mark.asyncio
    async def test_ivf_pq_performance(self):
        """Test IVF-PQ index performance"""
        from src.vector.faiss_index_factory import FAISSIndexFactory

        # Create index
        config = {"nlist": 100, "m": 64, "nbits": 8}
        index = FAISSIndexFactory.create_index("ivf_pq", 1536, config)

        # Measure search time
        start = time.time()
        # (Execute search)
        end = time.time()

        # Should be faster than Flat for large indexes
        assert (end - start) < 0.05
```

---

## 使用示例

### 1. 基础使用（向量检索）

```python
# config.py
retrieval_strategy = "vector"
faiss_index_type = "flat"
```

### 2. 混合检索

```python
# config.py
retrieval_strategy = "hybrid"
faiss_index_type = "ivf_pq"

hybrid_retrieval_config = {
    "alpha": 0.7,  # 70% vector, 30% BM25
    "bm25_k1": 1.2,
    "bm25_b": 0.75
}
```

### 3. 父子索引

```python
# config.py
retrieval_strategy = "parent_child"

parent_child_config = {
    "parent_chunk_size": 2000,
    "child_chunk_size": 400,
    "chunk_overlap": 50
}
```

### 4. 运行时切换策略

```python
# API调用
response = await client.post("/api/retrieval/search", json={
    "query": "test query",
    "k": 5,
    "strategy": "hybrid"  # Override default strategy
})
```

---

## 扩展性展示

### 添加新检索策略

只需3步，无需修改核心代码：

```python
# 1. 创建新策略
# src/retrieval/strategies/semantic_strategy.py
from .base import BaseRetrievalStrategy

class SemanticRetrievalStrategy(BaseRetrievalStrategy):
    async def search(self, query: str, k: int = 5, **kwargs):
        # 自定义语义检索逻辑
        pass

# 2. 注册策略
# src/retrieval/strategies/__init__.py
from .semantic_strategy import SemanticRetrievalStrategy
RetrievalStrategyFactory.register("semantic", SemanticRetrievalStrategy)

# 3. 配置使用
# config.py
retrieval_strategy = "semantic"
```

### 添加新FAISS索引类型

同样只需3步：

```python
# 1. 创建新索引类型
# src/vector/faiss_index_factory.py
class IVFFlatIndex(BaseFAISSIndex):
    def create_index(self) -> faiss.Index:
        nlist = self.config.get("nlist", 100)
        quantizer = faiss.IndexFlatL2(self.dimension)
        return faiss.IndexIVFFlat(quantizer, self.dimension, nlist)

# 2. 注册到工厂
FAISSIndexFactory._index_types["ivf_flat"] = IVFFlatIndex

# 3. 配置使用
faiss_index_type = "ivf_flat"
```

---

## 预期成果

### 功能指标

| 指标 | 目标值 | 验证方法 |
|------|-------|---------|
| 策略切换时间 | < 10ms | 单元测试 |
| 索引类型切换 | 无需重启 | 集成测试 |
| 新策略添加 | < 1小时 | 代码审查 |
| 系统兼容性 | 100% | 回归测试 |

### 性能指标

| 场景 | 当前 | 优化后 | 提升 |
|------|------|--------|------|
| 小规模检索（<1K文档） | 80ms | 20ms | -75% |
| 中等规模（1K-10K文档） | 800ms | 40ms | -95% |
| 大规模（10K-100K文档） | 8s | 100ms | -98.75% |

### 代码质量

| 指标 | 目标值 |
|------|-------|
| 接口覆盖率 | 100% |
| 单元测试覆盖率 | >90% |
| 集成测试覆盖率 | >80% |
| 代码复用率 | >70% |

---

## 风险评估

### 高风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| FAISS索引切换不兼容 | 高 | 保留原始索引备份，渐进式迁移 |
| 检索结果差异 | 中 | 详细的对比测试，保留旧策略作为fallback |

### 中风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 性能回退 | 中 | 性能基准测试，确保优化效果 |
| 配置复杂度 | 低 | 提供配置模板和文档 |

---

## 总结

本实施计划提供了：

1. ✅ 完整的架构设计（策略模式+工厂模式）
2. ✅ 核心接口定义（BaseRetrievalStrategy、FAISSIndexFactory）
3. ✅ 3种核心策略实现（向量、混合、父子索引）
4. ✅ 配置驱动的策略切换
5. ✅ 插件化的扩展机制
6. ✅ 详细的任务分解和验证标准

**下一步**: 运行 `/start-work` 开始执行！

---

**计划生成时间**: 2026-01-31
**计划版本**: 1.0.0

---

## ✅ 关键决策（已确认）

### 决策1: BM25库选择 ✅

**用户选择**: **Rank BM25**（rank-bm25库）

**理由**:
- ✅ 纯Python实现，无额外C++依赖
- ✅ API简洁（`index = BM25Okapi(tokenized_corpus)`）
- ✅ 适合中小规模数据（<50K文档）
- ✅ 性能满足当前系统需求
- ✅ 易于安装：`pip install rank-bm25`

**配置示例**:
```python
# requirements.txt
rank-bm25==0.2.2

# config.py
hybrid_retrieval_config = {
    "alpha": 0.7,  # Vector weight
    "bm25_k1": 1.2,
    "bm25_b": 0.75,
    "use_rank_bm25": True
}
```

---

### 决策2: FAISS索引迁移策略 ✅

**用户选择**: **渐进式迁移**（推荐方案）

**迁移步骤**:
1. **备份现有索引**
   ```bash
   cp -r data/faiss_index data/faiss_index_backup_flatl2
   ```

2. **后台异步构建新索引**
   ```python
   # 在独立任务中执行
   async def migrate_index_task():
       # 1. 读取现有文档
       documents = vector_store.get_all_documents()
       
       # 2. 创建新索引（IVF-PQ）
       new_index = FAISSIndexFactory.create_index(
           "ivf_pq", 
           dimension=1536,
           config={"nlist": 100, "m": 64, "nbits": 8}
       )
       
       # 3. 训练并添加文档
       vectors = [doc.vector for doc in documents]
       new_index.train_index(vectors)
       new_index.add_documents(documents)
       
       # 4. 保存新索引到临时位置
       new_index.save_local("data/faiss_index_ivfpq_new")
   ```

3. **配置切换（服务不中断）**
   ```python
   # config.py
   faiss_index_path = "./data/faiss_index_ivfpq_new"
   faiss_index_type = "ivf_pq"
   ```

4. **验证新索引功能**
   ```python
   # 验证脚本
   async def verify_index():
       results = await retrieval_service.search("test query", k=5)
       assert len(results) > 0
       assert results[0].score > 0.5
       print("✅ New index verified")
   ```

5. **删除旧索引**
   ```bash
   # 验证通过后，清理旧索引
   rm -rf data/faiss_index_backup_flatl2
   ```

**迁移时间估算**:
| 数据规模 | 文档数 | 迁移时间 | 停机时间 |
|---------|-------|---------|---------|
| 小规模 | <1K | <5分钟 | 0秒（后台迁移） |
| 中规模 | 1K-10K | 10-30分钟 | 0秒 |
| 大规模 | 10K-100K | 30-120分钟 | 0秒 |

**风险缓解**:
- ✅ 保留原始索引备份
- ✅ 新索引独立验证
- ✅ 配置热更新（无需重启）
- ✅ 自动回滚机制

---

### 决策3: 性能测试策略 ✅

**用户选择**: **完整的性能基准测试**

**测试场景矩阵**:

| 测试ID | 数据规模 | 文档数 | 策略 | 索引类型 | 目标响应 |
|--------|---------|-------|------|---------|---------|
| T1 | 小规模 | 1K | Vector | Flat | <20ms |
| T2 | 小规模 | 1K | Hybrid | Flat | <30ms |
| T3 | 中规模 | 10K | Vector | IVF-PQ | <40ms |
| T4 | 中规模 | 10K | Hybrid | IVF-PQ | <50ms |
| T5 | 大规模 | 100K | Vector | HNSW | <100ms |
| T6 | 大规模 | 100K | Hybrid | HNSW | <150ms |

**测试维度**:
1. **检索响应时间**（P50、P95、P99）
2. **内存占用**（峰值、平均）
3. **索引构建时间**
4. **检索准确率**（与FlatL2的召回率对比）
5. **并发性能**（QPS）

**测试工具**:
```python
# tests/performance/benchmark_retrieval.py
import pytest
import time
import statistics
from src.retrieval.strategies.factory import RetrievalStrategyFactory

class TestRetrievalPerformance:
    
    @pytest.mark.parametrize("test_id,strategy,index_type,k,expected_max_time", [
        ("T1", "vector", "flat", 5, 20),
        ("T2", "hybrid", "flat", 5, 30),
        ("T3", "vector", "ivf_pq", 5, 40),
        ("T4", "hybrid", "ivf_pq", 5, 50),
        ("T5", "vector", "hnsw", 5, 100),
        ("T6", "hybrid", "hnsw", 5, 150),
    ])
    @pytest.mark.asyncio
    async def test_search_performance(
        self, test_id, strategy, index_type, k, expected_max_time
    ):
        """Test search performance"""
        
        # Create strategy
        strategy_instance = RetrievalStrategyFactory.create(
            strategy,
            {},
            {"vector_store": vector_store}
        )
        
        # Warmup
        for _ in range(10):
            await strategy_instance.search("warmup query", k=k)
        
        # Measure 100 searches
        times = []
        for _ in range(100):
            start = time.time()
            await strategy_instance.search("test query", k=k)
            times.append((time.time() - start) * 1000)  # Convert to ms
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
        p99_time = statistics.quantiles(times, n=100)[98]  # 99th percentile
        
        # Assert performance
        assert avg_time < expected_max_time * 0.7, \
            f"{test_id}: Average time {avg_time:.2f}ms exceeds target {expected_max_time * 0.7:.2f}ms"
        
        print(f"{test_id}: Avg={avg_time:.2f}ms, P95={p95_time:.2f}ms, P99={p99_time:.2f}ms")
```

**性能报告模板**:
```markdown
# 检索性能基准测试报告

**测试日期**: 2026-01-31
**测试数据**: 100K文档
**测试环境**: CPU 8核, RAM 32GB

## 检索响应时间（ms）

| 测试ID | 平均 | P50 | P95 | P99 | 目标 | 状态 |
|--------|------|-----|-----|-----|------|------|
| T1 | 15.2 | 14.1 | 18.3 | 22.5 | <20 | ✅ |
| T2 | 22.8 | 21.3 | 27.1 | 32.5 | <30 | ✅ |
| T3 | 35.6 | 33.2 | 41.8 | 49.2 | <40 | ✅ |
| T4 | 43.2 | 40.5 | 52.3 | 61.8 | <50 | ✅ |
| T5 | 85.3 | 78.2 | 102.4 | 123.5 | <100 | ✅ |
| T6 | 128.7 | 115.6 | 152.3 | 184.2 | <150 | ✅ |

## 内存占用（MB）

| 索引类型 | 数据规模 | 内存占用 | 磁盘占用 |
|---------|---------|---------|---------|
| Flat | 100K | 450 | 380 |
| IVF-PQ | 100K | 280 | 240 |
| HNSW | 100K | 320 | 290 |

## 结论

✅ 所有测试场景均满足性能目标
✅ IVF-PQ提供最佳性价比（内存-37.5%，性能-84%）
✅ HNSW适合大规模高并发场景

**推荐配置**: 
- <10K文档: Flat索引
- 10K-100K文档: IVF-PQ索引
- >100K文档: HNSW索引
```

---

## 📋 实施检查清单

### Wave 1 前置条件
- [ ] 确认BM25库已安装（rank-bm25==0.2.2）
- [ ] 确认FAISS版本兼容（faiss-cpu>=1.7.0）
- [ ] 备份现有FAISS索引
- [ ] 准备测试数据集

### Wave 2 实施中
- [ ] 每个策略实现后运行单元测试
- [ ] 每个索引类型构建后验证功能
- [ ] 代码审查通过后进入下一Wave

### Wave 3 集成后
- [ ] 配置文件更新生效
- [ ] 依赖注入测试通过
- [ ] 策略切换功能验证

### Wave 4 完成后
- [ ] API端点功能测试
- [ ] 性能基准测试完成
- [ ] 性能报告生成
- [ ] 用户文档更新

---

