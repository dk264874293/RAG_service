# 登录注册功能数据库集成

## TL;DR

> **Quick Summary**: 为FastAPI RAG服务添加完整的用户注册和登录功能，将用户信息持久化到MySQL数据库。包括数据库模型、API端点、数据验证和测试框架设置。
>
> **Deliverables**:
> - MySQL用户表和SQLAlchemy ORM模型
> - 用户注册API (`POST /api/auth/register`)
> - 更新后的登录API（使用数据库验证）
> - MySQL连接配置
> - pytest测试框架设置
>
> **Estimated Effort**: Medium
> **Parallel Execution**: NO - sequential (数据库依赖)
> **Critical Path**: 配置MySQL → 创建数据模型 → 注册API → 更新登录API → 设置测试

---

## Context

### Original Request
"增加登陆注册逻辑，用户信息存入数据库"

### Interview Summary
**Key Discussions**:
- **数据库**: MySQL（用户选择）
- **用户表字段**: 用户名(username)、密码(password)、手机号(phone)
- **唯一性约束**: 手机号必须唯一
- **密码验证**: 简单验证（最少6位）
- **测试策略**: 设置pytest，先实现功能，再补充测试用例

**Research Findings**:
- 项目已有完整的认证基础设施（JWT、密码哈希）
- `src/api/routes/auth.py` 使用临时字典 `FAKE_USERS_DB`
- 已有 `src/core/security.py` 提供密码哈希和JWT功能
- 缺少数据库ORM和持久化
- 缺少用户注册API
- 项目没有pytest依赖

### Metis Review
**跳过Metis咨询**: Metis调用遇到技术问题，但由于所有需求已明确（数据库类型、表结构、约束、验证规则、测试策略），直接生成计划。

---

## Work Objectives

### Core Objective
将现有的基于临时字典的认证系统迁移到MySQL数据库持久化，并添加用户注册功能。

### Concrete Deliverables
- MySQL数据库连接配置（config.py）
- SQLAlchemy用户模型（User表）
- 用户注册API端点（`POST /api/auth/register`）
- 更新后的登录API（从数据库验证用户）
- 数据库初始化脚本
- pytest测试框架设置

### Definition of Done
- [ ] 用户可以成功注册（手机号唯一性约束生效）
- [ ] 用户可以使用手机号登录
- [ ] 密码正确哈希存储
- [ ] JWT令牌正确生成和验证
- [ ] pytest安装完成并可运行
- [ ] 所有API端点在 `/docs` 中可见

### Must Have
- MySQL数据库连接
- 用户表（id, username, password, phone, created_at, updated_at）
- 手机号唯一约束
- 密码最少6位验证
- 注册API返回JWT令牌
- 登录API支持手机号登录
- pytest安装

### Must NOT Have (Guardrails)
- 邮箱字段（未在需求中）
- 邮箱验证功能（未在需求中）
- 复杂密码验证（仅简单验证最少6位）
- 用户名唯一约束（仅需手机号唯一）
- 密码重置功能（未在需求中）
- 删除临时FAKE_USERS_DB（保留以备对比验证）

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO
- **User wants tests**: Tests-after (先实现，后测试)
- **Framework**: pytest

### Implementation + Verification Approach

每个TODO包含可执行的验证过程，通过bash命令或API调用来验证：

| Type | Verification Tool | Automated Procedure |
|------|------------------|---------------------|
| **数据库配置** | Bash (mysql/pymysql) | 测试连接并创建表 |
| **API端点** | Bash (curl) | 发送请求并验证响应 |
| **数据验证** | Bash (curl) | 发送边界值测试用例 |
| **测试框架** | Bash (pytest) | 运行pytest --help验证安装 |

**Evidence Requirements (Agent-Executable):**
- curl命令的JSON响应输出
- 数据库表结构查询结果
- pytest命令输出
- JWT令牌解码验证

---

## Execution Strategy

### Parallel Execution Waves

由于任务之间存在强依赖关系（数据库→模型→API→测试），采用顺序执行：

