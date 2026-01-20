# Cross-Disciplinary Assignment System (CDAS)

CDAS 是面向 K12 跨学科作业设计与评价的后端服务，支持“知识库解析 + 作业设计 + 分阶段提交 + 多主体评价”的完整流程。当前同时保留两条主线能力：

- **v1（Step0-4）**：文档知识库、CPOTE 解析与前端对接接口（`/api/*`）。
- **v2（作业系统）**：认证、学科、作业设计、提交与评价（`/api/v2/*`）。

## 目录

- [功能概览](#功能概览)
- [技术栈与架构](#技术栈与架构)
- [快速开始](#快速开始)
- [运行与调试](#运行与调试)
- [核心环境变量](#核心环境变量)
- [API 与前端对接](#api-与前端对接)
- [目录结构](#目录结构)
- [文档与参考](#文档与参考)
- [下一步规划](#下一步规划)

## 功能概览

- **文档知识库**：上传 PDF/Word 后解析、切片、向量化入 ChromaDB（v1）。
- **CPOTE 解析**：基于文档库存生成结构化 CPOTE 与任务包（v1）。
- **作业设计**：支持实践/探究/项目式作业、探究深度、提交模式与阶段模板（v2）。
- **学科体系**：学科与核心素养数据（按学段/分类筛选）（v2）。
- **提交与评价**：草稿/提交/评分状态，教师评价 + 学生自评/互评，AI 评价接口占位（v2）。
- **认证与角色**：教师/学生角色，简化 Bearer Token（v2，开发用）。

## 技术栈与架构

| 模块         | 说明                                                                 |
| ------------ | -------------------------------------------------------------------- |
| 框架         | FastAPI + Pydantic v2                                                |
| ORM/数据库   | SQLAlchemy 2.x + SQLite(开发)/PostgreSQL(生产计划)                    |
| Vector DB    | ChromaDB（磁盘持久化）                                                |
| AI/RAG       | LangChain + Google Gemini（LLM + Embedding，支持无 Key 回退）         |
| 文档解析     | PyPDF2、python-docx、自定义 chunking (`app/utils/text_processing.py`) |
| 依赖管理     | `requirements.txt`                                                   |

逻辑分层：

- `app/api/*`：v1 路由（documents/agents/frontend）
- `app/api/v2/*`：v2 路由（auth/subjects/assignments/submissions/evaluations）
- `app/services/*`：v1 业务服务（inventory/agents/assignments）
- `app/models/*`：SQLAlchemy 模型（Document/User/Subject/Assignment/Submission/Evaluation + enums）
- `app/utils/*`：文件存储、文本解析、切片工具

## 快速开始

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-org/CDAS-test2.git
   cd CDAS-test2
   ```
2. **创建虚拟环境（推荐）**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```
4. **配置 `.env`（可选）**
   ```env
   CDAS_DATABASE_URL=sqlite:///./storage/cdas.db
   CDAS_GEMINI_API_KEY=your_gemini_key_here
   CDAS_GEMINI_MODEL=models/gemini-1.5-pro-latest
   CDAS_GEMINI_EMBEDDING_MODEL=models/text-embedding-004
   ```
   > `.env` 与 `README.md` 位于同级目录，FastAPI 启动后会自动读取。
5. **启动服务**
   ```bash
   uvicorn app.main:app --reload
   ```

启动后会自动创建数据库表并初始化学科数据（见 `app/main.py`）。

## 运行与调试

- Swagger 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`GET /health`

若未提供 Gemini Key，CPOTE/评价仍会返回基于规则的占位结果；一旦 `.env` 中设置了 Key，即可启用真实 LLM/Embedding。

## 核心环境变量

| 变量                             | 默认值/说明                                               |
| -------------------------------- | --------------------------------------------------------- |
| `CDAS_DATABASE_URL`              | `sqlite:///./storage/cdas.db`，生产可改为 PostgreSQL URL  |
| `CDAS_DOCUMENTS_DIR`             | `./storage/documents`                                     |
| `CDAS_CHROMA_PERSIST_DIR`        | `./storage/chroma`                                        |
| `CDAS_GEMINI_API_KEY`            | Gemini API Key，缺失时回退到确定性逻辑                    |
| `CDAS_GEMINI_MODEL`              | `models/gemini-1.5-pro-latest`                            |
| `CDAS_GEMINI_EMBEDDING_MODEL`    | `models/text-embedding-004`                               |

（所有字段在 `app/config.py` 中定义，支持 `.env` + 系统环境变量。）

## API 与前端对接

### v1（Step0-4）
- 文档知识库：`/api/documents`
- CPOTE/评价：`/api/agents`
- 前端对接：`/api/assignments`、`/api/groups`、`/api/submissions`
- 参考文档：`docs/API_frontend_integration.md`、`docs/CDAS_step_plan.md`

### v2（作业系统）
- 认证：`/api/v2/auth`（`register/login/me`）
- 学科：`/api/v2/subjects`
- 作业设计：`/api/v2/assignments`（含发布、生成任务引导）
- 提交：`/api/v2/submissions`
- 评价：`/api/v2/evaluations`

> v2 受保护接口需 `Authorization: Bearer <token>`。当前 Token 实现为简化版本（见 `app/api/v2/auth.py`），生产环境建议替换为标准 JWT + 密钥管理。

## 目录结构

```
app/
  api/
    v2/               # v2 路由：认证/学科/作业/提交/评价
  config.py           # Pydantic Settings
  db.py               # SQLAlchemy engine + Session
  models/             # ORM 定义 + enums
  schemas/            # v1 Pydantic schema（Step0 契约）
  services/           # v1 业务服务
  utils/              # 存储、文本处理工具
docs/
  CDAS_step_plan.md   # Step0-4 改造方案
  API_frontend_integration.md  # v1 API & 前端用法
  PRODUCT_DESIGN.md   # 产品设计与作业流程规范
examples/
  assignment_config.json
storage/
  documents/          # 上传原文件
  chroma/             # Chroma 向量库
```

## 文档与参考

- `docs/PRODUCT_DESIGN.md`：作业类型、探究深度、评价维度、角色权限等产品定义。
- `docs/API_frontend_integration.md`：v1 前端对接与接口示例。
- `docs/CDAS_step_plan.md`：Step0-4 的数据契约、流程与实现计划。
- `docs/references/`：课程标准与研究资料摘录。

## 下一步规划

- 前端落地：教师端/学生端流程与 v2 API 对接。
- 认证升级：Token/密钥配置外置，接入标准 JWT 与权限策略。
- AI 能力：完善作业步骤生成与 AI 评价（目前为占位接口）。
- 生产部署：引入 Alembic 迁移、切换 PostgreSQL、对象存储与日志/监控。
