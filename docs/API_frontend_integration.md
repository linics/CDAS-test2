# CDAS API 前端对接指南

> 基础 URL：`http://127.0.0.1:8000`（生产环境替换为对应域名）。所有时间字段均为 UTC ISO8601。

## 1. 知识库存（Documents）

### 1.1 上传文件 `POST /api/documents/upload`

- **请求**：`multipart/form-data`，字段 `file`（PDF/Word）。
- **响应**

```json
{
  "document_id": 12,
  "filename": "lesson.pdf",
  "status": "indexing" // uploaded/indexing/ready/failed
}
```

- **状态流转**：`uploaded → indexing → ready`（成功）；异常则 `failed` 并写 `error_msg`。
- **前端用法（React Query）**

```ts
const uploadDoc = useMutation({
  mutationFn: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return fetch("/api/documents/upload", { method: "POST", body: form }).then(r => r.json());
  },
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
});
```

### 1.2 列表 `GET /api/documents`

```json
[
  {
    "id": 12,
    "filename": "lesson.pdf",
    "status": "ready",
    "upload_date": "2024-08-10T07:21:00Z",
    "metadata_json": { "page_count": 18, "chunk_count": 52 }
  }
]
```

前端可用 `status` 决定是否允许触发 CPOTE 解析；`metadata_json` 为空说明尚未完成解析。

### 1.3 详情 `GET /api/documents/{id}`

返回 `DocumentDetail`：在列表字段基础上增加 `error_msg`、`file_path`、`mime_type`、`size_bytes`。若 `status=="failed"`，UI 中提示 `error_msg` 并提供重试按钮（重新上传或重新解析）。

### 1.4 删除 `DELETE /api/documents/{id}`

同时清理 SQL 记录、磁盘文件、Chroma 向量。成功返回 `{"status": "deleted"}`。

## 2. Agent 层

### 2.1 解析 CPOTE `POST /api/agents/parse_cpote`

```json
// Request
{
  "document_id": 12,
  "assignment_title": "校园垃圾分类改进项目"
}

// Response
{
  "assignment_id": 45,
  "cpote": { "...": "CPOTEExtraction（含 source_refs）" },
  "milestones": [
    { "index": 1, "name": "组队与分工", "description": "...", "due_at": "2024-09-01T00:00:00Z" },
    { "index": 2, "name": "调查与研究", "...": "..." }
  ]
}
```

- 成功后自动在数据库写入 `Assignment` 与 `Document.cpote_json`。
- **错误码**：
  - 404：`document_id` 不存在。
  - 400：上下文不足（文档向量尚未 ready）。
  - 422：Gemini 输出缺少必填字段（响应中会附带 `missing_fields`）。
- 前端可在文档详情中提供“生成任务包”按钮，成功后跳转到 `/assignments/{assignment_id}` 页面。

### 2.2 AI 评价 `POST /api/agents/evaluate_submission`

```json
// Request
{
  "group_id": 101,
  "milestone_index": 2,
  "content": {
    "text": "我们完成了问卷并统计了结果......",
    "attachments": [{ "filename": "survey.pdf", "url": "https://cdn/..", "type": "pdf" }]
  }
}

// Response
{
  "submission_id": 301,
  "evaluation": {
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
    "summary": "团队按时提交并提供了数据支撑……",
    "improvements": ["进一步量化改进方案的预期效果", "在协作记录中补充分工细节"],
    "evidence": [
      { "source": "submission_text", "quote": "我们收集了100份问卷", "reason": "体现充分调研" }
    ]
  }
}
```

- **错误码**：404（group/assignment 不存在），400（`content.text` 为空）。
- `radar_data` 可直接用于 Recharts。

## 3. 前端 API（Assignment/Group/Submission）

### 3.1 获取任务包 `GET /api/assignments/{assignment_id}`

返回 `AssignmentConfig`：

```json
{
  "assignment_id": 45,
  "title": "校园垃圾分类改进项目",
  "cpote": { "...": "CPOTEExtraction" },
  "milestones": [
    { "index": 1, "name": "组队与分工", "description": "...", "due_at": "2024-08-10T00:00:00Z" },
    { "index": 2, "name": "调查与研究", "submission_requirements": "包含调研数据" }
  ],
  "groups": [
    {
      "id": 101,
      "assignment_id": 45,
      "name": "A组",
      "members": [
        { "name": "Alice", "role": "leader" },
        { "name": "Bob", "role": "researcher" }
      ]
    }
  ],
  "rubric": {
    "dimensions": ["participation", "collaboration", "inquiry", "innovation", "result"],
    "scale": "0-100",
    "criteria": { "participation": "0-20:缺失提交；21-60:部分完成；..." }
  }
}
```

### 3.2 小组管理

- 列表 `GET /api/groups?assignment_id=45` → `Group[]`。
- 创建 `POST /api/groups`

```json
{
  "assignment_id": 45,
  "name": "B组",
  "members": [
    { "name": "Carol", "role": "leader" },
    { "name": "Dave", "role": "designer" },
    { "name": "Eve", "role": "researcher" }
  ]
}
```

若人数需要前端限制为 4-6 人，可在提交前校验。成功后返回 `GroupResponse`（与 `Group` 同结构）。

### 3.3 阶段提交

- 保存 `POST /api/submissions`

```json
{
  "assignment_id": 45,
  "group_id": 101,
  "milestone_index": 2,
  "content": {
    "text": "阶段性草稿正文……",
    "attachments": [{ "filename": "draft.pdf", "url": "https://cdn/..", "type": "pdf" }]
  }
}
```

返回 `SubmissionResponse`，其中 `submitted_at` 已格式化为 UTC。

- 查询 `GET /api/submissions/{submission_id}` → `Submission`（包含 `ai_evaluation`，可能为 `null`）。

## 4. 前端状态管理建议

- **TanStack Query**：
  - `useQuery(['documents'], fetchDocuments)` 列出库存。
  - `useMutation` 配合 `invalidateQueries` 处理上传、创建组、提交作业等。
  - 对长任务（解析 CPOTE / AI 评价）可在 Mutation 的 `onSuccess` 中提示 Toast，并跳转到相应页面。
- **错误处理**：
  - 400/422：显示服务端返回的 `detail`，并允许用户修改重试。
  - 404：告知资源不存在，自动返回上一级。
  - 500：提示“服务器异常，请稍后重试”，可提供“重新尝试”按钮重新触发 Mutation。

## 5. 常见问题 & 调试

| 场景 | 现象 | 处理 |
| --- | --- | --- |
| 上传后一直 `indexing` | 文档较大或解析异常 | 通过 `GET /api/documents/{id}` 查看 `error_msg`，必要时重新上传 |
| 解析 CPOTE 返回 400/422 | 文档未 ready 或模型输出缺字段 | 确认文档状态为 `ready`；如仍失败，提示用户补充素材或稍后重试 |
| 评价接口 404 | group / assignment 未创建或 ID 不匹配 | 通过 `GET /api/groups` 检查 group 是否属于 assignment |
| Radar 图数据为空 | 还未触发 AI 评价 | 调用 `POST /api/agents/evaluate_submission` 或在 UI 上提示“等待评价” |

---

如需切换生产数据库或部署，请参考 `docs/CDAS_step_plan.md` 中 Step 1/Step 4 的注意事项（PostgreSQL、CORS、日志等）。
