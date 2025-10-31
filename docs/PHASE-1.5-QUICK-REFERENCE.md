# Phase 1.5 快速参考 | Quick Reference

## 📦 已完成的工作

### ✅ 数据库模型更新完成

所有新需求的数据库基础已经实现：

```python
# 1. 分离存储：临时 vs 永久
Image.storage_type = 'permanent' | 'temporary'
Image.expires_at  # 自动清理时间
Image.session_id  # 分组临时照片

# 2. 模板预处理
Template.is_preprocessed  # 是否已预处理
Template.male_face_count  # 男性脸数量
Template.female_face_count  # 女性脸数量

TemplatePreprocessing  # 新表：存储预处理数据
- face_data: JSON  # 人脸信息（位置、性别、特征点）
- masked_image_id  # 挖空图像ID

# 3. 灵活映射
FaceSwapTask.face_mappings: JSON  # 自定义脸部映射

# 4. 批量处理
BatchTask  # 新表：批量任务管理
FaceSwapTask.batch_id  # 关联批量任务
```

### ✅ 详细文档完成

1. **[PLAN-PHASE-1.5.md](./PLAN-PHASE-1.5.md)** - 完整计划
   - 5个检查点（Checkpoints）
   - 每个功能的详细规格
   - 测试策略
   - 成功标准

2. **[PHASE-1.5-IMPLEMENTATION-GUIDE.md](./PHASE-1.5-IMPLEMENTATION-GUIDE.md)** - 实施指南
   - 逐步实施说明
   - 每个功能的代码示例
   - 时间估算
   - 测试用例模板

---

## 🚀 立即执行（在您的 Mac 上）

### 第 1 步：拉取代码

```bash
cd ~/develop/project/animate-coswap
git pull origin claude/implement-plan-steps-011CUWofAJKPWXPtKKeXEhGH
```

### 第 2 步：运行数据库迁移 ⭐ 必须执行

```bash
cd backend
source ../venv/bin/activate

# 创建迁移
alembic revision --autogenerate -m "Add Phase 1.5 enhanced features"

# 查看生成的迁移文件
ls -la alembic/versions/

# 应用迁移
alembic upgrade head
```

### 第 3 步：验证数据库

```bash
# 检查新表
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt"

# 应该看到新表：
# - template_preprocessing
# - batch_tasks

# 检查 images 表的新字段
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\d images"

# 应该看到新字段：
# - storage_type
# - expires_at
# - session_id
```

---

## 📋 新增功能概览

### 1. 分离的上传 API

**现状：** 数据库模型已更新
**下一步：** 实现 API 端点

```python
# 将实现的 API
POST /api/v1/photos/upload      # 上传用户照片（临时）
DELETE /api/v1/photos/{id}      # 删除照片
POST /api/v1/templates/upload   # 上传模板（永久）
DELETE /api/v1/templates/{id}   # 删除模板
```

### 2. 模板预处理

**现状：** 数据库模型已更新
**下一步：** 实现预处理逻辑

**预处理流程：**
1. 检测人脸 → 2. 识别性别 → 3. 生成挖空图像 → 4. 保存结果

**将实现的 API：**
```python
GET /api/v1/templates/{id}/preprocessing  # 查看预处理状态
POST /api/v1/templates/{id}/reprocess     # 重新预处理
```

### 3. 批量处理

**现状：** 数据库模型已更新
**下一步：** 实现批量处理 API

**将实现的 API：**
```python
POST /api/v1/faceswap/batch              # 创建批量任务
GET /api/v1/faceswap/batch/{id}/status   # 查看批量状态
GET /api/v1/faceswap/batch/{id}/download # 下载ZIP结果
```

### 4. 自动清理

**现状：** 数据库模型已更新
**下一步：** 实现 Celery 定时任务

**功能：**
- 每小时自动删除过期的临时照片
- 释放存储空间
- 保护用户隐私

---

## 📊 实施计划

### Checkpoint 1.5.1 - 分离上传 API（2-3小时）
**任务：**
- [ ] 创建 `app/api/v1/photos.py`
- [ ] 创建 `app/api/v1/templates.py`（独立于现有）
- [ ] 实现临时存储逻辑
- [ ] 实现删除功能
- [ ] 编写测试

**测试后继续下一步 ↓**

### Checkpoint 1.5.2 - 模板预处理（4-5小时）
**任务：**
- [ ] 创建 `app/services/preprocessing/face_analyzer.py`
- [ ] 实现性别分类（使用 InsightFace）
- [ ] 实现人脸挖空
- [ ] 创建预处理 API
- [ ] 编写测试

**测试后继续下一步 ↓**

### Checkpoint 1.5.3 - 灵活映射（1小时）
**任务：**
- [ ] 更新 faceswap 服务支持自定义映射
- [ ] 实现默认映射逻辑
- [ ] 更新 API 接受映射配置
- [ ] 编写测试

**测试后继续下一步 ↓**

### Checkpoint 1.5.4 - 批量处理（3-4小时）
**任务：**
- [ ] 创建 `app/api/v1/batch.py`
- [ ] 实现批量任务创建
- [ ] 实现 ZIP 下载
- [ ] 编写测试

**测试后继续下一步 ↓**

