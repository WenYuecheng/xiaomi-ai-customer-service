"""
文件职责：
该文件负责测试应用的基础启动和依赖配置环境。

所属功能：
系统初始化与配置校验。

主要流程：
验证核心包的存在，并校验环境变量配置（如 OpenAI API Key）在特定条件下的必填性。
"""

from importlib.util import find_spec

import pytest

from app.core.config import Settings


def test_application_package_exists() -> None:
    """
    测试 FastAPI 应用的顶层包 'app' 是否已正确实现/存在。

    测试应用核心包是否存在，从而确保运行环境的 Python 路径设置正确且代码结构正常。
    """
    # 使用 find_spec 来寻找 app 模块，如果找不到则说明应用基础包尚未准备就绪，断言失败。
    assert find_spec("app") is not None, "FastAPI application package has not been implemented"


def test_openai_compatible_provider_requires_key_at_startup() -> None:
    """
    测试当配置的 LLM 提供商为 openai 时，是否必须提供相应的 API 密钥。

    预期在不提供 OPENAI_API_KEY 的情况下验证配置时，抛出包含特定提示信息的 ValueError。
    """
    # 构造一个 LLM provider 为 openai，但缺少 API key 的配置实例。
    settings = Settings(
        app_env="test",
        llm_provider="openai",
        openai_api_key=None,
        jwt_secret="test-secret-with-at-least-thirty-two-characters",  # noqa: S106
    )

    # 断言在调用验证方法时会抛出 ValueError，且异常信息中必须匹配 "OPENAI_API_KEY"。
    # 这是为了确保程序可以在启动前及时发现致命的缺失配置。
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        settings.validate_runtime_secrets()
