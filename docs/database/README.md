# 数据库与持久化

SQLite 保存用户、知识库、文档元数据、处理任务、chunk、会话、消息、引用、反馈、行为、Mock 订单、工单和训练版本。用户表包含显示名称、预设头像与 `token_version`；密码变更通过版本号即时撤销旧 JWT。Alembic 迁移位于 `backend/alembic/versions/`。

`conversation_knowledge_bases` 与 `advisor_session_knowledge_bases` 保存聊天和选购会话
固定的多知识库范围，联合主键防重复，`ordinal` 保留用户选择顺序。旧
`knowledge_base_id` 作为首库兼容字段继续保留；迁移 `7b41c2d9e610` 会把全部历史
会话自动回填到关联表，不删除旧数据。

原文保存到 `data/uploads`，Chroma 保存到 `data/chroma`，推荐模型产物保存到 `data/models`。Docker 中三者与 SQLite 共用命名卷 `app-data`。文档删除会先清理向量与原文，再删除关系数据；重建会先移除旧 chunk 向量，保证幂等。

迁移命令：

```bash
uv run --project backend alembic -c backend/alembic.ini upgrade head
```
