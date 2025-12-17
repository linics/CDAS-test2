# CDAS 重构步骤说明（Step 0 - Step 4）

本文档按要求提供后端/前端分离改造的可执行步骤，涵盖数据契约、数据库架构、Inventory 服务、Agent 设计与前端对接方案。所有时间字段使用 ISO8601 UTC。

---

## Step 0：统一数据契约（JSON 结构与示例）

> 所有结构在 DB 的 JSON 字段与 API 响应中一致复用，字段命名采用 snake_case。

### 1. CPOTEExtraction
- `context`: string
- `problem`: string
- `objective`: string
- `task`: string
- `evaluation`: string
- `source_refs`: array<SourceRef>（用于溯源防幻觉）

**SourceRef**
- `document_id`: string/int
- `page`: int
- `chunk_id`: string
- `text`: string

**示例**
```json
{
  "context": "学生将围绕校园垃圾分类开展探究。",
  "problem": "校园垃圾分类中存在混投和资源浪费。",
  "objective": "培养学生的可持续发展意识并提出改进方案。",
  "task": "分组调研垃圾分类现状，制定改进措施并制作汇报。",
  "evaluation": "根据调研质量、合作程度和成果可行性进行评价。",
  "source_refs": [
    { "document_id": 12, "page": 3, "chunk_id": "12-3-5", "text": "......" }
  ]
}
```

### 2. AssignmentConfig（学生任务包）
- `assignment_id`: string/int
- `title`: string
- `cpote`: CPOTEExtraction
- `milestones`: Milestone[]
- `groups`: Group[]（可为空，待前端创建）
- `rubric`: Rubric（用于评分一致性）

**示例**
```json
{
  "assignment_id": 45,
  "title": "校园垃圾分类改进项目",
  "cpote": { "...": "见上" },
  "milestones": [
    { "index": 1, "name": "组队与分工", "description": "提交分工表", "due_at": "2024-08-10T00:00:00Z" },
    { "index": 2, "name": "调查与研究", "description": "提交数据/草稿", "due_at": "2024-08-17T00:00:00Z" },
    { "index": 3, "name": "成果制作", "description": "提交PPT/报告", "due_at": "2024-08-24T00:00:00Z" },
    { "index": 4, "name": "汇报与评价", "description": "最终汇报", "due_at": "2024-08-31T00:00:00Z" }
  ],
  "groups": [],
  "rubric": {
    "dimensions": ["participation", "collaboration", "inquiry", "innovation", "result"],
    "scale": "0-100",
    "criteria": {
      "participation": "0-20: 无提交；21-60: 部分完成；61-85: 按时完成；86-100: 主动贡献",
      "collaboration": "......"
    }
  }
}
```

### 3. Milestone
- `index`: int（1-based）
- `name`: string
- `description`: string
- `due_at`: string (ISO8601 UTC)
- `submission_requirements`: string（可选，用于提示提交格式）

**示例**
```json
{ "index": 2, "name": "调查与研究", "description": "提交数据/草稿", "due_at": "2024-08-17T00:00:00Z", "submission_requirements": "包含访谈或问卷数据" }
```

### 4. Group
- `id`: string/int
- `assignment_id`: string/int
- `name`: string
- `members`: Member[]（4-6 人约束由业务层校验）

**Member**
- `name`: string
- `role`: string（如 leader/researcher/designer 等）
- `contact`: string（可选）

**示例**
```json
{
  "id": 101,
  "assignment_id": 45,
  "name": "A组",
  "members": [
    { "name": "Alice", "role": "leader" },
    { "name": "Bob", "role": "researcher" }
  ]
}
```

### 5. Submission
- `id`: string/int
- `group_id`: string/int
- `assignment_id`: string/int
- `milestone_index`: int
- `submitted_at`: string (ISO8601 UTC)
- `content`: SubmissionContent
- `ai_evaluation`: EvaluationResult | null

**SubmissionContent**
- `text`: string
- `attachments`: Attachment[]（可选）

