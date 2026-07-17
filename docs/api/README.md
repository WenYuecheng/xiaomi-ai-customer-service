# API 说明

运行后以 `/docs` 中的 OpenAPI 为唯一接口真相源，业务前缀为 `/api/v1`。除登录和健康检查外均需 Bearer JWT。

统一错误体为 `{"error":{"code","message","details"},"request_id"}`；响应头回传 `X-Request-ID`。聊天 SSE 顺序为 `meta → delta* → sources → done`，异常事件为 `error`。引用只从本次实际检索并送入模型的 chunk 生成。

主要资源：`auth`、`knowledge-bases`、`documents/jobs`、`chat/conversations/feedback`、`mock/orders`、`tickets`、`operations`、`recommendations`。
