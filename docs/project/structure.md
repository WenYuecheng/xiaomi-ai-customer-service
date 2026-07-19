# 小米智能客服机器人 — 项目文件结构说明

本文档说明项目中每个文件夹和文件的作用，帮助快速了解代码库组织方式。

---

## 根目录 `/robot/`

```
robot/
├── backend/                     # 后端服务（Python + FastAPI）
├── frontend/                    # 前端应用（Vue 3 + TypeScript）
├── data/                        # 运行时数据与样本文件
├── docs/                        # 项目文档
├── scripts/                     # 辅助脚本
├── jira/                        # Jira 证据材料
│
├── docker-compose.yml           # Docker 编排文件（一键启动前后端）
├── .env.example                 # 环境变量模板（需复制为 .env 并填写密钥）
├── .env                         # 实际环境变量（包含密钥，不提交 Git）
├── .gitignore                   # Git 忽略规则
├── .dockerignore                # Docker 构建忽略规则
├── README.md                    # 项目主文档（快速启动入口）
│
├── 客服机器人.docx               # 规划文档：早期需求草稿
├── 小米智能客服机器人_10天实施计划.md      # 规划文档：10 天排期（最终执行版）
├── 小米智能客服机器人_13天需求分析与Jira实施方案.docx  # 规划文档：Jira 需求分析
├── 小米智能客服机器人_Jira_Epic_Stories导入表.csv       # Jira 导入用 CSV（32 条 Story）
├── 小米智能客服机器人_技术栈项目结构与11天实施计划.docx  # 规划文档：技术选型说明
├── 必须做到要求.docx              # 规划文档：安全与验收强制要求
│
├── 2fee0dd447a8022d0f82667a9c9b6b72.jpg  # 截图/演示图片（验收证据）
├── 9de7bcd869fe84ecc842f8108e40f6d8.png  # 截图/演示图片（验收证据）
└── c10043f0cf2dec3e5aee281a2d89784e.jpg  # 截图/演示图片（验收证据）
```

---

## 后端目录 `/backend/`

