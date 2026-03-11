# 本地评测说明

## 评测入口

仓库现在有两条必须分开看的评测路径：

- mock 基线回归
- `agents_sdk` 真实 Ark 路径 spot check

命令：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock
backend\.venv\Scripts\python backend/scripts/run_eval_agents_sdk.py --sample-per-task-type 3
```

如果要专门复现 `recommendation-003`：

```bash
backend\.venv\Scripts\python backend/scripts/debug_agents_sdk_case.py --case-id recommendation-003 --path both --json
```

## 成功路径定义

评测里当前区分 4 种核心结果：

- `structured_direct_success_rate`
  - 真实 Ark structured 输出直接完成
- `json_fallback_success_rate`
  - 真实 Ark structured 失败，但 provider-side plain JSON fallback 完成
- `mock_fallback_success_rate`
  - 真实 provider 失败后由 mock 完成
- `hard_failure_rate`
  - 最终仍落在 `failed / cancelled`

`direct_success_rate` 的语义是：

- `structured_direct_success_rate + json_fallback_success_rate`

## recommendation-003 修复后的重点观察

修复前：

- structured 路径可能卡在 `Max turns ... exceeded`
- plain JSON fallback 可能继续 `Runner call timed out`
- 最终进入 mock fallback

修复后，优先观察：

- `provider_success_path`
- `used_mock_fallback`
- `error_bucket_counts`
- `structured_parse_error_count / json_fallback_parse_error_count`
- `timeout_error_count`

当前最新本地 spot check：

- `recommendation-003` 在 `structured` 路径下可直接完成
- 3 类任务各 3 条样本的最新结果为：
  - `direct_success_rate=1.000`
  - `structured_direct_success_rate=1.000`
  - `json_fallback_success_rate=0.000`
  - `mock_fallback_success_rate=0.000`

如果 `recommendation-003` 重新回退到 mock，优先检查：

1. 是否又出现旧 session 复用
2. recommendation 工具输出是否被放大或重新引入多工具循环
3. provider 是否出现新的可用性问题

## 错误分桶

当前主分桶：

- `schema_compatibility_error`
- `provider_exception`
- `parse_error`
- `validation_error`
- `fallback_to_mock`
- `hard_failed`

当前还额外统计：

- `structured_parse_error_count`
- `json_fallback_parse_error_count`
- `post_normalization_validation_issue_count`
- `timeout_error_count`

这意味着现在不需要只靠人工翻日志判断“Ark 不稳定”，而是可以直接看：

- 哪一类错误最多
- recommendation 热修复后哪些桶下降了
- mock fallback 是否真的减少了

## 输出解读

mock 评测应主要看：

- 全量通过率
- artifact 完整度
- 质量分是否退化

`agents_sdk` spot check 应主要看：

- `structured_direct_success_rate`
- `json_fallback_success_rate`
- `mock_fallback_success_rate`
- `hard_failure_rate`
- `avg_latency_ms`
- `p95_latency_ms`
- 主要错误桶和示例
