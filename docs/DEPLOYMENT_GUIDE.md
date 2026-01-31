# 🚀 RAG服务部署与运维指南

> **版本**: 1.0.0
> **更新日期**: 2026-01-29
> **维护者**: 汪培良

---

## 📚 目录

- [脚本概览](#脚本概览)
- [快速开始](#快速开始)
- [详细使用说明](#详细使用说明)
- [环境配置](#环境配置)
- [日志管理](#日志管理)
- [故障排查](#故障排查)
- [服务访问地址](#服务访问地址)
- [高级用法](#高级用法)

---

## 脚本概览

### 脚本列表

| 脚本文件 | 功能描述 | 适用场景 |
|---------|---------|---------|
| **deploy.sh** | 一键部署脚本 | 首次部署或完整重置 |
| **manage.sh** | 交互式管理菜单 | 新手友好，可视化操作 |
| **start.sh** | 启动开发服务器 | 日常开发调试 |
| **start-prod.sh** | 启动生产服务器 | 生产环境部署 |
| **stop.sh** | 停止服务 | 停止运行中的服务 |
| **restart.sh** | 重启服务 | 快速重启服务 |
| **status.sh** | 状态检查 | 查看服务运行状态 |

---

## 快速开始

### 方式1：一键部署（首次使用推荐）

```bash
./deploy.sh
```

**自动完成：**
1. ✅ 检查Python环境
2. ✅ 创建虚拟环境
3. ✅ 安装所有依赖
4. ✅ 创建必要目录
5. ✅ 生成配置文件
6. ✅ 启动开发服务

### 方式2：交互式菜单（日常使用）

```bash
./manage.sh
```

然后根据提示选择操作。

### 方式3：直接命令（高级用户）

```bash
# 启动开发服务
./start.sh

# 启动生产服务
./start-prod.sh

# 停止服务
./stop.sh

# 重启服务
./restart.sh

# 查看状态
./status.sh
```

---

## 详细使用说明

### 1. deploy.sh - 一键部署脚本

**功能：** 自动完成所有部署步骤

**使用方法：**
```bash
./deploy.sh
```

**执行流程：**
1. 检查Python版本
2. 创建Python虚拟环境（可选）
3. 安装项目依赖
4. 创建数据目录
5. 生成配置文件
6. 启动开发服务器

**适合场景：**
- 首次部署
- 完整重置环境
- 新开发环境搭建

---

### 2. manage.sh - 交互式管理菜单

**功能：** 提供友好的交互式菜单

**使用方法：**
```bash
./manage.sh
```

**菜单选项：**
```
1) 启动开发服务
2) 启动生产服务
3) 停止服务
4) 重启服务
5) 查看状态
6) 查看日志
0) 退出
```

**适合场景：**
- 新手用户
- 不熟悉命令行的用户
- 需要可视化操作界面

---

### 3. start.sh - 启动开发服务器

**功能：** 启动开发模式服务器

**使用方法：**
```bash
./start.sh
```

**特性：**
- ✅ 自动检查环境
- ✅ 自动安装依赖
- ✅ 自动创建目录
- ✅ 检查端口占用
- ✅ 后台运行
- ✅ 日志记录

**启动成功后显示：**
```
========================================
  RAG服务已启动
========================================
  API文档: http://localhost:8000/docs
  健康检查: http://localhost:8000/health/
  前端地址: http://localhost:3000
========================================
```

---

### 4. start-prod.sh - 启动生产服务器

**功能：** 启动生产模式服务器

**使用方法：**
```bash
./start-prod.sh
```

**特性：**
- 多工作进程（自动检测CPU核心数）
- 访问日志记录
- 生产级别日志
- 性能优化配置

**工作进程数：**
```bash
# 自动检测CPU核心数
WORKERS=$(python -c "import os; print(os.cpu_count())")

# 或手动指定
WORKERS=8 ./start-prod.sh
```

---

### 5. stop.sh - 停止服务

**功能：** 优雅地停止服务

**使用方法：**
```bash
./stop.sh          # 自动检测并停止
./stop.sh pid       # 仅通过PID文件停止
./stop.sh port     # 仅通过端口停止
```

**停止逻辑：**
1. 尝试通过PID文件停止
2. 检查端口占用并停止
3. 清理PID文件
4. 确认服务已停止

---

### 6. restart.sh - 重启服务

**功能：** 快速重启服务

**使用方法：**
```bash
./restart.sh
```

**执行流程：**
1. 停止服务
2. 等待2秒
3. 启动服务
4. 确认重启成功

---

### 7. status.sh - 状态检查

**功能：** 全面检查服务状态

**使用方法：**
```bash
./status.sh
```

**检查项目：**
- ✅ 服务进程状态
- ✅ 端口占用情况
- ✅ 健康状态
- ✅ 日志文件信息
- ✅ 数据目录状态
- ✅ 环境配置检查
- ✅ 访问地址列表

**输出示例：**
```
========================================
    RAG服务状态检查
========================================

[1] 服务进程检查
  ✓ 服务运行中 (PID: 14445)

[2] 端口占用检查
  ✓ 端口8000已监听

[3] 健康状态检查
  ✓ 服务健康: OK

[4] 日志文件检查
  ✓ 日志文件存在
    大小: 128K, 行数: 1523

[5] 数据目录检查
  ✓ data/uploads (文件数: 3, 大小: 2.5M)
  ✓ data/processed (文件数: 12, 大小: 8.2M)
  ...

[6] 环境配置检查
  ✓ .env文件存在
    DASHSCOPE_API_KEY: ✓
    OPENAI_API_KEY: ✓
    SECRET_KEY: ✓
    DEBUG_MODE: True

[7] 访问地址
  API文档:     http://localhost:8000/docs
  ReDoc文档:   http://localhost:8000/redoc
  健康检查:   http://localhost:8000/health/
  Prometheus:  http://localhost:8000/metrics
  前端应用:   http://localhost:3000
========================================
```

---

## 环境配置

### .env 文件说明

首次运行 `deploy.sh` 或 `start.sh` 会自动创建 `.env` 文件：

```bash
# API密钥（必须配置）
DASHSCOPE_API_KEY=your_dashscope_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# JWT密钥（自动生成）
SECRET_KEY=auto_generated_random_key

# 开发模式
DEBUG_MODE=True

# 文件上传配置
MAX_UPLOAD_SIZE=10485760
ENABLE_FILE_SECURITY_CHECK=True

# 文档分块配置
ENABLE_CHUNKING=True
CHUNK_SIZE=800
CHUNK_OVERLAP=100
```

**重要提醒：**
- ⚠️ 请务必编辑 `.env` 文件，填入真实的API密钥
- ⚠️ 生产环境请设置 `DEBUG_MODE=False`
- ⚠️ 生产环境请使用强随机密钥替换 `SECRET_KEY`

---

## 日志管理

### 查看实时日志

```bash
tail -f logs/server.log
```

### 查看最近错误

```bash
grep ERROR logs/server.log
```

### 查看最近警告

```bash
grep WARNING logs/server.log
```

### 统计错误数量

```bash
grep -c ERROR logs/server.log
```

---

## 故障排查

### 问题1：服务启动失败

**诊断步骤：**
```bash
# 1. 查看错误日志
cat logs/server.log

# 2. 检查Python版本
python --version

# 3. 重新安装依赖
pip install -r requirements.txt --upgrade

# 4. 检查端口占用
lsof -i:8000
```

### 问题2：端口被占用

**解决方案：**
```bash
# 方式1：使用停止脚本
./stop.sh port

# 方式2：手动停止
lsof -ti:8000 | xargs kill -9

# 方式3：查找并停止进程
ps aux | grep uvicorn
kill -9 <PID>
```

### 问题3：无法访问API

**诊断步骤：**
```bash
# 1. 检查服务状态
./status.sh

# 2. 检查健康状态
curl http://localhost:8000/health/

# 3. 检查防火墙
sudo ufw status

# 4. 查看进程
ps aux | grep uvicorn
```

### 问题4：依赖安装失败

**解决方案：**
```bash
# 升级pip
python -m pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 逐个安装依赖
pip install fastapi uvicorn
```

---

## 服务访问地址

启动成功后，可以通过以下地址访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| **API文档** | http://localhost:8000/docs | Swagger UI交互式文档 |
| **ReDoc文档** | http://localhost:8000/redoc | 更美观的API文档 |
| **健康检查** | http://localhost:8000/health/ | 服务健康状态端点 |
| **Prometheus** | http://localhost:8000/metrics | 性能指标端点 |
| **前端应用** | http://localhost:3000 | React前端界面 |

---

## 高级用法

### 自定义工作进程数

```bash
# 生产环境使用4个工作进程
WORKERS=4 ./start-prod.sh
```

### 使用虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
./start.sh
```

### 后台运行并记录日志

```bash
# 开发模式
nohup python -m uvicorn src.app:app --reload --host 0.0.0.0 --port 8000 > logs/server.log 2>&1 &

# 生产模式
nohup python -m uvicorn src.app:app --workers 4 --host 0.0.0.0 --port 8000 > logs/server.log 2>&1 &
```

---

## 生产环境部署

### 1. 配置生产环境变量

编辑 `.env` 文件：

```bash
DEBUG_MODE=False
SECRET_KEY=<strong_random_key>
```

### 2. 启动生产服务

```bash
./start-prod.sh
```

### 3. 使用系统服务（推荐）

创建 systemd 服务文件 `/etc/systemd/system/rag.service`：

```ini
[Unit]
Description=RAG Service
After=network.target

[Service]
Type=notify
User=your_user
WorkingDirectory=/Users/wangpeiliang/Desktop/AI/RAG_service
ExecStart=/usr/bin/python -m uvicorn src.app:app --host 0.0.0.0 --port 8000
ExecReload=/bin/kill -HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable rag
sudo systemctl start rag
sudo systemctl status rag
```

---

## 性能优化

### 调整工作进程数

生产环境自动根据CPU核心数设置工作进程数，也可手动指定：

```bash
WORKERS=8 ./start-prod.sh
```

### 监控服务状态

```bash
# 查看进程
ps aux | grep uvicorn

# 查看端口
lsof -i:8000

# 查看资源使用
htop
```

---

## 健康检查

### API健康检查

```bash
curl http://localhost:8000/health/
```

预期响应：
```json
{"status":"healthy"}
```

### 完整系统检查

```bash
# 检查服务状态
curl -s http://localhost:8000/health/ && echo "✅ 服务正常" || echo "❌ 服务异常"

# 检查向量索引
curl -s http://localhost:8000/api/retrieval/stats | python -m json.tool
```

---

## 使用技巧

### 1. 后台运行并查看日志

```bash
# 终端1：启动服务
./start.sh

# 终端2：实时查看日志
tail -f logs/server.log
```

### 2. 开发时自动重启

开发模式使用 `--reload` 参数，代码修改后自动重启服务。

### 3. 测试API

```bash
# 登录获取令牌
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"

# 使用令牌查询
TOKEN="your_token_here"
curl -X POST "http://localhost:8000/api/retrieval/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "k": 5}'
```

---

## 技术支持

如遇问题，请查看：
1. 日志文件：`logs/server.log`
2. API文档：http://localhost:8000/docs
3. 健康检查：http://localhost:8000/health/

---

**最后更新**: 2026-01-29
**维护者**: 汪培良
