#!/usr/bin/env python
"""
分代索引集成测试脚本
验证所有组件是否正确安装和配置
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_imports():
    """测试所有导入是否正常"""
    print_section("1. 测试模块导入")

    imports = [
        ("FAISS", "import faiss"),
        ("LangChain FAISS", "from langchain_community.vectorstores import FAISS"),
        ("RoutingTable", "from src.vector.routing_table import RoutingTable"),
        ("HotFAISSIndex", "from src.vector.hot_faiss_index import HotFAISSIndex"),
        ("ColdFAISSIndex", "from src.vector.cold_faiss_index import ColdFAISSIndex"),
        ("GenerationalIndexStore", "from src.vector.generational_index_store import GenerationalIndexStore"),
        ("EmbeddingService", "from src.vector.embed_service import EmbeddingService"),
        ("ArchiveTaskManager", "from src.tasks.archive_task import ArchiveTaskManager"),
        ("MaintenanceRouter", "from src.api.routes import maintenance"),
        ("APScheduler", "from apscheduler.schedulers.asyncio import AsyncIOScheduler"),
    ]

    failed = []
    for name, import_stmt in imports:
        try:
            exec(import_stmt)
            print(f"  ✓ {name}")
        except ImportError as e:
            print(f"  ✗ {name}: {e}")
            failed.append(name)

    if failed:
        print(f"\n❌ 导入失败: {', '.join(failed)}")
        print("请运行: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ 所有模块导入成功")
        return True


def test_config():
    """测试配置是否正确"""
    print_section("2. 测试配置")

    try:
        from config import settings

        configs = [
            ("分代索引启用", "enable_generational_index", settings.enable_generational_index),
            ("Hot索引最大容量", "hot_index_max_size", settings.hot_index_max_size),
            ("Hot索引类型", "hot_index_type", settings.hot_index_type),
            ("Cold索引类型", "cold_index_type", settings.cold_index_type),
            ("归档天数", "archive_age_days", settings.archive_age_days),
        ]

        for name, key, value in configs:
            print(f"  {name}: {value}")

        print("\n✅ 配置加载成功")
        return True

    except Exception as e:
        print(f"\n❌ 配置加载失败: {e}")
        return False


def test_routing_table():
    """测试路由表"""
    print_section("3. 测试路由表")

    try:
        from src.vector.routing_table import RoutingTable
        import tempfile

        # 创建临时路由表
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_routing.db")
            routing_table = RoutingTable(db_path)

            # 测试基本操作
            routing_table.set_location("doc_1", "hot", "file_1")
            routing_table.set_location("doc_2", "cold", "file_1")

            location = routing_table.get_location("doc_1")
            assert location == "hot", f"Expected 'hot', got '{location}'"

            stats = routing_table.get_stats()
            assert stats["total"] == 2, f"Expected 2, got {stats['total']}"

            print(f"  ✓ 设置位置")
            print(f"  ✓ 获取位置: {location}")
            print(f"  ✓ 统计: {stats}")

            routing_table.close()

        print("\n✅ 路由表测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 路由表测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_hot_index():
    """测试Hot索引"""
    print_section("4. 测试Hot索引")

    try:
        from src.vector.hot_faiss_index import HotFAISSIndex
        from src.vector.embed_service import EmbeddingService
        from config import settings
        import tempfile
        from langchain_core.documents import Document

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建嵌入服务
            embed_service = EmbeddingService(settings)

            # 创建Hot索引
            hot_index = HotFAISSIndex(
                index_path=os.path.join(tmpdir, "hot"),
                embedding_service=embed_service,
                max_size=1000,
                index_type="Flat"  # 使用Flat避免训练
            )

            # 测试添加文档
            docs = [
                Document(page_content="测试文档1", metadata={"source": "test1"}),
                Document(page_content="测试文档2", metadata={"source": "test2"}),
            ]

            doc_ids = await hot_index.add_documents(docs)
            print(f"  ✓ 添加文档: {len(doc_ids)} 个")

            # 测试搜索
            results = await hot_index.search("测试", k=2)
            print(f"  ✓ 搜索: 返回 {len(results)} 个结果")

            # 测试删除
            deleted = await hot_index.remove_doc(doc_ids[0])
            print(f"  ✓ 删除: {deleted} 个文档")

            stats = hot_index.get_stats()
            print(f"  ✓ 统计: size={stats['size']}, total_removed={stats['total_removed']}")

        print("\n✅ Hot索引测试通过")
        return True

    except Exception as e:
        print(f"\n❌ Hot索引测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cold_index():
    """测试Cold索引"""
    print_section("5. 测试Cold索引")

    try:
        from src.vector.cold_faiss_index import ColdFAISSIndex
        from src.vector.embed_service import EmbeddingService
        from config import settings
        import tempfile
        from langchain_core.documents import Document

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建嵌入服务
            embed_service = EmbeddingService(settings)

            # 创建Cold索引
            cold_index = ColdFAISSIndex(
                index_path=os.path.join(tmpdir, "cold"),
                embedding_service=embed_service,
                index_type="Flat"
            )

            # 测试添加文档
            docs = [
                Document(page_content="归档文档1", metadata={"source": "archive1"}),
                Document(page_content="归档文档2", metadata={"source": "archive2"}),
            ]

            doc_ids = await cold_index.add_documents(docs)
            print(f"  ✓ 添加文档: {len(doc_ids)} 个")

            # 测试搜索
            results = await cold_index.search("归档", k=2)
            print(f"  ✓ 搜索: 返回 {len(results)} 个结果")

            # 测试软删除
            deleted = await cold_index.soft_delete(doc_ids[0])
            print(f"  ✓ 软删除: {deleted} 个文档")

            stats = cold_index.get_stats()
            print(f"  ✓ 统计: size={stats['size']}, deleted_count={stats['deleted_count']}")

        print("\n✅ Cold索引测试通过")
        return True

    except Exception as e:
        print(f"\n❌ Cold索引测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_generational_store():
    """测试分代索引存储"""
    print_section("6. 测试分代索引存储")

    try:
        from src.vector.generational_index_store import GenerationalIndexStore
        from src.vector.embed_service import EmbeddingService
        from config import settings
        import tempfile
        from langchain_core.documents import Document

        with tempfile.TemporaryDirectory() as tmpdir:
            # 修改临时路径
            original_path = settings.faiss_index_path
            settings.faiss_index_path = tmpdir

            # 创建嵌入服务和分代存储
            embed_service = EmbeddingService(settings)
            store = GenerationalIndexStore(settings, embed_service)

            # 测试添加文档
            docs = [
                Document(page_content="分代索引测试", metadata={"source": "test"}),
            ]

            doc_ids = await store.add_documents(docs, file_id="test_file")
            print(f"  ✓ 添加文档到Hot索引: {len(doc_ids)} 个")

            # 测试搜索
            results = await store.search("测试", k=5)
            print(f"  ✓ 搜索: 返回 {len(results)} 个结果")

            # 测试删除
            deleted = await store.delete_documents("test_file")
            print(f"  ✓ 删除文档: {deleted} 个")

            # 获取统计
            stats = store.get_stats()
            print(f"  ✓ 统计: hot_size={stats['hot_index']['size']}, cold_size={stats['cold_index']['size']}")

            # 恢复原路径
            settings.faiss_index_path = original_path

        print("\n✅ 分代索引存储测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 分代索引存储测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        traceback.print_exc()
        return False


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "🚀" * 30)
    print("  分代索引集成测试")
    print("🚀" * 30)

    results = {
        "导入测试": test_imports(),
        "配置测试": test_config(),
        "路由表测试": test_routing_table(),
        "Hot索引测试": await test_hot_index(),
        "Cold索引测试": await test_cold_index(),
        "分代存储测试": await test_generational_store(),
    }

    # 打印总结
    print_section("测试总结")
    passed = sum(results.values())
    total = len(results)

    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")

    print("\n" + "=" * 60)
    print(f"  总计: {passed}/{total} 通过")
    print("=" * 60)

    if passed == total:
        print("\n🎉 所有测试通过！分代索引已成功集成。")
        print("\n下一步:")
        print("  1. 启用配置: 在 .env 中设置 ENABLE_GENERATIONAL_INDEX=true")
        print("  2. 安装依赖: pip install apscheduler")
        print("  3. 启动服务: python -m uvicorn src.app:app --reload")
        print("  4. 访问文档: http://localhost:8000/docs")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
