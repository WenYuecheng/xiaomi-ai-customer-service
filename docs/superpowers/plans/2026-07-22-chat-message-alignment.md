# Chat Message Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将可信问答中的用户消息整体放在右侧、小爱客服消息整体放在左侧，并保留全部现有交互。

**Architecture:** 继续复用现有 `ChatMessage.vue`。身份块根据消息角色渲染在正文前或后，角色修饰类负责桌面和移动端网格方向；不增加状态、组件或接口。

**Tech Stack:** Vue 3、TypeScript、Vue Test Utils、Vitest、scoped CSS。

## Global Constraints

- 用户身份、名称和气泡整体靠右；客服身份、名称和回答整体靠左。
- 不修改 SSE、Markdown、AI 轨迹、来源、反馈或工单行为。
- 只提交本功能文件，不提交 `install_arina_dream_skin.sh`。

---

### Task 1: 消息角色布局契约

**Files:**
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
- Modify: `frontend/src/components/chat/ChatMessage.vue`

**Interfaces:**
- Consumes: `ChatMessage` 的 `message.role: 'user' | 'assistant'` 属性。
- Produces: `.message--user` 中正文位于身份标识前，`.message--assistant` 中身份标识位于正文前。

- [x] **Step 1: 写入失败的组件测试**

为用户消息和客服消息分别挂载组件，断言用户的 `.message__body` DOM 索引小于 `.message__identity`，客服顺序相反，并检查身份文字。

- [x] **Step 2: 运行测试并确认失败**

Run: `pnpm test -- ChatMessage.test.ts`

Expected: 用户消息顺序断言失败，因为现有身份块始终先于正文。

- [x] **Step 3: 写入最小实现**

在正文前仅渲染客服身份，在正文后仅渲染用户身份；桌面端为用户配置 `minmax(0, 1fr) 72px`，客服配置 `72px minmax(0, 1fr)`。用户身份右对齐，用户正文右对齐并限制最大宽度；移动端缩小身份列但保留左右关系。

- [x] **Step 4: 运行组件测试并确认通过**

Run: `pnpm test -- ChatMessage.test.ts`

Expected: `ChatMessage.test.ts` 全部通过。

- [x] **Step 5: 提交布局实现**

```bash
git add frontend/src/components/chat/ChatMessage.vue frontend/src/components/chat/ChatMessage.test.ts
git commit -m "fix(frontend): align chat messages by role"
```

### Task 2: 全量验收与发布

**Files:**
- Modify: `docs/testing/test-report.md`

**Interfaces:**
- Consumes: Task 1 的角色布局。
- Produces: 可审计的自动化测试、构建和浏览器验收记录。

- [x] **Step 1: 运行完整前端验证**

Run: `pnpm test && pnpm typecheck && pnpm build`

Expected: Vitest、Vue TypeScript 和 Vite 构建均以状态码 0 完成。

- [x] **Step 2: 重建并检查 Docker 前端**

Run: `docker compose build frontend && docker compose up -d frontend`

Expected: frontend 为 running，访问 `http://localhost:8080` 返回 200。

- [x] **Step 3: 浏览器检查**

登录可信问答页面，确认用户身份与气泡在右、小爱客服身份与回答在左，并在窄屏宽度下确认无横向溢出。

- [x] **Step 4: 记录验收结果**

在 `docs/testing/test-report.md` 添加本功能的日期、测试数、构建状态和桌面/移动布局结果。

- [x] **Step 5: 提交验收记录并推送**

```bash
git add docs/testing/test-report.md docs/superpowers/plans/2026-07-22-chat-message-alignment.md
git commit -m "docs: record chat alignment acceptance"
git push -u origin codex/chat-message-alignment
```