```
Sequential Flow:
├── Task 1: 配置MySQL连接和依赖
├── Task 2: 创建用户数据模型
├── Task 3: 创建数据库初始化脚本
├── Task 4: 实现用户注册API
├── Task 5: 更新登录API
├── Task 6: 设置pytest测试框架
└── Task 7: 编写测试用例

Critical Path: 1 → 2 → 3 → 4 → 5 → 6 → 7
No parallelization due to database dependencies
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2 | None |
| 2 | 1 | 3, 4, 5 | None |
| 3 | 2 | 4, 5 | None |
| 4 | 2, 3 | 5 | None |
| 5 | 2, 3 | 6 | None |
| 6 | 4, 5 | 7 | None |
| 7 | 6 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| Sequential | All tasks | delegate_task(category="unspecified-high") |

---

## TODOs

- [ ] 1. 配置MySQL数据库连接和安装依赖

  **What to do**:
  - 在 `config.py` 中添加MySQL连接配置项（DATABASE_URL等）
  - 在 `requirements.txt` 中添加MySQL相关依赖：
    - `sqlalchemy`
    - `pymysql` 或 `aiomysql`（推荐aiomysql，异步兼容）
  - 更新 `.env.example` 添加MySQL配置模板

  **Must NOT do**:
  - 修改现有的其他配置项
  - 删除现有的数据库相关配置（如有）

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  > **Skills**: `[]`
  > **Reason**: 配置修改任务，不需要特殊技能

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 2 (数据模型)
  - **Blocked By**: None

  **References**:

  **Configuration References** (现有配置模式):
  - `config.py:20-30` - 现有Settings类结构，参考添加数据库配置字段
  - `config.py:289-297` - 现有JWT安全配置示例（字段命名模式）

  **Dependency References** (需要添加的包):
  - PyPI文档: `https://docs.sqlalchemy.org/en/20/orm/quickstart.html` - SQLAlchemy快速开始
  - PyPI文档: `https://github.com/aio-libs/aiomysql` - aiomysql异步驱动

  **Database Connection Pattern** (FastAPI + SQLAlchemy):
  ```python
  # 推荐模式参考：FastAPI官方文档
  # https://fastapi.tiangolo.com/tutorial/sql-databases/
  ```

  **Acceptance Criteria**:

  **Automated Verification**:
  ```bash
  # Agent runs:
  pip install -r requirements.txt
  # Assert: Exit code 0
  # Assert: aiomysql and sqlalchemy installed
  python -c "import sqlalchemy; import aiomysql; print('Dependencies OK')"
  # Assert: Output contains "Dependencies OK"
  ```

  **Evidence to Capture**:
  - [ ] pip install 输出（显示安装的包）
  - [ ] python import 验证输出
  - [ ] config.py 中添加的数据库配置字段

  **Commit**: YES
  - Message: `feat(config): add MySQL database connection configuration`
  - Files: `config.py`, `requirements.txt`, `.env.example`
  - Pre-commit: `python -c "import sqlalchemy; import aiomysql"`

---

- [ ] 2. 创建用户数据模型（SQLAlchemy ORM）

  **What to do**:
  - 创建 `src/models/user.py` 文件
  - 定义User表模型（继承Base）：
    ```python
    class User(Base):
        __tablename__ = "users"

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        username: Mapped[str] = mapped_column(String(50))
        phone: Mapped[str] = mapped_column(String(20), unique=True)  # 唯一约束
        password: Mapped[str] = mapped_column(String(255))  # bcrypt哈希
        created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
        updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    ```
  - 在 `src/models/__init__.py` 中导出User模型

  **Must NOT do**:
  - 添加未在需求中的字段（email等）
  - 添加用户名唯一约束（仅需手机号唯一）

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  > **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 3, 4, 5
  - **Blocked By**: Task 1

  **References**:

  **Pattern References** (现有模型结构):
  - `src/models/base.py:12-13` - Base基类定义
  - `src/models/document.py` - 文档模型示例（参考字段定义和类型）

  **SQLAlchemy Documentation**:
  - `https://docs.sqlalchemy.org/en/20/orm/mapping_api.html` - 映射API
  - `https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html` - 基本关系

  **Acceptance Criteria**:

  **Automated Verification**:
  ```bash
  # Agent runs:
  python -c "from src.models.user import User; print('User model imported successfully')"
  # Assert: Output contains "User model imported successfully"

  python -c "from src.models.user import User; print(f'Table name: {User.__tablename__}')"
  # Assert: Output contains "Table name: users"
  ```

  **Evidence to Capture**:
  - [ ] python import 验证输出
  - [ ] 表名验证输出
  - [ ] User模型代码

  **Commit**: YES
  - Message: `feat(models): add User ORM model with unique phone constraint`
  - Files: `src/models/user.py`, `src/models/__init__.py`