**Attachment**
- `filename`: string
- `url`: string
- `type`: string (e.g., "pdf", "image")

**示例**
```json
{
  "id": 301,
  "group_id": 101,
  "assignment_id": 45,
  "milestone_index": 2,
  "submitted_at": "2024-08-15T12:00:00Z",
  "content": {
    "text": "我们完成了问卷并统计了结果……",
    "attachments": [
      { "filename": "survey.pdf", "url": "https://cdn/...", "type": "pdf" }
    ]
  },
  "ai_evaluation": null
}
```

### 6. EvaluationResult（五维评分 + 雷达图）
- `scores`: ScoreBreakdown
- `radar_data`: RadarPoint[]（给前端 Recharts）
- `summary`: string
- `improvements`: string[]
- `evidence`: EvidenceItem[]

**ScoreBreakdown**
- `participation`: int (0-100)
- `collaboration`: int
- `inquiry`: int
- `innovation`: int
- `result`: int
- `overall`: int（平均或加权）

**RadarPoint**
- `dimension`: string (one of five)
- `score`: int

**EvidenceItem**
- `source`: string (e.g., "submission_text", "retrieved_chunk")
- `quote`: string
- `reason`: string

**示例**
```json
{
  "scores": {
    "participation": 82,
    "collaboration": 78,
    "inquiry": 85,
    "innovation": 74,
    "result": 88,
    "overall": 81
  },
  "radar_data": [
    { "dimension": "participation", "score": 82 },
    { "dimension": "collaboration", "score": 78 },
    { "dimension": "inquiry", "score": 85 },
    { "dimension": "innovation", "score": 74 },
    { "dimension": "result", "score": 88 }
  ],
  "summary": "团队按时提交并提供了数据支撑，成果具备可行性。",
  "improvements": ["进一步量化改进方案的预期效果", "在合作记录中补充分工细节"],
  "evidence": [
    { "source": "submission_text", "quote": "我们收集了200份问卷", "reason": "体现充分调研" }
  ]
}
```

---

## Step 1：Backend Setup & Database Schema（架构与模型）

### 1) 目录结构（FastAPI）
- `app/main.py`：FastAPI 入口
- `app/api/`：路由（documents, assignments, groups, submissions, agents）
- `app/models/`：SQLAlchemy 模型
- `app/schemas/`：Pydantic 模型（与 Step0 JSON 契约对应）
- `app/services/`：业务服务（inventory, agents, evaluation）
- `app/db.py`：Session/engine 管理
- `app/config.py`：环境配置（DB URL, Chroma persist_dir, Gemini key）
- `app/utils/`：文件存储、chunking、embedding

### 2) SQLAlchemy 模型（关键字段）
- **Document**: `id`, `filename`, `upload_date`, `parsing_status` (Enum: uploaded → indexing → ready / failed), `file_path`, `mime_type`, `size_bytes`, `cpote_json` (可为空), `metadata_json` (pages, chunk_count)
- **Assignment**: `id`, `title`, `scenario`（= cpote.context）, `milestones_json` (Milestone[]), `cpote_json` (CPOTEExtraction), `document_id` (FK), `rubric_json`
- **ProjectGroup**: `id`, `assignment_id` (FK), `members_json` (Group.members), `name`
- **Submission**: `id`, `group_id` (FK), `assignment_id` (FK), `milestone_index`, `content_json` (SubmissionContent), `ai_evaluation_json` (EvaluationResult), `submitted_at`

### 3) 状态机：Document.parsing_status
- **uploaded**（文件落盘成功）
- **indexing**（解析/向量化进行中）
- **ready**（向量入库完成，可检索）
- **failed**（解析或入库失败，需记录 error_msg）

流转：uploaded → indexing → ready / failed；失败可重试：failed → indexing → ready。

