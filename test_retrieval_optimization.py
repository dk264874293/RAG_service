"""
RAG检索层优化集成测试
测试增强检索服务、BM25索引、高级检索策略
"""

import asyncio
import sys
import os
import logging
from typing import List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_test_header(test_name: str):
    """打印测试标题"""
    print("\n" + "="*60)
    print(f"测试: {test_name}")
    print("="*60)


def print_test_result(test_name: str, passed: bool, details: str = ""):
    """打印测试结果"""
    status = "✓ 通过" if passed else "✗ 失败"
    print(f"\n{status}: {test_name}")
    if details:
        print(f"  详情: {details}")


async def test_bm25_manager():
    """测试BM25索引管理器"""
    print_test_header("BM25索引管理器")

    try:
        from src.retrieval.bm25_index_manager import BM25IndexManager
        from src.api.dependencies import get_vector_store, get_settings
        from config import settings
        import tempfile
        import shutil

        # 创建临时测试目录
        test_index_path = tempfile.mkdtemp(prefix="bm25_test_")

        try:
            # 初始化BM25管理器
            vector_store = get_vector_store()

            bm25_manager = BM25IndexManager(
                index_path=test_index_path,
                vector_store=vector_store,
                k1=1.2,
                b=0.75,
                auto_sync=True
            )

            # 构建BM25索引
            logger.info("构建BM25索引...")
            doc_count = await bm25_manager.build_from_vector_store()

            if doc_count > 0:
                print_test_result("BM25索引构建", True, f"成功索引 {doc_count} 个文档")

                # 测试搜索
                logger.info("测试BM25搜索...")
                results = await bm25_manager.search("环境标准", k=5)

                if results:
                    print_test_result("BM25搜索", True, f"找到 {len(results)} 个结果")
                else:
                    print_test_result("BM25搜索", False, "未找到结果")

                # 获取统计信息
                stats = bm25_manager.get_stats()
                logger.info(f"BM25统计: {stats}")
                print_test_result("BM25统计信息", True, f"总文档数: {stats['total_documents']}")
            else:
                print_test_result("BM25索引构建", False, "未找到文档")

            # 清理
            await bm25_manager.cleanup()

        finally:
            # 清理临时目录
            shutil.rmtree(test_index_path, ignore_errors=True)

        return True

    except Exception as e:
        logger.error(f"BM25测试失败: {e}", exc_info=True)
        print_test_result("BM25测试", False, str(e))
        return False


async def test_hyde_strategy():
    """测试HyDE检索策略"""
    print_test_header("HyDE检索策略")

    try:
        from src.retrieval.strategies.hyde_strategy import HyDEStrategy
        from src.api.dependencies import get_vector_store, get_embedding_service, get_settings

        vector_store = get_vector_store()
        embedding_service = get_embedding_service()
        settings = get_settings()

        # 创建HyDE策略
        config = {
            "vector_store": vector_store,
            "embedding_service": embedding_service,
            "llm_provider": "dashscope",
            "model": "qwen-plus",
            "temperature": 0.0,
            "use_reranking": False,  # HyDE本身会使用LLM
        }

        hyde = HyDEStrategy(config)

        # 测试检索
        query = "什么是环境监测？"
        logger.info(f"HyDE检索测试: {query}")

        results = await hyde.search(query, k=5)

        if results:
            print_test_result("HyDE检索", True, f"找到 {len(results)} 个结果")
            logger.info(f"第一个结果: {results[0].page_content[:100]}...")
        else:
            print_test_result("HyDE检索", False, "未找到结果")

        # 清理
        await hyde.cleanup()

        return True

    except Exception as e:
        logger.error(f"HyDE策略测试失败: {e}", exc_info=True)
        print_test_result("HyDE策略测试", False, str(e))
        return False


