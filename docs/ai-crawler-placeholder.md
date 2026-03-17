# AI Crawler Placeholder

仓库当前已经不是“纯空壳 crawler scaffold”，但也还远没有变成完整 crawler 平台。

## 当前已经实现的最小能力

- 10 类内容类别 taxonomy
- 渠道层 taxonomy
- source manifest
- 严格三层 schema：
  `RawDocument` / `NormalizedDocument` / `KnowledgeRecord`
- 公开静态 HTTP provider
- JSON / CSV / Markdown / TXT importer
- 微信公众号文章手动导入器
- 文件系统 raw / normalized 存储
- SQLite + FTS5 本地索引
- retrieval service
- 2 个 feature-flagged agent grounding 路径

## 当前明确没有实现的能力

- 通用多站点 crawler 平台
- 调度与增量抓取
- Playwright 动态渲染抓取主线
- 登录、验证码、代理、反爬绕过
- 公众号自动抓取
- 前端 crawler UI
- 将 crawler 直接并入主 runtime 主路径

## 当前真实边界

- crawler / retrieval 仍是实验性服务边界
- 只抓公开静态页面
- 难源优先通过 importer 进入体系
- 智能体只读 retrieval 结果
- placeholder 仍然是 placeholder，不会伪装成 implemented

## 未来扩展顺序

如果后续继续做 crawler，只能按以下顺序扩：

1. 单个来源适配
2. 单个验证路径
3. 单个 retrieval 消费者
4. 再考虑更广的 crawler 平台能力