### 4) JSON 字段对应 Step0
- `Document.cpote_json`：CPOTEExtraction（若解析后直接生成，可为空）
- `Assignment.milestones_json`：Milestone[]
- `Assignment.cpote_json`：CPOTEExtraction
- `Assignment.rubric_json`：Rubric
- `ProjectGroup.members_json`：Group.members
- `Submission.content_json`：SubmissionContent
- `Submission.ai_evaluation_json`：EvaluationResult

### 5) SQLite → PostgreSQL 迁移注意
- 使用 `UUID`/`BigInteger` 兼容两端；避免 SQLite 自增差异可用 `Integer` + autoincrement。
- JSON 字段：SQLite 用 `JSON`/`Text` + Pydantic 校验；Postgres 用 `JSONB`。
- 事务与并发：确保文件落盘与 DB 写入分步事务；Postgres 下使用 `SERIALIZABLE`/`READ COMMITTED`。
- 使用 Alembic 管理迁移，生产用 `psycopg`。

---

## Step 2：Inventory Service（上传 → 解析 → 切片 → 向量入库）

### API：POST /api/documents/upload
- **请求**：`multipart/form-data`，字段：`file` (pdf/docx)
- **响应示例**
```json
{ "document_id": 12, "filename": "lesson.pdf", "status": "uploaded" }
```

### 流程
1. **文件落盘**：保存至 `storage/documents/{document_id}/orig.pdf`；预留对象存储扩展点。
2. **更新状态**：`uploaded → indexing`。
3. **解析**：PDF/Word → 文本 + 页码。工具：PyPDF2 / pdfplumber；docx 用 `python-docx`（可扩展）。
4. **Chunking**：`chunk_size=800 tokens`，`overlap=200`；元数据：`document_id`, `page`, `chunk_id`, `order`.
5. **Embedding**：调用 Gemini Embedding；抽象接口 `embed_texts(texts) -> vectors`，便于切换。
6. **写入 ChromaDB**：`Collection` 按 `document_id` 分组；`persist_dir` 配置为 `./storage/chroma`.
7. **写入 SQL**：保存 `metadata_json`（页数、chunk_count）；状态置为 `ready`；失败则 `failed` 并记录 error。

### 其他 API
- **GET /api/documents**
  - 列出文档：`[{id, filename, status, upload_date, chunk_count}]`
- **GET /api/documents/{id}**
  - 详情：`{id, filename, status, metadata_json, error_msg?}`
- **DELETE /api/documents/{id}**（可选）
  - 同步删除：SQL 记录 + Chroma 过滤 `where document_id = id`。

### 实现要点（伪代码）
```
def upload_document(file):
    doc = Document(status="uploaded")
    save(file, path)
    doc.status = "indexing"; commit()
    try:
        text_chunks = parse_and_chunk(file)
        vectors = embed(text_chunks)
        chroma.upsert(ids=[chunk.id], embeddings=vectors, metadatas=chunk.meta)
        doc.metadata_json = {...}
        doc.status = "ready"
    except Exception as e:
        doc.status = "failed"; doc.error = str(e)
    commit()
    return doc
```

### 测试清单
- 上传 PDF 成功：状态流转到 `ready`，Chroma 存在对应 entries。
- 上传异常文件：状态为 `failed`，error_msg 有内容。
- 重新上传同名文件：生成新 document_id，不影响旧数据。
- 删除文档：SQL 与 Chroma 均清理。

---

## Step 3：Agent Layer

### 3.1 Meta-Agent：教案 → C-POTE → AssignmentConfig
- **API**：POST `/api/agents/parse_cpote`
  - 请求：`{ "document_id": 12, "assignment_title": "xxx" }`
  - 响应：`{ "assignment_id": 45, "cpote": CPOTEExtraction, "milestones": Milestone[] }`

#### 过程
1. 从 Chroma 按 `document_id` 检索高相关 chunk（top_k=8）。
2. 提示词模板：要求输出严格 JSON（Pydantic 校验）。
3. 解析 CPOTE；生成默认 Milestone 1-4（可根据 CPOTE.task 调整描述）。
4. 写入 Assignment（cpote_json, milestones_json, document_id）。

