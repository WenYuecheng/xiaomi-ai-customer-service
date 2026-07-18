# 测试报告

执行日期：2026-07-18。

## 用户注册与动态个人主页验收

- 后端：56 项 pytest 全部通过，覆盖率 89%；Ruff 格式与静态检查通过。
- 前端：14 个 Vitest 文件、28 项测试全部通过，`vue-tsc` 与 Vite 生产构建通过。
- 注册与安全：公开注册固定创建普通用户，用户名归一化、密码强度、重复用户名、越权字段、来源限流、头像白名单、资料更新与修改密码旧 JWT 失效均有自动测试。
- 个人主页：空状态与真实统计、14 天趋势、兴趣星系、统一活动时间轴、游标分页和跨用户隔离均有后端与组件测试；浏览器实测页面无控制台错误。
- Docker：使用临时用户 `profile_demo_0718` 完成注册和资料更新，显示名为“星河体验官”、头像为 `cosmos`。执行一次 `docker compose down` / `up -d` 后账号与资料完整保留，后端恢复为 healthy，前端正常运行。
- 遗留数据库：容器启动会识别旧版 `create_all` 数据库并安全补写 Alembic 基线，再升级用户资料字段；已有知识库、会话与模型数据未删除。
- 模型调用：本功能全部为确定性账户操作，验收过程未调用 DeepSeek。

## 第二阶段 AI 重排验收

- 后端：41 项 pytest 全部通过，覆盖率 88%；Ruff 格式与静态检查通过。
- 前端：15 项 Vitest 全部通过，`vue-tsc` 与 Vite 生产构建通过。
- AI 流程：正常知识问题固定执行 `DeepSeek 问题理解 → BGE 候选召回 → DeepSeek AI 重排 → DeepSeek 可信回答 → 引用校验`；重排异常、空选择、业务意图、敏感输入和 SSE 终态均有自动测试。
- 真实模型：Docker 中使用 `deepseek-chat` 和 `BAAI/bge-small-zh-v1.5` 验证“X20 Pro 最大吸力是多少？”。BGE 召回 1 个片段，AI 重排保留 1 个并说明“直接给出最大吸力 7000Pa”，最终回答“X20 Pro 最大吸力为 7000Pa”，来源为 `robot-vacuum-x20-pro.md`。
- SSE：真实请求按阶段发送 `understanding → retrieval → reranking → generation → grounding`，并在 `delta` 后返回实际来源；低置信度场景的每个终态事件只发送一次。
- Docker 持久化：本阶段连续完成 3 次 `docker compose down` / `up -d`，每次后端均恢复为 healthy、前端可访问。重启前后均为 3 个用户、2 个知识库、74 个文档、268 个 chunk、12 个会话、38 条消息、74 个上传文件、9 个 Chroma 文件和 25 个模型文件。

## 第一阶段与基础平台验收记录

- 后端：30 项 pytest 全部通过，覆盖率 88%；Ruff 格式与静态检查通过。
- 前端：4 项 Vitest 全部通过，`vue-tsc` 与 Vite 生产构建通过。
- RAG：10/10 公开样本文档入库成功；30/30 标准问题通过，正确率 100%。
- DeepSeek：独立临时环境完成 1 个真实流式 RAG 问题；SSE 顺序为 `meta → delta → sources → done`，回答“Xiaomi 14 的电池容量为 4610mAh”，真实来源数为 1。
- 数据库：全新 SQLite 执行 Alembic `upgrade head` 成功，`alembic check` 无模型漂移。
- Compose：Docker Desktop 经缓存清理和非破坏性重启后恢复，无需恢复出厂设置。前后端镜像构建成功，后端约 253MB、前端约 26.1MB，两个容器均为 healthy/running。
- 本地 Embedding：将 `sentence-transformers + PyTorch` 替换为 `FastEmbed + ONNX Runtime`，继续使用 `BAAI/bge-small-zh-v1.5`。锁文件已移除 PyTorch 和 CUDA 运行库；91MB 模型缓存持久化到 `/data/models/fastembed`。
- Docker 持久化：连续完成 3 次 `docker compose down` / `up -d`。每次均保持 3 个用户、1 个知识库、10 个文档、10 个 chunk、2 条消息、10 个上传文件、5 个 Chroma 文件和 14 个模型文件。
- Docker 数据保护：清理前备份 `robot_app-data` 到 `/private/tmp/robot_app-data-backup-20260717.tar.gz`，SHA-256 为 `f8bebf44a8c8e8032fe6ab702a28bfdeb1961af0a24076cdb850ad781fef519f`。

自动化覆盖认证与 RBAC、知识库 CRUD、安全上传、四格式解析、重复文件、失败任务、重建/删除、可信引用、低置信度兜底、多轮追问、SSE、反馈幂等、Mock 订单、工单、热词、画像隔离、推荐和离线训练。

工单回归：同一会话重复创建返回同一工单 ID；前端显示“创建中…”与持久的“工单已创建”禁用状态，失败时恢复按钮并展示错误。Docker 真实数据中由重复点击产生的 22 条冗余记录已在备份后清理，保留最早一条。

RAG 数据集位于 `data/evaluation/questions.csv`，至少 30 问，及格线为 80%。样本文档均记录公开来源和采集日期。最终验收须保存以下命令输出：

```bash
uv run --project backend --extra dev ruff check backend/app backend/tests scripts
LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock uv run --project backend --extra dev pytest backend/tests --cov=app
cd frontend && pnpm test && pnpm build
docker compose config
```

真实模型测试仅抽取少量问题，避免额度消耗；其结果必须与 Mock 自动测试分开记录。
