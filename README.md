# 小米智能客服机器人

面向课程验收的可信 RAG 客服平台。系统支持知识库与多格式文档、真实来源引用、低置信度兜底、多轮会话、SSE 流式回答、Mock 订单/工单、日志反馈、热词、用户画像、混合推荐和离线推荐训练。

## 快速启动

要求：Docker Desktop（含 Compose）。

```bash
cp .env.example .env
```

编辑 `.env`，至少设置以下随机值和三个演示账号密码：

```dotenv
JWT_SECRET=至少32位随机字符串
INITIAL_ADMIN_PASSWORD=你的管理员密码
INITIAL_OPERATOR_PASSWORD=你的运营账号密码
INITIAL_USER_PASSWORD=你的普通用户密码
```

然后运行：

```bash
docker compose up --build
```

- Web 工作台：<http://localhost:8080>
- Swagger：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/v1/health>

数据保存在 Docker 命名卷 `app-data`。删除容器不会丢失数据；只有显式删除该卷才会清空。

## 本地开发

后端固定 Python 3.11：

```bash
cd backend
uv sync --extra dev
uv run alembic upgrade head
uv run python -m app.commands init-demo
uv run fastapi dev
```

完成后用 `cd ..` 回到项目根目录执行下方评测脚本。

前端：

```bash
cd frontend
pnpm install
pnpm dev
```

## 模型配置

默认 `LLM_PROVIDER=mock`、`EMBEDDING_PROVIDER=mock`，无需密钥即可运行测试和完整业务流程。

OpenAI-compatible（包括 DeepSeek）配置：

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=deepseek-chat
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=通过本地环境设置，不要提交到 Git
```

本地 Ollama 配置：

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:4b
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

自动测试始终使用确定性 Mock，避免消耗 API 额度。真实模型只运行少量手工集成测试。

## 测试与质量检查

```bash
uv run --project backend --extra dev ruff format --check backend/app backend/tests scripts
uv run --project backend --extra dev ruff check backend/app backend/tests scripts
LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock uv run --project backend --extra dev pytest backend/tests --cov=app
cd frontend && pnpm test && pnpm build
```

执行 30 问 RAG 回归：

```bash
backend/.venv/bin/python scripts/run_rag_evaluation.py \
  --questions data/evaluation/questions.csv \
  --knowledge-base-id 你的知识库ID
```

## 关键安全边界

- JWT 只接受配置的 HS256 算法并验证签名、签发方和有效期。
- 密码使用 Bcrypt；密钥只从环境变量读取。
- 上传文件使用格式、签名、大小与安全路径校验。
- 文档和模型输出永远不会作为代码或系统命令执行。
- Mock 订单有明确标识，不包含真实个人信息。
- 用户画像只统计产品、意图和反馈，不保存地址、电话或支付信息。

## 项目结构

```text
backend/   FastAPI、SQLite、Chroma、后台处理、RAG 与运营推荐
frontend/  Vue 3、Element Plus、Pinia 与流式聊天工作台
data/      官方样本、评测集以及运行时持久化目录
docs/      需求追踪、API、数据库、测试和答辩材料
scripts/   评测及辅助脚本
jira/      Jira 导入与验收证据
```

完整接口以 Swagger 为准；所有业务 API 统一位于 `/api/v1`。

## 当前范围边界

订单与物流为明确标识的 Mock 演示数据。系统没有连接真实小米账户、支付、退款、售后、维修网点或多渠道平台；这些能力需要官方接口、授权与测试环境，不能用模拟结果冒充真实接入。DeepSeek 可通过 OpenAI-compatible 配置真实调用，BGE 可通过 `EMBEDDING_PROVIDER=bge` 本地运行。
