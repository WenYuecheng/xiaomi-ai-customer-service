# 项目结构、完整 README 与详细注释整理实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保持全部代码功能与可复现资产的前提下，规范详细注释、整理项目目录、生成准确完整的 README 和说明文档，并通过全量验收后推送 GitHub 主分支。

**Architecture:** 以现有 FastAPI/Vue 模块化单体为唯一代码真相源。注释变更通过 Ruff 和去除文档字符串后的 AST 对比约束为非功能性变更；目录整理使用 Git 重命名保留历史；README 和四份说明文件由代码、CLI 参数、测试输出和实际文件清单反向校验。

**Tech Stack:** Python 3.11、FastAPI、SQLAlchemy、Alembic、pytest、Ruff、Vue 3、TypeScript、Vitest、Vite、Docker Compose、Git。

## Global Constraints

- 不删除功能代码、锁文件、62 份正式知识资料、10 份基础样本、两套评测集、构建脚本或设计证据。
- 不提交 `.env`、API 密钥、SQLite、Chroma、上传文件、模型缓存、虚拟环境、Node 依赖或构建产物。
- 除恢复 `stream_prepared_chat` 的 `not prepared.requires_generation` 判断外，注释整理不得改变 Python 业务语义。
- Python 代码必须满足 Ruff 100 字符行长与当前 lint 规则。
- 所有文档命令、接口、路径、数量和测试结果必须由当前仓库实际状态验证。

---

### Task 1: 修复注释引入的语义回归并规范 Python 注释

**Files:**
- Modify: `backend/app/chat/service.py`
- Modify: `backend/app/**/*.py`
- Modify: `backend/alembic/**/*.py`
- Modify: `backend/tests/**/*.py`
- Test: `backend/tests/test_chat.py`

**Interfaces:**
- Consumes: 现有 `PreparedChat.requires_generation: bool` 与 `Message.content: str`。
- Produces: 业务语义与 `main@2651efe` 一致、仅增加中文说明的 Python 源码。

- [ ] **Step 1: 建立语义基线并复现格式失败**

运行：

```bash
backend/.venv/bin/ruff format --check backend/app backend/tests
backend/.venv/bin/ruff check backend/app backend/tests
```

预期：当前详细注释触发格式差异、尾随空格或 E501，证明验证能够捕获问题。

- [ ] **Step 2: 恢复被误改的生成边界**

将 `backend/app/chat/service.py` 中的分支恢复为：

```python
if not prepared.requires_generation:
    for index in range(0, len(prepared.message.content), 12):
        if is_cancelled():
            return
        yield prepared.message.content[index : index + 12]
    return
```

- [ ] **Step 3: 运行 Ruff 自动格式化并人工修正剩余注释**

运行：

```bash
backend/.venv/bin/ruff format backend/app backend/tests
backend/.venv/bin/ruff check backend/app backend/tests
```

对自动格式化后仍超过 100 字符的中文说明手工换行；不得使用 lint 忽略隐藏问题。

- [ ] **Step 4: 验证注释没有引入额外语义变化**

解析 `HEAD` 与工作区全部变更 Python 文件，删除模块、类和函数首个字符串表达式后比较 `ast.dump(..., include_attributes=False)`。预期仅 `backend/app/chat/service.py` 因恢复用户误改与工作区原状态不同；再以 `main@2651efe` 为功能基线确认恢复后的业务 AST 相同。

- [ ] **Step 5: 运行聊天回归并提交**

运行：

```bash
backend/.venv/bin/pytest backend/tests/test_chat.py -q
```

预期：聊天测试全部通过。

提交：

```bash
git add backend/app backend/alembic backend/tests
git commit -m "docs(backend): add verified Chinese code documentation"
```

### Task 2: 整理根目录与验收资产

**Files:**
- Create: `docs/planning/`
- Create: `docs/screenshots/`
- Create: `docs/project/`
- Move: 根目录 5 份规划文档到 `docs/planning/`
- Move: 根目录 Jira CSV 到 `jira/Jira_Epic_Stories导入表.csv`
- Move: 根目录 3 张图片到 `docs/screenshots/`
- Move: 根目录 4 份新增说明到 `docs/project/`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: 规格中已确认的文件映射。
- Produces: 根目录仅保留应用入口文件，历史资产通过 Git 重命名保留。

- [ ] **Step 1: 核对所有移动源文件唯一存在**

运行 `git status --short`、`git ls-files` 和根目录文件列表，确认每个源文件只对应一个目标文件，目标文件尚不存在。

- [ ] **Step 2: 创建目录并执行 Git 重命名**

按设计规格中的映射移动 5 份规划文档、Jira CSV 和 3 张截图。四份未跟踪 Markdown 使用以下目标：

