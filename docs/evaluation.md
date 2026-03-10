# 本地评测说明

## 运行语义前提

当前正式支持的 runtime mode 只有：

- `mock`
- `agents_sdk`

旧的 `live` 别名不再接受。继续传入会直接报错，避免把 mock 结果误读成真实 Ark 结果。

评测结果需要结合以下字段解读：

- `requested_runtime_mode`
- `effective_runtime_mode`
- `effective_model`
- `used_mock_fallback`
- `fallback_reason`

尤其要注意：

- `completed` 不一定代表 provider 直出成功
- `completed + used_mock_fallback=true` 代表“真实 provider 失败后，由 mock 补全并完成”
- mock 评测与 agents_sdk 评测现在必须分开看

## 数据集位置

本地评测样例位于：

- `backend/data/evals/competition_recommendation.json`
- `backend/data/evals/competition_eligibility_check.json`
- `backend/data/evals/competition_timeline_plan.json`

每条样例至少包含：

- `id`
- `task_type`
- `input`
- `expected_required_fields`
- `scoring_rubric`
- `optional_notes`

当前仍保持原有数据结构兼容，但评测逻辑已经从“字段存在”升级为“字段 + 基础质量评分”。

## 运行方式

命令行：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock
```

`agents_sdk` spot check：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval_agents_sdk.py --sample-per-task-type 5
```

输出完整 JSON：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock --json
```

只跑单一任务类型：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock --task-type competition_recommendation
```

若想对 `agents_sdk` 评测做更小样本抽样：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode agents_sdk --sample-per-task-type 3
```

## 当前评分方式

### 1. 结构检查

仍然保留：

- `expected_required_fields`
- `scoring_rubric.require_non_empty`

如果关键字段缺失或为空，case 会失败。

### 2. 质量评分

在结构检查之外，当前还会对三类任务做基础质量评分：

`competition_recommendation`

- 推荐结果是否接近本地 profile filter 的高分候选
- 推荐理由是否具体
- 风险提示是否有效
- 是否存在明显重复或空话

`competition_eligibility_check`

- 判断是否与本地 eligibility rules 一致
- 缺失条件是否具体
- rationale / attention points 是否足够支撑结论

`competition_timeline_plan`

- milestones 是否覆盖本地模板中的关键阶段
- 时间安排是否基本合理
- checklist / deliverables / stage_plan 是否存在明显遗漏

## 输出摘要解读

CLI 会输出：

- `total`
- `passed`
- `failed`
- `warning_cases`
- `low_quality_cases`
- `avg_quality`
- `direct_success_rate`
- `fallback_rate`
- `hard_failure_rate`
- `awaiting_review_ratio`
- `artifact_completeness_ratio`
- `avg_latency_ms`
- `p95_latency_ms`

单条 case 还会输出：

- `passed`
- `status`
- `completion_path`
- `requested/effective runtime`
- `fallback=true|false`
- `quality=当前分数/阈值`
- `missing`
- `warnings`
- `failed_checks`

## 通过标准

当前 case 判定通过，需要同时满足：

- 任务未进入 `failed` 或 `cancelled`
- 必填字段完整
- `quality_score >= quality_threshold`

`awaiting_review` 仍可通过，但会在 warnings 中显式提示。

`direct_success_rate` 的定义是：

- `completed` 或 `awaiting_review`
- `effective_runtime_mode == "agents_sdk"`
- `used_mock_fallback == false`

`fallback_rate` 的定义是：

- `used_mock_fallback == true`

`hard_failure_rate` 的定义是：

- 最终状态为 `failed` 或 `cancelled`

## 测试入口

基础回归测试：

- `backend/app/tests/test_eval_regression.py`

该测试会验证：

- 3 类任务样例数量
- mock 模式下全量回归通过
- 平均质量分数高于最低基线
- runtime summary 中的 direct success / fallback / failure 指标结构存在
