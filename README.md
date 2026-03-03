# Cross-Disciplinary Assignment System (CDAS)

CDAS 是一个面向 K12 教育的跨学科作业设计与评价系统。它利用 AI 辅助教师设计高质量的跨学科作业，并对学生的作业进行多维度评价。

详细设计文档请参考 `docs/PRODUCT_DESIGN.md`。

## 核心功能

- **作业设计 (Assignment Design v2)**：支持以核心学科为基础，融合多学科知识的作业生成。
- **智能评价 (AI Evaluation v2)**：基于知识、能力、情感等多维度的 AI 自动评价。
- **知识库 (Knowledge Base)**：支持上传 PDF/Word 格式的教学资料和课程标准（RAG）。
- **用户管理**：区分教师（设计/发布）与学生（提交/查看）角色。

## 技术栈

### Backend
- **Framework**: FastAPI (v0.110+) + Pydantic v2
- **Database**: SQLAlchemy 2.x + SQLite (dev)
- **Vector DB**: ChromaDB (for RAG)
- **AI Model**: DeepSeek (deepseek-chat) via DeepSeek API
- **Embedding**: BAAI/bge-large-zh-v1.5 via SiliconFlow API
- **Tools**: PyPDF2, python-docx

### Frontend
- **Framework**: React 18 + Vite
- **Styling**: Tailwind CSS + Shadcn UI (Archive Theme)
- **State**: TanStack Query + Context API

## 快速开始

### 1. 后端设置

```bash
# 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量 (参考 .env.example)
# 必须设置 API KEY 才能使用 AI 功能
# CDAS_DEEPSEEK_API_KEY=sk-...
# CDAS_SILICONFLOW_API_KEY=sk-...

# 启动服务
uvicorn app.main:app --reload
```

后端服务启动在: `http://127.0.0.1:8000`

### 2. 前端设置

```bash
cd frontend
npm install
npm run dev:local
```

前端服务启动在: `http://127.0.0.1:5173`

说明：当前前端主目录已合并到本仓库 `frontend/`。
历史独立前端目录 `D:\githubfiles\cdas-frontend-main` 可作为参考归档。

快速上手指引（15分钟）请参考：

- `frontend\docs\integration\onboarding-15min.md`

## API 文档

访问 Swagger UI 查看详细接口定义：`http://127.0.0.1:8000/docs`

### V2 API (主业务)
所有 V2 接口均以 `/api/v2` 为前缀：
- **认证**: `/api/v2/auth` (Login, Register, Me)
- **学科**: `/api/v2/subjects` (CRUD)
- **作业**: `/api/v2/assignments` (Design, List)
- **提交**: `/api/v2/submissions` (Grade, Feedback)
- **评价**: `/api/v2/evaluations`

### Legacy/Utils API
- **文档管理**: `/api/documents` (Upload, List)

## 质量基线检查（Normalization）

在合并或发版前，建议执行：

```bash
python scripts/check_backend_quality.py
```

该命令会依次执行：

- `python -m compileall -q app scripts tests`
- `python -m pytest -q`

如仅需快速语法检查，可使用：

```bash
python scripts/check_backend_quality.py --skip-tests
```

### 重建知识库索引（推荐）

当文档历史索引异常（如 embedding 维度不一致）时，可执行重建：

```bash
.venv\Scripts\python.exe scripts/reindex_documents.py
```

该脚本会：
- 重建 `cdas-documents` 向量集合
- 遍历现有 `documents` 记录并从文件重新解析、切片、入库
- 回写 `parsing_status / metadata_json / error_msg`

### 批量导入课标文档

```bash
.venv\Scripts\python.exe scripts/seed_knowledge_base.py
```

## 项目结构

```
CDAS-test2/
├── app/                 # 后端核心逻辑
│   ├── api/v2/          # V2 RESTful API 路由
│   ├── models/          # SQLAlchemy 数据库模型
│   ├── services/        # 业务逻辑 (AI, RAG, etc.)
│   └── main.py          # 应用入口
├── docs/                # 设计文档
├── scripts/             # 辅助脚本 (Clean, Seed)
└── storage/             # 数据库与文件存储 (Git ignored)
```

Canonical frontend repository (external):

- `D:\githubfiles\CDAS-test2\CDAS-test2\frontend`

Legacy frontend reference (not canonical):

- `D:\githubfiles\cdas-frontend-main`

## 配置说明 (.env)

| 变量名 | 示例值 | 说明 |
| :--- | :--- | :--- |
| `CDAS_DATABASE_URL` | `sqlite:///./storage/cdas.db` | 数据库连接串 |
| `CDAS_DEEPSEEK_API_KEY` | `sk-...` | DeepSeek API 密钥 (用于文本生成) |
| `CDAS_DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 模型版本 |
| `CDAS_SILICONFLOW_API_KEY` | `sk-...` | SiliconFlow API 密钥 (用于 Embedding) |
| `CDAS_SILICONFLOW_EMBEDDING_MODEL` | `BAAI/bge-large-zh-v1.5` | Embedding 模型版本 |
