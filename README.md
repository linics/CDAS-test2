# CDAS（Cross-Disciplinary Assignment System）

CDAS 是一套面向 K12 场景的跨学科作业系统，支持教师端作业设计、教案一键生成、过程性提交与教师评价，并提供知识库（RAG）能力辅助任务生成。

## 功能概览

- 教师端：创建/编辑/发布作业，支持 AI 预览与“从教案一键生成”。
- 学生端：按阶段提交成果，查看反馈与评分。
- 评价端：教师评分 + AI 辅助建议（证据绑定）。
- 知识库：上传文档、切片入库、向量检索，为生成提供参考上下文。
- 班级与小组：支持班级成员管理与作业小组协作。

## 技术栈

- Backend：FastAPI、Pydantic v2、SQLAlchemy 2.x、SQLite（开发环境）
- AI/RAG：DeepSeek、SiliconFlow Embedding、ChromaDB
- Frontend：React 18、Vite、TypeScript、Tailwind

## 快速启动

### 1) 启动后端

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

后端地址：`http://127.0.0.1:8000`  
Swagger：`http://127.0.0.1:8000/docs`

### 2) 启动前端

```bash
cd frontend
npm install
npm run dev:local
```

前端地址：`http://127.0.0.1:5173`

## 常用质量检查

### 后端基线检查

```bash
python scripts/check_backend_quality.py
```

快速模式（跳过测试）：

```bash
python scripts/check_backend_quality.py --skip-tests
```

### 前端检查

```bash
cd frontend
npm run check:lint
npm run check:typecheck
npm run check:test
npm run check:build
```

### API 联调冒烟

```bash
cd frontend
npm run check:api-e2e
```

## 环境变量（关键项）

建议在项目根目录配置 `.env`（可参考 `.env.example`）：

- `CDAS_DATABASE_URL`（默认可用 SQLite）
- `CDAS_DEEPSEEK_API_KEY`
- `CDAS_DEEPSEEK_MODEL`（默认 `deepseek-chat`）
- `CDAS_SILICONFLOW_API_KEY`
- `CDAS_SILICONFLOW_EMBEDDING_MODEL`

未配置 AI Key 时，系统会以默认模板/降级逻辑继续运行核心流程，但 AI 能力会受限。

## 目录结构

```text
CDAS-test2/
├─ app/                         # 后端应用
│  ├─ api/v2/                   # 业务 API（auth/assignments/submissions/evaluations/classes）
│  ├─ models/                   # 数据模型
│  ├─ services/                 # AI、RAG、知识库服务
│  └─ main.py                   # 应用入口
├─ frontend/                    # 前端应用（已合并到本仓）
│  ├─ src/app/
│  ├─ scripts/
│  └─ docs/integration/
├─ migrations/sql/              # SQL 迁移脚本
├─ scripts/                     # 后端运维与质量脚本
└─ storage/                     # 运行时数据（本地）
```

## 集成文档入口

推荐优先查看：

- `frontend/docs/integration/onboarding-15min.md`
- `frontend/docs/integration/release-gate-checklist.md`
- `frontend/docs/integration/issue-009-prompt-ui-spec.md`
- `frontend/docs/integration/issue-009-prompt-evaluation-results.md`

## 备注

- 当前仓库即主仓（monorepo），前后端一体维护。
- 请勿提交运行时产物（如 `storage/chroma`、`storage/documents/*`、`storage/uvicorn.pid`）。
