# HyperOS Knowledge & Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩充中国大陆官方知识库，并把聊天、画像、知识管理和运营分析升级为可解释、中文化、可视化的 HyperOS 极光体验。

**Architecture:** 保持 FastAPI 模块化单体、SQLite、Chroma 与 Vue 3 架构。新增只读聚合 API 为 ECharts 提供稳定数据；知识图谱由现有文档/chunk 元数据派生，不引入图数据库；训练继续使用离线 SVD，但记录数据指纹与指标变化。

**Tech Stack:** Python 3.11、FastAPI、SQLAlchemy、LangChain/Chroma、Vue 3、Element Plus、ECharts、Vitest、pytest。

## Global Constraints

- 正式知识只使用小米中国大陆官方公开页面或官方用户手册，并保存来源与采集日期。
- 中文 UI 不直接展示 `up/down`、内部意图名、工单英文状态或原始 JSON。
- 动画仅使用 `transform` 与 `opacity`，支持 `prefers-reduced-motion`，交互元素具备键盘焦点与可访问名称。
- 指标不得随机变化；无新增训练数据时返回并展示数据未变化。

---

### Task 1: 官方知识数据集

**Files:** `data/knowledge/manifest.csv`、`data/knowledge/**/*.md`、`data/evaluation/questions-expanded.csv`、`scripts/ingest_official_knowledge.py`

- [ ] 收集并验证 60–100 个官方来源，按 10 个主题目录生成结构化中文摘要与清单。
- [ ] 为每个文档写入 `source_url/captured_at/market/category/product_models/content_type` 元数据。
- [ ] 增加至少 100 条覆盖参数、使用、故障、售后的回归问题，并校验来源文件存在。
- [ ] 导入脚本创建或复用“中华人民共和国小米官方知识库”，轮询任务并输出成功/失败统计。

### Task 2: 可视化聚合 API

**Files:** `backend/app/knowledge/router.py`、`backend/app/knowledge/schemas.py`、`backend/app/operations/analytics.py`

- [ ] 先写 API 测试：知识概览返回文档/chunk/品类/产品/状态计数，图谱返回稳定节点与边。
- [ ] 实现 `GET /knowledge-bases/{id}/analytics` 与 `/graph`，权限沿用知识运营角色。
- [ ] 扩展热词响应为词频列表和按日期聚合的热力数据；画像响应增加已中文化的展示项。

### Task 3: 可解释训练

**Files:** `backend/app/operations/recommendation.py`、`backend/app/operations/schemas.py`、`backend/app/operations/router.py`

- [ ] 测试数据指纹、未变化跳过、样本数、数据集类型、K 值、基线差值和失败样例。
- [ ] 训练请求支持目标 `balanced/precision/recall`，响应增加 `dataset_name/sample_count/product_count/data_fingerprint/changed/metric_delta/explanation`。
- [ ] 真实数据不足时允许明确标识的演示数据；重复训练相同数据与目标时不产生虚假新指标。

### Task 4: 聊天、反馈与画像体验

**Files:** `frontend/src/views/ChatView.vue`、`frontend/src/components/chat/ChatMessage.vue`、`frontend/src/components/chat/FeedbackDrawer.vue`

- [ ] 黑盒测试点赞选中态、重复评价更新、点踩抽屉、错误恢复和中文画像标签。
- [ ] 实现 HyperOS 极光视觉、用户/助手气泡、参数高亮、来源色条与流式状态。
- [ ] 点赞按钮显示动态图标和“已记录”；点踩抽屉提供“不准确/没解决/不清楚/其他”与纠正文本。
- [ ] 画像使用偏好卡、意图环形图和反馈比例条，内部枚举通过统一中文映射展示。

### Task 5: 知识图谱与运营看板

**Files:** `frontend/src/components/knowledge/KnowledgeAnalytics.vue`、`frontend/src/components/operations/TopicVisualization.vue`、`frontend/src/components/operations/TrainingGuide.vue`

- [ ] 添加 ECharts 依赖并封装按需加载、ResizeObserver 与销毁逻辑。
- [ ] 知识页增加统计卡、可筛选关系图和点击节点详情，保留原列表作为可访问的数据替代视图。
- [ ] 运营页增加词云式热词布局、日历热力图、中文反馈/工单图标标签和训练引导面板。
- [ ] 训练面板解释目标、数据条件和指标含义，展示相对上版变化或“数据未变化”。

### Task 6: 验收与部署

- [ ] 后端 Ruff、pytest 与覆盖率通过；前端 Vitest、`vue-tsc` 和 Vite 构建通过。
- [ ] 导入正式知识库，抽查全部主题并运行扩展回归；真实 DeepSeek 仅执行 3 个跨品类问题。
- [ ] 重建 Docker，验证健康检查、图谱/热词/训练 API、反馈交互与重启持久化。
- [ ] 更新测试报告，记录资料数量、来源政策、回归正确率、图表空状态和训练数据指纹。
