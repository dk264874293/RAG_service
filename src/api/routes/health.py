from datetime import datetime
from fastapi import APIRouter, status
from typing import Dict, Any

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    系统健康检查端点

    返回系统各组件的状态信息，用于监控和故障排查。

    Returns:
        包含以下字段的字典：
        - status: 系统整体状态（healthy/unhealthy）
        - timestamp: 检查时间戳
        - services: 各服务组件的详细状态
    """
    services_status = {}

    # 检查存储服务
    try:
        from pathlib import Path

        upload_dir = Path("./data/uploads")
        processed_dir = Path("./data/processed")

        storage_ok = upload_dir.exists() and processed_dir.exists()
        services_status["storage"] = {
            "status": "ok" if storage_ok else "error",
            "upload_dir_exists": upload_dir.exists(),
            "processed_dir_exists": processed_dir.exists(),
        }
    except Exception as e:
        services_status["storage"] = {
            "status": "error",
            "message": str(e),
        }

    # 检查数据库服务
    try:
        import sqlite3
        from pathlib import Path

        db_path = Path("./data/uploads.db")
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM uploads")
            count = cursor.fetchone()[0]
            conn.close()

            services_status["database"] = {
                "status": "ok",
                "upload_records": count,
            }
        else:
            services_status["database"] = {
                "status": "ok",
                "upload_records": 0,
            }
    except Exception as e:
        services_status["database"] = {
            "status": "error",
            "message": str(e),
        }

    # 检查 OCR 服务
    try:
        # 检查 OCR 配置
        from config import settings

        ocr_available = settings.enable_pdf_ocr
        services_status["ocr"] = {
            "status": "available" if ocr_available else "disabled",
            "engine": settings.ocr_engine,
        }
    except Exception as e:
        services_status["ocr"] = {
            "status": "error",
            "message": str(e),
        }

    # 确定整体状态
    overall_status = "healthy"
    for service_name, service_info in services_status.items():
        if isinstance(service_info, dict) and service_info.get("status") in [
            "error",
            "unhealthy",
        ]:
            overall_status = "unhealthy"
            break

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "services": services_status,
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, str]:
    """
    就绪检查端点（Kubernetes 就绪探针）

    Returns:
        包含就绪状态的字典
    """
    return {
        "status": "ready",
        "timestamp": datetime.now().isoformat(),
    }
