# 当前状态

## Phase 5G 快照

当前仓库不是从零开始的 agent 原型，而是已经完成到 Phase 5G 的竞赛助手后端与最小前端面板。

系统当前已经具备：

- Ark-only agent runtime
- 3 类主任务：
  - `competition_recommendation`
  - `competition_eligibility_check`
  - `competition_timeline_plan`
- `task / run / events / artifacts` API
- 历史列表、`retry / cancel / review`
- 前端 `Simple / Advanced` 双模式输入
- `requested_runtime_mode / effective_runtime_mode / effective_model / used_mock_fallback / fallback_reason` 可观测
- `agents_sdk` 专用评测入口
- 最小浏览器 E2E
- 最小 CI matrix

## 5G 的核心修复

本轮优先处理的是 `recommendation-003`。

修复前的原始失败链路：

- `competition_recommendation` 的 structured 路径触发 `Max turns ... exceeded`
- 后续 provider-side plain JSON fallback 又触发 `Runner call timed out after 45.0s`
- 最终只能依赖 mock fallback，因此不是 direct success

修复后的关键变化：

- recommendation 的 provider grounding 改成单一、紧凑的本地过滤工具
- recommendation prompt 进一步收紧，只允许输出 canonical artifact 所需字段
- recommendation output drift 在进入严格校验前做最小 normalization
- SDK session id 变成“每次运行唯一”，避免 SQLite session 复用旧对话污染 spot check

当前最新实测下，`recommendation-003` 已可在真实 `agents_sdk` 路径上完成：

- `strict_mode=True`
- `effective_runtime_mode=agents_sdk`
- `used_mock_fallback=false`
- `provider_success_path=structured`

当前最新的 `agents_sdk` 3x3 spot check 结果是：

- `direct_success_rate=1.000`
- `structured_direct_success_rate=1.000`
- `mock_fallback_success_rate=0.000`

这说明本轮优先处理的 `recommendation-003` 主路径问题已经不再阻塞小样本直出。

## 当前成功语义

不要再把所有 `completed` 都解释成“Ark 直出成功”。

正确解释方式是：

- `effective_runtime_mode=agents_sdk` + `provider_success_path=structured`
  - Ark structured 直出成功
- `effective_runtime_mode=agents_sdk` + `provider_success_path=plain_json_fallback`
  - Ark structured 失败，但 provider-side JSON fallback 收敛成功
- `used_mock_fallback=true`
  - provider 失败，mock 补全完成

## 当前已知限制

- `queued / running` 仍不支持跨重启恢复
- `attachments` 仍只记录到 `payload.attachments`，runtime 不消费
- 一些 case 仍会出现 provider parse issue，但现在会被明确记录，不再默默混成 mock 成功
- 远端 GitHub Actions workflow 已入库；当前公开 GitHub API 对 `origin` 返回的是 `0 workflows / 0 workflow runs`，说明远端实证记录还没有出现
