# Cross-Disciplinary-Agent-System-CDAS-test2

## Step 0 数据契约

- 统一的 Pydantic 模型位于 `app/schemas/step0.py`，与 `docs/CDAS_step_plan.md` 描述的 JSON 契约保持一致。
- 示例请求/响应载荷可参考 `examples/assignment_config.json`，便于前后端对齐字段名称与嵌套结构。

开发者可直接导入这些模型生成/校验 API payload，避免不同服务间的字段偏差。
