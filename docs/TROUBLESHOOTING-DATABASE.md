# 数据库连接故障排除 | Database Connection Troubleshooting

## 常见错误 | Common Errors

### 错误 1: Password Authentication Failed

```
psycopg2.OperationalError: FATAL: password authentication failed for user "postgres"
```

**原因 | Cause:**
- 后端配置文件使用的数据库凭证与 Docker 容器不匹配
- 缺少 `.env` 文件或配置错误

**解决方案 | Solution:**

#### 方法 A: 自动设置（推荐）

```bash
# 运行自动设置脚本
cd ~/develop/project/animate-coswap
chmod +x scripts/setup_local_dev.sh
./scripts/setup_local_dev.sh
```

#### 方法 B: 手动设置

1. **创建 backend/.env 文件：**

```bash
cd ~/develop/project/animate-coswap
cp backend/.env.example backend/.env
```

2. **验证配置匹配：**

查看 `docker-compose.yml` 中的数据库配置：
```yaml
postgres:
  environment:
    POSTGRES_DB: faceswap
    POSTGRES_USER: faceswap_user
    POSTGRES_PASSWORD: faceswap_password
```

确保 `backend/.env` 中的 `DATABASE_URL` 匹配：
```env
DATABASE_URL=postgresql://faceswap_user:faceswap_password@localhost:5432/faceswap
```

3. **重启后端服务：**

```bash
# 停止当前运行的后端（Ctrl+C）
# 重新启动
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

---

### 错误 2: Connection Refused

```
connection to server at "localhost" (::1), port 5432 failed: Connection refused
```

**原因 | Cause:**
- PostgreSQL Docker 容器未运行
- 端口被其他服务占用

**解决方案 | Solution:**

1. **检查 Docker 容器状态：**

```bash
docker ps
```

应该看到：
```
CONTAINER ID   IMAGE                 STATUS
xxxxx          postgres:14-alpine    Up X minutes
xxxxx          redis:7-alpine        Up X minutes
```

2. **如果容器未运行，启动它们：**

```bash
docker-compose up -d postgres redis
```

3. **检查容器日志：**

```bash
docker logs faceswap_postgres
```

4. **检查端口占用：**

```bash
# macOS
lsof -i :5432

# 如果端口被占用，停止其他 PostgreSQL 服务或更改端口
```

---

### 错误 3: Database Does Not Exist

```
psycopg2.OperationalError: FATAL: database "faceswap" does not exist
```

**原因 | Cause:**
- 首次启动，数据库未创建
- Docker 容器被删除，数据丢失

**解决方案 | Solution:**

1. **重新创建容器（会创建数据库）：**

```bash
docker-compose down
docker-compose up -d postgres redis
```

2. **手动创建数据库（如果需要）：**

```bash
docker exec -it faceswap_postgres psql -U faceswap_user -c "CREATE DATABASE faceswap;"
```

3. **运行数据库迁移：**

```bash
cd backend
source ../venv/bin/activate
alembic upgrade head
```

---

### 错误 4: Table Does Not Exist

```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "images" does not exist
```

**原因 | Cause:**
- 数据库迁移未运行
- 数据库表未创建

**解决方案 | Solution:**

```bash
cd backend
source ../venv/bin/activate

# 检查迁移状态
alembic current

# 运行所有迁移
alembic upgrade head

# 如果没有迁移文件，创建初始迁移
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

---

## 完整诊断流程 | Complete Diagnostic Flow

### 步骤 1: 检查 Docker 服务

```bash
# 检查容器状态
docker ps

# 检查 PostgreSQL
docker exec faceswap_postgres pg_isready -U faceswap_user

# 检查 Redis
docker exec faceswap_redis redis-cli ping
```

**预期输出：**
```
PostgreSQL: ready
Redis: PONG
```

### 步骤 2: 检查环境配置

```bash
# 检查 .env 文件是否存在
ls -la backend/.env

# 查看数据库 URL 配置
grep DATABASE_URL backend/.env
```

**预期输出：**
```
DATABASE_URL=postgresql://faceswap_user:faceswap_password@localhost:5432/faceswap
```

### 步骤 3: 测试数据库连接

```bash
# 使用 psql 测试连接
docker exec -it faceswap_postgres psql -U faceswap_user -d faceswap -c "SELECT version();"
```

**如果成功，会显示 PostgreSQL 版本信息。**

### 步骤 4: 检查数据库表

```bash
# 列出所有表
docker exec -it faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt"
```