#### 防幻觉策略
- 检索到的 chunk 附带 `source_refs` 写入 CPOTEExtraction。
- 要求模型先列出引用的 chunk_id，再生成 CPOTE。
- 设定最低置信度：若关键字段为空或低于 token-length 阈值，返回错误 `{missing_fields: [...]}`。
- Pydantic 严格校验字段类型与非空；失败则返回 422。

#### 测试清单
- 提供有效 document_id：返回 Assignment 并持久化 JSON。
- 提供不存在的 document_id：返回 404。
- 刻意截断 chunk：应返回 missing_fields 或 400，避免幻觉。

### 3.2 Evaluation-Agent：Submission → 五维评分 → 雷达图
- **API**：POST `/api/agents/evaluate_submission`
  - 请求：`{ "group_id": 101, "milestone_index": 2, "content": SubmissionContent }`
  - 响应：`{ "evaluation": EvaluationResult }`

#### 评分 Rubric（区间例）
- 0-20：缺失提交/无关内容
- 21-60：部分完成，证据不足
- 61-85：完成主要要求，有证据
- 86-100：高质量、创新、证据充分
按维度加权后计算 overall（平均或自定义权重）。

#### 可重复性策略
- 模型先提取证据（EvidenceItem），再逐维打分。
- 固定输出格式（Pydantic）；分数保留整数。
- 设置随机性：`temperature=0.2`，并在提示中要求“在相同输入下保持一致评分”。

#### 流程伪代码
```
def evaluate_submission(payload):
    submission = upsert_submission(...)
    evidence = extract_evidence(payload.content.text)
    scores = score_with_rubric(evidence, rubric)
    radar = [{"dimension": k, "score": v} for k, v in scores.items() if k in dims]
    eval = {scores, radar_data: radar, summary, improvements, evidence}
    submission.ai_evaluation_json = eval
    commit()
    return eval
```

#### 测试清单
- 正常提交：返回 5 维评分且 radar_data 长度为 5。
- 同一内容多次调用：分数波动不超过设定阈值（如 ±5）。
- 无内容提交：返回 400 或低分并记录原因。

---

## Step 4：Frontend Integration Plan（对接方案）

### 页面与 API 映射
- **资料库页面**：调用 `GET /api/documents` 列表；上传用 `POST /api/documents/upload` 显示状态（uploaded/indexing/ready/failed）；详情 `GET /api/documents/{id}`；按钮触发 CPOTE 解析 `POST /api/agents/parse_cpote`。
- **作业页面**：展示 AssignmentConfig（title, cpote, milestones）；按 milestone 提供提交入口 `POST /api/submissions`（与 evaluate API 分离，先存再评）。
- **小组页面**：`GET/POST /api/groups`；前端在创建时校验成员数 4-6。
- **评价页面**：`GET /api/submissions/{id}` 显示 ai_evaluation；雷达图使用 `EvaluationResult.radar_data` 直接喂给 Recharts（`{ subject: dimension, A: score }` 或 `{ dimension, score }`）。

### 状态管理建议
- 使用 TanStack Query 统一数据获取与缓存；mutation 处理上传/提交。
- 全局错误边界 + toast；对 500/422 提供重试按钮。

### 错误处理与重试
- 上传失败：提示可重试；若 `failed` 状态提供“重新索引”按钮（调用重新解析端点）。
- 解析失败：展示 error_msg；允许再次触发 parse_cpote。
- 评价失败：保留 Submission，允许重新请求 evaluate_submission。

### 前端与 API 契约检查
- 所有日期字段按 UTC 显示；前端转换本地时区。
- 提交内容大小限制提示；支持附件上传时同步存储 URL。

### 测试清单
- 手动流程：上传文档 → 解析 → 生成 Assignment → 组队 → 阶段提交 → 评价展示。
- UI：雷达图渲染 5 维，缺失数据时显示占位提示。

