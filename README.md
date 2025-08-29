# AIQualityKit

**一个用于评估AI生成内容质量的工具集，包含引文分析、一致性检查和幻觉检测。**

---

## 核心功能

*   **引文分析 (Citation Analysis)**：验证AI回答中引用的来源是否真实、相关。
*   **一致性评估 (Consistency Evaluation)**：检查AI在回答中是否存在前后矛盾或逻辑不一致的地方。
*   **幻觉检测 (Hallucination Detection)**：识别并标记出AI回答中可能包含的虚假或捏造的信息。
*   **Web界面**：提供一个简单直观的前端页面，方便手动输入文本并获取即时分析结果。
*   **RESTful API**：提供标准API接口，便于集成到其他自动化测试流程中。

## 快速开始

### 1. 环境设置

本项目使用 [uv](https://github.com/astral-sh/uv) 进行包和环境管理。

首先，进入项目目录：
```bash
cd path\to\AIQualityKit
```

接着，创建并激活虚拟环境：
```bash
# 创建 .venv 虚拟环境
uv venv

# 激活环境 (Windows)
.venv\Scripts\activate
```

### 2. 安装依赖

```bash
uv pip install -e .
```

### 3. 环境变量配置（可选）

如果你想在服务端配置默认的API密钥，可以设置环境变量：

```bash
# Windows
set AL_KEY=你的百炼API密钥

# 或者创建 .env 文件
echo AL_KEY=你的百炼API密钥 > .env
```

注意：即使没有设置环境变量，你也可以通过前端界面输入API Key来使用所有功能。

### 4. 运行服务

```bash
# 使用UV运行服务器（推荐）
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

服务启动后，访问 `http://127.0.0.1:8000` 即可看到前端界面。

#### 替代启动方式

如果你已经激活了虚拟环境，也可以直接使用：
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 如何使用

### Excel批量分析（推荐）

1. 通过浏览器访问 `http://127.0.0.1:8000`。
2. 在"配置"区域输入百炼API Key。
3. 在"文件上传"区域选择或拖拽Excel文件（.xlsx格式）。
4. 选择分析模式：
   - **Fulltext分析**：完整文本分析，分析完整的问答内容
   - **Sliced分析**：分段分析，分别分析标注句子的一致性
5. 点击"开始分析"按钮。
6. 查看格式化的分析报告和详细结果。

### 文本直接分析

1. 滚动到页面下方的"文本分析"区域。
2. 在文本框中粘贴需要分析的AI生成内容。
3. 点击"分析文本"按钮。
4. 查看返回的JSON格式分析结果。
