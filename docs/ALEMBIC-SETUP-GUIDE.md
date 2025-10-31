# Alembic 数据库迁移设置指南 | Alembic Database Migration Setup Guide

## 问题描述 | Problem Description

当运行 `alembic upgrade head` 时，可能遇到以下错误：

```
pydantic_core._pydantic_core.ValidationError: 3 validation errors for Settings
SECRET_KEY
  Extra inputs are not permitted [type=extra_forbidden, ...]
ALGORITHM
  Extra inputs are not permitted [type=extra_forbidden, ...]
ACCESS_TOKEN_EXPIRE_MINUTES
  Extra inputs are not permitted [type=extra_forbidden, ...]
```

### 原因分析 | Root Cause

1. `.env.example` 文件中包含了 `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` 字段
2. 但是 `app/core/config.py` 中的 `Settings` 类没有定义这些字段
3. Pydantic v2 默认不允许额外字段（`extra = "forbid"`）
4. 当 Alembic 导入 Settings 时，触发验证错误

### 修复方案 | Solution

在 `Settings` 类中添加缺失的字段定义。

---

## ✅ 已修复 | Fixed

### 更新的文件 | Updated Files

**`backend/app/core/config.py`**

添加了三个安全相关的配置字段：

```python
# Security (for future authentication features)
SECRET_KEY: str = "your-secret-key-here-change-in-production"
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
```

这些字段用于未来的认证功能（JWT token 生成等）。

---

## 📋 在您的 Mac 上执行迁移 | Running Migrations on Your Mac

### 前置条件 | Prerequisites

1. ✅ Docker Desktop 正在运行
2. ✅ PostgreSQL 和 Redis 容器已启动
3. ✅ `.env` 文件已创建并配置

### 步骤 1: 拉取最新代码

```bash
cd ~/develop/project/animate-coswap

# 拉取修复
git fetch origin claude/implement-plan-steps-011CUWofAJKPWXPtKKeXEhGH
git pull origin claude/implement-plan-steps-011CUWofAJKPWXPtKKeXEhGH
```

### 步骤 2: 确保 Docker 服务运行

```bash
# 启动 PostgreSQL 和 Redis
docker-compose up -d postgres redis

# 验证服务状态
docker ps | grep faceswap

# 验证 PostgreSQL 就绪
docker exec faceswap_postgres pg_isready -U faceswap_user
# 应该输出: ready

# 验证 Redis 就绪
docker exec faceswap_redis redis-cli ping
# 应该输出: PONG
```

### 步骤 3: 确保 .env 文件存在

```bash
# 如果不存在，创建它
cp backend/.env.example backend/.env

# 验证配置
grep DATABASE_URL backend/.env
# 应该显示: DATABASE_URL=postgresql://faceswap_user:faceswap_password@localhost:5432/faceswap
```

### 步骤 4: 激活虚拟环境

```bash
# 如果虚拟环境不存在，创建它
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装或更新依赖
pip install -r backend/requirements-macos-m.txt
# 或
pip install -r backend/requirements.txt
```

### 步骤 5: 创建初始迁移

```bash
cd backend

# 创建初始迁移（基于当前数据库模型）
alembic revision --autogenerate -m "Initial migration"

# 检查生成的迁移文件
ls -la alembic/versions/
```

**预期输出：** 您应该看到一个新的 Python 文件，类似：
```
xxxx_initial_migration.py
```

### 步骤 6: 应用迁移

```bash
# 运行迁移
alembic upgrade head
```

**成功输出示例：**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> xxxx, Initial migration
```

### 步骤 7: 验证表已创建

```bash
# 列出所有表
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt"
```

**预期输出：**
```
              List of relations
 Schema |       Name        | Type  |    Owner
--------+-------------------+-------+--------------
 public | alembic_version   | table | faceswap_user
 public | crawl_tasks       | table | faceswap_user
 public | faceswap_tasks    | table | faceswap_user
 public | images            | table | faceswap_user
 public | templates         | table | faceswap_user
 public | users             | table | faceswap_user
