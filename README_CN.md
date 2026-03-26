# Animate-CoSwap: AI 情侣换脸平台

[English](./README.md)

基于 AI 的情侣换脸 Web 平台。上传两个人的照片，选择模板，利用前沿深度学习模型生成高质量换脸图像。

**状态:** MVP 已完成 (阶段 0–5) | **294 项测试通过** | **Python 3.10+ / React 18+**

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        客户端 (浏览器)                               │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────────┐   │
│  │  图片上传器   │  │  模板画廊      │  │    任务进度追踪         │   │
│  │  (React+TS)  │  │  (Ant Design) │  │  (轮询 / WebSocket)    │   │
│  └──────┬───────┘  └───────┬───────┘  └───────────┬────────────┘   │
│         └──────────────────┼──────────────────────┘                 │
│                            │ Axios HTTP                             │
└────────────────────────────┼────────────────────────────────────────┘
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                    Nginx 反向代理 (:80)                             │
└──────────────┬─────────────────────────────────┬──────────────────┘
               ▼                                 ▼
┌──────────────────────────┐    ┌──────────────────────────────────┐
│  前端静态资源 (:3000)      │    │   FastAPI 后端 (:8000)           │
│  Vite + React + TS       │    │                                  │
│                          │    │  API 层: /photos /templates      │
│  页面:                    │    │          /faceswap /admin        │
│  • 换脸工作流 (4步向导)    │    │          /catcher  /browser      │
│                          │    │                                  │
│  组件:                    │    │  服务层:                          │
│  • 图片上传               │    │  • FaceSwapper (核心换脸引擎)     │
│  • 模板画廊               │    │  • 模板预处理 (人脸检测+性别分类)  │
│  • 任务进度               │    │  • 人脸映射服务                   │
│                          │    │  • 批量处理服务                   │
└──────────────────────────┘    │  • 自动清理服务                   │
                                │  • 图片采集 (Pixiv/Danbooru)      │
                                │  • 图片浏览器 (搜索/过滤)          │
                                │                                  │
                                │  数据层:                          │
                                │  • PostgreSQL + SQLAlchemy ORM   │
                                │  • Redis (缓存 + 任务队列)        │
                                │  • 本地/S3 文件存储               │
                                └──────────────────────────────────┘
```

---

## 核心算法：换脸原理

本项目使用 **InsightFace** 生态系统，这是人脸分析和操作的行业标准。

### 处理流水线

```
丈夫照片 ──┐
           │    ┌─────────────┐    ┌────────────┐
           ├───►│  人脸检测    │───►│ 人脸嵌入    │──┐
           │    │  (SCRFD)    │    │ (ArcFace   │  │
妻子照片 ───┘    └─────────────┘    │  512维向量) │  │
                                   └────────────┘  │
                                                    │
模板图片 ────►┌─────────────────┐                    │
 (情侣照)     │ 人脸检测 + 性别  │                    │
              │ 分类 + 位置映射  │                    │
              └────────┬────────┘                    │
                       │                             │
                       ▼                             ▼
               ┌─────────────────────────────────────────┐
               │           人脸映射与交换                  │
               │                                         │
               │  1. 检测模板中所有人脸                    │
               │  2. 性别分类 (男/女)                     │
               │  3. 丈夫 → 男性人脸位置                   │
               │  4. 妻子 → 女性人脸位置                   │
               │  5. 交换人脸 #1 (inswapper_128.onnx)     │
               │  6. 交换人脸 #2 (inswapper_128.onnx)     │
               │  7. 融合与后处理                         │
               └──────────────────┬──────────────────────┘
                                  ▼
                          ┌──────────────┐
                          │   结果图像     │
                          └──────────────┘