### Checkpoint 1.5.5 - 自动清理（1-2小时）
**任务：**
- [ ] 创建 `app/services/cleanup/cleaner.py`
- [ ] 创建 Celery 定时任务
- [ ] 配置定时执行
- [ ] 编写测试

**✅ Phase 1.5 完成！**

---

## 🔑 关键代码示例

### 性别分类（InsightFace）

```python
# InsightFace 已经包含性别检测
face_app = FaceAnalysis(name='buffalo_l')
faces = face_app.get(image)

for face in faces:
    # face.sex: 0=female, 1=male
    gender = 'male' if face.sex == 1 else 'female'
    confidence = face.det_score  # 检测置信度
```

### 人脸挖空

```python
def generate_face_mask(image, faces):
    """生成挖空人脸的图像"""
    masked = image.copy()

    for face in faces:
        # 获取人脸区域
        x1, y1, x2, y2 = face['bbox']

        # 方案 A：用黑色填充（简单，MVP推荐）
        masked[y1:y2, x1:x2] = 0

        # 方案 B：使用 inpainting（高级）
        # mask = create_mask_from_landmarks(face['landmarks'])
        # masked = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)

    return masked
```

### 批量处理

```python
# 创建批量任务
batch = BatchTask(
    batch_id=generate_uuid(),
    husband_photo_id=1,
    wife_photo_id=2,
    template_ids=[3, 4, 5, 6],  # 4个模板
    total_tasks=4
)

# 为每个模板创建任务
for template_id in batch.template_ids:
    task = FaceSwapTask(
        task_id=generate_uuid(),
        batch_id=batch.batch_id,
        template_id=template_id,
        husband_photo_id=batch.husband_photo_id,
        wife_photo_id=batch.wife_photo_id
    )
    # 触发异步处理
```

---

## ⚠️ 重要提示

### 1. 数据库迁移是必需的

**不运行迁移会导致：**
- 应用启动失败
- API 错误
- 数据丢失风险

### 2. 字段重命名

一些字段已重命名以保持一致性：

| 旧名称 | 新名称 |
|--------|--------|
| Template.title | Template.name |
| Template.image_id | Template.original_image_id |
| FaceSwapTask.husband_image_id | FaceSwapTask.husband_photo_id |
| FaceSwapTask.wife_image_id | FaceSwapTask.wife_photo_id |

**需要更新的地方：**
- API 端点
- 前端代码
- 现有测试

### 3. InsightFace 性别检测

InsightFace 的 `buffalo_l` 模型已经包含性别检测功能：
- 不需要额外下载模型
- 准确率通常在 95%+
- 使用 `face.sex` 属性即可

---

## 📚 详细文档链接

- **[完整计划](./PLAN-PHASE-1.5.md)** - 所有功能的详细规格
- **[实施指南](./PHASE-1.5-IMPLEMENTATION-GUIDE.md)** - 代码示例和步骤
- **[原始 PLAN.md](../PLAN.md)** - 项目整体计划

---

## 🎯 成功标准

Phase 1.5 完成时应满足：

- [ ] 可以分别上传 photos 和 templates
- [ ] 上传的 template 自动触发预处理
- [ ] Gallery 显示原图和预处理图像
- [ ] 可以看到人脸性别标注
- [ ] 可以一次选择多个 templates
- [ ] 批量处理生成多个结果
- [ ] 可以下载批量结果（ZIP）
- [ ] 临时照片自动清理
- [ ] 所有测试通过（80%+ 覆盖率）

---

## 💡 实施建议

### 按顺序实施

**不要跳步骤！** 每个 Checkpoint 都有依赖关系：

1. 先实现上传 API（为后续提供数据）
2. 再实现预处理（为批量处理准备模板）
3. 然后灵活映射（增强单个处理）
4. 接着批量处理（使用以上功能）
5. 最后自动清理（维护系统）

### 每个 Checkpoint 都测试

不要等到全部完成才测试：
```bash
# 完成 Checkpoint 1.5.1 后
pytest tests/test_phase_1_5/test_photo_upload.py -v

# 完成 Checkpoint 1.5.2 后
pytest tests/test_phase_1_5/test_preprocessing.py -v

# 以此类推...
```

### 遇到问题查看

1. **实施指南** - 有详细代码示例
2. **PLAN 文档** - 有 API 规格和数据结构
3. **现有代码** - 参考现有的 faceswap 实现

---

## 📅 时间估算

**全职开发：** 2-3 天
**兼职开发：** 1-1.5 周

| Checkpoint | 时间 | 难度 |
|-----------|------|------|
| 1.5.1 上传 API | 2-3h | ⭐⭐ 中等 |
| 1.5.2 预处理 | 4-5h | ⭐⭐⭐ 较难 |
| 1.5.3 灵活映射 | 1h | ⭐ 简单 |
| 1.5.4 批量处理 | 3-4h | ⭐⭐ 中等 |
| 1.5.5 自动清理 | 1-2h | ⭐ 简单 |
| 测试编写 | 3-4h | ⭐⭐ 中等 |

**总计：** 14-19 小时纯编码时间

---

**创建时间：** 2025-10-31
**状态：** 数据库模型完成，等待 API 实现
**下一步：** 运行数据库迁移，然后开始 Checkpoint 1.5.1