---

- [ ] 3. 创建数据库初始化脚本

  **What to do**:
  - 创建 `scripts/init_db.py` 或 `src/models/init_db.py` 脚本
  - 实现：
    1. 创建数据库引擎（从config读取DATABASE_URL）
    2. 创建所有表（Base.metadata.create_all）
    3. 添加初始管理员用户（可选，使用get_password_hash加密密码）
  - 在 `manage.sh` 或创建新脚本中添加初始化命令

  **Must NOT do**:
  - 硬编码数据库连接信息（使用config.settings）
  - 删除现有数据（使用create_all，不使用drop_all）

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  > **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 4, 5
  - **Blocked By**: Task 2

  **References**:

  **Database Configuration References**:
  - `config.py:20-548` - Settings类，找到DATABASE_URL配置

  **Security References**:
  - `src/core/security.py:36-50` - get_password_hash函数，用于加密初始管理员密码

  **SQLAlchemy Documentation**:
  - `https://docs.sqlalchemy.org/en/20/core/metadata.html` - Metadata操作

  **Acceptance Criteria**:

  **Automated Verification**:
  ```bash
  # Agent runs:
  python src/models/init_db.py
  # Assert: Exit code 0
  # Assert: No error messages

  # 验证表是否创建（假设MySQL连接信息已配置）
  python -c "
  import asyncio
  from sqlalchemy import text
  from config import settings
  from src.models import Base, engine
  async def check():
    async with engine.begin() as conn:
      result = await conn.execute(text('SHOW TABLES LIKE \"users\"'))
      print(f'Table exists: {result.fetchone() is not None}')
  asyncio.run(check())
  "
  # Assert: Output contains "Table exists: True"
  ```

  **Evidence to Capture**:
  - [ ] init_db.py 执行输出
  - [ ] 表存在验证输出
  - [ ] init_db.py 代码

  **Commit**: YES
  - Message: `feat(db): add database initialization script`
  - Files: `src/models/init_db.py`

---

- [ ] 4. 实现用户注册API

  **What to do**:
  - 在 `src/api/routes/auth.py` 中添加注册端点：
    ```python
    @router.post("/register", response_model=TokenResponse)
    async def register(register_data: RegisterRequest):
        # 1. 验证手机号唯一性
        # 2. 验证密码长度（>=6）
        # 3. 哈希密码
        # 4. 创建用户
        # 5. 生成JWT令牌
    ```
  - 创建 `RegisterRequest` Pydantic模型（phone, password, username）
  - 实现密码长度验证（最少6位）
  - 实现手机号唯一性检查
  - 返回JWT令牌（同登录成功响应）

  **Must NOT do**:
  - 添加邮箱验证（未在需求中）
  - 实现复杂密码验证
  - 删除或修改现有的登录端点

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  > **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 5
  - **Blocked By**: Task 2, 3

  **References**:

  **Existing Auth Pattern**:
  - `src/api/routes/auth.py:20-33` - LoginRequest和TokenResponse模型结构
  - `src/api/routes/auth.py:75-118` - login端点实现，参考JWT生成逻辑
  - `src/api/routes/auth.py:42-72` - authenticate_user函数，参考验证逻辑

  **Security References**:
  - `src/core/security.py:36-50` - get_password_hash函数，用于密码哈希
  - `src/core/security.py:53-81` - create_access_token函数，用于生成JWT

  **Database Operation References**:
  - `src/models/user.py` - User模型定义

  **Error Handling Pattern**:
  - `src/api/routes/auth.py:93-98` - HTTPException示例

  **Acceptance Criteria**:

  **Automated Verification**:
  ```bash
  # Agent runs (需要先启动服务):
  # 注册新用户
  curl -X POST http://localhost:8000/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser","phone":"13800138000","password":"123456"}' \
    -s | jq '.access_token'
  # Assert: Returns non-empty JWT token
  # Assert: HTTP status 201

  # 测试手机号唯一性约束
  curl -X POST http://localhost:8000/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser2","phone":"13800138000","password":"123456"}' \
    -s | jq '.detail'
  # Assert: Returns error message about duplicate phone

  # 测试密码长度验证
  curl -X POST http://localhost:8000/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser3","phone":"13900139000","password":"123"}' \
    -s | jq '.detail'
  # Assert: Returns error message about password length
  ```

  **Evidence to Capture**:
  - [ ] 注册成功响应（access_token）
  - [ ] 手机号重复错误响应
  - [ ] 密码长度错误响应
  - [ ] 注册API代码

  **Commit**: YES
  - Message: `feat(auth): add user registration API with unique phone constraint`
  - Files: `src/api/routes/auth.py`

