# 小米智能客服机器人

> **面向课程验收的可信 RAG 智能客服平台**

基于检索增强生成（RAG）技术，以真实的小米产品文档为知识库，提供可解释的问答服务。每次回答都展示完整的五阶段 AI 执行轨迹，适合课程演示与技术验收。

---

## 功能亮点

- **可信 RAG 问答**：回答严格基于知识库文档，附带可点击的真实来源引用
- **五阶段 AI 轨迹**：问题理解 → 向量召回 → AI 重排 → 流式生成 → 引用校验，全程可视
- **多轮对话**：滚动摘要压缩历史，支持追问和上下文继承
- **AI 选购实验室**：输入品类和候选型号，生成结构化选购方案与雷达图
- **动态个人主页**：咨询次数、产品兴趣星系、14 天活跃趋势、活动时间轴
- **运营后台**：对话日志、热词统计、混合推荐、离线训练（TruncatedSVD）
- **三角色权限**：admin / operator / user，公开注册固定为普通用户
- **一键部署**：Docker Compose 两个容器，数据持久化到命名卷

---

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + TypeScript + Element Plus + ECharts + Pinia |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy + Alembic + SQLite |
| RAG | LangChain + ChromaDB + FastEmbed（BGE 向量模型） |
| LLM | 支持 Mock（无需密钥）/ DeepSeek / OpenAI / Ollama |
| 部署 | Docker Compose + Nginx |

---

## 前提条件

### Docker 启动（推荐，零环境要求）

只需安装 **Docker Desktop**（含 Docker Compose），版本不限。

- 下载地址：https://www.docker.com/products/docker-desktop/
- 安装后确认可用：`docker --version` 和 `docker compose version`

### 本地开发

- Python 3.11（严格，不支持 3.10 或 3.12+）
- Node.js 18+（用于前端）
- pnpm（前端包管理器）：`npm install -g pnpm`
- uv（Python 包管理器）：`pip install uv` 或参考 https://docs.astral.sh/uv/

---

## 方式一：Docker 一键启动（推荐新手）

### 第一步：克隆/下载项目

```bash
git clone <仓库地址>
cd robot
```

### 第二步：配置环境变量

```bash
cp .env.example .env
```

用任意文本编辑器打开 `.env`，**至少修改以下四个值**：

```dotenv
# 必填：至少 32 个随机字符，用于签发 JWT
JWT_SECRET=请替换为你的随机字符串例如abcdefghijklmnopqrstuvwxyz123456

# 必填：三个演示账号的密码
INITIAL_ADMIN_PASSWORD=你的管理员密码
INITIAL_OPERATOR_PASSWORD=你的运营账号密码
INITIAL_USER_PASSWORD=你的普通用户密码
```

> 其余配置保持默认即可，默认使用 Mock 模型（无需任何 AI 密钥）。

### 第三步：启动

```bash
docker compose up --build
```

首次启动会下载镜像并构建，约需 3-10 分钟（取决于网速）。
看到 `backend healthy` 后，即可访问：

| 地址 | 用途 |
|------|------|
| http://localhost:8080 | Web 工作台（前端） |
| http://localhost:8000/docs | Swagger API 文档 |
| http://localhost:8000/api/v1/health | 健康检查 |

### 停止与重启

```bash
# 停止（数据保留）
docker compose down

# 再次启动（不需要重新构建）
docker compose up -d

# 彻底清除数据（谨慎！）
docker compose down -v
```

---

## 方式二：本地开发启动

适合需要修改代码、调试或运行测试的场景。

### 后端启动

```bash
# 进入后端目录
cd backend

# 安装依赖（包括开发依赖）
uv sync --extra dev

# 初始化数据库表结构
uv run alembic upgrade head

# 创建演示账号和种子数据
uv run python -m app.commands init-demo

# 启动后端服务（默认监听 8000 端口）
uv run fastapi dev
```

