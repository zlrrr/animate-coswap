# MVP 设置问题修复指南 | MVP Setup Fix Guide

## 🎯 快速修复（推荐）

如果您遇到数据库表不存在或 Alembic 迁移失败的错误，运行以下命令自动修复：

```bash
cd ~/develop/project/animate-coswap

# 拉取最新修复
git pull origin claude/implement-plan-steps-011CUWofAJKPWXPtKKeXEhGH

# 运行完整设置脚本（一键修复所有问题）
chmod +x scripts/complete_mvp_setup.sh
./scripts/complete_mvp_setup.sh
```

这个脚本会自动：
- ✅ 检查并启动 Docker 服务
- ✅ 创建 `.env` 配置文件
- ✅ 创建 `alembic/versions` 目录
- ✅ 生成并应用数据库迁移
- ✅ 运行所有测试验证 MVP 功能

---

## 问题 1: 上传图片报错 `relation "images" does not exist`

### 错误详情

```
psycopg2.errors.UndefinedTable: relation "images" does not exist
LINE 1: INSERT INTO images (user_id, filename, storage_path, file_si...
```

### 原因

数据库表还没有创建。虽然 Alembic 配置文件已经存在，但迁移还没有实际运行。

### 解决方案

#### 方法 A: 使用自动化脚本（推荐）

```bash
cd ~/develop/project/animate-coswap

# 运行数据库初始化脚本
chmod +x scripts/init_database.sh
./scripts/init_database.sh
```

该脚本会：
1. 检查 Docker 服务状态
2. 验证 `.env` 配置
3. 创建 `alembic/versions` 目录（如果不存在）
4. 自动生成初始迁移
5. 应用迁移创建所有表
6. 验证表已创建

#### 方法 B: 手动步骤

```bash
cd ~/develop/project/animate-coswap

# 1. 确保 Docker 服务运行
docker-compose up -d postgres redis

# 2. 等待服务就绪
sleep 10
docker exec faceswap_postgres pg_isready -U faceswap_user

# 3. 创建 alembic/versions 目录
mkdir -p backend/alembic/versions

# 4. 激活虚拟环境
source venv/bin/activate

# 5. 进入 backend 目录
cd backend

# 6. 创建初始迁移
alembic revision --autogenerate -m "Initial migration"

# 7. 应用迁移
alembic upgrade head

# 8. 验证表已创建
cd ..
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

---

## 问题 2: Alembic 迁移生成失败

### 错误详情

```
FileNotFoundError: [Errno 2] No such file or directory:
'/Users/zhaolirong/develop/project/animate-coswap/backend/alembic/versions/3b5c042899af_initial_migration.py'
```

### 原因

`backend/alembic/versions/` 目录不存在。Git 默认不跟踪空目录，所以这个目录在您 clone/pull 代码后可能不存在。

### 解决方案

#### 快速修复

```bash
cd ~/develop/project/animate-coswap

# 创建目录
mkdir -p backend/alembic/versions

# 然后重新运行迁移
cd backend
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

#### 使用自动化脚本

```bash
# 运行数据库初始化脚本（会自动创建目录）
./scripts/init_database.sh
```

---

## 🧪 验证 MVP 功能

修复后，运行测试验证所有 MVP 功能正常：

```bash
cd ~/develop/project/animate-coswap

# 运行 MVP 测试
chmod +x scripts/test_mvp.sh
./scripts/test_mvp.sh
```

**测试覆盖的 MVP 功能：**

1. ✅ **Manual image upload** - 上传用户图片
2. ✅ **Template selection** - 浏览和选择模板
3. ✅ **Template creation** - 创建自定义模板
4. ⚠️ **Background processing** - 后台人脸交换（需要模型）
5. ✅ **Result gallery** - 查看结果画廊

---

## 🚀 启动 MVP 并测试

### 步骤 1: 启动后端

```bash
cd ~/develop/project/animate-coswap/backend
source ../venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**验证：** 访问 http://localhost:8000/docs 应该看到 API 文档

### 步骤 2: 启动前端（新终端）

```bash
cd ~/develop/project/animate-coswap/frontend
npm run dev
```

**验证：** 访问 http://localhost:5173 应该看到前端界面

### 步骤 3: 测试 MVP 工作流

#### 3.1 上传 Husband's Photo

1. 打开前端：http://localhost:5173
2. 点击 "Upload Husband's Photo"
3. 选择一张照片并上传
4. 确认上传成功（应该显示缩略图）

**验证成功标志：**
- ✅ 照片上传成功
- ✅ 显示缩略图
- ✅ 没有错误消息

**如果失败：**
```bash
# 检查数据库表
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt"