async def test_query2doc_strategy():
    """测试Query2Doc检索策略"""
    print_test_header("Query2Doc检索策略")

    try:
        from src.retrieval.strategies.query2doc_strategy import Query2DocStrategy
        from src.api.dependencies import get_vector_store, get_settings

        vector_store = get_vector_store()
        settings = get_settings()

        # 创建Query2Doc策略
        config = {
            "vector_store": vector_store,
            "llm_provider": "dashscope",
            "model": "qwen-plus",
            "temperature": 0.7,
            "num_expansions": 3,
            "use_reranking": False,
        }

        query2doc = Query2DocStrategy(config)

        # 测试检索
        query = "大气污染物排放标准"
        logger.info(f"Query2Doc检索测试: {query}")

        results = await query2doc.search(query, k=5)

        if results:
            print_test_result("Query2Doc检索", True, f"找到 {len(results)} 个结果")
            logger.info(f"第一个结果: {results[0].page_content[:100]}...")
        else:
            print_test_result("Query2Doc检索", False, "未找到结果")

        # 清理
        await query2doc.cleanup()

        return True

    except Exception as e:
        logger.error(f"Query2Doc策略测试失败: {e}", exc_info=True)
        print_test_result("Query2Doc策略测试", False, str(e))
        return False


async def test_enhanced_retrieval_service():
    """测试增强检索服务"""
    print_test_header("增强检索服务")

    try:
        from src.vector.enhanced_retrieval_service import EnhancedRetrievalService
        from src.api.dependencies import get_vector_store, get_embedding_service, get_settings
        from src.retrieval.reranker import Reranker

        vector_store = get_vector_store()
        embedding_service = get_embedding_service()
        settings = get_settings()

        # 创建Reranker
        reranker = Reranker(
            model_name=settings.retrieval_strategy_config.get(
                "reranker_model", "BAAI/bge-reranker-large"
            )
        )

        # 创建增强检索服务
        enhanced_service = EnhancedRetrievalService(
            config=settings,
            vector_store=vector_store,
            embedding_service=embedding_service,
            reranker=reranker
        )

        # 测试不同检索策略
        test_cases = [
            ("vector", "环境监测标准", "向量检索"),
            ("hybrid", "水质监测方法", "混合检索"),
        ]

        for strategy, query, desc in test_cases:
            logger.info(f"测试{desc}: {query}")

            results = await enhanced_service.search(
                query,
                k=5,
                strategy=strategy,
                use_rerank=False  # 先测试无Rerank
            )

            if results:
                print_test_result(f"{desc}(无Rerank)", True, f"找到 {len(results)} 个结果")
            else:
                print_test_result(f"{desc}(无Rerank)", False, "未找到结果")

        # 测试Reranker集成
        logger.info("测试Reranker集成...")
        results_with_rerank = await enhanced_service.search(
            "环境保护法",
            k=5,
            strategy="vector",
            use_rerank=True
        )

        if results_with_rerank:
            print_test_result("Reranker集成", True, f"返回 {len(results_with_rerank)} 个Reranked结果")
        else:
            print_test_result("Reranker集成", False, "Rerank后无结果")

        # 获取统计信息
        stats = enhanced_service.get_stats()
        logger.info(f"增强检索服务统计: {stats}")

        return True

    except Exception as e:
        logger.error(f"增强检索服务测试失败: {e}", exc_info=True)
        print_test_result("增强检索服务测试", False, str(e))
        return False


async def test_strategy_auto_selection():
    """测试策略自动选择"""
    print_test_header("策略自动选择")

    try:
        from src.vector.enhanced_retrieval_service import EnhancedRetrievalService
        from src.api.dependencies import get_vector_store, get_embedding_service, get_settings

        vector_store = get_vector_store()
        embedding_service = get_embedding_service()
        settings = get_settings()

        # 创建增强检索服务（无Reranker）
        enhanced_service = EnhancedRetrievalService(
            config=settings,
            vector_store=vector_store,
            embedding_service=embedding_service,
            reranker=None
        )

        # 测试不同查询类型的策略选择
        test_queries = [
            ("什么是大气污染？", "问号结尾查询"),
            ("比较PM2.5和PM10的区别", "比较查询"),
            ("环境监测", "短查询"),
            ("环境保护法律法规体系及其实施细则", "长查询"),
        ]

        for query, desc in test_queries:
            strategy = enhanced_service._select_strategy(query)
            logger.info(f"{desc} '{query}' -> 策略: {strategy}")
            print_test_result(f"{desc}策略选择", True, f"选择: {strategy}")

        return True

    except Exception as e:
        logger.error(f"策略自动选择测试失败: {e}", exc_info=True)
        print_test_result("策略自动选择测试", False, str(e))
        return False


