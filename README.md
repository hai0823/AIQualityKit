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

### 3. 运行服务

```bash
uvicorn app.main:app --reload
```

服务启动后，访问 `http://127.0.0.1:8000` 即可看到前端界面。

## 如何使用

1.  通过浏览器访问 `http://127.0.0.1:8000`。
2.  在文本框中粘贴需要分析的AI生成内容。
3.  点击 "Analyze" 按钮。
4.  在下方查看返回的分析结果。
