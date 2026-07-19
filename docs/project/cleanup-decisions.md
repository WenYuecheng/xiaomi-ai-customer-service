# 文件整合与保留决策

本文档记录 2026-07-19 最终交付整理的实际决定，不再作为待执行建议。

## 已完成的整理

- 5 份原始需求与排期文档已从根目录移动到 `docs/planning/`。
- Jira CSV 已移动到 `jira/Jira_Epic_Stories导入表.csv`。
- 3 张无语义文件名的历史图片已移动到 `docs/screenshots/`，改为稳定证据编号。
- 4 份新增项目说明已归档到 `docs/project/`。
- 根目录只保留 README、环境模板、Git/Docker 配置和 Compose 编排。

## 明确保留

| 资产 | 保留原因 |
|---|---|
| `backend/uv.lock` | 后端依赖精确复现，Docker 构建使用 `--frozen` |
| `frontend/pnpm-lock.yaml` | 前端依赖精确复现 |
| `scripts/collect_official_knowledge.py` | 62 份正式资料的可重建工具 |
| `scripts/build_extended_evaluation.py` | 114 问扩展评测的生成工具 |
| 两套 evaluation CSV | 30 问快速基线和 114 问扩展验证职责不同 |
| `data/knowledge/official/` | 正式知识库源码与真实引用依据 |
| `docs/superpowers/` | 设计、计划和 AI 辅助开发证据 |
| API/database/deployment 文档 | 内容职责不同，模块化入口更容易维护 |
| 三张历史图片 | 保留课程验收过程证据，不猜测图片业务含义 |

## 不纳入 Git

`.gitignore` 排除以下可生成或敏感内容：

```text
.env
.DS_Store
.coverage、htmlcov/
.venv/、__pycache__/、.pytest_cache/、.ruff_cache/
node_modules/、dist/、*.tsbuildinfo、自动生成 *.d.ts
data/app.db、data/uploads/、data/chroma/、data/models/、data/logs/
```

目录中的 `.gitkeep` 只用于保留空目录结构。

## 未采用的建议

- **不删除 `uv.lock`**：锁文件是可复现构建的一部分，不是缓存。
- **不合并两套评测集**：扩展集覆盖面更大，但基础集适合快速课程回归。
- **不删除一次性脚本**：知识与评测资产必须能够说明来源并重新构建。
- **不把 API、数据库、部署文档合成一个大文件**：职责分离比减少文件数量更重要。
- **不删除 `docs/superpowers/`**：其中内容是经过确认的设计与实施记录，而非运行时缓存。

## 后续清理规则

新增文件前先判断它属于源码、可复现输入、文档证据还是运行时输出。只有运行时输出和可重新下载的
缓存应被忽略；对历史证据的删除必须先确认其不再承担需求追踪或答辩用途。
