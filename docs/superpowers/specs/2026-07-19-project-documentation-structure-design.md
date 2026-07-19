# 项目结构、完整 README 与详细注释整理设计

## 目标

在不删除功能代码、可复现依赖、知识资料、评测资产和验收证据的前提下，完成后端详细注释规范化、根目录整理、项目说明归档和完整 README 更新，并将经过全量验证的结果同步到公开 GitHub 主分支。

## 已确认范围

本次整理以新增的四份说明文件为输入：

- `1_需求文档与完成情况.md`
- `2_文件结构说明.md`
- `3_文件整合删除建议.md`
- `4_完整README.md`

四份文件不再散落在根目录，修正事实后归档到 `docs/project/`。根目录只保留运行入口、环境模板、容器编排和主 README。

## 注释规范化

保留用户新增的中文模块说明、类说明、函数说明和关键流程注释，但必须满足以下约束：

- 注释不得改变原有业务逻辑、接口、异常和数据流。
- 恢复 `backend/app/chat/service.py` 中被误改的生成分支判断，以 `not prepared.requires_generation` 作为确定性业务回复与模型生成的边界。
- 使用 Ruff 统一格式，消除尾随空格、超过 100 字符的行和不规范的行内注释。
- 注释重点解释文件职责、调用链、边界条件和安全原因，不逐行复述代码。
- 测试注释说明场景、动作和预期结果，不加入无法由断言证明的结论。
- 通过去除注释和文档字符串后的 Python AST 比较，确认除已知误改恢复外没有语义变化。

## 目录整理

根目录规划材料移动到 `docs/planning/`：

| 原文件 | 目标文件 |
|---|---|
| `客服机器人 .docx` | `docs/planning/01_早期需求草稿.docx` |
| `小米智能客服机器人_13天需求分析与Jira实施方案.docx` | `docs/planning/02_13天需求分析与Jira实施方案.docx` |
| `小米智能客服机器人_技术栈项目结构与11天实施计划.docx` | `docs/planning/03_技术栈与11天实施计划.docx` |
| `小米智能客服机器人_10天实施计划.md` | `docs/planning/04_10天实施计划.md` |
| `必须做到要求.docx` | `docs/planning/05_必须做到要求.docx` |

Jira CSV 移动到 `jira/Jira_Epic_Stories导入表.csv`，并同步修改所有引用。

三张根目录图片移动到 `docs/screenshots/`，使用 `evidence-01.jpg`、`evidence-02.png`、`evidence-03.jpg` 作为稳定名称。图片作为历史验收证据保留，不猜测其业务含义。

四份新增说明文件修正后归档为：

- `docs/project/requirements-and-status.md`
- `docs/project/structure.md`
- `docs/project/cleanup-decisions.md`
- `docs/project/readme-source.md`

## 明确保留的资产

以下文件或目录不得因“精简”而删除：

- `backend/uv.lock` 和 `frontend/pnpm-lock.yaml`：保证依赖可复现。
- `scripts/collect_official_knowledge.py` 和 `scripts/build_extended_evaluation.py`：保证知识资料与扩展评测集可重新构建。
- `data/evaluation/questions.csv` 与 `questions-expanded.csv`：分别承担 30 问基线和扩展评测。
- `data/knowledge/official/` 下 62 份公开知识文档及清单。
- `docs/superpowers/specs/` 与 `docs/superpowers/plans/`：作为设计和实施证据。
- `docs/api/`、`docs/database/`、`docs/deployment/`：保持职责分离，不合并成单个大文件。

运行时数据库、上传文件、Chroma、模型缓存、虚拟环境、Node 依赖、构建产物和工具缓存继续由 `.gitignore` 排除。

## README 设计

根 README 以 `4_完整README.md` 为内容基础，但所有命令和数字必须由当前代码、锁文件和测试结果校验。README 包含：

- 项目定位、核心功能和可信 AI 执行流程。
- Docker 与本地开发的准确启动步骤。
- Mock、DeepSeek、Ollama 和 BGE 配置说明，密钥仅使用占位符。
- 演示账号、公开注册和角色权限说明。
- 10 份基础样本与 62 份正式公开知识资料的用途和导入方式。
- 与 `scripts/ingest_samples.py` 实际参数一致的批量导入命令。
- 页面、API、数据库和目录导航。
- 当前自动化测试数量、覆盖率和评测结果；若最终测试数量变化，以实际输出更新。
- Mock 订单、非实时价格、单容器规模和未接入真实小米业务系统等边界。
- 公开 GitHub 地址：`https://github.com/WenYuecheng/xiaomi-ai-customer-service`。

## 说明文件事实修正

归档前修正以下已识别偏差：

- 注册接口属于 `auth/router.py`，账号资料接口属于 `account/router.py`。
- JWT 签发与验证位于 `auth/security.py`。
- 前端画像组合逻辑使用 `useAccountDashboard.ts`，不存在 `useProfile.ts`。
- 检索为向量相似度与 jieba 词法分加权融合，不描述为 BM25。
- `docs/demo-script.md` 位于 `docs/` 根下，不位于 `docs/superpowers/`。
- 自动生成的前端声明文件和 TypeScript 缓存由 `.gitignore` 排除，不写入正式结构树。
- 批量导入脚本通过 `INGEST_PASSWORD` 注入凭据，并支持创建知识库或传入现有知识库 ID。

## 验证与发布

实施完成后执行：

1. Ruff 格式检查与静态检查。
2. 后端全量 pytest 与覆盖率。
3. 前端 Vitest、Vue TypeScript 和 Vite 生产构建。
4. Python AST 语义比较，确认注释整理未引入逻辑变化。
5. `git diff --check`、公开文件密钥模式扫描和 `.gitignore` 验证。
6. Docker Compose 配置、健康检查与页面可访问性检查。
7. 按“注释修复、目录整理、README 与文档、验收报告”保留分阶段提交。
8. 合并到 `main` 并推送公开 GitHub；不提交 `.env`、数据库或运行时数据。

## 验收标准

- 根目录结构与本设计一致，所有移动后的引用有效。
- 四份说明文件与实际代码、命令、目录和测试结果一致。
- 后端注释完整且 Ruff 零错误，除恢复误改外业务语义不变。
- README 可由新用户从零启动、导入资料、运行测试并理解范围边界。
- 后端、前端、构建和 Docker 验收全部通过。
- Git 工作区无运行时文件或凭据，公开主分支包含完整分阶段历史。
