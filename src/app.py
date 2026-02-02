from contextlib import asynccontextmanager
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from chain.chat_chain import ChatChain
from config import settings
from src.pipeline.document_processor import DocumentProcessingPipeline
from src.api.routes import (
    upload_router,
    markdown_router,
    health_router,
    retrieval_router,
    compliance_router,
    vector_router,
)
from src.api.routes import auth as auth_router
from src.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from src.middleware.performance_monitor import (
    PerformanceMonitorMiddleware,
    get_prometheus_metrics,
)
from src.utils.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

chat_chain = None
document_pipeline = None
executor = ThreadPoolExecutor(max_workers=5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global chat_chain, document_pipeline

    chat_chain = ChatChain()
    await chat_chain.initialize()

    config = {
        "enable_pdf_ocr": settings.enable_pdf_ocr,
        "ocr_engine": settings.ocr_engine,
        "ocr_confidence_threshold": settings.ocr_confidence_threshold,
        "ocr_module_confidence_threshold": settings.ocr_module_confidence_threshold,
        "ocr_api_endpoint": settings.ocr_api_endpoint,
        "ocr_output_dir": settings.ocr_output_dir,
        "ocr_error_continue": settings.ocr_error_continue,
        "enable_chunking": settings.enable_chunking,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "chunking_strategy": settings.chunking_strategy,
    }
    document_pipeline = DocumentProcessingPipeline(config)

    logger.info("服务启动完成")
    yield

    executor.shutdown(wait=True)
    logger.info("服务关闭完成")


app = FastAPI(
    title="智能客服系统",
    description="智能客服系统API",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(PerformanceMonitorMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(vector_router)
app.include_router(markdown_router)
app.include_router(health_router)
app.include_router(retrieval_router)
app.include_router(compliance_router)
app.include_router(auth_router.router)


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=get_prometheus_metrics(), media_type="text/plain")


if os.path.exists(settings.frontend_static_dir):
    app.mount(
        "/",
        StaticFiles(directory=settings.frontend_static_dir, html=True),
        name="static",
    )
