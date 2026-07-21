# 小米智能客服机器人：Jira Story 与代码对应说明

> 核对依据：`小米智能客服机器人_Jira_Epic_Stories导入表.csv`（32 条 Story）、技术实施计划、当前仓库代码与测试。状态含义：**完整**＝主要验收点有直接实现；**基本完整**＝主流程存在但个别验收细节依赖配置/演示；**部分**＝只有部分能力或交付证据不足。

## EP01｜知识库与文档管理

| Story | 状态 | 对应代码 | 实现解释与差距 |
|---|---|---|---|
| EP01-01 创建知识库 | 完整 | `backend/app/knowledge/router.py:188`；`backend/app/knowledge/schemas.py:6`；`backend/app/db/models.py:77`；`frontend/src/components/knowledge/KnowledgeBaseManager.vue` | POST 创建接口校验名称必填，服务端处理重名冲突；模型保存描述、负责人、Embedding 模型及独立 `collection_name`；前端表单创建后刷新列表。测试见 `backend/tests/test_auth_and_knowledge.py:27,61`。 |
| EP01-02 查看和筛选知识库列表 | 完整 | `backend/app/knowledge/router.py:221`；`frontend/src/components/knowledge/KnowledgeBaseManager.vue:60` | GET 列表支持 `q` 和 `status`，响应包含文档数、创建时间、负责人等；前端也提供名称/状态筛选和空表状态。 |
| EP01-03 上传多格式产品文档 | 完整 | `backend/app/ingestion/router.py:78`；`backend/app/ingestion/parsers.py`；`frontend/src/components/knowledge/DocumentManager.vue` | 上传接口校验扩展名、MIME/文件签名及大小，安全落盘后创建后台任务；解析器覆盖 PDF、DOCX、TXT、MD，页面轮询状态并显示错误。测试见 `test_documents.py:32,61,96`。 |
| EP01-04 解析和清洗文档内容 | 基本完整 | `backend/app/ingestion/parsers.py`；`backend/app/ingestion/worker.py:22`；`backend/app/db/models.py:123` | 解析器抽取正文并做空白/字符清洗，worker 保存来源元数据、状态和失败原因。标题结构与页眉页脚识别采用启发式处理，并非完整的版面语义解析。 |
| EP01-05 配置和预览文本切分 | 基本完整 | `backend/app/ingestion/router.py:78,176`；`backend/app/db/models.py:140`；`frontend/src/components/knowledge/DocumentManager.vue:143` | 上传时接收并校验 `chunk_size/chunk_overlap`，处理后 GET chunks 返回序号、内容和来源供预览。当前主要是“上传时配置”；没有看到对既有文档单独修改切分参数并即时预览后保存的完整编辑流程。 |
| EP01-06 生成和重建文档向量 | 完整 | `backend/app/ingestion/worker.py:22`；`backend/app/ingestion/router.py:238,251`；`backend/app/rag/vector_store.py` | 入库任务自动切分并写入向量库；reindex 手工重建、job retry 重试；重建前按文档清理旧向量，避免重复，任务保存进度/错误。 |
| EP01-07 删除文档及关联向量 | 完整 | `backend/app/ingestion/router.py:266`；`backend/app/ingestion/service.py`；`frontend/src/components/knowledge/DocumentManager.vue` | 删除服务同时移除向量、切块、元数据及原文件；前端负责二次确认。测试 `test_documents.py:78` 验证残留清理。 |

## EP02｜RAG 智能问答

