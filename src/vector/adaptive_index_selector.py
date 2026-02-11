"""
自适应索引选择器
根据数据规模、查询模式、硬件资源自动选择最优FAISS索引
"""

import logging
import math
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AdaptiveIndexSelector:
    """
    自适应索引选择器

    决策逻辑:
    - <10K: Flat (精确搜索)
    - 10K-100K: IVF (平衡)
    - 100K-1M: IVF 或 IVF-PQ (内存受限)
    - >1M: HNSW (最快)
    """

    # 索引类型阈值
    THRESHOLD_FLAT = 10000      # 10K
    THRESHOLD_IVF = 100000      # 100K
    THRESHOLD_LARGE = 1000000   # 1M

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.memory_limit_mb = self.config.get("memory_limit_mb", 4096)
        self.target_latency_ms = self.config.get("target_latency_ms", 100)
        self.prefer_accuracy = self.config.get("prefer_accuracy", True)

    def select_index(
        self,
        vector_count: int,
        dimension: int,
        current_index_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        选择最优索引类型

        Args:
            vector_count: 向量数量
            dimension: 向量维度
            current_index_type: 当前索引类型（用于评估是否需要迁移）

        Returns:
            {
                "index_type": "hnsw",
                "config": {...},
                "reason": "...",
                "should_migrate": False
            }
        """
        # 估算内存占用
        estimated_memory_mb = self._estimate_memory(vector_count, dimension, "flat")

        # 决策逻辑
        if vector_count < self.THRESHOLD_FLAT:
            return self._select_flat(vector_count, dimension)
        elif vector_count < self.THRESHOLD_IVF:
            return self._select_ivf(vector_count, dimension)
        elif vector_count < self.THRESHOLD_LARGE:
            # 检查内存限制
            if estimated_memory_mb > self.memory_limit_mb * 0.5:
                return self._select_ivf_pq(vector_count, dimension)
            else:
                return self._select_ivf(vector_count, dimension)
        else:
            # 大规模数据，根据延迟要求选择
            if self.target_latency_ms < 50:
                return self._select_hnsw(vector_count, dimension)
            else:
                # 延迟要求不严格，考虑内存
                if estimated_memory_mb > self.memory_limit_mb * 0.7:
                    return self._select_ivf_pq(vector_count, dimension)
                else:
                    return self._select_hnsw(vector_count, dimension)

    def _select_flat(self, vector_count: int, dimension: int) -> Dict[str, Any]:
        """选择 Flat 索引"""
        return {
            "index_type": "flat",
            "config": {
                "metric": "L2"
            },
            "reason": f"Vector count ({vector_count}) < {self.THRESHOLD_FLAT}, using exact search",
            "should_migrate": False,
            "estimated_memory_mb": self._estimate_memory(vector_count, dimension, "flat"),
            "estimated_latency_ms": self._estimate_latency(vector_count, "flat")
        }

    def _select_ivf(self, vector_count: int, dimension: int) -> Dict[str, Any]:
        """选择 IVF 索引"""
        # 自动计算 nlist (聚类中心数)
        nlist = min(100, int(math.sqrt(vector_count)))
        nprobe = max(1, int(nlist * 0.1))

        return {
            "index_type": "ivf",
            "config": {
                "nlist": nlist,
                "nprobe": nprobe,
                "metric": "L2"
            },
            "reason": f"Vector count ({vector_count}) in range [{self.THRESHOLD_FLAT}, {self.THRESHOLD_IVF}], using IVF",
            "should_migrate": False,
            "estimated_memory_mb": self._estimate_memory(vector_count, dimension, "ivf"),
            "estimated_latency_ms": self._estimate_latency(vector_count, "ivf")
        }

    def _select_ivf_pq(self, vector_count: int, dimension: int) -> Dict[str, Any]:
        """选择 IVF-PQ 索引（压缩）"""
        nlist = min(100, int(math.sqrt(vector_count)))
        nprobe = max(1, int(nlist * 0.1))

        # PQ 参数
        m = min(64, dimension)  # 子量化器数
        nbits = 8

        return {
            "index_type": "ivf_pq",
            "config": {
                "nlist": nlist,
                "nprobe": nprobe,
                "m": m,
                "nbits": nbits,
                "metric": "L2"
            },
            "reason": f"Vector count ({vector_count}) in range [{self.THRESHOLD_IVF}, {self.THRESHOLD_LARGE}], using IVF-PQ for memory efficiency",
            "should_migrate": False,
            "estimated_memory_mb": self._estimate_memory(vector_count, dimension, "ivf_pq", m=m),
            "estimated_latency_ms": self._estimate_latency(vector_count, "ivf_pq")
        }

    def _select_hnsw(self, vector_count: int, dimension: int) -> Dict[str, Any]:
        """选择 HNSW 索引"""
        # HNSW 参数
        M = 32  # 连接数
        efConstruction = 200
        efSearch = 64

        return {
            "index_type": "hnsw",
            "config": {
                "M": M,
                "efConstruction": efConstruction,
                "efSearch": efSearch,
                "metric": "L2"
            },
            "reason": f"Vector count ({vector_count}) >= {self.THRESHOLD_LARGE}, using HNSW for best performance",
            "should_migrate": False,
            "estimated_memory_mb": self._estimate_memory(vector_count, dimension, "hnsw", M=M),
            "estimated_latency_ms": self._estimate_latency(vector_count, "hnsw")
        }

    def _estimate_memory(
        self,
        vector_count: int,
        dimension: int,
        index_type: str,
        **params
    ) -> float:
        """估算内存占用 (MB)"""
        bytes_per_vector = dimension * 4  # float32

        if index_type == "flat":
            total_bytes = vector_count * bytes_per_vector
        elif index_type == "ivf":
            # IVF 需要额外的聚类中心
            nlist = params.get("nlist", 100)
            total_bytes = vector_count * bytes_per_vector + nlist * dimension * 4
        elif index_type == "ivf_pq":
            # PQ 压缩
            m = params.get("m", 64)
            nbits = params.get("nbits", 8)
            nlist = params.get("nlist", 100)
            total_bytes = vector_count * m * nbits // 8 + nlist * dimension * 4
        elif index_type == "hnsw":
            # HNSW 需要额外的图结构
            M = params.get("M", 32)
            total_bytes = vector_count * bytes_per_vector * (1 + M * 0.1)
        else:
            total_bytes = vector_count * bytes_per_vector

        return total_bytes / (1024 * 1024)

    def _estimate_latency(self, vector_count: int, index_type: str) -> float:
        """估算搜索延迟 (ms)"""
        if index_type == "flat":
            # O(n)
            return vector_count * 0.0001
        elif index_type == "ivf":
            # O(sqrt(n))
            return math.sqrt(vector_count) * 0.01
        elif index_type == "ivf_pq":
            # O(sqrt(n)), 稍快
            return math.sqrt(vector_count) * 0.008
        elif index_type == "hnsw":
            # O(log n)
            return math.log(vector_count) * 2 + 5
        else:
            return vector_count * 0.0001

    def should_upgrade(
        self,
        current_index_type: str,
        current_config: Dict[str, Any],
        vector_count: int,
        dimension: int,
        actual_latency_ms: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        判断是否需要升级索引

        Args:
            current_index_type: 当前索引类型
            current_config: 当前索引配置
            vector_count: 向量数量
            dimension: 向量维度
            actual_latency_ms: 实际搜索延迟（可选）

        Returns:
            {
                "should_upgrade": True,
                "recommended_index": "hnsw",
                "reason": "..."
            }
        """
        # 获取推荐索引
        recommended = self.select_index(vector_count, dimension)

        # 检查延迟
        if actual_latency_ms is not None:
            if actual_latency_ms > self.target_latency_ms * 1.5:
                return {
                    "should_upgrade": True,
                    "recommended_index": recommended["index_type"],
                    "recommended_config": recommended["config"],
                    "reason": f"Actual latency ({actual_latency_ms:.1f}ms) exceeds target ({self.target_latency_ms}ms)",
                    "estimated_improvement": actual_latency_ms / recommended["estimated_latency_ms"]
                }

        # 检查是否已经是推荐类型
        if recommended["index_type"] != current_index_type:
            # 检查是否值得迁移
            current_estimated_latency = self._estimate_latency(vector_count, current_index_type)
            recommended_latency = recommended["estimated_latency_ms"]

            if recommended_latency < current_estimated_latency * 0.8:  # 提升20%以上
                return {
                    "should_upgrade": True,
                    "recommended_index": recommended["index_type"],
                    "recommended_config": recommended["config"],
                    "reason": f"Recommended {recommended['index_type']} for better performance",
                    "estimated_improvement": current_estimated_latency / recommended_latency
                }

        return {
            "should_upgrade": False,
            "recommended_index": current_index_type,
            "reason": "Current index is optimal"
        }