访问 http://localhost:8000/docs 确认后端正常运行。

### 前端启动

打开新的终端：

```bash
# 从项目根目录进入前端
cd frontend

# 安装依赖
pnpm install

# 启动开发服务器（默认 5173 端口，支持热更新）
pnpm dev
```

访问 http://localhost:5173 即可使用。

> **注意**：本地开发时，前端代理配置在 `vite.config.ts` 中，默认将 `/api` 请求转发到 `http://localhost:8000`。

---

## 演示账号

系统默认创建以下三个演示账号（密码由 `.env` 配置）：

| 账号 | 用户名 | 角色 | 可访问功能 |
|------|--------|------|------------|
| 管理员 | admin | admin | 全部功能，包括知识库管理和运营后台 |
| 运营人员 | operator | operator | 知识库管理、文档上传、运营后台 |
| 普通用户 | customer | user | 聊天问答、AI 选购、个人主页 |

也可在登录页直接**注册新账号**（固定为普通用户角色，10 分钟内同一 IP 最多注册 5 次）。

---

## 导入样本知识库

首次启动后，知识库为空。可通过以下方式导入内置小米产品文档：

### 方式 A：通过 Web 界面上传

1. 以 admin 或 operator 身份登录
2. 点击导航栏「知识库」
3. 创建一个知识库（如「小米产品库」）
4. 将 `data/samples/` 目录下的 `.md` 文件逐一上传

### 方式 B：使用脚本批量导入（本地开发）

```bash
# 确保后端已启动，然后在项目根目录执行
cd backend

# 参数：知识库 ID（从 Web 界面创建后复制 UUID）
uv run python ../scripts/ingest_samples.py \
  --knowledge-base-id 你在Web界面创建的知识库UUID
```

---

## 模型配置

### 默认：Mock 模型（无需密钥，适合开发测试）

```dotenv
LLM_PROVIDER=mock
EMBEDDING_PROVIDER=mock
```

Mock 模式使用确定性算法生成回答，所有自动化测试均使用此模式。

### DeepSeek（推荐真实体验）

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=deepseek-chat
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=你的DeepSeek密钥
EMBEDDING_PROVIDER=bge
```

> DeepSeek API 注册：https://platform.deepseek.com/

### 本地 Ollama（无需网络 API）

先安装 Ollama（https://ollama.com），然后：

```bash
# 下载模型
ollama pull qwen3:4b
```

配置 `.env`：

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:4b
OLLAMA_BASE_URL=http://localhost:11434
# Docker 中使用：
# OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### BGE 本地向量模型

```dotenv
EMBEDDING_PROVIDER=bge
```

BGE 模型（约 91MB）首次使用时自动下载并缓存到 `data/models/`。

---

## 页面功能指南

| 页面路径 | 功能描述 | 建议账号 |
|---------|----------|---------|
| `/` → 自动跳转登录 | 登录/注册 | 任意 |
| `/chat` | 智能客服问答主页（含 AI 轨迹） | 任意 |
| `/advisor` | AI 选购实验室（选品类、比较型号） | 任意 |
| `/knowledge` | 知识库和文档管理 | admin / operator |
| `/operations` | 运营后台（日志、热词、推荐） | admin / operator |
| `/profile` | 个人主页（画像、历史、修改资料） | 任意 |

---

## 运行测试

### 后端测试

```bash
cd backend

# 代码格式检查
uv run --extra dev ruff format --check app tests

# 静态分析
uv run --extra dev ruff check app tests

# 单元测试（使用 Mock 模型，无需密钥）
LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock uv run --extra dev pytest tests --cov=app
```

预期结果：56 项全部通过，覆盖率 89%。

### 前端测试

```bash
cd frontend

# 单元测试
pnpm test