```text
docs/project/requirements-and-status.md
docs/project/structure.md
docs/project/cleanup-decisions.md
docs/project/readme-source.md
```

- [ ] **Step 3: 保留可复现资产并强化忽略规则**

确认 `.gitignore` 覆盖 `.DS_Store`、`*.tsbuildinfo`、自动生成声明、运行时数据和密钥；不得忽略 `uv.lock`、`pnpm-lock.yaml`、`data/knowledge/official/` 或 `data/evaluation/`。

- [ ] **Step 4: 验证结构并提交**

运行：

```bash
git diff --check
git status --short
```

提交：

```bash
git add .gitignore docs/planning docs/screenshots docs/project jira
git commit -m "chore: organize project documentation and evidence"
```

### Task 3: 修正四份项目说明并生成完整 README

**Files:**
- Modify: `README.md`
- Modify: `docs/project/requirements-and-status.md`
- Modify: `docs/project/structure.md`
- Modify: `docs/project/cleanup-decisions.md`
- Modify: `docs/project/readme-source.md`
- Modify: `docs/requirements/traceability.md`
- Modify: `jira/README.md`

**Interfaces:**
- Consumes: FastAPI 路由、`scripts/ingest_samples.py` CLI、`.env.example`、文件清单和测试输出。
- Produces: 可直接从零启动和验收的主 README，以及与代码一致的四份归档说明。

- [ ] **Step 1: 修正文档事实偏差**

明确写入：

```text
注册：POST /api/v1/auth/register
账号：/api/v1/account/*
画像 composable：frontend/src/composables/useAccountDashboard.ts
检索：70% 向量分 + 30% jieba 词法分，并取强词法分兜底
知识资料：10 份基础样本 + 62 份正式公开资料
评测：questions.csv 为 30 问基线；questions-expanded.csv 为 114 问扩展集
```

- [ ] **Step 2: 用准确命令重写根 README**

批量导入命令使用脚本真实接口：

```bash
INGEST_PASSWORD='你的运营账号密码' \
backend/.venv/bin/python scripts/ingest_samples.py \
  --base-url http://127.0.0.1:8000/api/v1 \
  --knowledge-base-name 小米产品公开资料
```

README 同时列出 Docker、本地开发、模型配置、资料导入、页面/API、测试、目录导航、安全边界和已知限制，并链接实际 GitHub 仓库。

- [ ] **Step 3: 更新全部移动引用**

使用 `rg` 搜索旧文件名和旧根路径，更新需求追踪矩阵、Jira 说明及其他文档中的引用，确保没有断链。

- [ ] **Step 4: 文档一致性检查并提交**

运行：

```bash
rg -n "useProfile|BM25|--knowledge-base-id|版本不限" README.md docs jira
git diff --check
```

预期：无已知错误描述或空白错误。

提交：

```bash
git add README.md docs/project docs/requirements jira/README.md
git commit -m "docs: publish complete verified project guide"
```

### Task 4: 全量质量、Docker 与公开发布验收

**Files:**
- Modify: `docs/testing/test-report.md`

**Interfaces:**
- Consumes: 完成后的所有代码和文档。
- Produces: 可复核的最终测试报告与公开 GitHub 主分支。

- [ ] **Step 1: 后端全量验证**

运行：

```bash
backend/.venv/bin/ruff format --check backend/app backend/tests scripts
backend/.venv/bin/ruff check backend/app backend/tests scripts
backend/.venv/bin/pytest backend/tests --cov=app
```

预期：Ruff 零错误、pytest 零失败、覆盖率不低于 87%。

- [ ] **Step 2: 前端全量验证**

运行：

```bash
cd frontend
pnpm test -- --run
pnpm build
```

预期：Vitest 零失败、Vue TypeScript 检查和 Vite 构建成功。

- [ ] **Step 3: Docker 验证**

运行：

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8000/api/v1/health
```

预期：后端 healthy、前端 running、健康接口返回 `status=ok`。

- [ ] **Step 4: 安全与结构验收**

运行已跟踪文件凭据模式扫描、`git diff --check`、根目录结构检查和旧路径搜索。扫描只允许 `.env.example`、README 中明确的占位值，不允许真实 `sk-` 密钥或 JWT 密钥。

- [ ] **Step 5: 更新报告并提交**

将实际测试数量、覆盖率、构建和 Docker 结果写入 `docs/testing/test-report.md`，提交：

```bash
git add docs/testing/test-report.md
git commit -m "docs: record final structure acceptance"
```

- [ ] **Step 6: 合并与推送**

确认工作区干净、当前功能分支历史完整后，快进合并到 `main`，在 `main` 上复核核心测试并执行：

```bash
git push origin main
```

预期：远端 `main` 指向最终验收提交，GitHub 保留全部分阶段历史。
