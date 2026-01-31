# 🤖 智能客服系统 (RAG Service)

> **版本**: 1.1.0
> **状态**: ✅ 生产就绪
> **更新日期**: 2026-01-29

---

## 📋 项目概述

智能客服系统是一个基于RAG（Retrieval-Augmented Generation）技术的智能问答系统，支持文档上传、向量化、智能检索和合规性检查等功能。

### 核心特性

- 📄 **多格式文档处理**: 支持PDF、Word、TXT、Markdown等多种格式
- 🔍 **语义检索**: 基于FAISS+DashScope的向量相似度搜索
- 📊 **合规性检查**: 环境监测数据自动合规性验证
- 🎯 **智能分块**: AdaptiveChunker支持多种分块策略
- 🔄 **批量处理**: 支持批量文件上传和处理
- 📈 **实时监控**: 完善的健康检查和日志系统

---

## 🚀 快速开始

### 前置要求

- Python 3.8+
- Node.js 16+ (前端)
- DashScope API Key
- OpenAI API Key (可选)

### 一键启动

```bash
# 克隆仓库
git clone <repository-url>
cd RAG_service

# 一键部署
./deploy.sh
```

### 手动启动

#### 1. 后端服务

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件，填入API密钥

# 启动开发服务
./start.sh

# 或启动生产服务
./start-prod.sh
```

#### 2. 前端服务

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务
npm run dev

# 或构建生产版本
npm run build
```

### 访问地址

- **API文档**: http://localhost:8000/docs
- **前端界面**: http://localhost:3000
- **健康检查**: http://localhost:8000/health/

---

## 📚 文档导航

### 用户文档

- **[用户指南](docs/USER_GUIDE.md)** - 合规性检查系统使用指南
- **[部署指南](docs/DEPLOYMENT_GUIDE.md)** - 服务部署与运维指南

### 技术文档

- **[合规性系统](docs/COMPLIANCE_SYSTEM.md)** - 环境监测数据合规性检查完整文档
- **[技术报告](docs/TECHNICAL_REPORTS.md)** - 评估、优化、修复和实现总结
- **[架构设计](docs/ARCHITECTURE.md)** - RAG架构实施计划

### 前端文档

- **[向量管理](frontend/docs/VECTOR_MANAGE.md)** - 前端向量管理模块文档

---

## 🎯 核心功能

### 1. 文档处理与向量化

```
上传文件 → 内容提取 → 智能分块 → 向量化 → FAISS索引
```

**支持格式**:
- PDF (.pdf)
- Word (.doc, .docx)
- 纯文本 (.txt)
- Markdown (.md)
- HTML (.html)
- PowerPoint (.pptx)
- Excel (.xlsx)

### 2. 语义检索

- 基于DashScope Embeddings的文本向量化
- FAISS向量数据库相似度搜索
- 支持元数据过滤
- 可配置返回结果数量

### 3. 合规性检查

- PDF自动数据提取
- 国标标准智能匹配
- 公式计算验证
- 合规性判断与报告

**支持标准**:
- GB 5085系列 (危险废物鉴别标准)
- GB 3838-2002 (地表水环境质量标准)
- 持续扩展中...

---

## 🏗️ 技术架构

### 后端技术栈

- **框架**: FastAPI
- **向量数据库**: FAISS
- **嵌入模型**: DashScope (text-embedding-v2)
- **文档处理**: pypdfium2, python-docx
- **数据库**: SQLite
- **OCR**: Tesseract, PaddleOCR

### 前端技术栈

- **框架**: React + TypeScript
- **构建工具**: Vite
- **UI组件**: 自定义组件 + Tailwind CSS
- **状态管理**: React Hooks
- **HTTP客户端**: Axios

---

## 📂 项目结构

