#!/usr/bin/env python3
"""
测试文件上传API
"""

import requests
import os
from pathlib import Path


BASE_URL = "http://localhost:8892"


def test_upload_file(file_path: str):
    """测试单文件上传"""
    print(f"\n测试上传文件: {file_path}")

    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return

    url = f"{BASE_URL}/api/upload"
    files = {"file": open(file_path, "rb")}

    try:
        response = requests.post(url, files=files)
        response.raise_for_status()

        result = response.json()
        print(f"上传成功!")
        print(f"  文件ID: {result['file_id']}")
        print(f"  文件名: {result['file_name']}")
        print(f"  文件大小: {result['file_size']} bytes")
        print(f"  处理状态: {result['processing_status']}")

        return result["file_id"]

    except requests.exceptions.RequestException as e:
        print(f"上传失败: {e}")
        return None


def test_batch_upload(file_paths: list):
    """测试批量上传"""
    print(f"\n测试批量上传，共 {len(file_paths)} 个文件")

    url = f"{BASE_URL}/api/upload/batch"

    files = []
    for file_path in file_paths:
        if os.path.exists(file_path):
            files.append(("files", open(file_path, "rb")))
        else:
            print(f"文件不存在: {file_path}")

    if not files:
        print("没有有效的文件")
        return

    try:
        response = requests.post(url, files=files)
        response.raise_for_status()

        result = response.json()
        print(f"批量上传完成!")
        print(f"  总计: {result['total']}")
        print(f"  成功: {result['success']}")
        print(f"  失败: {result['failed']}")

        for file_result in result["results"]:
            print(f"\n  - 文件: {file_result['file_name']}")
            print(f"    状态: {file_result['status']}")
            print(f"    消息: {file_result['message']}")

    except requests.exceptions.RequestException as e:
        print(f"批量上传失败: {e}")


def test_get_history():
    """测试获取上传历史"""
    print("\n测试获取上传历史")

    url = f"{BASE_URL}/api/uploads?limit=10"

    try:
        response = requests.get(url)
        response.raise_for_status()

        result = response.json()
        print(f"上传历史: 共 {result['total']} 条记录")

        for item in result["items"][:3]:
            print(f"\n  - {item['file_name']}")
            print(f"    ID: {item['file_id']}")
            print(f"    上传时间: {item['uploaded_at']}")
            print(f"    处理状态: {item['processing_status']}")

    except requests.exceptions.RequestException as e:
        print(f"获取历史失败: {e}")


def test_get_status(file_id: str):
    """测试获取文件状态"""
    print(f"\n测试获取文件状态: {file_id}")

    url = f"{BASE_URL}/api/upload/{file_id}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        result = response.json()
        print(f"文件状态:")
        print(f"  文件名: {result['file_name']}")
        print(f"  上传时间: {result['uploaded_at']}")
        print(f"  处理状态: {result['processing_status']}")

    except requests.exceptions.RequestException as e:
        print(f"获取状态失败: {e}")


def test_get_content(file_id: str):
    """测试获取文件内容"""
    print(f"\n测试获取文件内容: {file_id}")

    url = f"{BASE_URL}/api/upload/{file_id}/content"

    try:
        response = requests.get(url)
        response.raise_for_status()

        result = response.json()
        print(f"文件内容:")
        print(f"  文件ID: {result['file_id']}")
        print(f"  处理时间: {result['processed_at']}")

        if result.get("documents"):
            doc = result["documents"][0]
            print(f"  文档数量: {len(result['documents'])}")
            print(f"  内容预览: {doc['page_content'][:200]}...")

    except requests.exceptions.RequestException as e:
        print(f"获取内容失败: {e}")


def main():
    """主测试函数"""
    print("=" * 60)
    print("文件上传API测试")
    print("=" * 60)

    # 测试文件列表
    test_files = [
        "./test_data/sample.pdf",
        "./test_data/document.docx",
        "./test_data/text.txt",
    ]

    # 测试单文件上传
    file_id = None
    for test_file in test_files:
        result_id = test_upload_file(test_file)
        if result_id:
            file_id = result_id
            break

    # 测试获取历史
    test_get_history()

    # 如果有上传成功的文件，测试其他API
    if file_id:
        test_get_status(file_id)
        test_get_content(file_id)

    # 测试批量上传
    valid_files = [f for f in test_files if os.path.exists(f)]
    if len(valid_files) >= 2:
        test_batch_upload(valid_files[:2])

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
