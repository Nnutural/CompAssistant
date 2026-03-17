# Data Sources

本页描述 Phase 5H 之后，本地知识体系如何覆盖研究方案中的 10 类内容类别，以及每类当前采用的接入方式。

## 1. 渠道层

渠道与内容类别分开建模。

| Channel | 含义 | 本轮状态 |
| --- | --- | --- |
| `public_web` | 互联网公开静态网页 | implemented |
| `wechat_official_account` | 微信公众号文章文本导入 | importer |
| `manual_import` | 人工整理的 JSON/CSV 导入 | importer |
| `local_file` | 本地 Markdown/TXT/JSON 文件 | implemented / importer |

## 2. 10 类内容类别覆盖表

| 内容类别 | 当前主策略 | 当前状态 | 当前最小来源 |
| --- | --- | --- | --- |
| 国家政策 | `static_http_source` | implemented | 教育部大学生创新创业指导意见公开页 |
| 法律法规 | `static_http_source` | implemented | 国家自然科学基金条例公开页 |
| 社会热点 | `structured_importer` | importer | `social_hotspots.json` |
| 就业招聘 | `static_http_source` | implemented | 教育部高校毕业生就业创业工作通知 |
| 基金指南 | `static_http_source` | implemented | NSFC 项目指南公开页 |
| 获批项目 | `static_http_source` | implemented | 高校公开立项/获批项目通知页 |
| 竞赛信息 | `structured_importer` + `static_http_source` | implemented | `competitions.json` + 教育部竞赛通知页 |
| 获奖作品 | `structured_importer` | importer | `award_winning_works.csv` |
| 优秀模板 | `file_importer` | importer | `excellent_template.md` |
| 经验分享 | `file_importer` + `manual_curated_source` | importer | `experience_sharing.txt` + `wechat_article_experience.md` |

## 3. 当前真实静态源

以下来源已通过 `http_provider -> normalize_pipeline -> file_system_store -> sqlite_index_store` 实际进入本地知识闭环：

- 国家政策：`https://www.moe.gov.cn/jyb_xwfb/s6052/moe_838/202110/t20211013_571912.html`
- 法律法规：`https://www.nsfc.gov.cn/p1/2871/2873/69510.html`
- 就业招聘：`https://www.moe.gov.cn/srcsite/A15/s3265/202411/t20241112_1162526.html`
- 基金指南：`https://www.nsfc.gov.cn/p1/3381/2824/79214.html`
- 获批项目：`https://jwc.xjtu.edu.cn/info/1216/4162.htm`
- 竞赛信息：`https://www.moe.gov.cn/srcsite/A08/moe_742/s7172/s5644/201109/t20110930_171579.html`

## 4. 当前 importer 来源

- `backend/data/local_knowledge_imports/phase5h/social_hotspots.json`
- `backend/data/local_knowledge_imports/phase5h/award_winning_works.csv`
- `backend/data/local_knowledge_imports/phase5h/excellent_template.md`
- `backend/data/local_knowledge_imports/phase5h/experience_sharing.txt`
- `backend/data/local_knowledge_imports/phase5h/wechat_article_experience.md`

说明：

- 微信公众号渠道只支持导入用户已有文本/Markdown/JSON。
- 本轮没有实现公众号自动抓取。

## 5. 当前本地知识样例构建脚本

脚本：`backend/scripts/build_local_knowledge_demo.py`

脚本会：

- 拉取 6 个公开静态网页来源
- 读取 `competitions.json` 的最小竞赛样例
- 导入 JSON/CSV/Markdown/TXT 样例
- 将全部内容写入 `backend/data/local_knowledge/`

## 6. 明确不做的来源

- 登录站点
- 验证码站点
- 代理和反爬绕过
- Playwright 动态抓取主线
- 多站点调度器
- 智能体直接读取 raw 文件或原始网页