| Story | 状态 | 对应代码 | 实现解释与差距 |
|---|---|---|---|
| EP02-01 基于知识库单轮问答 | 完整 | `backend/app/chat/router.py:77`；`backend/app/chat/service.py:511,904`；`backend/app/rag/retrieval.py`；`backend/app/rag/reranking.py` | 统一入口完成问题分析、向量召回、重排、基于证据生成和持久化，JSON 返回 answer/message_id/conversation_id。评测入口为 `scripts/run_rag_evaluation.py:9`，题集在 `data/evaluation/questions.csv`。 |
| EP02-02 多轮上下文对话 | 完整 | `backend/app/chat/service.py:92,160,178`；`backend/app/chat/router.py:206,248`；`backend/app/db/models.py:195,214` | conversation_id 隔离保存消息，问题改写利用历史处理“它/这个型号”等追问；历史压缩保留最近 10 轮量级；DELETE 清空指定会话。测试见 `test_chat.py:413`。 |
| EP02-03 显示答案来源引用 | 完整 | `backend/app/db/models.py:233`；`backend/app/chat/schemas.py:24`；`backend/app/chat/service.py`；`frontend/src/components/chat/SourceRail.vue` | 检索命中的来源以 MessageSource 持久化并返回文件名、URL、片段、页码/分数；前端来源栏与消息绑定、可展开及安全打开 URL。测试见 `test_chat.py:29,92`。 |
| EP02-04 低置信度兜底回答 | 完整 | `backend/app/chat/service.py:42,451,626` | 无候选或低于向量/重排阈值时直接使用固定兜底，不调用普通生成；保存 fallback 次数，显式转人工或连续兜底给出人工建议。测试见 `test_chat.py:123,210,391,438`。 |
| EP02-05 配置检索参数 | 部分 | `backend/app/core/config.py:70-77`；`.env.example` | top_k、相似度阈值等由 Pydantic Settings 做范围校验，新请求读取配置；但未见管理员在线配置页面/API，也未见“配置变更时间和操作人”的专门审计闭环；最大上下文轮数主要由代码压缩策略控制。 |
| EP02-06 统一聊天接口兼容流式返回 | 完整 | `backend/app/chat/router.py:77,200`；`backend/app/chat/service.py:287,762,904`；`frontend/src/api/chat.ts:32` | 同一个 `/chat/completions` 根据 stream 返回 JSON 或 SSE；流中按序发送阶段、token、sources、done，支持 run 取消；异常走统一 AppError 结构。契约测试见 `test_chat.py:347,391`。 |

## EP03｜对话机器人前端

| Story | 状态 | 对应代码 | 实现解释与差距 |
|---|---|---|---|
| EP03-01 实现聊天主页面 | 完整 | `frontend/src/views/ChatView.vue:74,177,196`；`frontend/src/components/chat/ChatComposer.vue`；`frontend/src/components/chat/ChatMessage.vue` | 页面包含欢迎/空状态、消息列表、知识库选择、输入发送、加载、停止和新对话；空文本在 Composer 中被拦截。 |
| EP03-02 逐段展示流式答案 | 完整 | `frontend/src/api/chat.ts:32`；`frontend/src/views/ChatView.vue:30,74,182` | fetch 读取 SSE 并依次回调追加内容；AbortController 与后端 cancel 接口停止生成；中断时已写入的文本仍保留并显示错误。 |
| EP03-03 渲染 Markdown 答案 | 完整 | `frontend/src/components/chat/ChatMessage.vue:2,23-24` | markdown-it 渲染标题、列表、链接和代码等；关闭原生 HTML，再经 DOMPurify 清洗，降低 XSS 风险；样式负责换行和代码布局。 |
| EP03-04 展示和打开引用来源 | 完整 | `frontend/src/components/chat/ChatMessage.vue:35`；`frontend/src/components/chat/SourceRail.vue` | 仅在消息有来源且非特殊计划卡片时显示来源栏；来源可展开，HTTP(S) URL 新窗口打开，兜底不会渲染空来源组件。 |
| EP03-05 展示异常和空状态 | 基本完整 | `frontend/src/views/ChatView.vue:19,197,202`；`frontend/src/api/client.ts`；`frontend/src/api/chat.ts:42` | 页面有统一错误 Alert、初始空状态和生成忙碌态，流错误转换为用户提示且不展示服务端堆栈。不同错误码有归类逻辑；“五类异常各自独立重试按钮”的呈现不完全明确，主要通过重新发送完成重试。 |

## EP04｜业务工具与工单

| Story | 状态 | 对应代码 | 实现解释与差距 |
|---|---|---|---|
| EP04-01 识别对话意图并路由 | 完整 | `backend/app/chat/service.py:82,105,132` | `classify_intent` 区分 knowledge_query、tool_use、general_chat；业务意图走白名单工具，其他进入安全问答/生成流程，意图随消息保存供日志查询。 |
| EP04-02 查询 Mock 订单和物流 | 完整 | `backend/app/operations/router.py:79`；`backend/app/db/models.py:285`；`backend/app/chat/service.py:105` | MockOrder 与用户绑定，接口只按当前用户查询；聊天工具路由读取模拟订单并明确标识 Mock，不接触真实订单数据。 |
| EP04-03 触发人工转接 | 完整 | `backend/app/chat/service.py:82,329`；`backend/tests/test_chat.py:438` | “转人工”显式意图立即处理；连续兜底会追加人工建议；原因随意图/消息进入运营日志，用户仍可继续后续对话。 |
| EP04-04 根据会话创建结构化工单 | 完整 | `backend/app/operations/router.py:85,127,135`；`backend/app/operations/schemas.py:26`；`backend/app/db/models.py:298`；`frontend/src/components/operations/OperationsDashboard.vue:89` | 创建接口校验会话归属并生成分类、型号、摘要、已尝试方案、优先级等字段；后台可列表及更新状态/优先级，原会话独立保存。 |

## EP05｜运营权限与安全

