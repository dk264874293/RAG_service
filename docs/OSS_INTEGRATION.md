# 阿里云OSS集成文档

本文档说明如何配置和使用阿里云OSS存储功能。

## 概述

RAG服务现在支持两种存储后端：
- **本地文件系统（local）**：默认方式，文件存储在服务器本地磁盘
- **阿里云OSS（oss）**：分布式对象存储，提供高可用性和可扩展性

## 架构

```
应用层 (Services)
    ├── UploadService
    ├── MarkdownService
    └── DocumentService
            ↓
    StorageService (统一存储服务)
            ├── 自动选择适配器
            └── 支持自动回退
            ↓
    ┌───────────────┴───────────────┐
    ▼                               ▼
LocalStorageAdapter          OSSStorageAdapter
(本地文件系统)                (阿里云OSS)
```

## 配置步骤

### 1. 创建OSS Bucket

1. 登录阿里云控制台
2. 进入对象存储OSS服务
3. 创建新的Bucket：
   - 选择合适的区域
   - 读写权限：私有
   - 存储类型：标准存储

### 2. 获取访问密钥

1. 在阿里云控制台创建AccessKey
2. 保存AccessKey ID和Secret

### 3. 配置环境变量

复制OSS配置模板：
```bash
cp .env.oss.template .env
```

编辑 `.env` 文件，填入配置：

```bash
# 存储类型
STORAGE_TYPE=oss

# OSS配置
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET_NAME=your-bucket-name
OSS_PREFIX=rag-service/

# 可选配置
OSS_TIMEOUT=60
OSS_PRESIGN_URL_EXPIRE=3600
OSS_FALLBACK_TO_LOCAL=true
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

依赖包括：
- `oss2>=2.18.0` - 阿里云OSS SDK

### 5. 运行数据库迁移

如果已有数据，需要添加存储字段到数据库：

```bash
# 执行迁移
mysql -u root -p rag_service < migrations/001_add_storage_fields.sql
```

## 使用方式

### API接口

新的存储相关API：

- `GET /api/storage/status` - 获取存储服务状态
- `GET /api/storage/local/{file_path:path}` - 访问本地文件
- `GET /api/storage/url/{file_path:path}` - 获取文件访问URL
- `GET /api/storage/info/{file_path:path}` - 获取文件元数据
- `GET /api/storage/list` - 列出文件

### Python代码

```python
from src.api.dependencies import get_storage_service

# 获取存储服务
storage_service = get_storage_service()

# 上传文件
result = await storage_service.upload_file(
    "uploads/test.pdf",
    content=bytes,
    metadata={"original_filename": "test.pdf"}
)

# 获取文件URL
url = storage_service.get_file_url("uploads/test.pdf", expires=3600)

# 下载文件
content = await storage_service.download_file("uploads/test.pdf")

# 检查文件是否存在
exists = await storage_service.file_exists("uploads/test.pdf")

# 删除文件
success = await storage_service.delete_file("uploads/test.pdf")

# 列出文件
files = await storage_service.list_files(prefix="uploads/", limit=100)

# 获取文件元数据
metadata = await storage_service.get_file_metadata("uploads/test.pdf")
```

## 迁移策略

### 阶段1：本地存储（默认）

```bash
STORAGE_TYPE=local
```

- 所有文件存储在本地
- 验证服务功能正常

### 阶段2：OSS + 本地回退

```bash
STORAGE_TYPE=oss
OSS_FALLBACK_TO_LOCAL=true
```

- 新文件上传到OSS
- OSS失败时自动回退到本地
- 灰度验证OSS配置

### 阶段3：完全OSS

```bash
STORAGE_TYPE=oss
OSS_FALLBACK_TO_LOCAL=false
```

- 所有文件存储在OSS
- 本地仅作为临时缓存

## 回退机制

当OSS操作失败时：

1. 如果 `OSS_FALLBACK_TO_LOCAL=true`：
   - 自动使用本地存储
   - 记录警告日志
   - 服务继续运行

2. 如果 `OSS_FALLBACK_TO_LOCAL=false`：
   - 抛出异常
   - 返回错误给客户端
   - 确保数据一致性

## 故障排查

### OSS连接失败

检查配置：
```bash
# 验证环境变量
echo $OSS_ACCESS_KEY_ID
echo $OSS_ACCESS_KEY_SECRET
echo $OSS_ENDPOINT
echo $OSS_BUCKET_NAME
```

检查日志：
```
Failed to initialize OSS adapter: ...
OSS connection failed: ...
```

### 文件上传失败

1. 检查Bucket权限
2. 检查网络连接
3. 验证AccessKey权限

### 回退到本地存储

如果OSS初始化失败且启用了回退：
```
Failed to initialize OSS adapter: ...
Falling back to local storage
Storage adapter initialized: Local
```

## 数据迁移

### 从本地迁移到OSS

使用阿里云ossutil工具：

```bash
# 安装ossutil
wget http://gosspublic.alicdn.com/ossutil/1.7.15/ossutil64
chmod 755 ossutil64

# 配置
./ossutil64 config

# 同步文件
./ossutil64 cp -rf ./data/uploads/ oss://your-bucket/rag-service/uploads/ --update
```

### 从OSS迁移回本地

```bash
# 下载文件
./ossutil64 cp -rf oss://your-bucket/rag-service/uploads/ ./data/uploads/ --update

# 更新配置
STORAGE_TYPE=local
```

## 最佳实践

1. **使用CDN加速**：配置OSS的CDN加速域名
2. **生命周期管理**：设置旧文件自动删除策略
3. **跨区域复制**：重要数据跨区域备份
4. **监控告警**：配置OSS用量和异常监控
5. **访问控制**：使用RAM子账号而非主账号

## 成本优化

1. **存储类型**：根据访问频率选择存储类型
   - 标准存储：频繁访问
   - 低频存储：不常访问
   - 归档存储：长期归档

2. **CDN回源**：配置CDN降低OSS外网流量

3. **删除策略**：定期清理无用文件

## 安全建议

1. **保护AccessKey**：不要将密钥提交到版本控制
2. **使用RAM子账号**：最小权限原则
3. **启用日志审计**：记录OSS访问日志
4. **Bucket策略**：限制IP访问

## 参考文档

- [阿里云OSS Python SDK](https://help.aliyun.com/document_detail/32026.html)
- [OSS最佳实践](https://help.aliyun.com/document_detail/31827.html)
- [OSS计费说明](https://help.aliyun.com/document_detail/31877.html)
