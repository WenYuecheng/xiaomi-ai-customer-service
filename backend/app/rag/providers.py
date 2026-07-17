from typing import Protocol

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.core.config import Settings

SYSTEM_PROMPT = """你是小米产品客服。只能依据给定知识片段回答。
不得补充片段中没有的产品参数、政策或事实。回答简洁、清晰，并保留原始数值。
知识片段：
{context}
"""


class ChatProvider(Protocol):
    def generate(self, question: str, contexts: list[str], summary: str | None = None) -> str: ...


class MockChatProvider:
    def generate(self, question: str, contexts: list[str], summary: str | None = None) -> str:
        del question, summary
        return f"根据知识库，{contexts[0]}"


class LangChainChatProvider:
    def __init__(self, model) -> None:
        self.model = model

    def generate(self, question: str, contexts: list[str], summary: str | None = None) -> str:
        prompt = SYSTEM_PROMPT.format(context="\n\n".join(contexts))
        if summary:
            prompt += f"\n历史摘要：{summary}"
        response = self.model.invoke(
            [{"role": "system", "content": prompt}, {"role": "user", "content": question}]
        )
        return str(response.content)


def create_chat_provider(settings: Settings) -> ChatProvider:
    if settings.llm_provider == "mock":
        return MockChatProvider()
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI-compatible provider")
        return LangChainChatProvider(
            ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                temperature=0,
                max_retries=1,
                timeout=30,
            )
        )
    return LangChainChatProvider(
        ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )
    )

