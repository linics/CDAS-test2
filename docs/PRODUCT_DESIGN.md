# 跨学科作业系统（CDAS）产品设计文档

最后更新：2026-03-04

---

## 0. 文档定位

本文件是 CDAS 当前版本的产品与实现对齐文档，覆盖：

- 业务目标与角色边界
- 核心流程（设计、发布、提交、评价、知识库）
- AI 生成与提示词策略
- 数据模型与关键约束
- 工程治理（质量门、CI、部署约束）

配套治理文档请见：`frontend/docs/integration/`。

---

## 1. 产品目标与价值

CDAS（Cross-Disciplinary Assignment System）面向 K12 教学场景，目标是帮助教师以可控成本完成跨学科作业设计、过程引导与评价闭环。

### 1.1 核心价值

1. 降低设计成本：通过 AI 生成目标、阶段与量规，减少从零起稿成本。
2. 强化过程证据：支持阶段式提交，避免只看终稿。
3. 提高评价一致性：统一四档评价（优秀/良好/达标/需改进）与证据绑定反馈。
4. 保障可追溯：知识库、提交、评价均可追踪来源与过程。

### 1.2 非目标

- 不替代教师最终决策（AI 仅辅助，不自动发布/自动终评）。
- 不做复杂 LMS 全量能力（课表、点名、家校沟通等不在当前范围）。

---

## 2. 角色与权限

系统采用双角色模型：教师、学生。

### 2.1 教师

- 可创建/编辑/发布/归档作业
- 可上传教案与参考资料，触发 AI 生成
- 可查看提交、评分与反馈
- 可管理班级与小组

### 2.2 学生

- 查看被分配作业
- 按阶段提交内容与附件
- 查看教师反馈与评价结果

### 2.3 权限原则

- 最小权限：学生不可访问教师端管理页面与操作。
- 数据隔离：学生只能看到自己的提交与结果。
- 操作可审计：关键写操作都保留时间与操作者信息。

---

## 3. 核心业务流程

## 3.1 作业设计流程（教师）

1. 填写基础信息：主题、学段、年级、主学科、融合学科、作业类型。
2. 选择生成模式：
   - AI 预览（基于表单）
   - 从教案一键生成（基于上传并入库完成的文档）
3. 审核并编辑草稿：
   - 学习目标（knowledge/process/emotion）
   - 阶段与步骤（phases/steps/checkpoints）
   - 评价维度（rubric）
4. 保存草稿或发布。

## 3.2 发布与组织流程（教师）

1. 选择班级与目标学生范围
2. 配置截止时间、提交模式（一次性/分阶段）
3. 发布后可归档与解归档

## 3.3 提交流程（学生）

1. 查看当前阶段任务与证据要求
2. 填写提交内容 + 上传附件
3. 阶段推进（分阶段模式下自动生成下一阶段提交对象）
4. 查看教师评分与反馈

## 3.4 评价流程（教师）

1. 读取学生提交与证据
2. 使用 AI 辅助建议（可选）
3. 教师确认并提交最终评分与反馈

---

## 4. 知识库与 RAG 策略

## 4.1 文档输入

- 支持 PDF / DOCX
- 上传后进入解析、切片、向量化流程
- 文档状态必须 READY 才允许用于生成

## 4.2 生成链路中的 RAG 使用

- 通用 AI 预览：使用 RAG 检索上下文（按文档/学科过滤）。
- 教案一键生成：当前采用“教案直读 + 专用提示词”主链路，避免重检索导致延迟不稳定。
- 设计建议：保留轻量 RAG 增强开关（Top-K 小范围补充），默认不做重注入。

## 4.3 运行约束

- 运行时产物（向量库、临时文档）不纳入 Git 版本管理。
- 重建索引通过脚本执行，不依赖手工操作。

---

## 5. 作业结构与评价模型

## 5.1 作业结构（统一合同）

系统核心保持以下结构兼容：

- `objectives_json`
  - `knowledge`
  - `process`
  - `emotion`
- `phases_json[]`
  - `name`
  - `order`
  - `title`（可选，用于情境导引）
  - `steps[]`
    - `name`
    - `description`（学习支架）
    - `content`（情境承接，可选）
    - `checkpoints[]`
      - `content`
      - `evidence_type`（text/document/image/video/confirm/link）
- `rubric_json`
  - `dimensions[]`

## 5.2 评分协议

- 后端评分输入统一为 `score_numeric`（1-4）
- 显示映射：
  - 4 = 优秀
  - 3 = 良好
  - 2 = 达标
  - 1 = 需改进

## 5.3 AI 辅助评分输出要求

- 维度分数必须与 rubric 维度名严格对齐
- 必须给出证据、理由与改进项（action_items）
- 证据不足时必须降分并说明

---

## 6. AI 提示词体系（当前）

## 6.1 Prompt-A：通用作业生成（preview）

