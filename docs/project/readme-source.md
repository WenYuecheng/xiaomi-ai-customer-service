# README 写作依据与维护规则

根目录 `README.md` 是项目唯一快速入口，本文件记录它的事实来源，避免后续手工修改造成命令、数量
或接口漂移。

## 事实来源

| README 内容 | 唯一事实来源 |
|---|---|
| Python 与依赖版本 | `backend/pyproject.toml`、`backend/uv.lock` |
| 前端依赖与脚本 | `frontend/package.json`、`frontend/pnpm-lock.yaml` |
| 环境变量 | `.env.example`、`backend/app/core/config.py` |
| Docker 端口、卷和健康检查 | `docker-compose.yml`、两个 Dockerfile |
| API 路径 | FastAPI Router 与运行时 `/docs` |
| 页面和角色 | `frontend/src/router/index.ts`、`AppShell.vue` |
| 导入命令 | `scripts/ingest_samples.py --help` |
| 评测命令 | `scripts/run_rag_evaluation.py --help` |
| 知识数量 | Git 跟踪的 `data/samples/*.md` 与 `data/knowledge/official/*.md` |
| 测试数量和覆盖率 | 最新全量测试输出与 `docs/testing/test-report.md` |
| 已知边界 | 设计规格、Mock 标识和实际外部集成情况 |

## 当前核验值

- 后端 Python：`>=3.11,<3.12`。
- 基础产品样本：10 份，不包含 `SOURCES.md`。
- 正式公开知识文档：62 份，来源索引位于 `data/knowledge/manifest.csv`。
- 基础评测：30 问；扩展评测：114 问。
- 注册接口：`POST /api/v1/auth/register`。
- 账号接口：`/api/v1/account/*`。
- 检索：70% 向量分与 30% jieba 词法分融合，并保留强词法命中兜底。
- 当前提交前基线：后端 56 项、前端 28 项，覆盖率 89%；最终数字以测试报告为准。

## 维护要求

1. README 中不得出现真实密码、JWT 密钥或 `sk-` API 密钥。
2. 命令必须能从仓库根目录或明确写出的子目录直接执行。
3. 测试数量、知识数量和覆盖率变化时，同步修改 README、需求状态和测试报告。
4. 不把 Mock 业务描述成真实小米系统接入，不把可视化关系图描述成推理型知识图谱。
5. 所有移动后的文档必须更新链接；公开 GitHub 链接固定指向当前仓库。
