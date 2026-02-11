from .upload import router as upload_router
from .markdown import router as markdown_router
from .health import router as health_router
from .retrieval import router as retrieval_router
from .compliance import router as compliance_router
from .auth import router as auth_router
from .vector import router as vector_router
from . import maintenance

__all__ = [
    "upload_router",
    "markdown_router",
    "health_router",
    "retrieval_router",
    "compliance_router",
    "auth_router",
    "vector_router",
    "maintenance",
]
