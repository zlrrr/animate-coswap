# 模型文件下载修复指南 | Model Download Fix Guide

## 问题诊断 | Problem Diagnosis

你的 `inswapper_128.onnx` 模型文件大小为 **0 字节**（空文件），导致以下错误：

```
[ONNXRuntimeError] : 7 : INVALID_PROTOBUF : Load model from ... failed:Protobuf parsing failed.
```

**原因：** 模型文件下载失败或不完整。

---

## 快速修复 | Quick Fix

### 方案 1: 从 Hugging Face 下载（推荐）

1️⃣ **访问下载页面：**
```
https://huggingface.co/deepinsight/inswapper/tree/main
```

2️⃣ **下载文件：**
- 文件名：`inswapper_128.onnx`
- 大小：约 529 MB (554,950,545 bytes)

3️⃣ **移动到正确位置：**

**在你的 Mac 上执行：**
```bash
# 进入项目目录
cd ~/develop/project/animate-coswap

# 移动下载的文件
mv ~/Downloads/inswapper_128.onnx backend/models/inswapper_128.onnx

# 验证文件大小
ls -lh backend/models/inswapper_128.onnx
```

**预期输出：** 文件大小应该显示 ~529M

4️⃣ **验证下载：**
```bash
# 运行诊断脚本
python scripts/fix_model_download.py
```

5️⃣ **重新测试：**
```bash
python scripts/validate_algorithm.py
```

---

### 方案 2: 使用 wget（如果有 Hugging Face token）

```bash
# 需要先在 https://huggingface.co/settings/tokens 创建 token
wget --header="Authorization: Bearer YOUR_HF_TOKEN" \
  https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx \
  -O backend/models/inswapper_128.onnx
```

---

### 方案 3: 使用 curl（备用）

```bash
cd backend/models

# 尝试直接下载（可能需要 token）
curl -L -o inswapper_128.onnx \
  https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx
```

---

## 验证步骤 | Verification Steps

### 1. 检查文件大小

```bash
ls -lh backend/models/inswapper_128.onnx
```

**✅ 正确：** 显示 `529M` 或类似大小
**❌ 错误：** 显示 `0B` 或非常小的大小

### 2. 运行诊断脚本

```bash
python scripts/fix_model_download.py
```

**✅ 成功输出示例：**
```
✓ Model file exists
✓ File size looks good (529.33 MB)
🔍 Calculating MD5 checksum...
   MD5: e4a3f08c753cb72d04e10aa0f7dbe153

✅ Model File is Valid
```

### 3. 重新运行验证脚本

```bash
python scripts/validate_algorithm.py
```

---

## 常见问题 | FAQ

### Q1: 为什么原来的下载失败了？

**A:** InsightFace 官方 GitHub releases 可能需要认证或有下载限制。建议使用 Hugging Face 镜像。

### Q2: 文件下载很慢怎么办？

**A:**
- 使用浏览器下载（支持断点续传）
- 使用下载工具如 aria2
- 在网络较好的时段下载

### Q3: 下载后还是报错怎么办？

**A:** 检查以下几点：
1. 文件大小是否为 ~529 MB
2. 运行诊断脚本查看 MD5
3. 重新下载文件
4. 检查磁盘空间是否充足

### Q4: macOS 上没有 CoreML 加速？

**A:** 需要安装正确的 onnxruntime 版本。查看下一节。

---

## macOS M 芯片额外配置 | macOS M-chip Additional Setup

### 问题：没有 CoreML 加速

你的输出显示：
```
Available providers: 'AzureExecutionProvider, CPUExecutionProvider'
```

但没有 `CoreMLExecutionProvider`。

### 解决方案：

1️⃣ **检查当前 onnxruntime 版本：**
```bash
pip show onnxruntime
```

2️⃣ **确保使用正确的 requirements：**
```bash
# 激活虚拟环境
source venv/bin/activate

# 安装 macOS M 芯片专用依赖
pip install -r backend/requirements-macos-m.txt
```

3️⃣ **验证 CoreML 支持：**
```python
import onnxruntime as ort
print(ort.get_available_providers())
```

**预期输出应包含：**
```
['CoreMLExecutionProvider', 'CPUExecutionProvider', ...]
```

4️⃣ **如果还是没有 CoreML，重新安装：**
```bash
pip uninstall onnxruntime onnxruntime-silicon -y
pip install onnxruntime==1.16.3
```

---

## 快速命令总结 | Quick Command Summary

```bash
# 1. 下载模型（浏览器）
# 访问: https://huggingface.co/deepinsight/inswapper/tree/main
# 下载: inswapper_128.onnx

# 2. 移动文件
cd ~/develop/project/animate-coswap
mv ~/Downloads/inswapper_128.onnx backend/models/inswapper_128.onnx

# 3. 验证
ls -lh backend/models/inswapper_128.onnx
python scripts/fix_model_download.py

# 4. 测试
python scripts/validate_algorithm.py
```

---

## 需要帮助？| Need Help?

如果以上步骤都无法解决问题，请提供以下信息：

```bash
# 系统信息
uname -a
python --version
pip show onnxruntime

# 文件信息
ls -lh backend/models/inswapper_128.onnx
file backend/models/inswapper_128.onnx

# 运行诊断
python scripts/fix_model_download.py
```

---

**文档更新时间：** 2025-10-28
**适用版本：** animate-coswap v0.1.0+
