# Git 跟踪说明

本文件用于说明哪些内容通常应该提交到 Git，哪些内容通常应保留在本地。

## 建议提交到 Git

- `backend/` 与 `frontend/` 下的源代码。
- `docs/` 下的文档。
- `.codex/` 下的占位运行说明文档。
- `.codex/skills/` 下的技能定义。
- `docs/schemas/` 下的 JSON Schema。
- `backend/.env.example`、`frontend/.env.example` 这类环境变量样例文件。
- 仓库当前工作流已经使用的 lockfile 与依赖清单文件。
- `.gitignore`、`AGENTS.md` 和本文件这类仓库策略文件。

## 建议不要提交到 Git

- `.env` 文件中的真实密钥和凭证。
- `backend/.venv/` 这类虚拟环境目录。
- `frontend/node_modules/` 这类前端安装产物。
- `dist/`、`build/`、覆盖率报告和缓存等构建输出。
- 仅供个人使用的本地 IDE 配置。
- 运行日志、调试导出、临时文件和本地生成的测试产物。

## 规则来源

- 当前根目录 `.gitignore` 仍然是实际忽略规则的唯一执行来源。
- 如果后续需要调整忽略行为，应单独、有意识地更新 `.gitignore`。