```
backend/
├── app/                         # FastAPI 应用主体
│   ├── main.py                  # 应用入口：注册中间件、路由、生命周期管理
│   ├── commands.py              # CLI 命令：init-demo（初始化演示账号和订单）
│   ├── __init__.py
│   │
│   ├── core/                    # 核心基础设施
│   │   ├── config.py            # 全局配置：从 .env 加载所有环境变量（Settings 类）
│   │   ├── errors.py            # 自定义异常类和全局异常处理器
│   │   └── http.py              # RequestIdMiddleware（全链路追踪请求 ID）
│   │
│   ├── db/                      # 数据库层
│   │   ├── base.py              # SQLAlchemy 引擎、会话工厂、Base 声明
│   │   └── models.py            # 所有数据表定义（15 张表，含枚举类型）
│   │
│   ├── auth/                    # 认证与授权模块
│   │   ├── router.py            # 登录接口（/auth/login，返回 JWT）
│   │   ├── service.py           # 用户创建、密码哈希、JWT 签发
│   │   ├── security.py          # JWT 验证、密码哈希（bcrypt）
│   │   ├── dependencies.py      # FastAPI 依赖注入：current_user、require_role
│   │   ├── rate_limit.py        # 注册限流器（IP 维度，可配置）
│   │   ├── schemas.py           # 登录请求/响应 Pydantic 模型
│   │   └── __init__.py
│   │
│   ├── account/                 # 用户账号与个人主页模块
│   │   ├── router.py            # 注册、查看/更新资料、修改密码
│   │   ├── service.py           # 用户行为统计、画像计算、活动时间轴
│   │   ├── schemas.py           # 注册/资料请求响应模型（含 14 天趋势、兴趣星系）
│   │   └── __init__.py
│   │
│   ├── knowledge/               # 知识库管理模块
│   │   ├── router.py            # 知识库 CRUD（创建、列表、查看、删除）
│   │   ├── schemas.py           # 知识库请求响应模型
│   │   └── __init__.py
│   │
│   ├── ingestion/               # 文档摄入与处理模块
│   │   ├── router.py            # 上传、预览分块、重建索引、删除文档接口
│   │   ├── service.py           # 文档解析、切分、向量化业务逻辑
│   │   ├── parsers.py           # 多格式解析：PDF/DOCX/TXT/MD + 型号提取
│   │   ├── worker.py            # 后台工作线程（消费任务队列，异步处理文档）
│   │   ├── schemas.py           # 文档相关请求响应模型
│   │   └── __init__.py
│   │
│   ├── chat/                    # 智能问答模块（核心）
│   │   ├── router.py            # 聊天接口（JSON/SSE）、反馈、会话历史、工单
│   │   ├── service.py           # RAG 流水线编排（意图分析→检索→重排→生成）
│   │   ├── schemas.py           # 聊天消息、AI 轨迹、来源等数据模型
│   │   └── __init__.py
│   │
│   ├── rag/                     # RAG 引擎（底层技术组件）
│   │   ├── providers.py         # LLM 提供商：Mock / OpenAI-compatible / Ollama
│   │   ├── retrieval.py         # 向量检索：相似度搜索、BM25 混合检索
│   │   ├── reranking.py         # AI 重排：调用 LLM 对候选片段重新排序
│   │   ├── vector_store.py      # Chroma 向量库封装：增删查
│   │   └── __init__.py
│   │
│   ├── advisor/                 # AI 选购顾问模块
│   │   ├── router.py            # 顾问会话接口（JSON/SSE）、历史查询
│   │   ├── service.py           # 三段式选购流程（需求理解→证据召回→方案生成）
│   │   ├── schemas.py           # 顾问请求响应、产品卡片、雷达图等模型
│   │   └── __init__.py
│   │
│   └── operations/              # 运营分析与推荐模块
│       ├── router.py            # 对话日志、热词、画像、推荐、训练接口
│       ├── analytics.py         # 热词统计（时间衰减算法）
│       ├── recommendation.py    # 推荐引擎：实时混合召回 + TruncatedSVD 离线训练
│       ├── schemas.py           # 运营数据响应模型
│       └── __init__.py
│
├── tests/                       # 自动化测试
│   ├── conftest.py              # 测试夹具：内存 DB、测试客户端、Mock 提供商
│   ├── test_auth_and_knowledge.py  # 认证与知识库测试
│   ├── test_chat.py             # RAG 问答全流程测试（最大，含 SSE 与轨迹）
│   ├── test_documents.py        # 文档上传、解析、切分、删除测试
│   ├── test_operations.py       # 运营、推荐、离线训练测试
│   ├── test_advisor.py          # AI 选购顾问测试
│   ├── test_account.py          # 注册、画像、资料更新测试
│   ├── test_providers.py        # LLM 提供商单元测试
│   ├── test_vector_store.py     # Chroma 封装测试
│   ├── test_bootstrap.py        # 应用启动测试
│   ├── test_health.py           # 健康检查测试
│   ├── test_commands.py         # CLI 命令测试
│   ├── test_container_startup.py   # 容器启动测试
│   └── test_operations.py       # 运营功能测试
│
├── alembic/                     # 数据库迁移
│   ├── env.py                   # Alembic 运行环境配置
│   ├── script.py.mako           # 迁移脚本模板
│   └── versions/                # 各版本迁移脚本
│
├── Dockerfile                   # 后端镜像构建文件
├── alembic.ini                  # Alembic 配置（指定迁移路径和 DB URL）
├── pyproject.toml               # 项目依赖与工具配置（uv 管理）
└── uv.lock                      # 依赖锁文件（保证环境一致性）
```

---

## 前端目录 `/frontend/`

