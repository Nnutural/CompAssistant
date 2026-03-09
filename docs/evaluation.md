# 本地评测说明

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

输出完整 JSON：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock --json
```

只跑单一任务类型：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock --task-type competition_recommendation
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

单条 case 还会输出：

- `passed`
- `status`
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

## 测试入口

基础回归测试：

- `backend/app/tests/test_eval_regression.py`

该测试会验证：

- 3 类任务样例数量
- mock 模式下全量回归通过
- 平均质量分数高于最低基线
