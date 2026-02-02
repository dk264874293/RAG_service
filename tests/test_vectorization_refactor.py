"""
测试向量化逻辑剥离
验证 DocumentService 不再包含向量化逻辑
验证 VectorService 正确工作
"""

import sys
from pathlib import Path
import asyncio
from unittest.mock import Mock, AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.service.document_service import DocumentService
from src.service.vector_service import VectorService
from src.api.dependencies import (
    get_document_service,
    get_vector_service,
    get_upload_service,
)
from src.models.document import Document


def test_document_service_no_vectorization():
    """验证 DocumentService 不再包含向量化逻辑"""
    import inspect

    process_document_source = inspect.getsource(DocumentService.process_document)

    assert "index_document" not in process_document_source, (
        "DocumentService.process_document 不应包含 index_document 调用"
    )

    assert "embedding_service" not in process_document_source, (
        "DocumentService.process_document 不应包含 embedding_service 调用"
    )

    assert "vector_store" not in process_document_source, (
        "DocumentService.process_document 不应包含 vector_store 调用"
    )

    print("✓ DocumentService 不再包含向量化逻辑")


def test_vector_service_exists():
    """验证 VectorService 存在并正确初始化"""
    settings = Mock()
    vector_store = Mock()
    embedding_service = Mock()

    vector_service = VectorService(settings, vector_store, embedding_service)

    assert vector_service.settings == settings
    assert vector_service.vector_store == vector_store
    assert vector_service.embedding_service == embedding_service
    assert vector_service.indexer is not None

    print("✓ VectorService 正确初始化")


async def test_vector_service_vectorize_document():
    """验证 VectorService.vectorize_document 方法"""
    settings = Mock()
    vector_store = Mock()
    embedding_service = Mock()

    vector_service = VectorService(settings, vector_store, embedding_service)

    mock_documents = [
        Document(page_content="test content", metadata={"page": 1}, id_="doc1")
    ]

    with patch.object(
        vector_service.indexer, "index_document", new_callable=AsyncMock
    ) as mock_index:
        mock_index.return_value = True

        result = await vector_service.vectorize_document("file_id_123", mock_documents)

        assert result is True
        mock_index.assert_called_once_with("file_id_123", mock_documents)

    print("✓ VectorService.vectorize_document 正确工作")


async def test_vector_service_delete_vectors():
    """验证 VectorService.delete_vectors 方法"""
    settings = Mock()
    vector_store = Mock()
    vector_store.delete_documents = AsyncMock(return_value=3)
    vector_store.save_index = AsyncMock()

    embedding_service = Mock()

    vector_service = VectorService(settings, vector_store, embedding_service)

    result = await vector_service.delete_vectors("file_id_123")

    assert result == 3
    vector_store.delete_documents.assert_called_once_with("file_id_123")
    vector_store.save_index.assert_called_once()

    print("✓ VectorService.delete_vectors 正确工作")


def test_dependencies_vector_service():
    """验证依赖注入包含 vector_service"""
    vector_service = get_vector_service()
    assert vector_service is not None
    assert isinstance(vector_service, VectorService)

    print("✓ 依赖注入包含 vector_service")


def test_dependencies_upload_service_uses_vector_service():
    """验证 UploadService 使用 vector_service"""
    upload_service = get_upload_service()
    assert upload_service is not None
    assert upload_service.vector_service is not None
    assert isinstance(upload_service.vector_service, VectorService)

    print("✓ UploadService 正确注入 vector_service")


def main():
    print("开始测试向量化逻辑剥离...\n")

    test_document_service_no_vectorization()
    test_vector_service_exists()
    test_dependencies_vector_service()
    test_dependencies_upload_service_uses_vector_service()

    asyncio.run(test_vector_service_vectorize_document())
    asyncio.run(test_vector_service_delete_vectors())

    print("\n✅ 所有测试通过!")


if __name__ == "__main__":
    main()