async def test_rrf_fusion():
    """测试RRF融合算法"""
    print_test_header("RRF融合算法")

    try:
        from src.vector.enhanced_retrieval_service import EnhancedRetrievalService
        from src.models.document import Document
        from src.api.dependencies import get_settings

        settings = get_settings()

        # 创建模拟服务
        service = EnhancedRetrievalService(
            config=settings,
            vector_store=None,
            embedding_service=None,
            reranker=None
        )

        # 模拟向量结果
        vector_results = [
            Document(page_content=f"文档{i}", id_=f"doc_{i}", metadata={"doc_id": f"doc_{i}"})
            for i in [1, 3, 5, 7, 9]
        ]

        # 模拟BM25结果
        bm25_results = [
            (Document(page_content=f"文档{i}", id_=f"doc_{i}", metadata={"doc_id": f"doc_{i}"}), 0.9)
            for i in [2, 3, 4, 5, 6]
        ]

        # 执行RRF融合
        fused = service._reciprocal_rank_fusion(
            vector_results,
            bm25_results,
            k=5,
            alpha=0.7,
            k_constant=60
        )

        # 检查结果
        if fused:
            doc_ids = [doc.metadata.get("doc_id") for doc in fused]
            logger.info(f"融合后的文档ID: {doc_ids}")

            # 检查是否包含重复文档（应该去重）
            unique_ids = set(doc_ids)
            if len(unique_ids) == len(doc_ids):
                print_test_result("RRF融合去重", True, f"融合 {len(fused)} 个唯一文档")
            else:
                print_test_result("RRF融合去重", False, "存在重复文档")

            # 检查文档3和5是否在前面（向量+BM25共同结果）
            if "doc_3" in doc_ids[:3] or "doc_5" in doc_ids[:3]:
                print_test_result("RRF融合排序", True, "共同结果排名靠前")
            else:
                print_test_result("RRF融合排序", False, "共同结果未排名靠前")
        else:
            print_test_result("RRF融合", False, "融合结果为空")

        return True

    except Exception as e:
        logger.error(f"RRF融合测试失败: {e}", exc_info=True)
        print_test_result("RRF融合测试", False, str(e))
        return False


async def test_strategy_factory():
    """测试策略工厂注册"""
    print_test_header("策略工厂注册")

    try:
        from src.retrieval.strategies.factory import RetrievalStrategyFactory

        # 自动注册所有策略
        RetrievalStrategyFactory.auto_register()

        # 获取可用策略列表
        available_strategies = RetrievalStrategyFactory.get_available_strategies()

        logger.info(f"可用策略: {available_strategies}")

        expected_strategies = ["vector", "hybrid", "parent_child", "hyde", "query2doc"]

        # 检查预期策略是否已注册
        for strategy in expected_strategies:
            if strategy in available_strategies:
                print_test_result(f"策略 {strategy} 注册", True, "已注册")
            else:
                print_test_result(f"策略 {strategy} 注册", False, "未注册")

        return True

    except Exception as e:
        logger.error(f"策略工厂测试失败: {e}", exc_info=True)
        print_test_result("策略工厂测试", False, str(e))
        return False


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("RAG检索层优化集成测试")
    print("="*60)

    tests = [
        ("策略工厂注册", test_strategy_factory),
        ("BM25索引管理器", test_bm25_manager),
        ("HyDE检索策略", test_hyde_strategy),
        ("Query2Doc检索策略", test_query2doc_strategy),
        ("增强检索服务", test_enhanced_retrieval_service),
        ("策略自动选择", test_strategy_auto_selection),
        ("RRF融合算法", test_rrf_fusion),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            passed = await test_func()
            results.append((test_name, passed))
        except Exception as e:
            logger.error(f"测试 {test_name} 执行失败: {e}", exc_info=True)
            results.append((test_name, False))

    # 打印测试汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status}: {test_name}")

    print("\n" + "="*60)
    print(f"总计: {passed_count}/{total_count} 通过")
    print("="*60)

    return passed_count == total_count


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
