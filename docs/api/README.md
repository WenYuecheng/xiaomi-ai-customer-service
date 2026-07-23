# API 说明

运行后以 `/docs` 中的 OpenAPI 为唯一接口真相源，业务前缀为 `/api/v1`。除登录、注册和健康检查外均需 Bearer JWT。

统一错误体为 `{"error":{"code","message","details"},"request_id"}`；响应头回传 `X-Request-ID`。聊天 SSE 顺序为 `meta → trace(理解) → trace(检索) → trace(重排) → trace(生成中) → delta* → sources → trace(生成完成) → trace(引用校验) → done`，异常事件为 `error`。`trace` 按 `stage` 幂等更新，JSON 响应和历史消息使用同一 `ai_trace` 结构。引用只从本次实际检索、通过重排并送入生成模型的 chunk 产生。

账户接口包括 `POST /auth/register`、`GET /auth/me`、`PATCH /account/profile`、`POST /account/change-password`、`GET /account/dashboard` 和 `GET /account/activities`。活动分页游标仅由后端生成；客户端不得构造用户 ID 或角色字段。

主要资源：`auth/account`、`knowledge-bases`、`documents/jobs`、`chat/conversations/feedback`、`advisor`、`mock/orders`、`tickets`、`operations`、`recommendations`。

聊天和 Advisor 首轮支持多知识库范围：

```json
{
  "knowledge_base_ids": ["核心库 UUID", "官方完整库 UUID"],
  "message": "扫地机器人无法开机怎么排查？"
}
```

数组会自动去重且限制 1–5 个，只接受 `active` 知识库。旧字段 `knowledge_base_id`
保留兼容；新旧字段表达不同范围时返回 `422 knowledge_base_selection_conflict`。
响应、SSE `meta` 和会话历史均返回 `knowledge_base_ids`，每个来源增加
`knowledge_base_id` 与 `knowledge_base_name`。
