# 测试报告

执行日期：2026-07-17。

- 后端：23 项 pytest 全部通过，覆盖率 87%。
- 前端：2 项 Vitest 全部通过，`vue-tsc` 与 Vite 生产构建通过。
- RAG：10/10 公开样本文档入库成功；30/30 标准问题通过，正确率 100%。
- 数据库：全新 SQLite 执行 Alembic `upgrade head` 成功，`alembic check` 无模型漂移。
- Compose：`docker compose config --quiet` 通过；Docker 守护进程未启动，未完成镜像构建和三次重启持久化实测。

自动化覆盖认证与 RBAC、知识库 CRUD、安全上传、四格式解析、重复文件、失败任务、重建/删除、可信引用、低置信度兜底、多轮追问、SSE、反馈幂等、Mock 订单、工单、热词、画像隔离、推荐和离线训练。

RAG 数据集位于 `data/evaluation/questions.csv`，至少 30 问，及格线为 80%。样本文档均记录公开来源和采集日期。最终验收须保存以下命令输出：

```bash
uv run --project backend ruff check backend/app backend/tests scripts
uv run --project backend pytest backend/tests --cov=app
cd frontend && pnpm test && pnpm build
docker compose config
```

真实模型测试仅抽取少量问题，避免额度消耗；其结果必须与 Mock 自动测试分开记录。
