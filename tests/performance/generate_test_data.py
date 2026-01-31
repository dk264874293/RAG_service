"""
Generate test data for performance benchmarking
Creates synthetic documents with embeddings
"""

import numpy as np
import json
from pathlib import Path


def generate_test_documents(num_docs: int, dimension: int = 1536):
    """Generate test documents with random embeddings

    Args:
        num_docs: Number of documents to generate
        dimension: Embedding dimension (default 1536)

    Returns:
        List of document dictionaries with id, content, metadata, embedding
    """
    documents = []

    topics = [
        "人工智能技术发展趋势",
        "机器学习在医疗领域的应用",
        "深度学习模型优化方法",
        "自然语言处理最新进展",
        "计算机视觉技术应用",
        "数据科学与最佳实践",
        "云计算架构设计",
        "网络安全防护策略",
        "区块链技术创新",
    ]

    for i in range(num_docs):
        topic = topics[i % len(topics)]
        content = f"""
        关于{topic}的详细说明。本文档包含相关的技术细节、实施建议和案例分析。
        {topic}是一个快速发展的领域，需要持续关注最新的技术趋势和行业动态。

        关键要点：
        1. 理解{topic}的核心概念和基础原理
        2. 掌握当前主流的技术栈和工具
        3. 分析实际应用场景和成功案例
        4. 制定学习和实践路线图
        5. 跟踪行业前沿动态和学术研究进展

        实施建议：
        - 建立系统的知识体系
        - 参与开源项目和社区讨论
        - 动手实践，积累项目经验
        - 定期回顾和总结学习成果
        - 持续优化工作流程和学习方法
        """

        doc_id = f"doc_{i:06d}"
        embedding = np.random.randn(dimension).astype("float32")
        embedding = embedding / np.linalg.norm(embedding)

        documents.append(
            {
                "id": doc_id,
                "content": content.strip(),
                "metadata": {
                    "topic": topic,
                    "doc_type": "research_paper",
                    "length": len(content),
                    "index": i,
                },
                "embedding": embedding,
            }
        )

    return documents


def build_bm25_corpus(documents):
    """Build tokenized corpus for BM25

    Args:
        documents: List of document dictionaries

    Returns:
        List of tokenized documents
    """
    import jieba

    corpus = []
    for doc in documents:
        tokens = list(jieba.cut(doc["content"]))
        corpus.append(tokens)

    return corpus


def save_test_data(documents, output_path: str = "./data/test_data.json"):
    """Save test data to JSON file

    Args:
        documents: List of document dictionaries
        output_path: Path to save data
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    data_without_embeddings = [
        {k: v for k, v in doc.items() if k != "embedding"} for doc in documents
    ]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data_without_embeddings, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(documents)} documents to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate test data for RAG benchmarking"
    )
    parser.add_argument(
        "--num_docs", type=int, default=1000, help="Number of documents to generate"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./data/test_data.json",
        help="Output path for test data",
    )
    args = parser.parse_args()

    print(f"Generating {args.num_docs} test documents...")
    documents = generate_test_documents(args.num_docs)

    save_test_data(documents, args.output)
    print(f"✅ Test data generation completed")
