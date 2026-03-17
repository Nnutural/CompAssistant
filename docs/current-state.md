# Current State

## 1. 主系统状态

主系统仍然是现有 competitions API、agent runtime、task API 和前端任务流。

保持不变的路径：

- competitions API
- mock runtime 和 Agents SDK runtime
- task history / retry / cancel / review 流程
- 前端主任务表单和结果展示

## 2. Phase 5H 新增但隔离的本地知识能力

当前已经具备：

- 三层统一数据模型：
  `RawDocument` / `NormalizedDocument` / `KnowledgeRecord`
- 10 类内容类别 taxonomy
- 渠道层 taxonomy：
  `public_web` / `wechat_official_account` / `manual_import` / `local_file`
- 公开静态 HTTP provider
- JSON / CSV / Markdown / TXT importer
- 本地文件系统 raw / normalized 存储
- SQLite + FTS5 检索
- retrieval service：
  `search_documents()` / `get_document()`
- 两个 feature-flagged agent grounding 路径：
  `eligibility-checker` 和 `competition-recommender`

## 3. 当前覆盖范围

- 10 类内容类别都已进入代码、manifest 和文档结构
- 6 类具备真实公开静态网页来源：
  国家政策、法律法规、就业招聘、基金指南、获批项目、竞赛信息
- 其余类别通过 importer 进入同一条本地知识链路：
  社会热点、获奖作品、优秀模板、经验分享
- 微信公众号渠道仅支持手动导入已有文章文本，不支持自动抓取

## 4. 当前仍然没有实现

- 完整 crawler 平台
- 多站点调度
- 浏览器动态渲染抓取
- 登录与验证码处理
- 代理和反爬绕过
- 将 crawler 直接接入主任务流
- 面向前端的新 crawler 页面

## 5. 当前结论

仓库已经达到“全类别覆盖的数据源扩展”最小原型：

- 不是所有类别都自动抓取
- 但所有类别都已有 taxonomy / manifest / code / docs 对应项
- 并且每一类至少有一种可落地接入方式
