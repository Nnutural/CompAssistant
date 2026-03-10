# Phase 5C-mini / 5D-lite Demo

当前推荐把这份文档作为最小演示入口使用。`docs/demo-phase5b.md` 保留历史定位，不再作为当前主流程。

## Demo Checklist

- 后端已启动
- 前端已启动
- 若需要稳定演示，后端运行在 `RESEARCH_RUNTIME_MODE=mock`
- 浏览器打开后可访问 Agent 面板
- 最近任务列表可读取
- `frontend/e2e/fixtures/agent-demo-cases.json` 可用

## 固定演示样例

### 1. recommendation-001

- 任务类型：`competition_recommendation`
- 输入模式：`simple`
- 预期状态：`completed`

重点观察：

- 提交前能看到 objective 预览
- payload 预览里能看到 `profile.ability_tags`
- 创建后能立即拿到 `run_id`
- 事件时间线持续推进
- 完成后 artifacts 出现
- 可以执行一次 `retry`

### 2. eligibility-009

- 任务类型：`competition_eligibility_check`
- 输入模式：`simple`
- 预期状态：`awaiting_review`

重点观察：

- 竞赛搜索建议列表能明确给出 `全国大学生智能汽车竞赛 (#10)`
- 页面会显示最终提交的 `competition_id`
- 历史列表可以筛出 `待审核`
- 可以演示 `review_accept / review_reject / review_annotate`

### 3. timeline-001

- 任务类型：`competition_timeline_plan`
- 输入模式：`simple`
- 预期状态：`completed`

重点观察：

- 竞赛搜索建议列表会把 `中国软件杯大学生软件设计大赛 (#24)` 放到前面
- payload 预览里能看到 `deadline` 和 `constraints.available_hours_per_week`
- artifacts 中能看到时间线计划结果

## 录屏 / 答辩推荐顺序

1. 打开首页，先展示 `竞赛列表` 页面仍然可用。
2. 切到 `智能体面板`。
3. 用 `recommendation-001` 展示 Simple Mode：
   - 填表
   - 看 objective / payload 预览
   - 切到 Advanced Mode，确认 JSON 可见
   - 创建任务
4. 展示当前任务区、事件时间线、artifacts。
5. 展示最近任务列表，并执行一次 `retry`。
6. 再切回 `竞赛列表`，证明原页面未受影响。
7. 如需补“人工审核”叙事，再用 `eligibility-009` 演示待审核与 `review`。

## 截图点位

- Simple Mode 的 payload 预览
- Advanced Mode 的 JSON 编辑器
- 当前任务状态卡
- 事件时间线
- artifacts 结果区
- 最近任务列表
- retry 后生成的新 run_id

## 演示证据资产

- 固定样例：`frontend/e2e/fixtures/agent-demo-cases.json`
- 浏览器 smoke：`frontend/e2e/agent-panel.spec.ts`
- 运行配置：`frontend/playwright.config.ts`

## 注意事项

- 当前 attachments 只是 `payload.attachments` 元数据入口，不代表完整多模态消费。
- 当前浏览器 smoke 只自动覆盖 recommendation happy path 与一次 retry。
- 本轮没有重构 runtime，也没有改 task API。