| Story | 状态 | 对应代码 | 实现解释与差距 |
|---|---|---|---|
| EP05-01 记录和查询对话日志 | 完整 | `backend/app/operations/router.py:220`；`backend/app/db/models.py:214,233`；`frontend/src/components/operations/OperationsDashboard.vue:30,81` | 每次问答保存问题、答案、意图、耗时、来源和用户/时间；后台接口受管理员/运营角色限制并支持关键词、时间筛选，前端展示明细。 |
| EP05-02 收集回答评价和修正 | 完整 | `backend/app/chat/router.py:262`；`backend/app/chat/schemas.py:85`；`backend/app/db/models.py:253`；`frontend/src/components/chat/FeedbackDrawer.vue` | 赞/踩及纠正内容关联 message/conversation；重复提交幂等更新；运营后台可按 rating 筛选。测试见 `test_chat.py:320`。 |
| EP05-03 实现用户登录和角色权限 | 完整 | `backend/app/auth/router.py:34,67,93`；`backend/app/auth/security.py`；`backend/app/auth/dependencies.py:58`；`frontend/src/router/index.ts` | 密码哈希、JWT 登录，admin/operator/user 三角色；后端依赖做强制 RBAC，前端路由/导航隐藏无权页面。测试见 `test_auth_and_knowledge.py:6,46`。 |
| EP05-04 安全管理模型密钥和配置 | 完整 | `backend/app/core/config.py:31`；`.env.example:18`；`.gitignore`；`backend/tests/test_bootstrap.py:12` | 密钥只从环境读取，示例文件留空；选择需要密钥的 provider 时启动校验失败并给出明确错误，代码/日志未写入完整 key。 |
| EP05-05 过滤敏感内容和限制输入 | 完整 | `backend/app/chat/schemas.py:20`；`backend/app/chat/service.py:210,521`；`backend/app/core/config.py:77`；`backend/app/ingestion/router.py:78` | 聊天长度、上传大小/类型均受限；可配置敏感词命中后在模型调用前阻断并写审计事件；危险或伪造文件被拒绝。测试见 `test_chat.py:490`、`test_documents.py:61`。 |

## EP06｜测试部署与文档

| Story | 状态 | 对应代码/材料 | 实现解释与差距 |
|---|---|---|---|
| EP06-01 建立标准问答回归测试集 | 完整 | `data/evaluation/questions.csv`；`scripts/run_rag_evaluation.py:9`；`scripts/build_extended_evaluation.py:5` | 题集不少于 30 条，脚本逐题请求、核验知识点/来源并输出正确率和失败明细；`docs/testing/test-report.md:40` 记录验收命令。 |
| EP06-02 完成核心接口和功能测试 | 完整 | `backend/tests/`；`frontend/src/**/*.test.ts`；`docs/testing/test-report.md:7` | pytest 覆盖认证、知识库、上传、RAG、会话、反馈、权限、Mock 工具及异常；Vitest 覆盖前端关键交互。当前报告记录后端 56 项通过、覆盖率 89%，超过 15 条要求。 |
| EP06-03 使用 Docker Compose 部署 MVP | 完整 | `docker-compose.yml:1`；`backend/Dockerfile`；`frontend/Dockerfile`；`frontend/nginx.conf` | Compose 编排前后端，后端健康检查，环境变量注入，命名 volume 持久化数据库/上传/向量等数据；README 给出单命令启动方式。 |
| EP06-04 完善 README 和 API 文档 | 基本完整 | `README.md:29,116,149`；`docs/api/README.md`；`docs/database/README.md`；`backend/app/main.py:22` | README 覆盖配置、启动、测试、评测与常见安全事项；FastAPI 自动暴露 Swagger/OpenAPI，数据库文档说明迁移/初始化。接口示例集中在 Swagger 和 API 文档，完整度应以实际 Swagger 模型为准。 |
| EP06-05 完成 Jira Sprint 报告与交付归档 | 部分 | `jira/README.md:3`；`docs/requirements/traceability.md`；`docs/testing/test-report.md` | 已有 32 Story 追踪矩阵、测试报告和真实证据流程说明；但仓库中未发现实际导出的 Sprint Report、燃尽图、Epic 进度截图/文件，也未见完整 PPT 交付包，因此只能判为部分完成。 |

## 总结

- **完整：26 条**
- **基本完整：4 条**（EP01-04、EP01-05、EP03-05、EP06-04）
- **部分：2 条**（EP02-05、EP06-05）

最值得补齐的两处是：为检索参数增加管理员配置与审计闭环；从 Jira 实际导出 Sprint Report、燃尽图和 Epic 进度证据。另可增强既有文档的切分参数编辑/即时预览，以及异常态的显式重试入口。