---

- [ ] 5. 更新登录API支持数据库验证

  **What to do**:
  - 修改 `src/api/routes/auth.py` 中的 `authenticate_user` 函数：
    - 从FAKE_USERS_DB字典改为从数据库查询用户
    - 支持使用phone作为登录账号（或同时支持username）
  - 保留FAKE_USERS_DB作为备选（注释掉，不删除）
  - 更新登录端点描述，说明支持手机号登录

  **Must NOT do**:
  - 删除FAKE_USERS_DB（保留以备对比）
  - 修改JWT令牌生成逻辑
  - 更改API端点路径

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  > **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 6
  - **Blocked By**: Task 2, 3

  **References**:

  **Existing Login Implementation**:
  - `src/api/routes/auth.py:54-72` - authenticate_user函数（当前使用FAKE_USERS_DB）
  - `src/api/routes/auth.py:75-118` - login端点实现

  **Database Query Pattern**:
  - `src/models/user.py` - User模型定义
  - 参考 `src/service/upload_service.py` 或其他服务中的数据库查询模式

  **SQLAlchemy Async Query**:
  - `https://docs.sqlalchemy.org/en/20/orm/quickstart.html#selecting-orm-entities-and-columns`

  **Acceptance Criteria**:

  **Automated Verification**:
  ```bash
  # Agent runs:
  # 使用注册的用户登录
  curl -X POST http://localhost:8000/api/auth/login/json \
    -H "Content-Type: application/json" \
    -d '{"username":"13800138000","password":"123456"}' \
    -s | jq '.access_token'
  # Assert: Returns non-empty JWT token
  # Assert: HTTP status 200

  # 测试错误密码
  curl -X POST http://localhost:8000/api/auth/login/json \
    -H "Content-Type: application/json" \
    -d '{"username":"13800138000","password":"wrongpassword"}' \
    -s | jq '.detail'
  # Assert: Returns error message about wrong credentials

  # 测试不存在的用户
  curl -X POST http://localhost:8000/api/auth/login/json \
    -H "Content-Type: application/json" \
    -d '{"username":"99999999999","password":"123456"}' \
    -s | jq '.detail'
  # Assert: Returns error message about user not found
  ```

  **Evidence to Capture**:
  - [ ] 登录成功响应（access_token）
  - [ ] 错误密码响应
  - [ ] 不存在用户响应
  - [ ] 更新后的authenticate_user函数代码

  **Commit**: YES
  - Message: `feat(auth): update login to use MySQL database`
  - Files: `src/api/routes/auth.py`

---

