# macOS 本地开发快速启动指南 | Quick Start Guide for macOS

## 🚀 5 分钟快速启动 | 5-Minute Quick Start

### 前置条件 | Prerequisites

1. **Docker Desktop** - 从 https://www.docker.com/products/docker-desktop 下载
2. **Python 3.10+** - 从 https://www.python.org/downloads/macos/ 下载（推荐 ARM64 版本）
3. **Node.js 18+** - 从 https://nodejs.org/ 下载

### 方法 A: 自动化设置（推荐）

```bash
# 1. 克隆或进入项目目录
cd ~/develop/project/animate-coswap

# 2. 运行自动化设置脚本
chmod +x scripts/setup_local_dev.sh
./scripts/setup_local_dev.sh

# 3. 启动所有服务
chmod +x scripts/start_dev.sh
./scripts/start_dev.sh
```

就这么简单！浏览器打开 http://localhost:5173

---

### 方法 B: 手动设置

#### 步骤 1: 启动 Docker 服务

```bash
cd ~/develop/project/animate-coswap

# 启动 PostgreSQL 和 Redis
docker-compose up -d postgres redis

# 等待服务就绪（约 5-10 秒）
sleep 10

# 验证服务运行
docker ps
```

**预期输出：** 应看到 `faceswap_postgres` 和 `faceswap_redis` 在运行

#### 步骤 2: 设置 Python 环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖（macOS M 芯片）
pip install -r backend/requirements-macos-m.txt

# 或安装通用依赖
pip install -r backend/requirements.txt
```

#### 步骤 3: 配置环境变量

```bash
# 复制示例配置
cp backend/.env.example backend/.env

# 配置文件已经匹配 docker-compose.yml，无需修改
```

**重要：** `backend/.env` 中的数据库配置必须与 `docker-compose.yml` 一致：

```env
DATABASE_URL=postgresql://faceswap_user:faceswap_password@localhost:5432/faceswap
```

#### 步骤 4: 运行数据库迁移

```bash
cd backend

# 创建初始迁移（如果不存在）
alembic revision --autogenerate -m "Initial migration"

# 运行迁移
alembic upgrade head

cd ..
```

#### 步骤 5: 启动后端

```bash
# 在一个终端窗口
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**验证：** 访问 http://localhost:8000/docs 应看到 API 文档

#### 步骤 6: 设置并启动前端

```bash
# 在另一个终端窗口
cd frontend

# 首次运行：安装依赖
npm install

# 复制环境配置
cp .env.example .env

# 启动开发服务器
npm run dev
```

**验证：** 访问 http://localhost:5173 应看到应用界面

---

## 🔍 故障排除 | Troubleshooting

### 问题 1: 数据库连接失败

**错误信息：**
```
password authentication failed for user "postgres"
```

**解决方案：**

```bash
# 运行诊断脚本
chmod +x scripts/diagnose_db.sh
./scripts/diagnose_db.sh
```

诊断脚本会自动检测问题并提供修复建议。

**手动修复：**

1. 检查 `.env` 文件是否存在：
   ```bash
   ls -la backend/.env
   ```

2. 如果不存在，创建它：
   ```bash
   cp backend/.env.example backend/.env
   ```

3. 验证配置：
   ```bash
   grep DATABASE_URL backend/.env
   ```

   应该显示：
   ```
   DATABASE_URL=postgresql://faceswap_user:faceswap_password@localhost:5432/faceswap
   ```

4. 重启后端服务

### 问题 2: Docker 容器未运行

**错误信息：**
```
connection refused
```

**解决方案：**

```bash
# 检查 Docker Desktop 是否运行
docker ps

# 如果没有输出或报错，启动 Docker Desktop 应用

# 启动数据库服务
docker-compose up -d postgres redis

# 等待服务就绪
sleep 10

# 验证
docker exec faceswap_postgres pg_isready -U faceswap_user
docker exec faceswap_redis redis-cli ping
```

### 问题 3: 数据表不存在

**错误信息：**
```
relation "images" does not exist
```

**解决方案：**

