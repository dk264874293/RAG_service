"""
Simplified performance benchmark script
Direct FAISS index testing without full strategy stack
"""

import time
import statistics
import asyncio
from typing import List, Dict

import numpy as np
from rank_bm25 import BM25Okapi

import sys

sys.path.insert(0, ".")

from config import settings
from src.vector.faiss_index_factory import FAISSIndexFactory


def load_test_data(data_path: str) -> List[Dict]:
    """Load test data from JSON file"""
    import json

    with open(data_path, "r", encoding="utf-8") as f:
        documents = json.load(f)

    print(f"Loaded {len(documents)} documents from {data_path}")
    return documents


def generate_test_queries() -> List[str]:
    """Generate test queries"""
    queries = [
        "人工智能的发展趋势",
        "机器学习应用案例",
        "深度学习优化",
        "自然语言处理",
        "计算机视觉技术",
        "数据科学最佳实践",
        "云计算架构",
        "网络安全防护",
        "区块链技术创新",
    ]

    return queries


async def benchmark_faiss_search(index_info: Dict, queries: List[str], k: int = 5):
    """Benchmark FAISS index search performance"""
    index_wrapper = index_info["index_wrapper"]
    index_class_name = index_wrapper.__class__.__name__.replace("Index", "").lower()
    print(f"\n{'=' * 60}")
    print(f"Benchmarking FAISS {index_class_name} Index")
    print(f"  Test queries: {len(queries)}")
    print(f"  K: {k}")
    print(f"  Test runs: 10")
    print(f"{'=' * 60}")

    faiss_index = index_info["index"]

    import faiss

    times = []

    for i in range(10):
        for query in queries:
            start = time.time()

            import numpy as np

            query_vector = np.random.randn(1536).astype("float32")
            query_vector = query_vector / np.linalg.norm(query_vector)

            distances, indices = faiss_index.search(query_vector.reshape(1, -1), k)

            end = time.time()
            elapsed_ms = (end - start) * 1000
            times.append(elapsed_ms)

            if i < 3:
                print(
                    f"  Query {i + 1}/{len(times)}: {elapsed_ms:.2f}ms, k={k} results"
                )

    avg_time = statistics.mean(times)
    p95_time = statistics.quantiles(times, n=20)[18]
    p99_time = statistics.quantiles(times, n=100)[98]

    print(f"\n{'=' * 60}")
    print(f"Results for FAISS {index_class_name} Index:")
    print(f"  Average: {avg_time:.2f}ms")
    print(f"  P95: {p95_time:.2f}ms")
    print(f"  P99: {p99_time:.2f}ms")
    print(f"  Min: {min(times):.2f}ms")
    print(f"  Max: {max(times):.2f}ms")

    return {
        "index_type": index_class_name,
        "avg_time_ms": avg_time,
        "p95_time_ms": p95_time,
        "p99_time_ms": p99_time,
        "min_time_ms": min(times),
        "max_time_ms": max(times),
    }


async def run_full_benchmark(data_size: str, index_type: str):
    """Run full benchmark for all index types"""
    print(f"\n{'#' * 60}")
    print(f"# Full Benchmark: {data_size.upper()} - {index_type.upper()} Index")
    print(f"{'#' * 60}\n")

    data_path = f"data/test_{data_size}.json"
    documents = load_test_data(data_path)

    queries = generate_test_queries()

    results = []

    print(f"\n{'#' * 60}")
    print(f"# Building Indexes")
    print(f"{'#' * 60}\n")

    dimension = 1536
    embeddings = np.array(
        [np.random.randn(dimension).astype("float32") for doc in documents]
    )
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    index_wrapper = FAISSIndexFactory.create_index(index_type, dimension, {})
    index = index_wrapper.get_index()

    if hasattr(index, "is_trained") and not index.is_trained:
        print("Training IVF-PQ index...")
        index.train(embeddings)
        print("✅ IVF-PQ index trained")

    index.add(embeddings)
    print(f"✅ FAISS {index_type} index built")

    index_info = {
        "index": index,
        "index_wrapper": index_wrapper,
    }

    result = await benchmark_faiss_search(index_info, queries, k=5)
    results.append(result)

    print(f"\n{'#' * 60}")
    print(f"# Benchmark Complete: {data_size.upper()} - {index_type.upper()}")
    print(f"{'#' * 60}\n")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run simplified FAISS performance benchmark"
    )
    parser.add_argument(
        "--size", type=str, default="1k", choices=["1k"], help="Test data size"
    )
    parser.add_argument(
        "--index",
        type=str,
        default="flat",
        choices=["flat", "ivf_pq", "hnsw"],
        help="FAISS index type",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./data/benchmark_results.json",
        help="Output path for benchmark results",
    )
    args = parser.parse_args()

    asyncio.run(run_full_benchmark(args.size, args.index))
