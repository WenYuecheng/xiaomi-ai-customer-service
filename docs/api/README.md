# API 说明

运行后以 `/docs` 中的 OpenAPI 为唯一接口真相源，业务前缀为 `/api/v1`。除登录和健康检查外均需 Bearer JWT。

统一错误体为 `{"error":{"code","message","details"},"request_id"}`；响应头回传 `X-Request-ID`。聊天 SSE 顺序为 `meta → trace(理解) → trace(检索) → trace(重排) → trace(生成中) → delta* → sources → trace(生成完成) → trace(引用校验) → done`，异常事件为 `error`。`trace` 按 `stage` 幂等更新，JSON 响应和历史消息使用同一 `ai_trace` 结构。引用只从本次实际检索、通过重排并送入生成模型的 chunk 产生。

主要资源：`auth`、`knowledge-bases`、`documents/jobs`、`chat/conversations/feedback`、`mock/orders`、`tickets`、`operations`、`recommendations`。
