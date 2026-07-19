# 小米智能客服机器人 — 文件整合与删除建议

本文档梳理可安全删除、建议移动或整合的文件，供最终交付前的清理参考。

> **注意**：以下均为建议，不涉及代码逻辑改动，操作前请确认已完成所有验收。

---

## 第一类：建议直接删除

这些文件不属于任何功能代码，对运行、测试、文档均无贡献。

### 1. 根目录散落的截图/图片文件

| 文件 | 原因 |
|------|------|
| `2fee0dd447a8022d0f82667a9c9b6b72.jpg` | 命名无语义，属于临时截图，建议移入 `docs/screenshots/` 或直接删除 |
| `9de7bcd869fe84ecc842f8108e40f6d8.png` | 同上 |
| `c10043f0cf2dec3e5aee281a2d89784e.jpg` | 同上 |

**建议操作**：若为验收截图证据，移动到 `docs/screenshots/` 并改为语义化文件名；否则直接删除。

### 2. 开发工具自动生成文件（不应纳入 Git）

| 文件/目录 | 原因 |
|------|------|
| `backend/.DS_Store` | macOS 系统文件，已在 .gitignore 中，应从 Git 追踪中移除 |
| `frontend/.DS_Store` | 同上 |
| `.DS_Store`（根目录） | 同上 |
| `frontend/tsconfig.app.tsbuildinfo` | TypeScript 编译缓存，不需提交 |
| `frontend/tsconfig.node.tsbuildinfo` | 同上 |
| `frontend/auto-imports.d.ts` | 由 unplugin-auto-import 自动生成，每次构建会重新生成 |
| `frontend/components.d.ts` | 由 unplugin-vue-components 自动生成，同上 |
| `backend/.ruff_cache/` | Ruff 工具缓存，不需提交 |
| `.ruff_cache/`（根目录） | 同上 |
| `backend/.pytest_cache/` | pytest 缓存，不需提交 |
| `backend/.coverage` | 覆盖率报告数据文件，不需提交 |
| `.coverage`（根目录若存在） | 同上 |
| `frontend/dist/` | 前端构建产物，不需提交（Docker 内构建） |
| `frontend/node_modules/` | 依赖包，不需提交 |
| `backend/.venv/` | Python 虚拟环境，不需提交 |
| `backend/uv.lock` | 可选保留（便于复现），但 Docker 内无需 |
| `.pnpm-store/` | pnpm 全局缓存，不需提交 |
| `data/app.db` | 运行时数据库，属于持久化数据，不应提交 |

---

## 第二类：建议移动/合并整合（不删除，仅重组织）

### 1. 根目录规划文档过多，建议统一移至 `docs/planning/`

当前根目录存在 6 个规划类文档，建议整合到 `docs/planning/` 目录：

| 当前位置 | 建议移动到 |
|---------|-----------|
| `客服机器人.docx` | `docs/planning/01_早期需求草稿.docx` |
| `小米智能客服机器人_13天需求分析与Jira实施方案.docx` | `docs/planning/02_13天需求分析与Jira实施方案.docx` |
| `小米智能客服机器人_技术栈项目结构与11天实施计划.docx` | `docs/planning/03_技术栈与11天实施计划.docx` |
| `小米智能客服机器人_10天实施计划.md` | `docs/planning/04_10天实施计划.md` |
| `必须做到要求.docx` | `docs/planning/05_必须做到要求.docx` |
| `小米智能客服机器人_Jira_Epic_Stories导入表.csv` | `jira/Jira_Epic_Stories导入表.csv` |

**理由**：根目录应只保留启动和理解项目必须的文件（README、docker-compose、.env.example 等），规划文档是开发过程产物。

### 2. `data/evaluation/questions-expanded.csv` 可考虑合并

| 文件 | 说明 |
|------|------|
| `data/evaluation/questions.csv` | 30 条基础回归集（脚本默认使用） |
| `data/evaluation/questions-expanded.csv` | 扩展版（更多问题） |

**建议**：如果扩展版已完全覆盖基础版内容，可以将 `questions.csv` 重命名为 `questions-basic.csv`，或直接将 `questions-expanded.csv` 重命名为 `questions.csv` 作为唯一的回归集。

### 3. `docs/` 各子目录仅有 README，可合并为一个文档

当前 `docs/api/`、`docs/database/`、`docs/deployment/` 各目录只有一个 README.md，内容简单（指向代码或 Swagger）。建议：

- 将这三个 README.md 合并为 `docs/REFERENCES.md`，一个文件集中说明文档入口。
- 删除三个空目录（保留 `docs/requirements/` 和 `docs/testing/` 不变，这两个有实质内容）。

### 4. `docs/superpowers/` 目录

该目录（若存在实际文件）属于 AI 辅助工具配置，不是项目功能代码，建议：

- 移至 `.superpowers/`（已存在于根目录）中统一管理，或直接删除。

---

## 第三类：暂时保留，验收后可酌情删除

| 文件 | 说明 |
|------|------|
| `scripts/collect_official_knowledge.py` | 知识采集辅助脚本，一次性使用，不影响运行 |
| `scripts/build_extended_evaluation.py` | 扩展评测集构建脚本，评测完成后可归档 |
| `jira/README.md` | 内容简短，可合并到主 README 或 docs/requirements/traceability.md |

---

## 清理后的理想根目录结构

```
robot/
├── backend/            # 后端（保持不变）
├── frontend/           # 前端（保持不变）
├── data/               # 数据（仅保留 samples/ 和 evaluation/，其余运行时生成）
├── docs/               # 文档（planning/ + requirements/ + testing/ + screenshots/）
├── scripts/            # 脚本（仅保留 ingest_samples.py 和 run_rag_evaluation.py）
├── jira/               # Jira 证据（含 CSV 导入表）
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## .gitignore 补充建议

确认 `.gitignore` 包含以下规则（如未覆盖请补充）：

```gitignore
# macOS
.DS_Store

# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/
.coverage

# Node
node_modules/
dist/
*.tsbuildinfo
auto-imports.d.ts
components.d.ts
.pnpm-store/

# 运行时数据（不提交到 Git）
data/app.db
data/uploads/
data/chroma/
data/models/
data/logs/

# 密钥
.env
```