- [ ] 6. 设置pytest测试框架

  **What to do**:
  - 在 `requirements.txt` 中添加pytest相关依赖：
    - `pytest`
    - `pytest-asyncio` （用于FastAPI异步测试）
    - `httpx` （用于测试API客户端）
    - `pytest-cov` （可选，覆盖率）
  - 创建 `pytest.ini` 或 `pyproject.toml` 配置文件
  - 创建示例测试文件 `tests/test_auth.py`，包含简单测试用例

  **Must NOT do**:
  - 编写完整的测试套件（仅需框架和示例）
  - 修改现有代码以适配测试（除非必要）

  **Recommended Agent Profile**:
  > **Category**: `quick`
  > **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 7
  - **Blocked By**: Task 4, 5

  **References**:

  **Pytest Documentation**:
  - `https://docs.pytest.org/en/7.1.x/` - Pytest官方文档
  - `https://fastapi.tiangolo.com/tutorial/testing/` - FastAPI测试指南

  **Existing Test Pattern**:
  - `tests/performance/run_benchmark.py` - 现有测试文件结构参考

  **Acceptance Criteria**:

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest --help
  # Assert: Exit code 0
  # Assert: Help output contains pytest version

  pytest tests/test_auth.py -v
  # Assert: Tests run (may fail, but no syntax errors)
  ```

  **Evidence to Capture**:
  - [ ] pytest --help 输出
  - [ ] pytest test_auth.py 运行输出
  - [ ] pytest.ini 或 pyproject.toml 配置
  - [ ] test_auth.py 示例代码

  **Commit**: YES
  - Message: `chore(test): add pytest framework and test configuration`
  - Files: `requirements.txt`, `pytest.ini`, `tests/test_auth.py`

---

- [ ] 7. 编写认证API测试用例

  **What to do**:
  - 在 `tests/test_auth.py` 中添加完整测试用例：
    1. 测试用户注册成功
    2. 测试手机号唯一性约束
    3. 测试密码长度验证
    4. 测试使用手机号登录成功
    5. 测试错误密码登录失败
    6. 测试JWT令牌验证
  - 使用pytest-asyncio异步测试
  - 使用测试数据库（可选，或使用真实数据库清理）

  **Must NOT do**:
  - 测试邮箱验证功能（未实现）
  - 测试密码重置功能（未实现）

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  > **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None
  - **Blocked By**: Task 6

  **References**:

  **Test Pattern References**:
  - `https://fastapi.tiangolo.com/tutorial/testing/` - FastAPI测试示例
  - `tests/performance/run_benchmark_simple.py` - 现有测试代码模式参考

  **API Endpoint References**:
  - `src/api/routes/auth.py:120-162` - register端点（待实现）
  - `src/api/routes/auth.py:75-118` - login端点（待更新）

  **Acceptance Criteria**:

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest tests/test_auth.py -v --tb=short
  # Assert: All tests pass (or documented failures)
  # Assert: At least 6 test cases run
  ```

  **Evidence to Capture**:
  - [ ] pytest 运行输出
  - [ ] 测试通过/失败统计
  - [ ] 完整测试代码

  **Commit**: YES
  - Message: `test(auth): add comprehensive auth API test cases`
  - Files: `tests/test_auth.py`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(config): add MySQL database connection configuration` | config.py, requirements.txt, .env.example | `python -c "import sqlalchemy; import aiomysql"` |
| 2 | `feat(models): add User ORM model with unique phone constraint` | src/models/user.py, src/models/__init__.py | `python -c "from src.models.user import User"` |
| 3 | `feat(db): add database initialization script` | src/models/init_db.py | `python src/models/init_db.py` |
| 4 | `feat(auth): add user registration API with unique phone constraint` | src/api/routes/auth.py | `curl POST /api/auth/register` |
| 5 | `feat(auth): update login to use MySQL database` | src/api/routes/auth.py | `curl POST /api/auth/login/json` |
| 6 | `chore(test): add pytest framework and test configuration` | requirements.txt, pytest.ini, tests/test_auth.py | `pytest --help` |
| 7 | `test(auth): add comprehensive auth API test cases` | tests/test_auth.py | `pytest tests/test_auth.py -v` |

---

## Success Criteria

### Verification Commands

```bash
# 1. 验证数据库配置
python -c "from config import settings; print(settings.DATABASE_URL)"

# 2. 验证数据模型
python -c "from src.models.user import User; print(User.__tablename__)"

# 3. 初始化数据库
python src/models/init_db.py

# 4. 启动服务
./start.sh

# 5. 测试注册
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","phone":"13800138000","password":"123456"}' | jq

# 6. 测试登录
curl -X POST http://localhost:8000/api/auth/login/json \
  -H "Content-Type: application/json" \
  -d '{"username":"13800138000","password":"123456"}' | jq

# 7. 运行测试
pytest tests/test_auth.py -v
```

### Final Checklist
- [ ] 用户可以成功注册（手机号唯一性约束生效）
- [ ] 用户可以使用手机号登录
- [ ] 密码正确哈希存储（bcrypt）
- [ ] JWT令牌正确生成和验证
- [ ] pytest安装完成并可运行
- [ ] 所有API端点在 `/docs` 中可见
- [ ] 所有测试通过
