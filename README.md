# 小米智能客服机器人

> 面向课程演示与验收的可信 RAG 智能客服平台

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB)](backend/pyproject.toml)
[![Vue 3](https://img.shields.io/badge/Vue-3-42B883)](frontend/package.json)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-009688)](backend/pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-109%20passed-brightgreen)](docs/testing/test-report.md)

项目基于真实公开的小米产品资料构建知识库，通过“问题理解、知识召回、AI 重排、
可信生成、引用校验”提供可解释的智能问答。系统包含完整前后端、知识入库、AI 选购、
用户画像、运营分析、推荐训练、Mock 业务工具和 Docker 持久化，可在没有云模型密钥时
使用确定性 Mock 完成自动测试与课程演示。

协作仓库：<https://gitee.com/jiangyuchenjyc/xiaomi-ai-customer-service-robot>

## 功能亮点

- **可信 RAG 问答**：知识型回答必须附带本次实际采用的文档片段；无依据时明确兜底。
- **五阶段 AI 轨迹**：页面实时展示 DeepSeek 问题理解、BGE 召回、DeepSeek 重排、
  DeepSeek 生成和引用校验，不展示密钥、系统提示词或模型思维链。
- **型号防混淆**：产品型号硬过滤结合向量与词法融合检索，避免 X20/X20 Pro 等串答。
- **多知识库融合**：聊天和 AI 选购可同时选择 1–5 个库，每库独立召回后全局排序，
  引用卡明确标注来源库；默认使用核心库与官方完整库。
- **多轮与流式输出**：滚动摘要、最近 10 轮、问题改写、SSE、停止生成和历史恢复。
- **AI 选购实验室**：结构化理解预算和偏好，输出产品卡、对比表、雷达图和真实来源。
- **知识运营**：PDF/DOCX/TXT/MD 入库、任务恢复、切分预览、重建、删除和知识图谱。
- **用户空间**：公开注册、主题头像、成长等级、兴趣星系、14 天趋势和活动时间轴。
- **运营与推荐**：日志、中文反馈、热词云、画像、混合推荐和 TruncatedSVD 离线训练。
- **业务演示**：明确标记的 Mock 订单物流、人工转接和结构化工单。
- **安全与权限**：JWT、Bcrypt、三角色 RBAC、注册限流、敏感输入和安全文件上传。

## AI 执行流程

存在可靠知识候选时，一次普通知识问答的可视化流程为：

```text
DeepSeek 1/3：理解意图并结合历史改写问题
→ BAAI/bge-small-zh-v1.5：每库召回最多 8 条，全局保留最多 12 条
→ DeepSeek 2/3：在候选 ID 白名单内重排并保留最多 4 个
→ DeepSeek 3/3：只依据通过重排的来源生成回答
→ Citation Guard：校验答案来源和引用真实性
```

没有可靠候选时会跳过重排或生成；DeepSeek 不可用时问题理解与重排可降级为确定性逻辑。
订单、转人工等业务意图只执行必要的理解步骤，不让模型伪造业务数据。

## 技术栈

| 层次 | 技术 |
|---|---|
| 前端 | Vue 3、TypeScript、Vite 8、Element Plus、Pinia、ECharts |
| 后端 | Python 3.11、FastAPI、Pydantic 2、SQLAlchemy 2、Alembic |
| 数据 | SQLite、Chroma、本地文件、Docker 命名卷 |
| RAG | LangChain、FastEmbed、BAAI/bge-small-zh-v1.5、jieba 词法融合 |
| LLM | 确定性 Mock、OpenAI-compatible（含 DeepSeek）、Ollama |
| 推荐 | 热度与偏好混合推荐、scikit-learn TruncatedSVD |
| 质量 | pytest、coverage、Ruff、Vitest、Vue TypeScript、Vite build |

## 快速开始：Docker Compose

### 1. 准备环境

安装可用的 Docker Desktop 与 Docker Compose，然后克隆仓库：

```bash
git clone https://gitee.com/jiangyuchenjyc/xiaomi-ai-customer-service-robot.git
cd xiaomi-ai-customer-service-robot
cp .env.example .env
```

### 2. 配置本地密钥和演示密码

编辑 `.env`，至少填写：

```dotenv
JWT_SECRET=替换为至少32个随机字符
INITIAL_ADMIN_PASSWORD=替换为管理员演示密码
INITIAL_OPERATOR_PASSWORD=替换为运营演示密码
INITIAL_USER_PASSWORD=替换为普通用户演示密码
VITE_AMAP_KEY=高德Web端Key
VITE_AMAP_SECURITY_CODE=高德JS安全密钥
```

`.env` 已被 Git 忽略，不要把真实 DeepSeek 密钥、JWT 密钥或密码写入 README、源码或提交历史。
高德的两个 `VITE_AMAP_*` 变量属于前端构建期配置；修改后必须重新执行
`docker compose build frontend && docker compose up -d frontend`，仅重启旧容器不会生效。

### 3. 构建并启动

```bash
docker compose up -d --build
docker compose ps
```

后端首次使用 BGE 时可能需要下载约 91 MB 的 ONNX 模型。等待后端状态变为 `healthy` 后访问：

| 地址 | 用途 |
|---|---|
| <http://localhost:8080> | Web 工作台 |
| <http://localhost:8000/docs> | Swagger API |
| <http://localhost:8000/api/v1/health> | 健康检查 |

停止和恢复：

```bash
docker compose down       # 保留命名卷数据
docker compose up -d      # 使用原数据恢复
```

只有明确执行 `docker compose down -v` 才会删除本项目 Docker 数据卷。

## 本地开发

本项目后端要求 Python `>=3.11,<3.12`，前端需要 Node.js 18+ 与 pnpm。

### 后端

```bash
cd backend
uv sync --extra dev
uv run alembic upgrade head
uv run python -m app.commands init-demo
uv run fastapi dev
```

### 前端

在另一终端执行：

```bash
cd frontend
pnpm install
pnpm dev
```

开发页面位于 <http://localhost:5173>，Vite 会把 `/api` 代理到 <http://localhost:8000>。

## 演示账号与公开注册

初始化命令会读取 `.env` 创建三个演示账号：

| 用户名 | 角色 | 权限 |
|---|---|---|
| `admin` | `admin` | 全部页面、知识库和运营后台 |
| `operator` | `operator` | 知识库、文档任务和运营后台 |
| `customer` | `user` | 可信问答、AI 选购和个人主页 |

密码由本地 `.env` 决定。登录页也支持公开注册；新账号固定为 `user`，同一来源默认
10 分钟最多尝试 5 次，客户端不能指定角色、激活状态或令牌版本。

## 知识资料

仓库提供两组可追溯资料：

- `data/samples/`：10 份小型基础样本，用于快速演示和 30 问基线回归。
- `data/knowledge/official/`：62 份由 46 个公开来源页面整理的正式资料，覆盖手机、
  平板、穿戴、空气净化、空调、电视、路由、扫地机器人、售后政策和故障排查。
- `data/knowledge/manifest.csv`：记录正式资料的分类、产品型号和来源 URL。

资料仅用于课程演示；产品参数、价格和服务政策应以小米官网当前页面为准。

### 批量导入基础样本

确保后端运行后，在项目根目录执行：

```bash
INGEST_PASSWORD='你的运营账号密码' \
backend/.venv/bin/python scripts/ingest_samples.py \
  --base-url http://127.0.0.1:8000/api/v1 \
  --knowledge-base-name 小米产品基础样本
```

### 批量导入正式资料

```bash
INGEST_PASSWORD='你的运营账号密码' \
backend/.venv/bin/python scripts/ingest_samples.py \
  --samples data/knowledge/official \
  --base-url http://127.0.0.1:8000/api/v1 \
  --knowledge-base-name 小米官方公开资料
```

若知识库已存在，使用 `--knowledge-base-id UUID` 代替 `--knowledge-base-name`。
脚本输出每个任务的终态和最终 `knowledge_base_id`。

## 模型配置

### Mock：开发与自动测试

```dotenv
LLM_PROVIDER=mock
EMBEDDING_PROVIDER=mock
```

Mock 使用确定性分析、重排、回答和 Hash Embedding，不需要网络或 API 额度。

### DeepSeek + 本地 BGE

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=deepseek-chat
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=只在本地env中填写
EMBEDDING_PROVIDER=bge
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

DeepSeek 通过 LangChain 的 OpenAI-compatible 适配器接入。真实验收只需少量代表问题，
批量回归应切换到 Mock，避免不必要的费用。

### Ollama

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:4b
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

本地非 Docker 开发可把地址改为 `http://localhost:11434`。

## 页面导航

| 路径 | 功能 | 角色 |
|---|---|---|
| `/login` | 登录与公开注册 | 公开 |
| `/chat` | 可信 RAG 问答、AI 轨迹、来源、反馈和工单 | 所有登录用户 |
| `/advisor` | AI 选购实验室与历史方案 | 所有登录用户 |
| `/profile` | AI 数字空间、画像、活动和账户安全 | 所有登录用户 |
| `/knowledge` | 知识库、文档任务和知识图谱 | admin/operator |
| `/operations` | 日志、热词、反馈、工单、推荐和训练 | admin/operator |

## API 概览

所有业务接口前缀为 `/api/v1`，完整契约以运行时 Swagger 为准。

| 模块 | 主要接口 |
|---|---|
| 认证 | `POST /auth/login`、`POST /auth/register`、`GET /auth/me` |
| 账号 | `PATCH /account/profile`、`POST /account/change-password`、主页与活动接口 |
| 知识库 | `/knowledge-bases` CRUD |
| 文档 | `/documents`、`/jobs`、切分、重建和重试 |
| 问答 | `POST /chat/completions`、会话历史、取消生成和反馈 |
| 顾问 | `/advisor/sessions` 与回合接口 |
| 业务 | `/mock/orders`、`/tickets` |
| 运营推荐 | `/operations/*`、`/recommendations`、`/recommendation/training-runs` |

聊天支持 JSON 和 SSE。SSE 依次发送 `meta`、五阶段 `trace`、`delta`、`sources` 和
`done`；失败时发送 `error`。引用只能来自本次实际送入生成模型的片段。
聊天与 Advisor 新客户端提交 `knowledge_base_ids`（1–5 个、自动去重）；旧版
`knowledge_base_id` 继续兼容。两者同时提交但范围冲突时返回
`422 knowledge_base_selection_conflict`。

## 测试与质量检查

在项目根目录执行后端检查：

```bash
backend/.venv/bin/ruff format --check backend/app backend/tests scripts
backend/.venv/bin/ruff check backend/app backend/tests scripts
LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock \
backend/.venv/bin/pytest backend/tests --cov=app
```

前端：

```bash
cd frontend
pnpm test -- --run
pnpm build
```

当前基线为后端 76 项（覆盖率 90%）、唯一前端 33 项全部通过。最终实测记录见
[测试报告](docs/testing/test-report.md)。

### RAG 回归

基础集包含 30 问，扩展集包含 114 问。运行前应使用 Mock 模型启动后端并导入匹配知识库：

```bash
EVAL_PASSWORD='你的普通用户密码' \
backend/.venv/bin/python scripts/run_rag_evaluation.py \
  --base-url http://127.0.0.1:8000/api/v1 \
  --questions data/evaluation/questions.csv \
  --knowledge-base-id 你的知识库UUID
```

验收线为不低于 80%；当前 30 问 Mock 基线记录为 30/30。

### 双产品知识库

新增产品资料按用途隔离，避免客服问答混入竞品：

- `data/knowledge/product-core/`：30 份小米、REDMI、米家资料。
- `data/knowledge/product-comparison/`：20 份竞品资料，仅用于选购与对比。
- `data/knowledge/audits/product-source-review.xlsx`：来源、价格口径、分库和人工审核台账。

导入前会强制检查元数据、来源 URL、审核状态和未核实标记；密码只从环境变量读取：

```bash
INGEST_PASSWORD='你的运营账号密码' \
backend/.venv/bin/python scripts/ingest_product_knowledge.py \
  --base-url http://127.0.0.1:8000/api/v1
```

脚本会创建或复用“小米生态核心库”和“竞品选购对比库”，重复文件按文件名跳过，
并把文档主要来源写入引用卡片。自动质量检查不替代审核表中的人工终审。

### 四格式上传复验

`data/upload-fixtures/` 长期保留 PDF、DOCX、TXT、MD 四种非产品事实样本。建议先创建
独立“文件上传验收库”，再从前端批量上传；也可用运营账号执行：

```bash
INGEST_PASSWORD='你的运营账号密码' \
backend/.venv/bin/python scripts/verify_upload_fixtures.py
```

## 项目结构

```text
backend/               FastAPI、数据库、文档处理、RAG、顾问和运营模块
frontend/              Vue 工作台、组件、API 封装、状态和测试
data/samples/          10 份快速演示知识样本
data/knowledge/        62 份官方资料、50 份分库产品资料及来源审核表
data/evaluation/       30 问基础集与 114 问扩展集
data/upload-fixtures/  PDF、DOCX、TXT、MD 四种真实上传验收文件
docs/planning/         原始需求与实施规划
docs/project/          需求完成情况、结构和整理决策
docs/requirements/     Story 追踪矩阵
docs/testing/          实际测试与 Docker 验收记录
docs/superpowers/      设计规格和实施计划证据
scripts/               知识采集、批量导入和回归评测工具
jira/                  Jira CSV 与个人 Sprint 证据说明
```

详细说明见 [项目文件结构](docs/project/structure.md)。

## 安全边界

- JWT 固定验证配置算法、签名、签发方、有效期和 `token_version`。
- 密码使用 Bcrypt；修改密码会使所有旧 JWT 失效。
- 注册用户固定为普通角色，服务端执行用户名、密码、头像白名单和频率校验。
- 上传执行扩展名、MIME、文件签名、大小、安全文件名和路径隔离校验。
- 敏感输入在创建模型 Provider 前拦截，审计日志不保存原始密码内容。
- Markdown 经 DOMPurify 清洗；显示名和活动内容使用普通 Vue 文本绑定。
- 文档片段被视为不可信数据，不得覆盖系统规则或要求模型选择虚假来源 ID。
- 用户画像、推荐、活动、订单和工单查询均按当前用户或角色隔离。

## 范围边界

本项目是单人课程演示系统，不声称具备以下生产接入：

- 真实小米账号、订单、支付、退款、优惠券、发票或售后系统。
- 真实物流提醒、维修进度、工单自动分派或客服坐席平台。
- APP、微信、抖音、企业微信、语音或跨渠道会话同步。
- 产品主数据实时同步、知识图谱推理或生产级高并发部署。

Mock 订单会明确显示“Mock 演示数据”。知识图谱是基于已入库资料的可视化关系网络，
不是独立的知识图谱推理引擎。价格和政策来自文档采集时间，最终以官方当前页面为准。

## 文档入口

- [完整需求与完成情况](docs/project/requirements-and-status.md)
- [项目文件结构](docs/project/structure.md)
- [文件整理决策](docs/project/cleanup-decisions.md)
- [API 说明](docs/api/README.md)
- [数据库与持久化](docs/database/README.md)
- [部署说明](docs/deployment/README.md)
- [需求追踪矩阵](docs/requirements/traceability.md)
- [测试报告](docs/testing/test-report.md)
- [课程演示脚本](docs/demo-script.md)