# 生产构建验证
pnpm build
```

预期结果：28 项全部通过，构建成功。

### RAG 回归评测

```bash
# 在项目根目录执行（需后端已启动且已导入知识库）
backend/.venv/bin/python scripts/run_rag_evaluation.py \
  --questions data/evaluation/questions.csv \
  --knowledge-base-id 你的知识库UUID
```

预期结果：30/30 通过，正确率 100%。

---

## 常见问题排查

### Q: 启动后前端显示空白或 404

**原因**：后端还在初始化中，前端等待后端健康才能启动。
**解决**：等待 `docker compose logs backend` 输出 `Application startup complete` 后再刷新。

### Q: 登录提示"用户名或密码错误"

**原因**：`.env` 中的密码未填写，或 `init-demo` 未执行。
**Docker 解决**：确认 `.env` 中三个密码已填写，然后 `docker compose down && docker compose up --build`。
**本地解决**：重新执行 `uv run python -m app.commands init-demo`。

### Q: 上传文档后状态一直是 "processing"

**原因**：后台 Worker 处理卡住（通常是 Embedding 模型首次下载）。
**解决**：查看日志 `docker compose logs backend`，如果是网络问题等待下载完成即可。BGE 模型约 91MB，首次下载需要网络。

### Q: 问答结果始终是 "未找到可靠依据"

**原因**：
1. 知识库为空（未上传文档）
2. 使用 Mock Embedding 但问题与文档语义差异较大（Mock 用哈希算法，不是真正的语义检索）
**解决**：上传样本文档，或改用 BGE/OpenAI Embedding。

### Q: Docker 构建失败

**原因**：网络问题导致依赖下载超时。
**解决**：
```bash
docker compose build --no-cache
```
或配置 Docker 使用国内镜像源。

### Q: Python 版本不对

**原因**：本项目严格要求 Python 3.11。
**解决**：使用 `pyenv` 安装 3.11，或通过 uv 管理：
```bash
uv python install 3.11
```

---

## API 接口概览

所有接口统一前缀为 `/api/v1`，完整文档见 http://localhost:8000/docs（Swagger UI）。

| 模块 | 接口前缀 | 说明 |
|------|----------|------|
| 认证 | `/auth` | 登录（返回 JWT） |
| 账号 | `/account` | 注册、查看/更新资料、修改密码 |
| 知识库 | `/knowledge-bases` | 知识库 CRUD |
| 文档 | `/documents` | 上传、查看、删除、重建索引 |
| 问答 | `/chat` | 流式/非流式问答、反馈、会话历史、工单 |
| 顾问 | `/advisor` | AI 选购会话 |
| 运营 | `/operations` | 日志、热词、推荐、训练 |
| 系统 | `/health` | 健康检查 |

---

## 项目结构速览

```
robot/
├── backend/        Python FastAPI 后端（核心业务逻辑、RAG 引擎）
├── frontend/       Vue 3 前端（聊天界面、AI 轨迹展示）
├── data/           运行时数据目录（DB、向量库、上传文件、样本文档）
├── docs/           项目文档（需求追踪、测试报告）
├── scripts/        辅助脚本（批量导入、RAG 评测）
├── jira/           Jira 验收证据
├── docker-compose.yml
├── .env.example    → 复制为 .env 并填写密钥
└── README.md
```

---

## 数据安全说明

- **密钥**：`.env` 文件包含 JWT 密钥，请勿提交到 Git
- **数据库**：`data/app.db` 包含用户信息，请勿公开
- **持久化**：Docker 使用命名卷 `app-data`，`docker compose down` 不会删除数据；只有 `docker compose down -v` 才会清空
- **备份**：`docker run --rm -v robot_app-data:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz /data`

---

## 已知限制

| 限制 | 说明 |
|------|------|
| 订单/物流 | 为 Mock 演示数据，非真实小米系统 |
| 支付/退款 | 未接入真实支付系统 |
| 价格 | 仅来自知识文档，标注采集时间，非实时 |
| 并发 | 单容器模式，适合演示而非生产 |
