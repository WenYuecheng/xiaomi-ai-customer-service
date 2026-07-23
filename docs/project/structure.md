# 小米智能客服机器人——项目文件结构说明

本文档描述最终交付结构。运行时生成内容由 `.gitignore` 排除，不属于源码交付物。

## 根目录

```text
robot/
├── backend/             Python FastAPI 后端
├── frontend/            Vue 3 + TypeScript 前端
├── data/                知识资料、评测集和运行时目录占位
├── docs/                项目、规划、接口、数据库、部署与测试文档
├── scripts/             数据采集、导入和评测脚本
├── jira/                Jira CSV 与证据说明
├── docker-compose.yml   前后端编排与持久化卷
├── .env.example         无真实凭据的环境变量模板
├── .gitignore           本地密钥、缓存和运行时数据排除规则
├── .dockerignore        Docker 构建上下文排除规则
└── README.md            项目唯一主入口
```

本地可能出现 `.env`、`.coverage`、`.DS_Store` 等文件，但它们不会进入 Git。

## 后端 `backend/`

```text
backend/
├── app/
│   ├── main.py                 应用工厂、生命周期、中间件和路由注册
│   ├── commands.py             遗留库基线兼容与演示数据初始化命令
│   ├── core/
│   │   ├── config.py           Pydantic Settings 与环境变量校验
│   │   ├── errors.py           统一业务异常和错误响应
│   │   └── http.py             请求 ID 中间件
│   ├── db/
│   │   ├── base.py             SQLAlchemy Engine、Session 与 Base
│   │   └── models.py           15 张业务表与枚举
│   ├── auth/
│   │   ├── router.py           登录、注册和当前用户接口
│   │   ├── service.py          用户创建与密码认证
│   │   ├── security.py         Bcrypt、JWT 签发和验证
│   │   ├── dependencies.py     当前用户与 RBAC 依赖
│   │   ├── rate_limit.py       来源维度注册限流
│   │   └── schemas.py          认证请求和响应模型
│   ├── account/
│   │   ├── router.py           资料、改密、个人主页和活动接口
│   │   ├── service.py          用户统计、画像、趋势和时间轴聚合
│   │   └── schemas.py          账号、活动与仪表盘模型
│   ├── knowledge/
│   │   ├── router.py           知识库 CRUD 与可视化分析
│   │   ├── schemas.py          知识库和知识图谱响应模型
│   │   └── selection.py        1–5 库选择、兼容与有效状态校验
│   ├── ingestion/
│   │   ├── router.py           上传、预览、重建、重试和删除接口
│   │   ├── parsers.py          PDF/DOCX/TXT/MD 解析和型号提取
│   │   ├── service.py          解析、切分和向量补偿逻辑
│   │   ├── worker.py           单进程后台任务 Worker
│   │   └── schemas.py          文档和任务模型
│   ├── rag/
│   │   ├── providers.py        Mock/OpenAI-compatible/Ollama 适配器
│   │   ├── vector_store.py     Chroma 与 Mock 向量库封装
│   │   ├── retrieval.py        向量分与 jieba 词法分融合检索
│   │   └── reranking.py        AI 重排结果白名单和阈值过滤
│   ├── chat/
│   │   ├── router.py           JSON/SSE、会话、取消生成和反馈
│   │   ├── service.py          理解、检索、重排、生成和引用流水线
│   │   └── schemas.py          消息、来源与 AI 轨迹模型
│   ├── advisor/
│   │   ├── router.py           AI 选购会话、回合和历史接口
│   │   ├── service.py          需求理解、分型号召回和方案生成
│   │   └── schemas.py          产品卡、对比表、雷达和来源模型
│   └── operations/
│       ├── router.py           订单、工单、日志、画像、推荐和训练接口
│       ├── analytics.py        中文热词与时间衰减统计
│       ├── recommendation.py   混合推荐与 TruncatedSVD 训练
│       └── schemas.py          运营与推荐响应模型
├── tests/                      76 项后端测试及共享夹具
├── alembic/
│   ├── env.py                  迁移运行环境
│   └── versions/               初始、Advisor、用户资料与多库范围迁移
├── Dockerfile                  Python 3.11 非 root 后端镜像
├── pyproject.toml              依赖与 pytest/Ruff 配置
├── uv.lock                     精确依赖锁文件
└── alembic.ini                 Alembic 配置
```

### 后端模块边界