# 应该看到 images 表
```

#### 3.2 上传 Wife's Photo

重复上述步骤上传 Wife's Photo。

#### 3.3 选择或创建模板

1. 点击 "Select Template" 或 "Create Template"
2. 如果创建模板：
   - 上传模板图片
   - 填写模板名称
   - 点击创建
3. 如果选择模板：
   - 从列表中选择一个模板

**验证成功标志：**
- ✅ 模板列表显示
- ✅ 可以创建新模板
- ✅ 模板缩略图正确显示

#### 3.4 开始 Face-Swap 处理

1. 确保已上传两张照片和选择模板
2. 点击 "Start Face-Swap" 或 "Process"
3. 观察处理状态

**注意：** 如果模型文件不存在，会显示错误。这是正常的。

**下载模型文件：**
- 参考：[MODEL-DOWNLOAD-FIX.md](./MODEL-DOWNLOAD-FIX.md)
- 从 Hugging Face 下载 `inswapper_128.onnx`
- 放置到 `backend/models/` 目录

#### 3.5 查看结果

处理完成后（如果模型可用），结果会显示在 Result Gallery。

---

## 🔍 故障排除

### 问题：数据库连接失败

**症状：**
```
connection refused / connection to server ... failed
```

**解决：**
```bash
# 检查 Docker
docker ps | grep faceswap

# 重启服务
docker-compose restart postgres

# 或运行诊断
./scripts/diagnose_db.sh
```

### 问题：表已存在但 Alembic 报错

**症状：**
```
relation "images" already exists
```

**解决：**
```bash
cd backend

# 标记当前数据库状态（不运行迁移）
alembic stamp head

# 验证
alembic current
```

### 问题：迁移文件已生成但无法应用

**症状：**
```
Target database is not up to date
```

**解决：**
```bash
cd backend

# 查看当前状态
alembic current

# 查看历史
alembic history

# 应用所有待处理的迁移
alembic upgrade head
```

### 问题：前端无法连接后端

**症状：**
- 前端显示网络错误
- API 调用失败

**检查：**

1. 后端是否运行：
   ```bash
   curl http://localhost:8000/
   # 应该返回 JSON
   ```

2. 检查 CORS 配置（backend/app/main.py）

3. 检查前端 API URL 配置（frontend/.env）：
   ```env
   VITE_API_URL=http://localhost:8000
   ```

---

## 📊 测试结果验证

运行完整测试套件：

```bash
cd ~/develop/project/animate-coswap

# 1. 配置测试
python scripts/test_settings.py

# 2. Alembic 配置测试
python scripts/test_alembic_config.py

# 3. 基础测试
cd backend
pytest tests/test_basic.py -v

# 4. MVP 工作流测试
pytest tests/test_mvp_workflow.py -v

# 5. 完整测试
pytest tests/ -v
```

**预期结果：**
- ✅ 配置测试：全部通过
- ✅ 基础测试：47/47 通过
- ✅ MVP 工作流测试：大部分通过（模型相关测试可能跳过）

---

## 📝 创建的新文件

### 脚本

1. **`scripts/init_database.sh`** - 数据库初始化自动化脚本
2. **`scripts/test_mvp.sh`** - MVP 功能测试脚本
3. **`scripts/complete_mvp_setup.sh`** - 完整 MVP 设置脚本

### 测试

4. **`backend/tests/test_mvp_workflow.py`** - 端到端 MVP 工作流测试
   - 测试图片上传
   - 测试模板创建和选择
   - 测试 Face-Swap 任务创建
   - 测试结果画廊
   - 集成测试完整工作流

### 配置

5. **`backend/alembic/versions/.gitkeep`** - 确保目录被 Git 跟踪

---

## 🎯 MVP 功能状态

| 功能 | 状态 | 说明 |
|------|------|------|
| **Manual image upload** | ✅ 完全可用 | 支持上传 husband 和 wife 照片 |
| **Template selection** | ✅ 完全可用 | 可以浏览和选择模板 |
| **Template creation** | ✅ 完全可用 | 可以创建自定义模板 |
| **Background processing** | ⚠️ 需要模型 | 需要下载 inswapper_128.onnx |
| **Result gallery** | ✅ 完全可用 | 可以查看所有图片和结果 |

---

## 🔄 完整 MVP 工作流示例

```bash
# === 初始设置（只需运行一次）===

# 1. 拉取代码
cd ~/develop/project/animate-coswap
git pull

# 2. 运行完整设置
./scripts/complete_mvp_setup.sh

# 3. 下载模型（可选，用于face-swap）
# 参考 docs/MODEL-DOWNLOAD-FIX.md

# === 每次开发 ===

# 终端 1: 启动后端
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload --port 8000

# 终端 2: 启动前端
cd frontend
npm run dev

# 浏览器: 打开 http://localhost:5173
# 测试 MVP 功能

# === 测试 ===

# 运行测试验证
./scripts/test_mvp.sh
```

---

## 🆘 获取帮助

如果问题仍未解决：

1. 运行诊断脚本：
   ```bash
   ./scripts/diagnose_db.sh
   ./scripts/test_settings.py
   ```

2. 查看相关文档：
   - [数据库故障排除](./TROUBLESHOOTING-DATABASE.md)
   - [Alembic 设置指南](./ALEMBIC-SETUP-GUIDE.md)
   - [快速启动指南](./QUICK-START-MACOS.md)

3. 检查日志：
   ```bash
   # Docker 日志
   docker logs faceswap_postgres

   # 后端日志（在运行 uvicorn 的终端查看）
   ```

---

**最后更新：** 2025-10-31
**版本：** animate-coswap MVP v0.1.0
**分支：** claude/implement-plan-steps-011CUWofAJKPWXPtKKeXEhGH
