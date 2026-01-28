"""
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 21:43:00
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-07 08:14:50
FilePath: /RAG_agent/config.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Dict, List
from pathlib import Path


class Settings(BaseSettings):
    openai_api_key: str
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-3.5-turbo"
    openai_embedding_model: str = "text-embedding-ada-002"
    gemini_api_key: str
    mineru_api_key: str
    dashscope_api_key: str
    dashscope_embedding_model: str = (
        "text-embedding-v2"  # 使用v2（1536维）而不是v3（384维）
    )
    chroma_persist_dir: str = "./data/chroma"
    collection_name: str = "evaluation_collection"  # 统一使用evaluation_collection
    upload_dir: str = "./data/uploads"
    max_upload_size: int = 10485760

    # 分块配置
    chunk_size: int = 800
    chunk_overlap: int = 100
    use_llama_index_semantic: bool = False
    chunking_strategy: str = "hybrid"
    enable_hybrid_chunking: bool = True
    hybrid_chunk_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "recursive": 0.4,
            "tabular": 0.3,
            "fixed": 0.2,
            "semantic": 0.1,
        }
    )
    doc_type_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "standard_document": "recursive",
            "technical_table": "tabular",
            "method_description": "semantic",
            "legal_document": "recursive",
            "research_paper": "semantic",
            "financial_report": "tabular",
            "source_code": "code",
            "default": "fixed",
        }
    )

    # 检索配置
    top_k: int = 10
    retrieval_fusion_strategy: str = "reciprocal_rank_fusion"
    enable_hybrid_retrieval: bool = True
    retrieval_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "vector": 0.5,
            "keyword": 0.3,
            "structured": 0.2,
        }
    )
    enable_reranking: bool = True
    reranker_top_k: int = 20
    reranker_model: str = "BAAI/bge-reranker-large"
    enable_metadata_filter: bool = True
    standard_priority_order: List[str] = Field(
        default_factory=lambda: ["GB", "HJ", "HG", "T"]
    )

    # 评估配置
    enable_retrieval_evaluation: bool = True
    evaluation_k_values: List[int] = Field(default_factory=lambda: [1, 3, 5, 10])
    evaluation_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "recall@10": 0.70,
            "precision@5": 0.70,
            "mrr": 0.60,
            "ndcg@10": 0.70,
            "composite_score": 0.70,
        }
    )
    enable_auto_evaluation: bool = False
    evaluation_interval: int = 10

    # LLM配置
    temperature: float = 0.7
    llm_provider: str = "openai"
    llm_model: str = "gpt-3.5-turbo"

    # 安全配置
    enable_file_security_check: bool = True
    max_file_size_mb: int = 10
    allowed_file_types: List[str] = Field(
        default_factory=lambda: [
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".md",
            ".html",
            ".pptx",
            ".xlsx",
        ]
    )

    # OCR配置
    enable_pdf_ocr: bool = True
    pdf_parse_mode: str = "text_layer"  # text_layer 或 full_ocr
    ocr_engine: str = "paddleocr"
    fallback_to_cloud: bool = True
    ocr_languages: List[str] = Field(default_factory=lambda: ["ch", "en"])
    ocr_confidence_threshold: float = 0.6

    # 图片处理配置
    extract_images: bool = True
    save_extracted_images: bool = False
    min_image_size: int = 100
    max_image_size_mb: int = 5

    # 缓存配置
    enable_ocr_cache: bool = True
    cache_ttl_hours: int = 24
    max_cache_size_mb: int = 1024
    cache_dir: str = "./data/cache"

    # A/B测试配置
    enable_ab_testing: bool = False
    ab_test_traffic_percentage: float = 0.1
    experiment_groups: Dict[str, float] = Field(
        default_factory=lambda: {
            "control": 0.5,
            "ocr_basic": 0.3,
            "ocr_enhanced": 0.2,
        }
    )
    evaluation_data_dir: str = "./data/evaluation"

    # 预览配置
    preview_enabled: bool = True
    preview_output_dir: str = "./data/previews"

    # Markdown编辑器配置
    markdown_editor_enabled: bool = True
    markdown_output_dir: str = "./output_dir"
    markdown_max_file_size: int = 10485760  # 10MB

    # 前端配置
    frontend_static_dir: str = "./static"
    frontend_dev_port: int = 3000

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._create_directories()

    def _create_directories(self):
        Path(self.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        Path(self.evaluation_data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.preview_output_dir).mkdir(parents=True, exist_ok=True)
        if self.markdown_editor_enabled:
            Path(self.markdown_output_dir).mkdir(parents=True, exist_ok=True)
            Path(self.frontend_static_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
