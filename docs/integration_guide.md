# 分代索引集成完成指南

## 已完成的集成工作

### 1. 代码文件已创建

```
src/vector/
├── routing_table.py              ✅ SQLite路由表
├── hot_faiss_index.py           ✅ Hot索引（支持物理删除）
├── cold_faiss_index.py          ✅ Cold索引（只读优化）
└── generational_index_store.py  ✅ 分代索引存储

src/tasks/
└── archive_task.py              ✅ 归档任务管理器

src/api/routes/
└── maintenance.py               ✅ 维护API接口

docs/
├── generational_index_design.md      ✅ 详细设计文档
├── generational_index_quickstart.md  ✅ 快速启动指南
└── integration_guide.md              ✅ 本文档

test_generational_index.py       ✅ 集成测试脚本
```

### 2. 现有文件已修改

| 文件 | 修改内容 |
|------|----------|
| `config.py` | 添加分代索引配置项（约40行） |
| `src/api/dependencies.py` | 支持分代索引切换（约10行） |
| `src/app.py` | 注册维护API路由（约2行） |
| `src/api/routes/__init__.py` | 导出maintenance模块（约2行） |
| `requirements.txt` | 添加apscheduler依赖 |

### 3. 新增配置项（.env）

```bash
# ========== 分代索引配置 ==========
ENABLE_GENERATIONAL_INDEX=true    # 启用分代索引
HOT_INDEX_MAX_SIZE=1000000        # Hot索引最大容量
HOT_INDEX_TYPE=IVFPQ              # Hot索引类型
COLD_INDEX_TYPE=HNSW              # Cold索引类型
ARCHIVE_AGE_DAYS=30               # 归档天数
ARCHIVE_SCHEDULE="0 2 * * *"      # 归档时间（每天凌晨2点）
HOT_SEARCH_WEIGHT=0.7             # Hot搜索权重
COLD_SEARCH_WEIGHT=0.3            # Cold搜索权重
```

## 快速验证步骤

### 步骤1: 安装依赖

```bash
cd /Users/wangpeiliang/Desktop/AI/RAG_service
pip install apscheduler>=3.10.0
```

### 步骤2: 运行集成测试

```bash
python test_generational_index.py
```

预期输出：
```
🚀🚀🚀...  分代索引集成测试  🚀🚀🚀...

============================================================
  1. 测试模块导入
============================================================
  ✓ FAISS
  ✓ LangChain FAISS
  ✓ RoutingTable
  ✓ HotFAISSIndex
  ✓ ColdFAISSIndex
  ✓ GenerationalIndexStore
  ✓ EmbeddingService
  ✓ ArchiveTaskManager
  ✓ MaintenanceRouter
  ✓ APScheduler

✅ 所有模块导入成功

... (更多测试)

============================================================
  测试总结
============================================================
  导入测试: ✅ 通过
  配置测试: ✅ 通过
  路由表测试: ✅ 通过
  Hot索引测试: ✅ 通过
  Cold索引测试: ✅ 通过
  分代存储测试: ✅ 通过

============================================================
  总计: 6/6 通过
============================================================

🎉 所有测试通过！分代索引已成功集成。
```

### 步骤3: 启用分代索引

在 `.env` 文件中添加：
```bash
ENABLE_GENERATIONAL_INDEX=true
```

### 步骤4: 启动服务

```bash
python -m uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

查看日志确认使用分代索引：
```
INFO: Using GenerationalIndexStore (Hot/Cold architecture)
INFO: Hot FAISS Index initialized: type=IVFPQ, path=./data/faiss_index/hot
INFO: Cold FAISS Index initialized: type=HNSW, path=./data/faiss_index/cold
INFO: Routing table initialized at ./data/faiss_index/routing.db
```

### 步骤5: 测试API

#### 5.1 查看索引统计
```bash
curl http://localhost:8000/api/maintenance/index/stats
```

#### 5.2 检查健康状态
```bash
curl http://localhost:8000/api/maintenance/index/health
```

#### 5.3 启动定时任务
```bash
curl -X POST http://localhost:8000/api/maintenance/tasks/start
```

#### 5.4 手动触发归档
```bash
curl -X POST http://localhost:8000/api/maintenance/index/archive
```

## 故障排查

### 问题1: 导入错误

```
ImportError: cannot import name 'GenerationalIndexStore'
```

**解决方案**: 确保在项目根目录运行，或添加项目路径到PYTHONPATH
```bash
export PYTHONPATH=/Users/wangpeiliang/Desktop/AI/RAG_service:$PYTHONPATH
```

### 问题2: FAISS版本问题

```
AttributeError: module 'faiss' has no attribute 'IDRemover'
```

**解决方案**: FAISS-CPU版本可能较旧，更新版本
```bash
pip install --upgrade faiss-cpu
```

### 问题3: 配置未生效

**解决方案**: 检查 `.env` 文件是否存在，并确保配置项名称正确（区分大小写）

### 问题4: 服务启动失败

**解决方案**: 查看详细错误日志
```bash
python -m uvicorn src.app:app --log-level debug
```

## API文档

启动服务后访问: http://localhost:8000/docs

新增的维护接口：
- `POST /api/maintenance/index/archive` - 手动触发归档
- `POST /api/maintenance/index/rebuild-cold` - 重建Cold索引
- `GET /api/maintenance/index/stats` - 索引统计
- `GET /api/maintenance/index/health` - 健康检查
- `POST /api/maintenance/tasks/start` - 启动定时任务
- `GET /api/maintenance/tasks/status` - 任务状态

## 向后兼容性

如果需要回退到传统软删除方式，只需设置：
```bash
ENABLE_GENERATIONAL_INDEX=false
```

系统会自动使用原有的 `FAISSVectorStore`，无需其他修改。

## 下一步优化

1. **监控告警**: 集成Prometheus监控索引健康指标
2. **性能测试**: 在生产环境前进行压测
3. **灰度上线**: 先在测试环境验证，再逐步切换流量
4. **文档完善**: 根据实际使用情况更新文档

---

如有问题，请参考详细设计文档：`docs/generational_index_design.md`