```

### 步骤 8: 启动后端服务

```bash
# 在 backend 目录，虚拟环境已激活
uvicorn app.main:app --reload --port 8000
```

**成功输出应包含：**
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## 🔍 故障排除 | Troubleshooting

### 错误 1: Alembic 仍然报 Pydantic 验证错误

**症状：**
```
pydantic_core._pydantic_core.ValidationError: ... validation errors for Settings
```

**解决方案：**

1. 确保您已拉取最新代码：
   ```bash
   git pull origin claude/implement-plan-steps-011CUWofAJKPWXPtKKeXEhGH
   ```

2. 验证 `app/core/config.py` 包含新字段：
   ```bash
   grep -A 3 "SECRET_KEY" backend/app/core/config.py
   ```

   应该看到：
   ```python
   SECRET_KEY: str = "your-secret-key-here-change-in-production"
   ALGORITHM: str = "HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
   ```

3. 重新安装包（确保使用最新代码）：
   ```bash
   pip install -e backend/
   ```

### 错误 2: 数据库连接失败

**症状：**
```
sqlalchemy.exc.OperationalError: ... connection refused
```

**解决方案：**

运行诊断脚本：
```bash
./scripts/diagnose_db.sh
```

或手动检查：
```bash
# 检查容器
docker ps | grep faceswap_postgres

# 检查连接
docker exec faceswap_postgres pg_isready -U faceswap_user
```

详见 [DATABASE TROUBLESHOOTING](./TROUBLESHOOTING-DATABASE.md)

### 错误 3: 表已存在

**症状：**
```
sqlalchemy.exc.ProgrammingError: ... relation "images" already exists
```

**原因：** 数据库中已有表，但 Alembic 版本表不同步。

**解决方案：**

**选项 A: 标记当前状态（推荐）**
```bash
cd backend

# 删除现有迁移
rm -rf alembic/versions/*.py

# 创建新的初始迁移
alembic revision --autogenerate -m "Initial migration"

# 手动标记为已应用（不实际运行）
alembic stamp head
```

**选项 B: 重置数据库（会丢失数据！）**
```bash
# 停止并删除容器和数据
docker-compose down -v

# 重新启动
docker-compose up -d postgres redis

# 等待就绪
sleep 10

# 运行迁移
cd backend
alembic upgrade head
```

### 错误 4: 找不到模块

**症状：**
```
ModuleNotFoundError: No module named 'app'
```

**解决方案：**

确保在正确的目录：
```bash
# 必须在 backend/ 目录中运行 alembic
cd backend
alembic upgrade head
```

---

## 🧪 验证配置 | Verify Configuration

运行自动化测试脚本：

```bash
# 测试 Settings 配置
python scripts/test_settings.py

# 测试 Alembic 配置
python scripts/test_alembic_config.py
```

**所有测试通过后：**
```
✅ All configuration tests passed!
✅ Alembic configuration is valid!
```

---

## 📚 Alembic 常用命令 | Common Alembic Commands

```bash
# 在 backend/ 目录中运行

# 查看当前迁移状态
alembic current

# 查看迁移历史
alembic history

# 创建新迁移（自动检测模型变化）
alembic revision --autogenerate -m "描述"

# 升级到最新版本
alembic upgrade head

# 升级到特定版本
alembic upgrade <revision_id>

# 回滚一个版本
alembic downgrade -1

# 回滚到特定版本
alembic downgrade <revision_id>

# 查看SQL（不执行）
alembic upgrade head --sql

# 标记当前数据库状态（不执行迁移）
alembic stamp head
```

---

## 🔐 生产环境注意事项 | Production Notes

在生产环境中，务必修改以下配置：

**`.env` 文件：**
```env
# 生成强随机密钥
SECRET_KEY=<使用 openssl rand -hex 32 生成>

# 数据库密码
DATABASE_URL=postgresql://user:<strong-password>@host:5432/dbname

# Redis（如果启用认证）
REDIS_URL=redis://<password>@host:6379/0
```

**生成安全的 SECRET_KEY：**
```bash
# 方法 1: 使用 OpenSSL
openssl rand -hex 32

# 方法 2: 使用 Python
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## ✅ 测试结果 | Test Results

修复后，所有配置和基础测试通过：

```
✅ 47/47 基础和平台测试通过
✅ Settings 配置加载成功
✅ Alembic 环境导入成功
✅ 数据库模型验证通过
✅ 52% 代码覆盖率
```

---

## 🆘 需要更多帮助 | Getting More Help

- 📖 [快速启动指南](./QUICK-START-MACOS.md)
- 🔧 [数据库故障排除](./TROUBLESHOOTING-DATABASE.md)
- 🔧 [模型下载修复](./MODEL-DOWNLOAD-FIX.md)
- 📖 [macOS M 芯片指南](./GETTING-STARTED-MACOS-M.md)

运行诊断工具：
```bash
./scripts/diagnose_db.sh
python scripts/test_alembic_config.py
```

---

**最后更新：** 2025-10-31
**修复版本：** animate-coswap v0.1.0+
**修复分支：** claude/implement-plan-steps-011CUWofAJKPWXPtKKeXEhGH