```

### 关键算法说明

| 阶段 | 模型/方法 | 说明 |
|------|----------|------|
| **人脸检测** | SCRFD (buffalo_l) | 检测人脸边界框和5点关键点，在WiderFace上达到SOTA精度，比RetinaFace快2.5倍 |
| **人脸嵌入** | ArcFace (buffalo_l) | 提取512维人脸嵌入向量，使用加性角度间隔损失实现高区分度的身份特征学习 |
| **性别/年龄** | 属性模型 (buffalo_l) | 对检测到的人脸进行性别和年龄分类，用于自动的丈夫→男性/妻子→女性映射 |
| **换脸** | inswapper_128.onnx | 核心交换模型，采用编码器-解码器架构，保留目标姿态、光照和表情的同时替换身份特征 |
| **后处理** | OpenCV 融合 | 无缝边界融合，减少交换边界处的伪影 |

### 性能指标

| 指标 | CPU (x86_64) | GPU (CUDA) | Apple Silicon |
|------|:----------:|:----------:|:-------------:|
| 人脸检测 | ~50ms | ~10ms | ~15ms |
| 单脸交换 | ~3s | ~0.5s | ~1s |
| 情侣完整交换 | ~8s | ~2s | ~3s |
| 检测准确率 | ≥95% | ≥95% | ≥95% |

---

## 与同类项目对比

| 项目 | Stars | 核心技术 | 特点 | Web界面 | 批量处理 |
|------|:-----:|---------|------|:-------:|:-------:|
| **[InsightFace](https://github.com/deepinsight/insightface)** | 24k+ | ArcFace + inswapper | 算法库/工具包 | 无 | 无 |
| **[FaceFusion](https://github.com/facefusion/facefusion)** | 20k+ | InsightFace + GFPGAN | CLI + Gradio | Gradio | 无 |
| **[roop](https://github.com/s0md3v/roop)** | 26k+ | InsightFace | 一键换脸 | Gradio | 无 |
| **[DeepFaceLab](https://github.com/iperov/DeepFaceLab)** | 47k+ | 自定义自编码器 | 需训练，质量最高 | 无 | 无 |
| **Animate-CoSwap** | — | InsightFace + inswapper | 全栈Web应用 | React | 支持 |

### 我们的优势
1. **情侣专属工作流** — 自动性别分类，智能匹配丈夫/妻子到模板中对应人脸
2. **生产级Web架构** — REST API + React前端 + PostgreSQL + Redis，非Gradio演示
3. **模板画廊系统** — 持久化、分类管理、预处理（人脸检测、性别分类、蒙版生成）
4. **批量处理** — 同一对照片一次处理多个模板
5. **会话管理** — 临时存储+自动过期清理，适合多用户部署

### 待改进方向
1. **人脸增强** — 尚未集成 GFPGAN/CodeFormer 后处理，这将显著提升输出质量
2. **视频支持** — 当前仅支持图片，视频换脸需要逐帧处理和时间一致性
3. **实时预览** — 处理过程中无实时预览，可通过WebSocket添加

---

## 功能特性

### 已实现
- 分离的照片（临时）和模板（永久）上传接口
- 模板预处理：人脸检测与性别分类
- 灵活的人脸映射：自动性别匹配或手动自定义
- 批量换脸处理（多模板）
- 过期文件自动清理
- Pixiv/Danbooru 图片采集（Catcher 服务）
- 高级搜索与过滤（Browser 服务）
- React TypeScript 前端（4步向导工作流）
- Docker Compose 部署（开发+生产）
- Prometheus + Grafana 监控（可选）

---

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | 0.104+ |
| 数据库 | PostgreSQL + SQLAlchemy | 14+ / 2.0+ |
| 任务队列 | Celery + Redis | 5.3+ / 7+ |
| 人脸分析 | InsightFace | 0.7.3 |
| 换脸模型 | inswapper_128.onnx | — |
| ML推理 | ONNX Runtime | 1.16+ |
| 前端框架 | React + TypeScript | 18.2+ / 5.3+ |
| UI库 | Ant Design | 5.11+ |
| 构建工具 | Vite | 5.0+ |
| 容器化 | Docker + Docker Compose | — |

---

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/zlrrr/animate-coswap.git
cd animate-coswap

# 2. 启动基础设施
docker-compose up -d postgres redis

# 3. 后端设置
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 4. 下载换脸模型 (~554MB)
mkdir -p models
wget https://huggingface.co/ezioruan/inswapper_128.onnx -O models/inswapper_128.onnx

# 5. 启动后端
uvicorn app.main:app --reload --port 8000

# 6. 前端设置 (新终端)
cd frontend && npm install && npm run dev
```

访问: 前端 `http://localhost:3000` | API文档 `http://localhost:8000/docs`

### Docker 全栈部署

```bash
docker-compose --profile full up --build
```

### 运行测试

```bash
cd backend
pytest tests/ -v --tb=short         # 全部测试
pytest tests/ --benchmark-only      # 性能基准测试
pytest tests/ --cov=app             # 覆盖率报告
```

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/photos/upload` | 上传临时照片 |
| `POST` | `/api/v1/templates/upload` | 上传永久模板 |
| `GET` | `/api/v1/templates/` | 列出/筛选模板 |
| `POST` | `/api/v1/faceswap/swap` | 创建换脸任务 |
| `GET` | `/api/v1/faceswap/task/{id}` | 查询任务状态 |
| `POST` | `/api/v1/faceswap/batch` | 批量换脸 |
| `POST` | `/api/v1/admin/cleanup/expired` | 清理过期文件 |

完整交互式文档: `http://localhost:8000/docs` (Swagger UI)

---

## 开发路线

- [x] 阶段 0: 环境搭建与算法验证
- [x] 阶段 1: 后端 REST API
- [x] 阶段 1.5: 增强功能（预处理、批量、映射、清理）
- [x] 阶段 2: React 前端
- [x] 阶段 3: 图片采集服务
- [x] 阶段 4: 图片浏览服务
- [x] 阶段 5: 生产部署
- [ ] 阶段 6: 人脸增强 (GFPGAN/CodeFormer)
- [ ] 阶段 7: 视频换脸
- [ ] 阶段 8: 用户认证与多租户

---

## 文档

- [项目计划 (PLAN.md)](./PLAN.md) — 完整路线图
- [快速开始 (QUICKSTART.md)](./QUICKSTART.md) — 5分钟上手
- [API 文档](./docs/phase-1/api-documentation.md) — 接口参考
- [MVP 报告](./docs/MVP-COMPLETE.md) — 完成情况总结
- [部署指南](./docs/DEPLOYMENT.md) — 生产环境部署
- [平台支持](./docs/PLATFORM-SUPPORT.md) — 各操作系统指南

---

## 致谢

- [InsightFace](https://github.com/deepinsight/insightface) — 人脸检测、识别与换脸模型
- [FastAPI](https://fastapi.tiangolo.com/) — 现代 Python Web 框架
- [React](https://react.dev/) — 前端 UI 库
- [Ant Design](https://ant.design/) — UI 组件库