**应该看到：**
```
          List of relations
 Schema |      Name       | Type  |    Owner
--------+-----------------+-------+--------------
 public | alembic_version | table | faceswap_user
 public | images          | table | faceswap_user
 public | tasks           | table | faceswap_user
```

### 步骤 5: 检查后端日志

启动后端时查看输出：

```bash
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**正常输出应包含：**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**错误输出示例：**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) ...
```

---

## 快速修复脚本 | Quick Fix Script

创建一个快速诊断脚本：

```bash
#!/usr/bin/env bash
# 保存为 scripts/diagnose_db.sh

echo "=== Diagnosing Database Connection ==="

echo -e "\n1. Checking Docker containers..."
docker ps | grep faceswap

echo -e "\n2. Testing PostgreSQL..."
docker exec faceswap_postgres pg_isready -U faceswap_user

echo -e "\n3. Testing Redis..."
docker exec faceswap_redis redis-cli ping

echo -e "\n4. Checking .env file..."
if [ -f backend/.env ]; then
    echo "✓ backend/.env exists"
    grep DATABASE_URL backend/.env
else
    echo "✗ backend/.env NOT found"
    echo "  Run: cp backend/.env.example backend/.env"
fi

echo -e "\n5. Listing database tables..."
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt"

echo -e "\n6. Checking migration status..."
cd backend
source ../venv/bin/activate
alembic current
```

运行诊断：

```bash
chmod +x scripts/diagnose_db.sh
./scripts/diagnose_db.sh
```

---

## macOS 特定问题 | macOS-Specific Issues

### Docker Desktop 未运行

**症状：**
```
Cannot connect to the Docker daemon
```

**解决方案：**
1. 打开 Docker Desktop 应用
2. 等待 Docker 图标显示为绿色（运行中）
3. 重试命令

### 端口冲突（5432 已被占用）

**检查：**
```bash
lsof -i :5432
```

**如果发现其他 PostgreSQL 进程，选项：**

**选项 A: 停止本地 PostgreSQL**
```bash
# Homebrew 安装的 PostgreSQL
brew services stop postgresql

# 或手动停止
launchctl unload ~/Library/LaunchAgents/homebrew.mxcl.postgresql.plist
```

**选项 B: 更改 Docker 容器端口**

编辑 `docker-compose.yml`:
```yaml
postgres:
  ports:
    - "5433:5432"  # 使用 5433 而不是 5432
```

然后更新 `backend/.env`:
```env
DATABASE_URL=postgresql://faceswap_user:faceswap_password@localhost:5433/faceswap
```

### 权限问题

**症状：**
```
permission denied while trying to connect to the Docker daemon socket
```

**解决方案：**
```bash
# 将当前用户添加到 docker 组
sudo dscl . -append /Groups/docker GroupMembership $USER

# 重启 Docker Desktop
# 注销并重新登录 macOS
```

---

## 数据库重置 | Database Reset

如果所有方法都失败，完全重置数据库：

```bash
# 警告：这会删除所有数据！
cd ~/develop/project/animate-coswap

# 1. 停止所有容器
docker-compose down

# 2. 删除数据卷（清除所有数据）
docker volume rm animate-coswap_postgres_data

# 3. 重新启动
docker-compose up -d postgres redis

# 4. 等待服务就绪
sleep 5

# 5. 运行迁移
cd backend
source ../venv/bin/activate
alembic upgrade head

# 6. 重启后端
uvicorn app.main:app --reload --port 8000
```

---

## 预防措施 | Prevention

### 1. 使用自动化脚本

```bash
# 使用提供的设置脚本
./scripts/setup_local_dev.sh

# 使用启动脚本
./scripts/start_dev.sh
```

### 2. 添加到 .gitignore

确保 `.env` 文件不被提交：

```bash
# .gitignore 应包含
backend/.env
frontend/.env
```

### 3. 定期备份开发数据库

```bash
# 导出数据
docker exec faceswap_postgres pg_dump -U faceswap_user faceswap > backup.sql

# 恢复数据
docker exec -i faceswap_postgres psql -U faceswap_user -d faceswap < backup.sql
```

---

## 获取帮助 | Getting Help

如果问题仍未解决，收集以下信息：

```bash
# 系统信息
uname -a
docker --version
python3 --version

# Docker 状态
docker ps -a
docker logs faceswap_postgres

# 配置文件
cat backend/.env | grep DATABASE_URL

# 后端日志
# 粘贴 uvicorn 启动时的错误信息
```

然后提供这些信息寻求帮助。

---

**文档更新时间：** 2025-10-31
**适用版本：** animate-coswap v0.1.0+
