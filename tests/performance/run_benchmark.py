"""
Complete performance benchmark script
Tests all retrieval strategies with real data
"""

import time
import statistics
import asyncio
from typing import List, Dict
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

import sys

sys.path.insert(0, ".")

from src.api.dependencies import (
    get_embedding_service,
    get_retrieval_strategy,
)
from config import settings
from src.vector.faiss_index_factory import FAISSIndexFactory
from src.retrieval.strategies.factory import RetrievalStrategyFactory
from src.retrieval.strategies import vector_strategy
from src.retrieval.strategies import hybrid_strategy
from src.vector.vector_store import FAISSVectorStore
from src.api.dependencies import get_embedding_service

RetrievalStrategyFactory.register("vector", vector_strategy.VectorRetrievalStrategy)
RetrievalStrategyFactory.register("hybrid", hybrid_strategy.HybridRetrievalStrategy)


def load_test_data(data_path: str):
    """Load test data from JSON file

    Args:
        data_path: Path to test data JSON

    Returns:
        List of document dictionaries
    """
    import json

    with open(data_path, "r", encoding="utf-8") as f:
        documents = json.load(f)

    print(f"Loaded {len(documents)} documents from {data_path}")
    return documents


def build_bm25_index(documents):
    """Build BM25 index from documents

    Args:
        documents: List of document dictionaries

    Returns:
        BM25Okapi index
    """
    import jieba

    corpus = []
    for doc in documents:
        tokens = list(jieba.cut(doc["content"]))
        corpus.append(tokens)

    print(f"Building BM25 index from {len(corpus)} documents...")
    bm25_index = BM25Okapi(corpus)
    print(f"✅ BM25 index built")

    return bm25_index


def build_faiss_index_with_embeddings(documents, embeddings, index_type: str):
    """Build FAISS index with provided embeddings

    Args:
        documents: List of document dictionaries
        embeddings: NumPy array of embeddings
        index_type: Type of FAISS index (flat, ivf_pq, hnsw)

    Returns:
        FAISS index object
    """
    print(f"Building FAISS {index_type} index from {len(documents)} documents...")

    dimension = embeddings.shape[1]
    index_wrapper = FAISSIndexFactory.create_index(index_type, dimension, {})
    index = index_wrapper.get_index()

    if hasattr(index, "is_trained") and not index.is_trained:
        print("Training IVF-PQ index...")
        index.train(embeddings)
        print("✅ IVF-PQ index trained")

    index.add(embeddings)
    print(f"✅ FAISS {index_type} index built")

    return index_wrapper


def generate_test_queries() -> List[str]:
    """Generate test queries

    Returns:
        List of test query strings
    """
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


async def benchmark_search(
    strategy_name: str,
    test_queries: List[str],
    vector_store: object,  # type: ignore  # type: ignore
    bm25_index: object,  # type: ignore
    k: int = 5,
    warmup_runs: int = 3,
    test_runs: int = 10,
) -> Dict[str, float]:
    """Benchmark search performance for a strategy

    Args:
        strategy_name: Name of Strategy to test
        test_queries: List of query strings
        k: Number of results to return
        warmup_runs: Number of warmup runs
        test_runs: Number of test runs
        vector_store: FAISS index object
        bm25_index: BM25 index object

    Returns:
        Dictionary with performance metrics
    """
    print(f"\n{'=' * 60}")
    print(f"Benchmarking strategy: {strategy_name}")
    print(f"  Test queries: {len(test_queries)}")
    print(f"  K: {k}")
    print(f"  Warmup runs: {warmup_runs}")
    print(f"  Test runs: {test_runs}")
    print(f"{'=' * 60}")

    from src.api.dependencies import get_embedding_service

    dependencies = {}
    if vector_store:
        dependencies["vector_store"] = vector_store
    if bm25_index:
        dependencies["bm25_index"] = bm25_index
        dependencies["embedding_service"] = get_embedding_service()

        strategy = RetrievalStrategyFactory.create(
            strategy_name=strategy_name,
            config={},
            dependencies=dependencies,
        )

        strategy_name_lower = strategy_name.lower()
        print(f"\nTesting strategy: {strategy_name.upper()}")
        print(f"Strategy loaded: {strategy.get_name()}")

        for i in range(warmup_runs):
            for query in test_queries[:1]:
                await strategy.search(query, k=k)

        times = []
        for i, query in enumerate(test_queries):
            start = time.time()
            results = await strategy.search(query, k=k)
            end = time.time()

            elapsed_ms = (end - start) * 1000
            times.append(elapsed_ms)

            if i < 5:
                print(
                    f"  Query {i + 1}/{len(test_queries)}: {elapsed_ms:.2f}ms, {len(results)} results"
                )


async def run_full_benchmark(data_size: str, index_type: str):
    """Run full benchmark for all strategies

    Args:
        data_size: Size of test data (1k, 10k)
        index_type: Type of FAISS index
    """
    print(f"\n{'#' * 60}")
    print(f"# Full Benchmark: {data_size.upper()} - {index_type.upper()} Index")
    print(f"{'#' * 60}\n")

    data_path = f"data/test_{data_size}.json"
    documents = load_test_data(data_path)

    test_queries = generate_test_queries()

    results = []

    bm25_index = None

    if data_size == "1k" or data_size == "10k":
        bm25_index = build_bm25_index(documents)

    dimension = 1536
    embeddings = np.array(
        [np.random.randn(dimension).astype("float32") for doc in documents]
    )
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    print(f"Building FAISS {index_type} index from {len(documents)} documents...")

    index_wrapper = build_faiss_index_with_embeddings(documents, embeddings, index_type)
    faiss_index = index_wrapper.get_index()

    vector_store = FAISSVectorStore(settings, get_embedding_service())
    vector_store.vector_store = faiss_index

    print(f"✅ FAISS {index_type} index built with vector_store")

    strategies_to_test = ["vector"]

    if index_type == "flat":
        pass
    else:
        pass

    for strategy_name in strategies_to_test:
        if strategy_name == "hybrid" and bm25_index is None:
            print(f"Skipping {strategy_name} - no BM25 index")
            continue

        strategy_name_lower = strategy_name.lower()
        print(f"\nTesting strategy: {strategy_name.upper()}")

        result = await benchmark_search(
            strategy_name=strategy_name_lower,
            test_queries=test_queries,
            k=5,
            warmup_runs=3,
            test_runs=10,
            vector_store=faiss_index,
            bm25_index=bm25_index,
        )
        results.append(result)

    print(f"\n{'#' * 60}")
    print(f"# Benchmark Complete: {data_size.upper()} - {index_type.upper()}")
    print(f"{'#' * 60}\n")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run full retrieval performance benchmark"
    )
    parser.add_argument(
        "--size", type=str, default="1k", choices=["1k", "10k"], help="Test data size"
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
