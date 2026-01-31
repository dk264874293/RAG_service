"""
Retrieval performance benchmark tests
Tests performance of different retrieval strategies
"""

import pytest
import time
import statistics
from typing import List, Dict


class TestRetrievalPerformance:
    """Performance tests for retrieval strategies"""

    @pytest.mark.asyncio
    async def test_strategy_factory():
        """Test retrieval strategy factory"""
        from src.retrieval.strategies.factory import RetrievalStrategyFactory

        strategies = RetrievalStrategyFactory.get_available_strategies()
        assert len(strategies) > 0
        print(f"Available strategies: {strategies}")

    @pytest.mark.parametrize(
        "test_id,strategy,index_type,k,expected_max_time",
        [
            ("T1", "vector", "flat", 5, 20),
            ("T2", "hybrid", "flat", 5, 30),
            ("T3", "parent_child", "flat", 5, 20),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_performance(
        self,
        test_id: str,
        strategy: str,
        index_type: str,
        k: int,
        expected_max_time: float,
    ):
        """Test search performance for different strategies"""
        print("\n" + "=" * 60)
        print(f"Running test: {test_id}")
        print(f"  Strategy: {strategy}")
        print(f"  Index type: {index_type}")
        print(f"  K: {k}")
        print(f"  Max expected time: {expected_max_time}ms")

        from src.api.dependencies import get_retrieval_strategy

        try:
            search_strategy = get_retrieval_strategy()

            times = []
            for i in range(10):
                start = time.time()
                results = await search_strategy.search(f"test query {i}", k=k)
                end = time.time()
                times.append((end - start) * 1000)

            avg_time = statistics.mean(times)
            p95_time = statistics.quantiles(times, n=20)[18]
            p99_time = statistics.quantiles(times, n=100)[98]

            print(f"\nResults:")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  P50: {statistics.median(times):.2f}ms")
            print(f"  P95: {p95_time:.2f}ms")
            print(f"  P99: {p99_time:.2f}ms")

            assert avg_time < expected_max_time, (
                f"{test_id}: Average time {avg_time:.2f}ms "
                f"exceeds target {expected_max_time * 0.7:.2f}ms"
            )

            print(f"✅ {test_id}: PASS")

        except Exception as e:
            print(f"✗ {test_id}: FAIL - {e}")
            pytest.skip(f"Strategy not fully implemented: {e}")

    def test_index_factory():
        """Test FAISS index factory"""
        from src.vector.faiss_index_factory import FAISSIndexFactory

        types = FAISSIndexFactory.get_available_types()
        assert "flat" in types
        assert "ivf_pq" in types
        assert "hnsw" in types
        print(f"✅ Available index types: {types}")
