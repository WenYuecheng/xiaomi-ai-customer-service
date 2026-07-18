# 需求追踪说明

实施期间以 `小米智能客服机器人_Jira_Epic_Stories导入表.csv` 的 32 条 Story 为主键，测试使用 `EPxx-序号` 标记。额外需求使用以下编号：

- EXT-01：文档语义预处理
- EXT-02：用户画像
- EXT-03：当前热词
- EXT-04：历史会话保存与压缩
- EXT-05：混合推荐
- EXT-06：离线训练、模型版本与 Precision/Recall@K

## Story 追踪矩阵

| Story | 实现/接口 | 测试或验收证据 |
|---|---|---|
| EP01-01 创建知识库 | `knowledge/router.py` | `test_auth_and_knowledge.py` |
| EP01-02 查看筛选知识库 | `GET /knowledge-bases` | API 测试、知识库页面 |
| EP01-03 多格式上传 | `POST /documents/upload` | PDF/DOCX/TXT/MD 测试 |
| EP01-04 解析清洗 | `ingestion/parsers.py` | 文本抽取、签名失败测试 |
| EP01-05 切分预览 | `/documents/{id}/chunks` | chunk 参数/预览测试 |
| EP01-06 生成重建向量 | `/documents/{id}/reindex`、job retry | worker 与文档测试 |
| EP01-07 删除文档向量 | `DELETE /documents/{id}` | 删除残留测试 |
| EP02-01 单轮问答 | `/chat/completions` | 30/30 RAG 回归 |
| EP02-02 多轮上下文 | 会话、滚动摘要、最近 10 轮、问题改写 | 追问、提示词历史与隔离测试 |
| EP02-03 来源引用 | `MessageSource`、公开 URL、可点击来源卡片 | grounded source 与安全 URL 测试 |
| EP02-04 低置信兜底 | 阈值与 `FALLBACK_ANSWER` | 无关问题、连续兜底测试 |
| EP02-05 检索参数 | 环境配置 `TOP_K`/阈值 | Pydantic 范围校验 |
| EP02-06 JSON/SSE | JSON 与五类 SSE 事件、原生模型 token 流 | SSE 顺序与 provider 流测试 |
| EP03-01 聊天主页 | `ChatView.vue` | 前端构建 |
| EP03-02 流式与停止 | `api/chat.ts`、服务端 run 取消、AbortController | SSE/原生流测试、前端构建 |
| EP03-03 安全 Markdown | markdown-it + DOMPurify | XSS 组件测试 |
| EP03-04 引用来源 | `SourceRail.vue` | 组件测试 |
| EP03-05 异常空状态 | 页面 alert/empty/loading | 前端构建与演示脚本 |
| EP04-01 意图路由 | `classify_intent` | knowledge/tool/general 测试 |
| EP04-02 Mock 订单物流 | `/mock/orders`、工具路由 | 用户隔离与明确标识测试 |
| EP04-03 人工转接 | 显式意图、连续兜底 | 转人工测试 |
| EP04-04 结构化工单 | `/tickets` 创建、列表、状态与优先级更新 | 工单字段/流转测试 |
| EP05-01 对话日志 | `/operations/logs?q=` | RBAC 与运营测试 |
| EP05-02 评价修正 | `/chat/feedback`、后台反馈 | 幂等更新测试 |
| EP05-03 登录角色 | JWT/Bcrypt/RBAC | 认证权限测试 |
| EP05-04 密钥配置 | Settings/`.env.example` | 敏感信息扫描 |
| EP05-05 敏感输入 | 长度、文件、敏感词与审计 | blocked input 测试 |
| EP06-01 标准回归集 | `questions.csv`、评测脚本 | 30/30，100% |
| EP06-02 核心测试 | pytest/Vitest | 后端 29、前端 3 |
| EP06-03 Compose MVP | 两个 Dockerfile、Compose | 配置通过；Docker Desktop 存储 I/O 故障待恢复后实测 |
| EP06-04 README/API | README、Swagger、数据库文档 | 本地端到端启动验证 |
| EP06-05 Jira 归档 | `jira/README.md`、本矩阵 | 单人真实证据流程 |

扩展项：EXT-01 语义清洗与型号提取；EXT-02 画像；EXT-03 时间衰减热词；EXT-04 滚动摘要；EXT-05 混合推荐；EXT-06 TruncatedSVD 离线训练与 Precision/Recall@K，均由 `test_operations.py` 覆盖。
