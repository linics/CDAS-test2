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
- **Framework**: FastAPI + Pydantic v2
- **Database**: SQLAlchemy 2.x + SQLite (dev)
- **Vector DB**: ChromaDB (for RAG)
- **AI Model**: Google Gemini 1.5 Pro
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
.\.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量 (参考 .env.example)
# CDAS_DATABASE_URL=sqlite:///./storage/cdas.db
# CDAS_GEMINI_API_KEY=your_key

# 启动服务
uvicorn app.main:app --reload
```

### 2. 前端设置

```bash
cd frontend
npm install
npm run dev
```

服务默认地址：
- API Docs: `http://127.0.0.1:8000/docs`
- Frontend: `http://127.0.0.1:5173`

## 项目结构

```
CDAS-test2/
├── app/                 # 后端核心逻辑
│   ├── api/v2/          # RESTful API 路由
│   ├── models/          # 数据库模型
│   ├── services/        # 业务逻辑 (AI, RAG, etc.)
│   └── ...
├── frontend/            # React 前端应用
│   ├── src/             
│   │   ├── components/  # UI 组件
│   │   ├── pages/       # 页面视图 (Login, Dashboard, etc.)
│   │   └── ...
├── docs/                # 设计文档
├── scripts/             # 辅助脚本
└── storage/             # 数据库与文件存储 (Git ignored)
```

## 文档索引

- `docs/PRODUCT_DESIGN.md`: 产品详细设计方案
- `docs/API_frontend_integration_v2.md`: 前后端接口对接文档