```
frontend/
├── src/                         # 源代码
│   ├── main.ts                  # 应用入口：挂载 Vue、注册插件
│   ├── App.vue                  # 根组件
│   ├── types.ts                 # 全局 TypeScript 类型定义
│   │
│   ├── api/                     # API 请求层
│   │   ├── client.ts            # axios 实例（带拦截器、Token 注入）
│   │   └── chat.ts              # SSE 流式聊天封装（streamChat 函数）
│   │
│   ├── stores/                  # Pinia 状态管理
│   │   └── auth.ts              # 认证状态（token、用户信息、登录/登出）
│   │
│   ├── router/                  # 路由配置
│   │   └── index.ts             # 路由定义（含登录守卫）
│   │
│   ├── composables/             # Vue Composable（可复用逻辑）
│   │   └── useProfile.ts        # 用户画像数据获取逻辑
│   │
│   ├── styles/                  # 全局样式
│   │   └── main.css             # 全局 CSS 变量与基础样式
│   │
│   ├── views/                   # 页面视图
│   │   ├── LoginView.vue        # 登录/注册页
│   │   ├── ChatView.vue         # 聊天主页（RAG 问答 + AI 轨迹）
│   │   ├── AdvisorView.vue      # AI 选购实验室页
│   │   ├── KnowledgeView.vue    # 知识库管理页
│   │   ├── OperationsView.vue   # 运营后台页
│   │   ├── ProfileView.vue      # 个人主页（画像、历史、资料）
│   │   ├── ChatView.test.ts     # ChatView 单元测试
│   │   ├── AdvisorView.test.ts  # AdvisorView 单元测试
│   │   └── ProfileView.test.ts  # ProfileView 单元测试
│   │
│   └── components/              # 可复用组件
│       ├── AppShell.vue         # 应用外壳（导航栏 + 侧边栏布局）
│       ├── auth/                # 认证相关组件
│       ├── chat/                # 聊天相关组件
│       │   ├── ChatComposer.vue    # 输入框组件
│       │   ├── ChatMessage.vue     # 消息气泡（含 AI 轨迹展开）
│       │   ├── SourceRail.vue      # 来源引用卡片列表
│       │   ├── FeedbackDrawer.vue  # 反馈抽屉
│       │   └── ProfileDrawer.vue   # 个人画像侧边栏
│       ├── advisor/             # 选购顾问相关组件
│       ├── knowledge/           # 知识库相关组件
│       ├── account/             # 账号相关组件
│       └── operations/          # 运营后台相关组件
│
├── index.html                   # HTML 入口
├── vite.config.ts               # Vite 构建配置（代理、插件）
├── vitest.config.ts             # Vitest 测试配置
├── tsconfig.json                # TypeScript 根配置
├── tsconfig.app.json            # 应用 TS 配置
├── tsconfig.node.json           # Node 环境 TS 配置
├── package.json                 # 前端依赖（axios/vue/element-plus/echarts 等）
├── pnpm-lock.yaml               # pnpm 锁文件
├── nginx.conf                   # Nginx 配置（Docker 内静态文件托管）
├── Dockerfile                   # 前端镜像构建文件
├── auto-imports.d.ts            # 自动导入声明（unplugin-auto-import 生成）
└── components.d.ts              # 组件类型声明（unplugin-vue-components 生成）
```

---

## 数据目录 `/data/`

```
data/
├── app.db                       # SQLite 数据库文件（运行时生成，含所有业务数据）
├── chroma/                      # ChromaDB 向量数据库（持久化向量索引）
├── uploads/                     # 用户上传的原始文档存储目录
├── models/                      # FastEmbed 模型缓存（约 91MB ONNX 模型文件）
├── logs/                        # 运行日志（如有）
├── evaluation/                  # RAG 评测数据集
│   ├── questions.csv            # 30 条标准回归测试问题（基础版）
│   └── questions-expanded.csv   # 扩展回归集（更多问题，含意图分类）
└── samples/                     # 内置知识库样本文档（10 个小米产品规格 MD 文件）
    ├── SOURCES.md               # 样本来源说明（记录官方采集来源与日期）
    ├── xiaomi-14.md             # 小米 14 手机规格
    ├── smart-band-7.md          # 小米手环 7 规格
    ├── smart-band-9.md          # 小米手环 9 规格
    ├── smart-band-10.md         # 小米手环 10 规格
    ├── robot-vacuum-5.md        # 小米扫地机器人 5 规格
    ├── robot-vacuum-t12.md      # 扫地机器人 T12 规格
    ├── robot-vacuum-t12-specs.md # T12 详细参数
    ├── robot-vacuum-x10.md      # 扫地机器人 X10 规格
    ├── robot-vacuum-x20.md      # 扫地机器人 X20 规格
    └── robot-vacuum-x20-pro.md  # 扫地机器人 X20 Pro 规格
```

---

## 文档目录 `/docs/`

```
docs/
├── api/
│   └── README.md                # API 文档说明（以 Swagger /docs 为准）
├── database/
│   └── README.md                # 数据库文档说明（以代码模型为准）
├── requirements/
│   └── traceability.md          # 需求追踪矩阵（Story -> 接口 -> 测试 的对应表）
├── testing/
│   └── test-report.md           # 测试报告（含三阶段验收记录）
├── deployment/
│   └── README.md                # 部署文档说明
└── superpowers/                 # AI 辅助工具配置（如有）
    └── demo-script.md           # 演示脚本（验收演示步骤）
```

---

## 脚本目录 `/scripts/`

```
scripts/
├── ingest_samples.py            # 批量导入 data/samples/ 中的样本文档到知识库
├── run_rag_evaluation.py        # 执行 RAG 评测（对照 questions.csv 验证正确率）
├── build_extended_evaluation.py # 构建扩展评测集（生成 questions-expanded.csv）
└── collect_official_knowledge.py # 从公开来源采集并处理官方知识（内容辅助工具）
```

---

## Jira 目录 `/jira/`

```
jira/
└── README.md                    # Jira 证据说明（Sprint 记录要求与归档说明）
```

> 原始 32 条 Story 以 CSV 格式保存在根目录：`小米智能客服机器人_Jira_Epic_Stories导入表.csv`
