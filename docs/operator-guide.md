# Operator Guide

## 启动方式

后端：

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 推荐的演示顺序

1. 先用前端 Agent 面板演示 Simple / Advanced 输入
2. 展示 `status / events / artifacts / history`
3. 展示 `requested_runtime_mode / effective_runtime_mode / provider_success_path / used_mock_fallback`
4. 最后再演示 `retry / review`

## 如何解释完成状态

演示时不要把所有 `completed` 都说成“Ark 成功”。

请按下面规则解释：

- `effective_runtime_mode=agents_sdk` + `provider_success_path=structured`
  - Ark structured 直出成功
- `effective_runtime_mode=agents_sdk` + `provider_success_path=plain_json_fallback`
  - Ark JSON fallback 成功，但不是 structured 直出
- `used_mock_fallback=true`
  - provider 失败，mock 补全完成

## recommendation-003 专项复现

本轮最重要的长尾 case 是 `recommendation-003`。

本地复现命令：

```bash
backend\.venv\Scripts\python backend/scripts/debug_agents_sdk_case.py --case-id recommendation-003 --path both --json
```

看点：

- structured 是否还能复现旧的 `Max turns + timeout` 组合
- `provider_success_path` 最终是什么
- turn 摘要里有没有重复 tool loop

当前最新实测下：

- `recommendation-003` 的主路径已经是 `provider_success_path=structured`
- 如果强制跑 `--path both`，plain JSON fallback 支路仍可能单独超时；这不影响主路径已恢复

## 评测命令

mock 基线：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock
```

真实 Ark spot check：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval_agents_sdk.py --sample-per-task-type 3
```

## 浏览器级验证

前端最小浏览器 smoke：

```bash
cd frontend
npm run test:e2e
```

当前 smoke 覆盖：

- recommendation happy path
- review 失败 detail 展示

## CI 说明

仓库内已经有最小 CI workflow：

- 默认 matrix：`windows-latest` + `ubuntu-latest`
- 默认内容：后端关键回归、前端 build、Linux Playwright smoke
- 手动触发内容：
  - `agents_sdk` spot check
  - 单 case `agents_sdk` debug（默认 `recommendation-003`）

如果要远端验证 recommendation 长尾 case，请优先使用 workflow_dispatch 的单 case debug job，而不是每次都跑全量真实评测。
当前公开 GitHub API 对 `origin` 还没有返回任何 workflow run 记录，因此“远端 CI 已配置”不等于“远端已经产生 green 证据”。
