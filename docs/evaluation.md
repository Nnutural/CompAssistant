# Evaluation

## 数据集位置

本地评测样例位于：

- `backend/data/evals/competition_recommendation.json`
- `backend/data/evals/competition_eligibility_check.json`
- `backend/data/evals/competition_timeline_plan.json`

每条 case 至少包含：

- `id`
- `task_type`
- `input`
- `expected_required_fields`
- `scoring_rubric`
- `optional_notes`

## 当前覆盖

- `competition_recommendation`：10 条
- `competition_eligibility_check`：10 条
- `competition_timeline_plan`：10 条

## 运行方式

### 命令行运行

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock
```

### 输出完整 JSON 报告

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock --json
```

### 仅跑某一类任务

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock --task-type competition_recommendation
```

## 结果判定

每条 case 会输出：

- 是否通过
- 最终状态
- 缺失字段列表
- warning 列表
- 结果摘要

当前通过标准：

- 任务未进入 `failed`
- `expected_required_fields` 全部存在且非空

## 测试入口

基础回归测试位于：

- `backend/app/tests/test_eval_regression.py`

该测试会验证：

- 数据集总量与任务覆盖
- mock 模式下全量回归无失败 case
