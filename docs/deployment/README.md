# 部署说明

复制 `.env.example` 为 `.env`，生成至少 32 字节的 `JWT_SECRET`，填写三个演示账号密码，再执行 `docker compose up --build`。后端容器以非 root 用户运行，前端使用非特权 Nginx；运行时目录由命名卷持久化。

云模型密钥只允许通过环境变量注入。默认 Mock 模型可离线完成全部自动测试。若使用本机 Ollama，容器内地址设为 `http://host.docker.internal:11434`。生产环境不要使用演示密码或公开暴露 SQLite 数据卷。
