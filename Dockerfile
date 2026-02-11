# 多阶段构建 - 优化镜像大小
# Stage 1: 构建阶段
FROM python:3.10-slim as builder

# 设置工作目录
WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libfreetype6-dev \
    libpng-dev \
    libjpeg-dev \
    libtiff-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖到临时目录
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt --prefix=/install

# Stage 2: 运行阶段
FROM python:3.10-slim

# 设置标签
LABEL maintainer="rick_wang@yunquna.com"
LABEL description="RAG Service - Environmental Compliance Checking"
LABEL version="1.0.0"

# 创建非root用户
RUN groupadd -r raguser && useradd -r -g raguser raguser

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # 应用路径
    APP_HOME=/app \
    # 数据路径
    DATA_DIR=/app/data \
    FAISS_INDEX_PATH=/app/data/faiss_index \
    UPLOAD_DIR=/app/data/uploads \
    PROCESSED_DIR=/app/output_dir \
    CACHE_DIR=/app/data/cache \
    # 日志路径
    LOG_DIR=/app/logs

# 创建必要目录
RUN mkdir -p ${APP_HOME} ${DATA_DIR} ${UPLOAD_DIR} ${PROCESSED_DIR} \
    ${CACHE_DIR} ${FAISS_INDEX_PATH} ${LOG_DIR} && \
    chown -R raguser:raguser ${APP_HOME} ${DATA_DIR} ${LOG_DIR}

# 从构建阶段复制安装的包
COPY --from=builder /install /usr/local

# 复制应用代码
WORKDIR ${APP_HOME}
COPY --chown=raguser:raguser . .

# 安装Tesseract（OCR依赖）
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 切换到非root用户
USER raguser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/').read() or exit(1)"

# 启动命令
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
