# Task Types

## 当前主任务

### 1. `competition_recommendation`

输入：

- 用户画像 `profile`
- 方向
- 年级
- 能力标签
- 偏好标签

输出：

- `profile_summary`
- `recommendations`
- `risk_overview`

典型用途：

- 给学生推荐更适合当前能力与偏好的竞赛列表

### 2. `competition_eligibility_check`

输入：

- `competition_id`
- 用户画像 `profile`

输出：

- `competition_name`
- `eligibility_label`
- `is_eligible`
- `missing_conditions`
- `attention_points`
- `rationale`

典型用途：

- 判断某个学生是否适合参加指定竞赛

### 3. `competition_timeline_plan`

输入：

- `competition_id`
- `deadline`
- 用户约束 `constraints`

输出：

- `preparation_checklist`
- `milestones`
- `stage_plan`
- `reverse_schedule`

典型用途：

- 围绕指定 DDL 生成准备清单与倒排计划

## legacy 兼容任务

### `research_plan`

- 仍保留兼容
- 仍可通过旧 `research-runtime` 路由运行
- 不再作为新的前端主接入路径

## API 创建示例

```json
{
  "task_type": "competition_recommendation",
  "objective": "Recommend competitions for a freshman algorithm student.",
  "payload": {
    "profile": {
      "direction": "算法/编程",
      "grade": "freshman",
      "ability_tags": ["algorithms", "cpp"],
      "preference_tags": ["team"]
    }
  },
  "dry_run": false
}
```
