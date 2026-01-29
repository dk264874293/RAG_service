"""
智能分块策略
支持多种分块策略：语义分块、递归分块、固定大小分块等
支持LlamaIndex语义分块器（如果可用）
"""

from typing import List, Dict, Optional
import logging
from ..models.document import Document

logger = logging.getLogger(__name__)


class AdaptiveChunker:
    """自适应分块器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.chunk_size = self.config.get("chunk_size", 1000)
        self.chunk_overlap = self.config.get("chunk_overlap", 200)
        self.use_llama_index_semantic = self.config.get(
            "use_llama_index_semantic", False
        )

        # 文档类型到策略的映射，使用配置或默认值
        default_mapping = {
            "research_paper": "semantic",
            "legal_document": "recursive",
            "technical_doc": "fixed",
            "financial_report": "tabular",
            "source_code": "code",
            "default": "fixed",
        }
        self.doc_type_to_strategy = self.config.get("doc_type_mapping", default_mapping)

    def chunk_document(self, text: str, doc_type: str = "default") -> List[str]:
        """根据文档类型选择分块策略"""
        enable_hybrid = self.config.get("enable_hybrid_chunking", False)

        if enable_hybrid:
            return self._hybrid_chunk(text, doc_type)

        strategy_name = self.doc_type_to_strategy.get(doc_type, "fixed")

        if strategy_name == "semantic":
            chunks = self._semantic_chunk(text)
        elif strategy_name == "recursive":
            chunks = self._recursive_chunk(text)
        elif strategy_name == "fixed":
            chunks = self._fixed_size_chunk(text)
        elif strategy_name == "tabular":
            chunks = self._tabular_chunk(text)
        elif strategy_name == "code":
            chunks = self._code_chunk(text)
        else:
            chunks = self._fixed_size_chunk(text)

        # 添加重叠窗口
        if self.chunk_overlap > 0:
            chunks = self._add_overlap(chunks, self.chunk_overlap)

        # 边界优化
        chunks = self._optimize_boundaries(chunks)

        return chunks

    def _fixed_size_chunk(self, text: str) -> List[str]:
        """固定大小分块"""
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _recursive_chunk(self, text: str) -> List[str]:
        """递归分块 - 按段落、句子、单词层级递归"""
        # 首先按段落分割
        paragraphs = text.split("\n\n")
        chunks = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(para) <= self.chunk_size:
                chunks.append(para)
            else:
                # 段落太大，按句子分割
                sentences = self._split_sentences(para)
                current_chunk = []
                current_length = 0

                for sentence in sentences:
                    sentence_length = len(sentence)
                    if (
                        current_length + sentence_length > self.chunk_size
                        and current_chunk
                    ):
                        chunks.append(" ".join(current_chunk))
                        current_chunk = [sentence]
                        current_length = sentence_length
                    else:
                        current_chunk.append(sentence)
                        current_length += sentence_length

                if current_chunk:
                    chunks.append(" ".join(current_chunk))

        return chunks

    def _semantic_chunk(self, text: str) -> List[str]:
        """语义分块 - 基于语义相似度"""
        # 如果启用了LlamaIndex语义分块并且相关库可用，则使用LlamaIndex
        if self.use_llama_index_semantic:
            try:
                return self._semantic_chunk_llama_index(text)
            except ImportError as e:
                logger.warning(f"LlamaIndex不可用，回退到默认语义分块: {e}")
            except Exception as e:
                logger.error(f"LlamaIndex语义分块失败: {e}")
                logger.warning("回退到默认语义分块")

        # 默认语义分块：使用句子边界和简单启发式规则
        sentences = self._split_sentences(text)
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)
            # 如果当前块为空或添加句子后不超过限制，继续添加
            if current_length + sentence_length <= self.chunk_size:
                current_chunk.append(sentence)
                current_length += sentence_length
            else:
                # 保存当前块
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                # 开始新块
                current_chunk = [sentence]
                current_length = sentence_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _semantic_chunk_llama_index(self, text: str) -> List[str]:
        """使用LlamaIndex进行语义分块"""
        try:
            from llama_index.core import Document as LlamaDocument
            from llama_index.core.node_parser import SemanticSplitterNodeParser
            from llama_index.embeddings.openai import OpenAIEmbedding
            import os

            # 获取API密钥（简化版，实际应从配置中获取）
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY未设置，无法使用LlamaIndex语义分块")
                raise ValueError("OPENAI_API_KEY未设置")

            # 创建嵌入模型
            embed_model = OpenAIEmbedding(api_key=api_key)

            # 定义中文句子分割器
            import re

            def chinese_sentence_tokenizer(text: str) -> list[str]:
                sentences = re.findall(r"[^。！？…\n]+[。！？…\n]?", text)
                return [s.strip() for s in sentences if s.strip()]

            # 创建语义分块器
            semantic_splitter = SemanticSplitterNodeParser(
                buffer_size=1,
                breakpoint_percentile_threshold=95,
                embed_model=embed_model,
                sentence_splitter=chinese_sentence_tokenizer,
            )

            # 创建LlamaIndex文档对象
            llama_doc = LlamaDocument(text=text)

            # 执行分块
            nodes = semantic_splitter.get_nodes_from_documents([llama_doc])

            # 提取文本块
            chunks = [
                node.get_content().strip()
                for node in nodes
                if node.get_content().strip()
            ]

            if not chunks:
                logger.warning("LlamaIndex语义分块未产生任何块，回退到默认分块")
                raise ValueError("未产生分块")

            logger.info(f"LlamaIndex语义分块产生了 {len(chunks)} 个块")
            return chunks

        except ImportError as e:
            logger.error(f"导入LlamaIndex模块失败: {e}")
            raise ImportError("请安装llama-index包: pip install llama-index")
        except Exception as e:
            logger.error(f"LlamaIndex语义分块过程中出错: {e}")
            raise

    def _tabular_chunk(self, text: str) -> List[str]:
        """表格分块 - 保持表格结构"""
        lines = text.split("\n")
        chunks = []
        current_table = []
        in_table = False

        for line in lines:
            line_stripped = line.strip()

            # 检测表格行的特征
            is_table_row = self._is_table_row(line)

            if is_table_row:
                if not in_table:
                    # 进入表格
                    in_table = True
                    current_table = []
                current_table.append(line)
            else:
                if in_table:
                    # 离开表格，保存表格
                    if current_table:
                        table_content = "\n".join(current_table)
                        chunks.append(self._format_table_chunk(table_content))
                    current_table = []
                    in_table = False

                # 保存非表格内容
                if line_stripped:
                    chunks.append(line_stripped)

        # 处理最后的表格
        if current_table:
            table_content = "\n".join(current_table)
            chunks.append(self._format_table_chunk(table_content))

        return chunks

    def _is_table_row(self, line: str) -> bool:
        """检测是否为表格行"""
        # 特征1：包含多个制表符
        if line.count("\t") >= 2:
            return True

        # 特征2：包含多个连续空格（对齐的列）
        consecutive_spaces = [m.group() for m in re.finditer(r" {3,}", line)]
        if len(consecutive_spaces) >= 2:
            return True

        # 特征3：包含表格分隔符（如 | 或 +）
        if "|" in line or line.startswith("+") or line.startswith("-"):
            return True

        # 特征4：包含数字对齐模式（如 1.23  45.6）
        numbers = re.findall(r"\d+\.?\d*", line)
        if len(numbers) >= 3:
            return True

        return False

    def _format_table_chunk(self, table_content: str) -> str:
        """格式化表格块，添加元数据"""
        formatted = f"[表格]\n{table_content}\n[/表格]"
        return formatted

    def _code_chunk(self, text: str) -> List[str]:
        """代码分块 - 保持代码结构"""
        # 按函数、类等代码块分割
        lines = text.split("\n")
        chunks = []
        current_block = []
        indent_level = 0

        for line in lines:
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                # 空行或注释，继续添加到当前块
                current_block.append(line)
            else:
                # 计算缩进
                current_indent = len(line) - len(stripped)
                if current_indent == 0 and current_block:
                    # 新的顶级块，保存之前的块
                    chunks.append("\n".join(current_block))
                    current_block = [line]
                else:
                    current_block.append(line)

        if current_block:
            chunks.append("\n".join(current_block))

        return chunks

    def _hybrid_chunk(self, text: str, doc_type: str = "default") -> List[str]:
        """混合分块策略：结合多种分块策略"""
        weights = self.config.get(
            "hybrid_chunk_weights",
            {
                "recursive": 0.4,
                "tabular": 0.3,
                "fixed": 0.2,
                "semantic": 0.1,
            },
        )

        # 并行使用多种策略分块
        all_chunks = []

        # 1. 递归分块（主策略）
        if weights.get("recursive", 0) > 0:
            recursive_chunks = self._recursive_chunk(text)
            for i, chunk in enumerate(recursive_chunks):
                all_chunks.append(
                    {
                        "content": chunk,
                        "strategy": "recursive",
                        "weight": weights.get("recursive", 0),
                        "order": i,
                    }
                )

        # 2. 表格分块（检测表格）
        if weights.get("tabular", 0) > 0:
            tabular_chunks = self._tabular_chunk(text)
            for i, chunk in enumerate(tabular_chunks):
                all_chunks.append(
                    {
                        "content": chunk,
                        "strategy": "tabular",
                        "weight": weights.get("tabular", 0),
                        "order": i + len(recursive_chunks),
                    }
                )

        # 3. 固定分块（兜底）
        if weights.get("fixed", 0) > 0:
            fixed_chunks = self._fixed_size_chunk(text)
            for i, chunk in enumerate(fixed_chunks):
                all_chunks.append(
                    {
                        "content": chunk,
                        "strategy": "fixed",
                        "weight": weights.get("fixed", 0),
                        "order": i + len(recursive_chunks) + len(tabular_chunks),
                    }
                )

        # 4. 语义分块（可选）
        if weights.get("semantic", 0) > 0:
            try:
                semantic_chunks = self._semantic_chunk(text)
                for i, chunk in enumerate(semantic_chunks):
                    all_chunks.append(
                        {
                            "content": chunk,
                            "strategy": "semantic",
                            "weight": weights.get("semantic", 0),
                            "order": i
                            + len(recursive_chunks)
                            + len(tabular_chunks)
                            + len(fixed_chunks),
                        }
                    )
            except Exception as e:
                logger.warning(f"语义分块失败，跳过: {e}")

        # 去重（基于相似度）
        unique_chunks = self._deduplicate_chunks(all_chunks)

        # 按权重排序，保留高权重块
        sorted_chunks = sorted(
            unique_chunks,
            key=lambda x: (
                -x["weight"],  # 权重高的优先
                x["order"],  # 保持原始顺序
            ),
        )

        # 提取内容
        final_chunks = [chunk["content"] for chunk in sorted_chunks]

        # 添加重叠窗口
        if self.chunk_overlap > 0:
            final_chunks = self._add_overlap(final_chunks, self.chunk_overlap)

        # 边界优化
        final_chunks = self._optimize_boundaries(final_chunks)

        logger.info(
            f"混合分块完成: 总块数={len(final_chunks)}, "
            f"递归={len([c for c in all_chunks if c['strategy'] == 'recursive'])}, "
            f"表格={len([c for c in all_chunks if c['strategy'] == 'tabular'])}, "
            f"固定={len([c for c in all_chunks if c['strategy'] == 'fixed'])}, "
            f"语义={len([c for c in all_chunks if c['strategy'] == 'semantic'])}"
        )

        return final_chunks

    def _deduplicate_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """基于相似度去重"""
        unique_chunks = []
        seen_content = set()

        for chunk in chunks:
            content = chunk["content"].strip()
            # 计算内容哈希
            content_hash = hash(content)

            # 检查是否已存在相似内容
            is_duplicate = False
            for seen_hash in seen_content:
                if content_hash == seen_hash:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_chunks.append(chunk)
                seen_content.add(content_hash)

        return unique_chunks

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        import re

        # 中英文句子分割
        pattern = r"[。！？.!?]\s*"
        sentences = re.split(pattern, text)
        # 过滤空句子并添加标点
        result = []
        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if sent:
                # 尝试恢复标点（简化版）
                if i < len(sentences) - 1:
                    # 查找原始文本中的标点
                    match = re.search(
                        r"[。！？.!?]",
                        text[text.find(sent) : text.find(sent) + len(sent) + 5],
                    )
                    if match:
                        sent += match.group()
                result.append(sent)
        return result

    def _add_overlap(self, chunks: List[str], overlap_size: int) -> List[str]:
        """添加重叠窗口"""
        if len(chunks) <= 1:
            return chunks

        overlapped_chunks = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            # 从前一个块的末尾提取重叠部分
            overlap_text = (
                prev_chunk[-overlap_size:]
                if len(prev_chunk) > overlap_size
                else prev_chunk
            )

            # 合并重叠部分和当前块
            overlapped_chunk = overlap_text + current_chunk
            overlapped_chunks.append(overlapped_chunk)

        return overlapped_chunks

    def _optimize_boundaries(self, chunks: List[str]) -> List[str]:
        """优化分块边界"""
        optimized = []
        for chunk in chunks:
            # 确保不在单词中间断开（简化版）
            # 实际应用中可以使用更复杂的边界检测
            optimized.append(chunk.strip())

        return optimized
