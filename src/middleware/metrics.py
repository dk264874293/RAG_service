"""
自定义Prometheus指标定义
定义业务特定的指标
"""

from prometheus_client import Counter, Histogram, Gauge, Summary, Info
from prometheus_client import CollectorRegistry
from typing import Dict, Any, Optional
import time
import functools


# ============================================
# HTTP指标
# ============================================

http_requests_total = Counter(
    'http_requests_total',
    'HTTP请求总数',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP请求延迟',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    '当前正在处理的HTTP请求数',
    ['method', 'endpoint']
)

# ============================================
# 业务指标
# ============================================

# 文档处理
document_processing_total = Counter(
    'document_processing_total',
    '文档处理总数',
    ['status', 'document_type']
)

document_processing_duration_seconds = Histogram(
    'document_processing_duration_seconds',
    '文档处理耗时',
    ['document_type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
)

upload_queue_size = Gauge(
    'upload_queue_size',
    '上传队列积压数量'
)

# OCR处理
ocr_processing_total = Counter(
    'ocr_processing_total',
    'OCR处理总数',
    ['status', 'engine']
)

ocr_processing_duration_seconds = Histogram(
    'ocr_processing_duration_seconds',
    'OCR处理耗时',
    ['engine'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

ocr_processing_failed_total = Counter(
    'ocr_processing_failed_total',
    'OCR处理失败总数',
    ['engine', 'error_type']
)

# 向量化
document_vectorization_total = Counter(
    'document_vectorization_total',
    '文档向量化总数',
    ['status']
)

document_vectorization_duration_seconds = Histogram(
    'document_vectorization_duration_seconds',
    '文档向量化耗时',
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

vector_index_size = Gauge(
    'vector_index_size',
    '向量索引大小（文档数）',
    ['index_type']
)

# ============================================
# 检索指标
# ============================================

search_requests_total = Counter(
    'search_requests_total',
    '检索请求总数',
    ['strategy', 'status']
)

search_duration_seconds = Histogram(
    'search_duration_seconds',
    '检索耗时',
    ['strategy'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

retrieval_documents_returned = Histogram(
    'retrieval_documents_returned',
    '检索返回文档数量',
    ['strategy'],
    buckets=[1, 5, 10, 20, 50, 100]
)

# 检索质量
retrieval_relevance_score = Histogram(
    'retrieval_relevance_score',
    '检索相关性分数',
    ['strategy'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# Reranker
reranker_requests_total = Counter(
    'reranker_requests_total',
    'Reranker请求总数',
    ['status']
)

reranker_duration_seconds = Histogram(
    'reranker_duration_seconds',
    'Reranker耗时',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

reranker_score_delta = Histogram(
    'reranker_score_delta',
    'Reranker分数变化',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
)

# ============================================
# 向量存储指标
# ============================================

faiss_index_compaction_total = Counter(
    'faiss_index_compaction_total',
    'FAISS索引压缩总数',
    ['status']
)

faiss_deleted_ids_count = Gauge(
    'faiss_deleted_ids_count',
    'FAISS软删除ID数量',
    ['index_type']
)

generational_migration_total = Counter(
    'generational_migration_total',
    '分代索引迁移总数',
    ['direction', 'status']
)

hot_index_size = Gauge(
    'hot_index_size',
    'Hot索引大小（向量数）'
)

cold_index_size = Gauge(
    'cold_index_size',
    'Cold索引大小（向量数）'
)

# ============================================
# BM25指标
# ============================================

bm25_index_size = Gauge(
    'bm25_index_size',
    'BM25索引大小（文档数）'
)

bm25_search_duration_seconds = Histogram(
    'bm25_search_duration_seconds',
    'BM25搜索耗时',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# ============================================
# LLM调用指标
# ============================================

llm_requests_total = Counter(
    'llm_requests_total',
    'LLM请求总数',
    ['provider', 'model', 'status']
)

llm_duration_seconds = Histogram(
    'llm_duration_seconds',
    'LLM请求耗时',
    ['provider', 'model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'LLM Token消耗总数',
    ['provider', 'model', 'type']  # type: prompt|completion
)

# ============================================
# 业务指标
# ============================================

active_users_total = Gauge(
    'active_users_total',
    '活跃用户数',
    ['window']  # window: 1h, 24h, 7d
)

compliance_checks_total = Counter(
    'compliance_checks_total',
    '合规检查总数',
    ['result']  # result: compliant|non_compliant|error
)

# ============================================
# 系统资源指标
# ============================================

process_cpu_seconds_total = Counter(
    'process_cpu_seconds_total',
    '进程CPU时间（秒）',
    ['mode']  # mode: user|system
)

process_resident_memory_bytes = Gauge(
    'process_resident_memory_bytes',
    '进程常驻内存大小（字节）'
)

process_open_fds = Gauge(
    'process_open_fds',
    '进程打开文件描述符数量'
)

# ============================================
# 辅助函数和装饰器
# ============================================

def track_time(histogram: Histogram, labels: Optional[Dict[str, str]] = None):
    """
    追踪函数执行时间的装饰器

    用法:
        @track_time(document_processing_duration_seconds, {'document_type': 'pdf'})
        def process_document(doc):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    histogram.labels(**labels).observe(duration)
                else:
                    histogram.observe(duration)
        return wrapper
    return decorator


def track_counter(counter: Counter, labels: Optional[Dict[str, str]] = None, status: str = "success"):
    """
    追踪函数调用次数的装饰器

    用法:
        @track_counter(http_requests_total, {'method': 'GET', 'endpoint': '/api/search'})
        def search():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if labels:
                    counter.labels(**labels, status=status).inc()
                else:
                    counter.labels(status=status).inc()
                return result
            except Exception as e:
                if labels:
                    counter.labels(**labels, status="error").inc()
                else:
                    counter.labels(status="error").inc()
                raise
        return wrapper
    return decorator


class MetricsHelper:
    """指标辅助类"""

    @staticmethod
    def record_search(strategy: str, duration: float, doc_count: int, status: str = "success"):
        """记录检索指标"""
        search_requests_total.labels(strategy=strategy, status=status).inc()
        search_duration_seconds.labels(strategy=strategy).observe(duration)
        retrieval_documents_returned.labels(strategy=strategy).observe(doc_count)

    @staticmethod
    def record_document_processing(doc_type: str, duration: float, status: str = "success"):
        """记录文档处理指标"""
        document_processing_total.labels(status=status, document_type=doc_type).inc()
        document_processing_duration_seconds.labels(document_type=doc_type).observe(duration)

    @staticmethod
    def record_ocr(engine: str, duration: float, status: str = "success"):
        """记录OCR指标"""
        ocr_processing_total.labels(status=status, engine=engine).inc()
        ocr_processing_duration_seconds.labels(engine=engine).observe(duration)

        if status == "failed":
            ocr_processing_failed_total.labels(engine=engine, error_type="unknown").inc()

    @staticmethod
    def update_vector_index_sizes():
        """更新向量索引大小指标"""
        # 这些值应该从实际的索引中获取
        # 这里只是示例
        vector_index_size.labels(index_type="flat").set(0)
        vector_index_size.labels(index_type="ivf").set(0)
        vector_index_size.labels(index_type="ivf_pq").set(0)
        vector_index_size.labels(index_type="hnsw").set(0)
