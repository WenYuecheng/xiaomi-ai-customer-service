# 测试报告

执行日期：2026-07-18 至 2026-07-23。

## 多知识库检索、上传与唯一前端验收（2026-07-23）

- API 与数据：聊天和 Advisor 支持 1–5 个知识库，旧单库字段继续兼容；新增两张关联表，真实 Alembic 测试证明旧聊天与旧 Advisor 会话均正确回填。
- 检索：每库独立混合召回最多 8 条，全局去重排序后最多 12 条进入 AI 重排；来源响应展示所属知识库。`小米17T`、`小米 17T`、`Xiaomi 17T` 和 Pro 版本不再截断为“小米 17”，明确新型号会覆盖不兼容的旧话题。
- 上传：修复隐藏 input 点击冒泡导致的递归；批量上传单文件失败不再中断后续文件。`data/upload-fixtures/` 中四个真实文件均通过签名、解析、Worker 和 chunk 标记测试，PDF 中文可提取、DOCX 压缩包校验无错误。
- 前端：队长版本已成为唯一 `frontend/`，重复目录删除；聊天与 AI 选购共用多库选择组件，默认核心库和官方完整库，最多 5 个并保存上次选择。来源卡片展示来源库。
- 自动化：Ruff 格式与静态检查通过；后端 76 项全部通过、覆盖率 90%；前端 16 个测试文件 33 项全部通过；Vue TypeScript 与 Vite 8 构建成功。
- Docker：迁移前备份 `robot_app-data`（55MB）；新镜像构建成功，后端 healthy、前端 HTTP 200，迁移版本为 `7b41c2d9e610`。迁移后保留 7 个用户、4 个知识库、124 个文档、333 个 chunk、20 个会话。
- 持久化：连续 3 次 `docker compose down` / `up -d --wait` 后上述用户、知识库、文档、chunk 和会话计数均保持不变。
- 受控项：Docker 实库中的演示账号密码已由使用者修改，正常登录返回 401，因此未重置账号、未绕过认证，也未在该卷重复写入四份验收文件；四格式真实 HTTP 上传由隔离自动化数据库完成。

## 双产品知识库质量验收（2026-07-23）

- 数据分库：30 份小米、REDMI、米家资料进入“小米生态核心库”；20 份其他品牌资料进入“竞品选购对比库”。
- 来源：50 份文档的主要来源和价格来源覆盖率均为 100%；联网检查 50/50 个主要来源返回 HTTP 200。
- 清洗：从可回答正文移除 156 条带“待人工、待复核、待确认、需复核”的内容；审核表仍明确标注需要人工终审，自动检查不冒充人工审核。
- 实体：解析器读取 Markdown front matter 中的通用型号并传播到全部 chunk；两库临时入库后产品实体分别为 30 和 20。
- RAG：临时 SQLite/Chroma 中 50/50 文档处理成功、失败 0、来源覆盖率 100%；小米 17 Ultra 只引用核心库 `PROD-010`，OPPO Pad 4 Pro 只引用对比库 `PROD-030`。
- 自动化：后端 68 项测试退出码为 0，Ruff 格式和静态检查通过；主前端 14 个测试文件、30 项测试通过，Docker 部署的队长前端 14 个测试文件、28 项测试通过；两个前端均通过 Vue TypeScript 与 Vite 生产构建。
- Docker 实装：使用最新后端与队长前端重建镜像并启动；后端为 `healthy`，前端与健康接口均返回 HTTP 200。实际导入“小米生态核心库”30/30 份（37 个 chunk）和“竞品选购对比库”20/20 份（28 个 chunk），失败 0，两个知识库来源覆盖率均为 100%。
- 数据保护：导入前将 `robot_app-data` 备份到 `/private/tmp/robot_app-data-pre-rag-20260723.tar.gz`（54MB），SHA-256 为 `bb61476f5cf803ccc5df2b7551c6de437deb99d5a0e9c6df7ba2ea44ed8f8f8a`。
- 审核表：保留 4 个原有公式，LibreOffice 重算后未发现 `#REF!`、`#DIV/0!`、`#VALUE!`、`#N/A` 或 `#NAME?`。

## 对话消息角色对齐验收（2026-07-22）

- 布局：用户消息正文先于身份标识渲染，气泡与“你”整体靠右；小爱客服身份标识先于回答正文，整体靠左。
- 响应式：桌面端 1440px 下用户身份坐标位于气泡右侧、客服身份位于回答左侧；移动端 390px 下保持相同方向，两个消息容器边界均未超出视口。
- 自动化：14 个 Vitest 文件、30 项测试全部通过，其中 `ChatMessage` 新增 2 项角色顺序回归测试；`vue-tsc` 类型检查与 Vite 8 生产构建成功。
- Docker：前端镜像重新构建并启动，前端返回 HTTP 200，后端保持 healthy 且健康检查返回 `status=ok`。
- 真实页面：使用已有管理员账号提问“小米 14 的电池容量是多少？”，页面正确显示右侧用户问题、左侧小爱客服回答、5 阶段 AI 执行轨迹和真实来源。
- 范围控制：未修改消息接口、SSE、Markdown、AI 轨迹、来源、反馈或工单逻辑；无关文件 `install_arina_dream_skin.sh` 未提交。

## 最终项目结构、README 与详细注释验收（2026-07-19）

- 后端：56 项 pytest 全部通过，覆盖率 89%；65 个 Python 文件通过 Ruff 格式与静态检查。
- 前端：14 个 Vitest 文件、28 项测试全部通过；Vue TypeScript 与 Vite 8 生产构建成功。
- 注释语义：比较 `origin/main` 与详细注释提交中的 54 个 Python 文件，移除模块、类和函数文档字符串后，AST 语义差异为 0；聊天生成边界保持 `not prepared.requires_generation`。
- Docker：前后端镜像重新构建成功；后端状态 healthy，前端 running，`/api/v1/health` 返回 `status=ok`。
- 项目结构：5 份规划材料归档到 `docs/planning/`，3 张验收图片归档到 `docs/screenshots/`，Jira CSV 移至 `jira/`，4 份项目说明归档到 `docs/project/`；根目录只保留启动必需文件。
- 文档事实：README 命令已与两个脚本的 `--help` 输出核对；本地 Markdown 链接缺失数为 0。文档记录 10 份基础样本、62 份正式资料、30 问基础集和 114 问扩展集。
- 公开安全：已跟踪运行时产物数量为 0；未发现 `sk-` 密钥模式，`.env`、数据库、Chroma、上传文件、模型和缓存均未纳入 Git。

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
