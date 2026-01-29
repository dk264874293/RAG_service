"""
RAG服务配置文件
Author: 汪培良 <rick_wang@yunquna.com>
Date: 2026-01-06 21:43:00
LastEditors: 汪培良 <rick_wang@yunquna.com>
LastEditTime: 2024-01-28
Description: 统一的配置管理，支持从环境变量和.env文件加载配置项
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Dict, List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """
    RAG服务配置类，继承自BaseSettings支持从环境变量和.env文件加载
    所有配置项均可通过环境变量覆盖（使用大写下划线格式）
    """

    # ==================== API密钥配置 ====================

    # OpenAI API密钥，从环境变量OPENAI_API_KEY读取，必需配置
    openai_api_key: str

    # OpenAI API基础URL，默认使用官方API地址
    # 可选值：官方地址、自定义代理地址
    openai_api_base: str = "https://api.openai.com/v1"

    # OpenAI API基础URL（别名，兼容环境变量）
    openai_base_url: Optional[str] = None

    # OpenAI对话模型名称，默认使用gpt-3.5-turbo
    # 可选值：gpt-3.5-turbo、gpt-4、gpt-4-turbo-preview
    openai_model: str = "gpt-3.5-turbo"

    # OpenAI对话模型名称（别名，兼容环境变量）
    openai_model_name: Optional[str] = None

    # OpenAI嵌入模型，用于文本向量化，默认使用ada-002
    # 维度：1536维，影响向量检索质量
    openai_embedding_model: str = "text-embedding-ada-002"

    # Google Gemini API密钥，从环境变量GEMINI_API_KEY读取，可选配置
    gemini_api_key: Optional[str] = None

    # Mineru API密钥，从环境变量MINERU_API_KEY读取，可选配置
    # Mineru是专业的文档解析API服务
    mineru_api_key: Optional[str] = None

    # 阿里云Dashscope API密钥，从环境变量DASHSCOPE_API_KEY读取，必需配置
    # Dashscope提供通义千问等大模型服务
    dashscope_api_key: str

    # 阿里云Dashscope嵌入模型名称
    # 使用v2版本（1536维）而不是v3（384维），提供更好的向量表示
    dashscope_embedding_model: str = "text-embedding-v2"

    # ==================== 数据存储配置 ====================

    # Chroma向量数据库持久化目录，存储向量索引和元数据
    # 用于RAG系统的向量检索
    chroma_persist_dir: str = "./data/chroma"

    # Chroma集合名称，用于区分不同的向量集合
    # 统一使用evaluation_collection，避免数据混淆
    collection_name: str = "evaluation_collection"

    # 文件上传目录，用于存储用户上传的原始文件
    # 支持的文件类型见allowed_file_types配置
    upload_dir: str = "./data/uploads"

    # FAISS向量存储配置
    # 用于基于FAISS的高性能向量相似度检索
    faiss_index_path: str = "./data/faiss_index"
    faiss_dimension: int = 1536  # DashScope text-embedding-v2 向量维度

    # 最大上传文件大小（字节），默认10MB（10485760）
    # 超过此大小的文件将被拒绝
    max_upload_size: int = 10485760

    # ==================== 文档分块配置 ====================

    # 是否启用文档分块，默认True
    # True：将文档分成多个小块进行向量化，提高检索精度
    # False：将整个文档作为单个向量存储
    enable_chunking: bool = True

    # 文档分块大小（字符数），默认800字符
    # 影响检索粒度：太小导致上下文断裂，太大降低检索精确度
    chunk_size: int = 800

    # 分块重叠字符数，默认100字符
    # 确保分块之间的上下文连续性，避免信息丢失
    chunk_overlap: int = 100

    # 是否使用LlamaIndex语义分块
    # True：基于语义相似度进行分块；False：基于固定长度分块
    use_llama_index_semantic: bool = False

    # 文档分块策略，默认hybrid（混合策略）
    # 可选值：
    #   - hybrid: 混合策略，结合多种分块方法
    #   - recursive: 递归分块，适用于结构化文档
    #   - fixed: 固定大小分块，适用于无结构文档
    #   - semantic: 语义分块，基于内容相似度
    #   - tabular: 表格分块，适用于表格数据
    #   - code: 代码分块，适用于程序代码
    chunking_strategy: str = "hybrid"

    # 是否启用混合分块，结合多种分块策略
    # True：根据hybrid_chunk_weights组合多种策略；False：使用单一策略
    enable_hybrid_chunking: bool = True

    # 混合分块权重分配，控制不同分块策略的占比
    # 总和应为1.0，影响最终分块效果
    hybrid_chunk_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "recursive": 0.4,  # 递归分块权重40%
            "tabular": 0.3,  # 表格分块权重30%
            "fixed": 0.2,  # 固定分块权重20%
            "semantic": 0.1,  # 语义分块权重10%
        }
    )

    # 文档类型到分块策略的映射，根据文档类型自动选择分块策略
    # 键：文档类型名称；值：分块策略名称
    doc_type_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "standard_document": "recursive",  # 标准文档使用递归分块
            "technical_table": "tabular",  # 技术表格使用表格分块
            "method_description": "semantic",  # 方法描述使用语义分块
            "legal_document": "recursive",  # 法律文档使用递归分块
            "research_paper": "semantic",  # 研究论文使用语义分块
            "financial_report": "tabular",  # 财务报告使用表格分块
            "source_code": "code",  # 源代码使用代码分块
            "default": "fixed",  # 默认使用固定分块
        }
    )

    # ==================== 检索配置 ====================

    # 检索返回的Top-K文档数量，默认10
    # 影响检索结果的多样性：K值太大返回不相关内容，太小遗漏相关内容
    top_k: int = 10

    # 检索融合策略，默认reciprocal_rank_fusion（倒数排名融合）
    # 可选值：
    #   - reciprocal_rank_fusion: 倒数排名融合，RRF算法
    #   - weighted_sum: 加权求和
    #   - concatenation: 结果拼接
    retrieval_fusion_strategy: str = "reciprocal_rank_fusion"

    # 是否启用混合检索，结合向量检索、关键词检索和结构化检索
    # True：提高检索召回率和准确率；False：仅使用向量检索
    enable_hybrid_retrieval: bool = True

    # 混合检索权重分配，控制不同检索方法的贡献度
    # 总和应为1.0，影响最终检索结果排序
    retrieval_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "vector": 0.5,  # 向量检索权重50%
            "keyword": 0.3,  # 关键词检索权重30%
            "structured": 0.2,  # 结构化检索权重20%
        }
    )

    # 是否启用结果重排序，使用reranker模型优化检索结果
    # True：提高排序准确性，但增加响应时间；False：使用原始检索结果
    enable_reranking: bool = True

    # 重排序前保留的文档数量，默认20
    # 重排序后返回top_k个结果，此值应大于top_k
    reranker_top_k: int = 20

    # 重排序模型名称，用于对检索结果进行重新排序
    # 默认使用BAAI/bge-reranker-large，支持其他BGE系列模型
    reranker_model: str = "BAAI/bge-reranker-large"

    # 是否启用元数据过滤，根据文档元数据进行筛选
    # True：支持按文档属性过滤；False：忽略元数据
    enable_metadata_filter: bool = True

    # 标准文献优先级排序，按文档类型排序检索结果
    # 优先级：GB（国标）> HJ（环保）> HG（化工）> T（推荐）
    standard_priority_order: List[str] = Field(
        default_factory=lambda: ["GB", "HJ", "HG", "T"]
    )

    # ==================== 评估配置 ====================

    # 是否启用检索效果评估，计算检索质量指标
    # True：自动计算recall、precision、MRR、NDCG等指标；False：跳过评估
    enable_retrieval_evaluation: bool = True

    # 评估的K值列表，对应不同的召回数
    # 例如：[1,3,5,10]表示评估@1、@3、@5、@10的检索效果
    evaluation_k_values: List[int] = Field(default_factory=lambda: [1, 3, 5, 10])

    # 评估指标阈值，用于判断检索效果是否达标
    # 当指标值低于此阈值时，视为不达标
    evaluation_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "recall@10": 0.70,  # 召回率@10阈值70%
            "precision@5": 0.70,  # 精确率@5阈值70%
            "mrr": 0.60,  # 平均倒数排名阈值0.6
            "ndcg@10": 0.70,  # 归一化折损累积增益@10阈值70%
            "composite_score": 0.70,  # 综合评分阈值70%
        }
    )

    # 是否启用自动评估，定期运行评估任务
    # True：每evaluation_interval次查询后自动评估；False：手动触发评估
    enable_auto_evaluation: bool = False

    # 自动评估间隔（次数），默认10次查询后评估一次
    # 用于控制评估频率，避免频繁评估影响性能
    evaluation_interval: int = 10

    # ==================== LLM配置 ====================

    # LLM温度参数，控制生成随机性，范围0.0-2.0，默认0.7
    # 0.0：确定性输出，适合事实性回答
    # 0.7：适中的创造性，适合一般对话
    # 1.0+：高创造性，适合创意生成
    temperature: float = 0.7

    # LLM提供商，默认openai
    # 可选值：
    #   - openai: OpenAI系列模型
    #   - gemini: Google Gemini系列模型
    #   - dashscope: 阿里云通义系列模型
    llm_provider: str = "openai"

    # LLM模型名称，与provider对应，默认gpt-3.5-turbo
    # openai: gpt-3.5-turbo、gpt-4、gpt-4-turbo-preview
    # gemini: gemini-pro、gemini-pro-vision
    # dashscope: qwen-turbo、qwen-plus、qwen-max
    llm_model: str = "gpt-3.5-turbo"

    # ==================== 安全配置 ====================

    # JWT密钥，用于签名和验证JWT令牌
    # 从环境变量SECRET_KEY读取，生产环境必须使用强随机密钥
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

    # JWT签名算法，默认HS256
    # 可选值：HS256（HMAC SHA-256）、RS256（RSA SHA-256）
    algorithm: str = "HS256"

    # 访问令牌过期时间（分钟），默认30分钟
    # 控制令牌有效期，过期后需要重新登录
    access_token_expire_minutes: int = 30

    # API密钥，用于API密钥认证方式
    # 从环境变量API_KEY读取，可选配置
    api_key: Optional[str] = os.getenv("API_KEY", None)

    # 是否启用JWT认证，默认True
    # True：保护需要认证的端点；False：允许匿名访问（开发模式）
    enable_jwt_auth: bool = True

    # 是否启用API密钥认证，默认False
    # True：允许使用API密钥访问；False：仅使用JWT认证
    enable_api_key_auth: bool = False

    # 是否启用文件安全检查，验证文件类型和大小
    # True：执行安全检查；False：跳过检查（仅用于开发环境）
    enable_file_security_check: bool = True

    # 最大文件大小（MB），默认10MB
    # 超过此大小的文件将被拒绝上传
    max_file_size_mb: int = 10

    # 允许的文件扩展名列表
    # 仅支持列表中定义的文件类型，其他类型将被拒绝
    allowed_file_types: List[str] = Field(
        default_factory=lambda: [
            ".pdf",  # PDF文档
            ".docx",  # Word文档
            ".doc",  # 旧版Word文档
            ".txt",  # 纯文本文件
            ".md",  # Markdown文档
            ".html",  # HTML网页
            ".pptx",  # PowerPoint演示文稿
            ".xlsx",  # Excel电子表格
        ]
    )

    # ==================== OCR配置 ====================

    # 是否启用PDF OCR识别，对无法直接提取文本的PDF进行OCR
    # True：对PDF进行OCR识别；False：仅提取文本层
    enable_pdf_ocr: bool = True

    # OCR引擎，默认paddle（飞桨）
    # 可选值：
    #   - paddle: 飞桨OCR远程API，需要配置endpoint和key
    ocr_engine: str = os.getenv("OCR_ENGINE", "PP-OCRv5")

    # PaddleOCR API端点（远程模式必需）
    # 从环境变量PADDLE_API_ENDPOINT读取
    ocr_api_endpoint: Optional[str] = os.getenv("OCR_API_ENDPOINT", None)

    # OCR 远程 API密钥（别名，兼容环境变量）
    ocr_api_key: Optional[str] = os.getenv("OCR_API_KEY", None)

    # PaddleOCR输出目录（远程模式必需，用于保存Markdown和图片）
    # OCR识别后生成的Markdown文件和图片保存在此目录
    ocr_output_dir: Optional[str] = "./output_dir/"

    # 本地OCR失败时是否回退到云端OCR
    # True：失败后调用云端API；False：仅使用本地OCR
    fallback_to_cloud: bool = True

    # OCR识别语言列表，默认支持中英文
    # 可选值：ch（中文）、en（英文）、japan（日文）、korean（韩文）等
    # 支持同时识别多种语言
    ocr_languages: List[str] = Field(default_factory=lambda: ["ch", "en"])

    # OCR置信度阈值，范围0.0-1.0，默认0.6
    # 低于此值的识别结果将被过滤，提高识别准确性
    # 用于PDF提取器过滤低置信度结果
    ocr_confidence_threshold: float = 0.6

    # OCR模块内部置信度阈值，范围0.0-1.0
    # 用于OCR引擎内部过滤低置信度结果，默认使用ocr_confidence_threshold
    # 可通过环境变量OCR_MODULE_CONFIDENCE_THRESHOLD覆盖
    ocr_module_confidence_threshold: Optional[float] = None

    # ==================== 图片处理配置 ====================

    # 是否从文档中提取图片，默认True
    # True：提取PDF、Word等文档中的图片；False：忽略图片
    extract_images: bool = True

    # 是否保存提取的图片到本地，默认False
    # True：保存到output_images目录；False：仅提取不保存
    save_extracted_images: bool = False

    # 最小图片尺寸（像素），默认100
    # 小于此尺寸（100x100）的图片将被忽略
    min_image_size: int = 100

    # 最大图片大小（MB），默认5MB
    # 超过此大小的图片将被拒绝
    max_image_size_mb: int = 5

    # ==================== Redis配置 ====================

    # Redis服务器主机地址
    redis_server_host: Optional[str] = None

    # Redis服务器端口
    redis_server_port: Optional[str] = None

    # Redis数据库编号
    redis_server_db: Optional[str] = None

    # 用户代理字符串
    user_agent: Optional[str] = None

    # ==================== 缓存配置 ====================

    # 是否启用OCR结果缓存，避免重复识别相同内容
    # True：缓存OCR结果，提高重复文档处理速度；False：每次都重新识别
    enable_ocr_cache: bool = True

    # OCR缓存生存时间（秒），默认3600秒（1小时）
    # 用于OCRService内部的缓存管理
    # 缓存文件超过此时间后将失效，需要重新OCR识别
    cache_ttl: int = 3600

    # 缓存生存时间（小时），默认24小时
    # 用于文档处理流水线的缓存管理
    # 缓存文件超过此时间后将失效，需要重新OCR识别
    cache_ttl_hours: int = 24

    # OCR错误时是否继续处理，默认False
    # True：OCR失败时继续处理后续图片；False：中断处理
    ocr_error_continue: bool = False

    # 最大缓存大小（MB），默认1024MB（1GB）
    # 超过此大小时，最旧的缓存文件将被删除
    max_cache_size_mb: int = 1024

    # 缓存文件存储目录
    # OCR识别结果和中间文件将保存在此目录
    cache_dir: str = "./data/cache"

    # ==================== A/B测试配置 ====================

    # 是否启用A/B测试，对比不同OCR方案效果
    # True：启用A/B测试，流量分配到不同实验组；False：仅使用默认方案
    enable_ab_testing: bool = False

    # A/B测试流量分配（0.0-1.0），默认0.1（10%）
    # 表示有多少比例的流量进入测试组，其余使用对照组
    ab_test_traffic_percentage: float = 0.1

    # 实验组分配，定义不同OCR方案的流量占比
    # control: 对照组，使用当前默认OCR方案
    # ocr_basic: 基础OCR组，使用基础OCR配置
    # ocr_enhanced: 增强OCR组，使用增强OCR配置
    experiment_groups: Dict[str, float] = Field(
        default_factory=lambda: {
            "control": 0.5,  # 对照组流量50%
            "ocr_basic": 0.3,  # 基础OCR组流量30%
            "ocr_enhanced": 0.2,  # 增强OCR组流量20%
        }
    )

    # 评估数据存储目录，用于保存测试结果和评估报告
    # A/B测试的统计数据、性能指标等保存在此目录
    evaluation_data_dir: str = "./data/evaluation"

    # ==================== 预览配置 ====================

    # 是否启用文档预览功能，生成文档的可视化预览
    # True：生成HTML预览文件；False：跳过预览生成
    preview_enabled: bool = True

    # 预览文件输出目录
    # 生成的HTML预览文件将保存在此目录，供前端访问
    preview_output_dir: str = "./data/previews"

    # ==================== Markdown编辑器配置 ====================

    # 是否启用Markdown在线编辑器，允许在Web界面编辑Markdown文件
    # True：提供Markdown编辑器功能；False：禁用编辑功能
    markdown_editor_enabled: bool = True

    # Markdown文件存储目录，默认./src/extractor/ocr_module/output_dir
    # OCR识别后生成的Markdown文件保存在此目录
    # 建议使用绝对路径或相对于项目根目录的相对路径
    markdown_output_dir: str = "./src/extractor/ocr_module/output_dir"

    # 最大Markdown文件大小（字节），默认10MB
    # 超过此大小的Markdown文件将无法编辑和保存
    markdown_max_file_size: int = 10485760  # 10MB

    # ==================== 前端配置 ====================

    # 前端静态文件目录，生产构建后的文件存放位置
    # 开发模式：前端运行在独立服务器
    # 生产模式：前端构建产物输出到此目录，由后端统一提供
    frontend_static_dir: str = "./static"

    # 前端开发服务器端口，默认3000
    # 仅在开发模式下使用，生产模式由后端统一部署
    frontend_dev_port: int = 3000

    # 是否启用调试模式，默认False
    # True：启用热重载、详细日志等开发特性
    # False：生产模式，禁用热重载，优化性能
    debug_mode: bool = False

    class Config:
        """Pydantic配置类"""

        # 环境变量文件路径，默认使用项目根目录下的.env文件
        env_file = ".env"
        # 是否区分大小写，False表示环境变量不区分大小写
        case_sensitive = False
        # 是否允许额外字段，True表示忽略未定义的环境变量
        extra = "ignore"

    def __init__(self, **kwargs):
        """初始化配置并自动创建所需目录"""
        super().__init__(**kwargs)
        # 处理别名字段
        if self.openai_base_url:
            self.openai_api_base = self.openai_base_url
        if self.openai_model_name:
            self.openai_model = self.openai_model_name
        if self.ocr_api_key:
            self.ocr_api_key = self.ocr_api_key
        self._create_directories()

    def _create_directories(self):
        """
        自动创建所有需要的目录
        在配置加载后自动调用，确保所有目录存在
        """
        # 创建向量数据库目录
        Path(self.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        # 创建文件上传目录
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        # 创建OCR缓存目录
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        # 创建评估数据目录
        Path(self.evaluation_data_dir).mkdir(parents=True, exist_ok=True)
        # 创建预览输出目录
        Path(self.preview_output_dir).mkdir(parents=True, exist_ok=True)

        # 创建Markdown编辑器相关目录（如果启用）
        if self.markdown_editor_enabled:
            # 创建Markdown文件存储目录
            Path(self.markdown_output_dir).mkdir(parents=True, exist_ok=True)
            # 创建前端静态文件目录
            Path(self.frontend_static_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