目标：从教师输入上下文生成结构化草稿。

约束：

- 严格 JSON 输出（objectives/phases/rubric）
- 阶段要有递进关系
- step 描述强调学习支架，避免空泛模板语
- checkpoint 控制为 1-2 条且可核验

## 6.2 Prompt-B：教案一键生成（from-lesson-plan）

目标：从已入库教案生成可编辑作业草稿，不直接发布。

约束：

- 保留教案教学意图与结构主线
- 优先映射“目标-活动-产出-评价”
- 失败快速回退默认模板，保证流程不断

## 6.3 Prompt-C：AI 评分建议（ai-assist）

目标：辅助教师评分，不替代教师最终判断。

约束：

- 证据绑定评分
- 输出改进行动建议
- 禁止臆造证据

## 6.4 ISSUE-009 设计约束

详见：`frontend/docs/integration/issue-009-prompt-ui-spec.md`

当前已落地：

- 设计页默认三字段编辑（任务动作/学习支架/提交证据）
- 学生端阶段显示“情境导引 + 学习支架 + 提交证据”
- 提交区新增阶段证据清单联动

---

## 7. 前端交互设计基线

## 7.1 教师端作业设计页

- 默认轻量编辑，减少低价值字段干扰
- 高级字段折叠（阶段名、课时建议、评价要点）
- 支持教案一键生成并回填

## 7.2 学生端作业详情页

- 当前阶段清晰展示
- 证据类型中文化标注
- 提交区提供可点击的证据提示条目

## 7.3 反馈机制

- 成功/警告/错误统一右下可关闭气泡
- 超时错误给出明确下一步建议

---

## 8. 工程架构与服务边界

## 8.1 仓库结构

- 后端：`app/`
- 前端：`frontend/`
- 迁移脚本：`migrations/sql/`
- 质量脚本：`scripts/` 与 `frontend/scripts/`

## 8.2 后端模块

- `app/api/v2/`：业务 API
- `app/models/`：数据模型
- `app/services/`：AI 与知识库服务
- `app/config.py`：环境配置与路径归一化

## 8.3 前端模块

- `frontend/src/app/pages/`：业务页面
- `frontend/src/app/lib/api.ts`：API 合同与请求
- `frontend/src/app/lib/mappers.ts`：数据映射

---

## 9. 质量门与交付规范

## 9.1 后端质量门

- `python scripts/check_backend_quality.py`
  - 语法编译检查
  - pytest

## 9.2 前端质量门

- `npm run check:lint`
- `npm run check:typecheck`
- `npm run check:test`
- `npm run check:build`

## 9.3 集成联调门

- `npm run check:api-e2e`

## 9.4 CI 工作流

- `backend-quality.yml`
- `frontend-quality.yml`

关键策略：

- CI 使用显式环境变量，避免路径污染
- 前端 integration-e2e 按开关与 secret 条件执行

---

## 10. 配置与部署约束

## 10.1 关键环境变量

- 数据与存储：
  - `CDAS_DATABASE_URL`
  - `CDAS_DOCUMENTS_DIR`
  - `CDAS_CHROMA_PERSIST_DIR`
  - `CDAS_AI_LOGS_DIR`
- CORS：
  - `CDAS_CORS_ALLOWED_ORIGINS`
  - `CDAS_CORS_ALLOW_ORIGIN_REGEX`
- AI：
  - `CDAS_DEEPSEEK_API_KEY`
  - `CDAS_SILICONFLOW_API_KEY`

## 10.2 路径与跨平台

- 运行路径统一经配置归一化，不依赖当前工作目录
- 禁止将本机绝对路径写入业务代码与关键文档

## 10.3 安全要求

- `.env` 永不入库
- 一旦密钥泄露，必须立即 rotate
- 运行时数据与临时日志不进 Git

---

## 11. 当前状态与后续迭代

## 11.1 当前已完成

- 教案一键生成（可编辑草稿）
- 提示词体系分层与 ISSUE-008 修复
- ISSUE-009 第一至第三批（提示词 + UI 联动）
- 跨环境部署可移植性修复（路径/CORS/CI）

## 11.2 近期建议迭代

1. ISSUE-009 证据清晰度定向优化（提升 checkpoint 可核验质量）
2. 学生提交区与阶段任务引导继续精简
3. 教案链路轻量 RAG 增强（可配置开关）
4. 关键文档历史绝对路径清洗

---

## 12. 附录：相关文档入口

- 规范与路线：`frontend/docs/integration/normalization-plan-2weeks.md`
- 质量与发布：`frontend/docs/integration/release-gate-checklist.md`
- 提示词与交互规范：`frontend/docs/integration/issue-009-prompt-ui-spec.md`
- 提示词评估结果：`frontend/docs/integration/issue-009-prompt-evaluation-results.md`
- 问题对齐看板：`frontend/docs/integration/alignment-issues.md`