```bash
cd backend
source ../venv/bin/activate

# 运行迁移
alembic upgrade head

# 如果还是失败，重新创建迁移
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 问题 4: 模型文件缺失或损坏

**错误信息：**
```
INVALID_PROTOBUF: Protobuf parsing failed
```

**解决方案：**

```bash
# 运行模型诊断
python scripts/fix_model_download.py
```

按照脚本提示下载正确的模型文件。详见 `docs/MODEL-DOWNLOAD-FIX.md`

### 问题 5: CoreML 不可用

**症状：**
```
Available providers: 'CPUExecutionProvider'
# 缺少 CoreMLExecutionProvider
```

**解决方案：**

```bash
# 运行 CoreML 诊断
python scripts/diagnose_coreml.py

# 如果需要，重新安装 onnxruntime
pip uninstall onnxruntime onnxruntime-gpu onnxruntime-silicon -y
pip install onnxruntime==1.16.3

# 验证
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
```

---

## 📋 完整诊断流程 | Complete Diagnostic

如果遇到任何问题，按顺序运行这些诊断：

```bash
# 1. 诊断数据库连接
./scripts/diagnose_db.sh

# 2. 诊断 CoreML 支持（macOS M 芯片）
python scripts/diagnose_coreml.py

# 3. 诊断模型文件
python scripts/fix_model_download.py

# 4. 验证算法
python scripts/validate_algorithm.py
```

---

## 🛠️ 有用的命令 | Useful Commands

### Docker 管理

```bash
# 查看运行中的容器
docker ps

# 查看容器日志
docker logs faceswap_postgres
docker logs faceswap_redis

# 停止所有服务
docker-compose down

# 完全重置（删除数据）
docker-compose down -v
docker-compose up -d postgres redis
```

### 数据库管理

```bash
# 连接到数据库
docker exec -it faceswap_postgres psql -U faceswap_user -d faceswap

# 列出所有表
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt"

# 查看迁移状态
cd backend && alembic current

# 创建新迁移
cd backend && alembic revision --autogenerate -m "描述"

# 运行迁移
cd backend && alembic upgrade head

# 回滚迁移
cd backend && alembic downgrade -1
```

### 后端管理

```bash
# 启动后端（开发模式）
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload --port 8000

# 运行测试
pytest

# 运行特定测试
pytest tests/test_basic.py

# 查看测试覆盖率
pytest --cov=app tests/
```

### 前端管理

```bash
# 安装依赖
cd frontend && npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

---

## 🎯 服务端口速查 | Port Reference

| 服务 | 端口 | URL |
|------|------|-----|
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
| Backend API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| Frontend | 5173 | http://localhost:5173 |

---

## 🔐 默认凭证 | Default Credentials

**PostgreSQL:**
- User: `faceswap_user`
- Password: `faceswap_password`
- Database: `faceswap`

**Redis:**
- 无密码（本地开发）

⚠️ **生产环境请务必修改这些凭证！**

---

## 📝 开发工作流 | Development Workflow

### 每天开始开发

```bash
# 1. 启动 Docker 服务（如果未运行）
docker-compose up -d postgres redis

# 2. 启动后端
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload --port 8000

# 3. 在新终端，启动前端
cd frontend
npm run dev
```

### 每天结束开发

```bash
# 停止后端和前端：Ctrl+C

# 可选：停止 Docker 服务（释放资源）
docker-compose down

# 或保持运行（下次启动更快）
```

### 修改数据库模型

```bash
# 1. 编辑 backend/app/models/database.py

# 2. 创建迁移
cd backend
alembic revision --autogenerate -m "描述修改内容"

# 3. 检查生成的迁移文件
ls -la alembic/versions/

# 4. 应用迁移
alembic upgrade head

# 5. 重启后端
```

---

## 🆘 获取更多帮助 | Getting More Help

### 详细文档

- [模型下载修复](MODEL-DOWNLOAD-FIX.md)
- [数据库故障排除](TROUBLESHOOTING-DATABASE.md)
- [跨平台支持](PLATFORM-SUPPORT.md)
- [macOS M 芯片指南](GETTING-STARTED-MACOS-M.md)

### 运行诊断

```bash
# 完整系统诊断
./scripts/diagnose_db.sh
python scripts/diagnose_coreml.py
python scripts/fix_model_download.py
```

### 收集系统信息

如果需要报告问题，收集以下信息：

```bash
# 系统信息
uname -a
python3 --version
node --version
docker --version

# Docker 状态
docker ps -a
docker logs faceswap_postgres --tail 50

# 配置信息
cat backend/.env | grep DATABASE_URL

# 后端日志
# 启动后端时的完整输出
```

---

**最后更新：** 2025-10-31
**适用版本：** animate-coswap v0.1.0+
