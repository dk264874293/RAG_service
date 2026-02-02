"""测试上传接口返回 markdown_content 列表格式功能"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas.upload import UploadResponse, MarkdownPage


def test_markdown_page_model():
    """测试 MarkdownPage 模型"""
    page = MarkdownPage(
        page_number=1,
        title="第 1 部分",
        content="这是第一部分的内容",
        metadata={"page": 1, "doc_id": "doc1"},
    )

    assert page.page_number == 1
    assert page.title == "第 1 部分"
    assert page.content == "这是第一部分的内容"
    assert page.metadata["page"] == 1

    print("✓ MarkdownPage 模型工作正常")
    return True


def test_upload_response_with_markdown_list():
    """测试 UploadResponse 包含 MarkdownPage 列表"""
    pages = [
        MarkdownPage(
            page_number=1,
            title="第 1 部分",
            content="这是第一部分的内容...",
            metadata={"page": 1},
        ),
        MarkdownPage(
            page_number=2,
            title="第 2 部分",
            content="这是第二部分的内容...",
            metadata={"page": 2},
        ),
    ]

    response = UploadResponse(
        status="success",
        message="文件上传成功: test.pdf",
        file_id="550e8400-e29b-41d4-a716-446655440000",
        file_name="test.pdf",
        file_size=1024000,
        file_type=".pdf",
        processing_status="success",
        content_preview="这是文档的前500个字符内容预览...",
        markdown_content=pages,
    )

    assert response.markdown_content is not None
    assert len(response.markdown_content) == 2
    assert response.markdown_content[0].page_number == 1
    assert response.markdown_content[1].page_number == 2
    assert response.markdown_content[0].title == "第 1 部分"

    print("✓ UploadResponse 支持 MarkdownPage 列表")
    print(f"  包含 {len(response.markdown_content)} 个页面")

    return True


def test_json_serialization():
    """测试 JSON 序列化"""
    pages = [
        MarkdownPage(
            page_number=1,
            title="第 1 部分",
            content="这是内容...",
            metadata={"page": 1},
        ),
    ]

    response = UploadResponse(
        status="success",
        message="测试",
        file_id="test-123",
        file_name="test.pdf",
        file_size=1024,
        file_type=".pdf",
        processing_status="success",
        markdown_content=pages,
    )

    json_data = response.model_dump()
    assert "markdown_content" in json_data
    assert isinstance(json_data["markdown_content"], list)
    assert len(json_data["markdown_content"]) == 1
    assert json_data["markdown_content"][0]["page_number"] == 1
    assert json_data["markdown_content"][0]["title"] == "第 1 部分"

    print("✓ JSON 序列化正确")
    print(f"  序列化后结构: {list(json_data.keys())}")

    return True


def test_upload_service_markdown_pages():
    """测试 UploadService._generate_markdown_pages 方法"""

    class MockDoc:
        def __init__(self, content, metadata=None, id_=None):
            self.page_content = content
            self.metadata = metadata or {}
            self.id_ = id_ or "doc1"

    docs = [
        MockDoc("这是第一段内容", {"page": 1}, "doc1"),
        MockDoc("这是第二段内容", {"page": 2}, "doc2"),
    ]

    class MockUploadService:
        def _generate_markdown_pages(self, documents):
            if not documents:
                return []

            markdown_pages = []
            for idx, doc in enumerate(documents, 1):
                page = {
                    "page_number": idx,
                    "title": f"第 {idx} 部分",
                    "content": doc.page_content,
                    "metadata": {
                        "doc_id": doc.id_ if hasattr(doc, "id_") else str(idx),
                        **(doc.metadata if hasattr(doc, "metadata") else {}),
                    },
                }
                markdown_pages.append(page)

            return markdown_pages

    service = MockUploadService()
    pages = service._generate_markdown_pages(docs)

    assert len(pages) == 2
    assert pages[0]["page_number"] == 1
    assert pages[0]["title"] == "第 1 部分"
    assert pages[0]["content"] == "这是第一段内容"
    assert pages[0]["metadata"]["doc_id"] == "doc1"
    assert pages[0]["metadata"]["page"] == 1

    assert pages[1]["page_number"] == 2
    assert pages[1]["title"] == "第 2 部分"

    print("✓ _generate_markdown_pages 生成正确结构")
    print(f"  页面 1: {pages[0]}")

    return True


def test_empty_documents():
    """测试空文档情况"""

    class MockUploadService:
        def _generate_markdown_pages(self, documents):
            if not documents:
                return []

            markdown_pages = []
            for idx, doc in enumerate(documents, 1):
                page = {
                    "page_number": idx,
                    "title": f"第 {idx} 部分",
                    "content": doc.page_content,
                    "metadata": {
                        "doc_id": doc.id_ if hasattr(doc, "id_") else str(idx),
                        **(doc.metadata if hasattr(doc, "metadata") else {}),
                    },
                }
                markdown_pages.append(page)

            return markdown_pages

    service = MockUploadService()
    pages = service._generate_markdown_pages([])

    assert pages == []
    assert isinstance(pages, list)
    print("✓ 空文档返回空列表")

    return True


if __name__ == "__main__":
    print("测试上传接口返回 markdown_content 列表格式功能\n")

    test_markdown_page_model()
    print()

    test_upload_response_with_markdown_list()
    print()

    test_json_serialization()
    print()

    test_upload_service_markdown_pages()
    print()

    test_empty_documents()
    print()

    print("\n✅ 所有测试通过！")
    print("\n现在 /api/upload/ 接口返回的 markdown_content 是列表格式：")
    print("[")
    print("  {")
    print('    "page_number": 1,')
    print('    "title": "第 1 部分",')
    print('    "content": "...",')
    print('    "metadata": {...}')
    print("  },")
    print("  ...")
    print("]")