```
RAG_service/
├── docs/                       # 项目文档
│   ├── USER_GUIDE.md
│   ├── COMPLIANCE_SYSTEM.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── TECHNICAL_REPORTS.md
│   └── ARCHITECTURE.md
├── frontend/                    # 前端项目
│   ├── docs/                    # 前端文档
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── ...
│   └── ...
├── src/                        # 后端源码
│   ├── api/                    # API路由
│   │   └── routes/
│   ├── compliance/             # 合规性检查模块
│   ├── extractor/              # 文档提取器
│   ├── models/                 # 数据模型
│   ├── pipeline/               # 处理管道
│   ├── service/                # 业务服务
│   ├── vector/                 # 向量服务
│   └── app.py                  # 应用入口
├── data/                       # 数据目录
├── logs/                       # 日志目录
├── .sisyphus/                  # 内部计划文档
├── deploy.sh                   # 一键部署脚本
├── manage.sh                   # 交互式管理脚本
├── start.sh                    # 启动开发服务
├── start-prod.sh               # 启动生产服务
├── stop.sh                     # 停止服务
├── restart.sh                  # 重启服务
├── status.sh                   # 状态检查
├── requirements.txt             # Python依赖
└── README.md                   # 项目说明
```

---

## 🔧 脚本说明

| 脚本 | 功能 | 适用场景 |
|------|------|---------|
| **deploy.sh** | 一键部署 | 首次部署或完整重置 |
| **manage.sh** | 交互式管理菜单 | 新手友好，可视化操作 |
| **start.sh** | 启动开发服务器 | 日常开发调试 |
| **start-prod.sh** | 启动生产服务器 | 生产环境部署 |
| **stop.sh** | 停止服务 | 停止运行中的服务 |
| **restart.sh** | 重启服务 | 快速重启服务 |
| **status.sh** | 状态检查 | 查看服务运行状态 |

详见 [部署指南](docs/DEPLOYMENT_GUIDE.md)。

---

## 🌐 API端点

### 文档上传
- `POST /api/upload` - 上传单个文件
- `POST /api/upload/batch` - 批量上传文件
- `GET /api/upload/history` - 获取上传历史

### 向量检索
- `POST /api/retrieval/search` - 语义搜索
- `POST /api/retrieval/search-with-scores` - 带分数搜索
- `GET /api/retrieval/stats` - 索引统计

### 合规性检查
- `POST /api/compliance/check` - 上传文件检查
- `POST /api/compliance/check-by-path` - 文件路径检查
- `GET /api/compliance/standards` - 列出国标文件
- `GET /api/compliance/health` - 健康检查

### 系统管理
- `GET /health/` - 系统健康检查
- `GET /metrics` - Prometheus指标

详见 [API文档](http://localhost:8000/docs)。

---

## 📊 性能指标

| 指标 | 目标值 | 实际值 |
|------|-------|--------|
| 文档嵌入延迟 | < 500ms | ~300ms |
| 检索响应时间 | < 100ms | ~80ms |
| 索引容量 | > 10K | 10K+ |
| 检索准确性 | > 0.7 | ~0.75 |
| 并发性能 | > 100 QPS | ~120 QPS |

---

## 🧪 测试

### 后端测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_compliance.py
pytest tests/test_api.py

# 测试覆盖率
pytest --cov=src --cov-report=html
```

### 前端测试

```bash
cd frontend

# 运行单元测试
npm test

# E2E测试
npm run test:e2e
```

---

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出改进建议！

### 贡献流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范

- 后端: 遵循 PEP 8
- 前端: 遵循 ESLint + Prettier
- 提交信息: 遵循 Conventional Commits

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 👨‍💻 作者

**汪培良**
- Email: rick_wang@yunquna.com
- GitHub: [your-github-username]

---

## 🙏 致谢

感谢以下开源项目的支持：

- [FastAPI](https://fastapi.tiangolo.com/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [React](https://reactjs.org/)
- [DashScope](https://dashscope.aliyun.com/)

---

## 📞 技术支持

如遇问题，请：
1. 查看 [文档](docs/) 目录
2. 提交 [Issue](https://github.com/your-repo/issues)
3. 联系项目维护者

---

**最后更新**: 2026-01-29
**文档版本**: 1.1.0