- Router 只负责 HTTP、依赖注入和响应组装；业务聚合放在 Service。
- Pydantic Schema 是 API 边界；SQLAlchemy Model 是持久化边界。
- `rag/` 不直接处理 HTTP；`chat/` 与 `advisor/` 负责流程编排。
- 注册属于 `auth/router.py`；资料与主页属于 `account/router.py`。
- JWT 签发与验证属于 `auth/security.py`，不是 `auth/service.py`。

## 前端 `frontend/`

```text
frontend/
├── src/
│   ├── main.ts                         Vue、Pinia 与全局样式入口
│   ├── App.vue                         根路由容器
│   ├── types.ts                        共享 API 类型
│   ├── api/
│   │   ├── client.ts                   Axios、Bearer Token 与 401 处理
│   │   ├── chat.ts                     SSE 聊天协议解析
│   │   └── advisor.ts                  Advisor JSON/SSE API
│   ├── stores/auth.ts                  登录、注册和当前用户状态
│   ├── router/index.ts                 路由、角色守卫和登录重定向
│   ├── composables/
│   │   ├── useAccountDashboard.ts      个人主页与资料更新状态
│   │   └── useAdvisorLab.ts             AI 选购状态和流式事件
│   ├── views/                           登录、聊天、顾问、知识库、运营和主页
│   ├── components/
│   │   ├── auth/                        注册表单
│   │   ├── chat/                        消息、轨迹、来源、反馈和画像
│   │   ├── advisor/                     需求表单、方案、雷达和历史
│   │   ├── knowledge/                   知识库、文档和知识图谱
│   │   ├── operations/                  热词、运营面板和训练说明
│   │   └── account/                     身份卡、统计、星系、趋势和设置
│   └── styles/main.css                  设计变量、响应式和降级动画
├── Dockerfile                           Vite 构建与非特权 Nginx 镜像
├── nginx.conf                           静态资源与 `/api` 反向代理
├── vite.config.ts                       Vue、自动导入和开发代理
├── vitest.config.ts                     组件测试配置
├── package.json                         脚本与直接依赖
└── pnpm-lock.yaml                       精确前端依赖锁文件
```

测试文件与对应组件或视图相邻。`auto-imports.d.ts`、`components.d.ts`、
`*.tsbuildinfo`、`dist/` 和 `node_modules/` 均为生成内容，不纳入 Git。

## 数据 `data/`

```text
data/
├── upload-fixtures/          四种真实文件上传验收资料
├── samples/                 10 份快速演示样本与 SOURCES.md
├── knowledge/
│   ├── manifest.csv         46 个公开来源页面的分类和 URL
│   └── official/            62 份整理后的正式知识 Markdown
├── evaluation/
│   ├── questions.csv        30 问基础回归集
│   └── questions-expanded.csv  114 问扩展集
├── uploads/.gitkeep         原文目录占位，实际文件忽略
├── chroma/.gitkeep          向量目录占位，实际文件忽略
├── models/.gitkeep          模型缓存目录占位，实际文件忽略
└── logs/.gitkeep            日志目录占位，实际文件忽略
```

本地开发可能生成 `data/app.db`；Docker 则把 SQLite、上传、Chroma 和模型缓存保存在
`app-data` 命名卷中。两者都不提交 Git。

## 文档 `docs/`

```text
docs/
├── project/                 最终需求状态、结构、整理决策和 README 写作依据
├── planning/                5 份原始需求与实施规划
├── screenshots/             3 张历史验收图片
├── requirements/            Story 追踪矩阵
├── testing/                 自动化、真实模型和 Docker 测试报告
├── api/                     API 契约说明
├── database/                表、迁移和持久化说明
├── deployment/              部署和安全配置说明
├── superpowers/specs/       已批准的设计规格
├── superpowers/plans/       可复核的实施计划
└── demo-script.md           课程演示步骤
```

## 脚本和 Jira

```text
scripts/
├── ingest_samples.py             批量创建/选择知识库并上传 Markdown
├── run_rag_evaluation.py         使用登录用户执行基线或扩展评测
├── collect_official_knowledge.py 从 manifest 重新采集正式公开资料
└── build_extended_evaluation.py  生成扩展评测 CSV

jira/
├── Jira_Epic_Stories导入表.csv    32 条 Jira Story 导入文件
└── README.md                      单人 Sprint 与证据归档规则
```

## 结构维护原则

1. 新业务模块放入独立后端包和前端组件目录，不在根目录堆放源码。
2. 新文档必须进入职责明确的 `docs/` 子目录，并从主 README 建立入口。
3. 可重新生成的依赖、缓存和运行时数据不提交；依赖锁文件必须提交。
4. 基础与扩展评测保留为不同资产，不用一个文件覆盖另一个。
5. 文件移动使用 Git 重命名，保证课程验收能够追溯历史。
