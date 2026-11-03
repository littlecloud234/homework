"""大模型调用封装：只负责一次对话补全，不做业务判断。"""
import time
from dataclasses import dataclass

from django.conf import settings
from openai import OpenAI


@dataclass(frozen=True)
class LLMResult:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


def _client() -> OpenAI:
    if not settings.LLM_API_KEY:
        raise RuntimeError(
            "未配置 LLM_API_KEY。请在 .env 中填写模型服务密钥，"
            "或将 LLM_BASE_URL 指向本地 vLLM 等兼容服务。"
        )
    return OpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        timeout=settings.LLM_TIMEOUT,
        max_retries=2,
    )


def chat_completion(messages: list[dict], temperature: float = 0.2) -> LLMResult:
    client = _client()
    started = time.perf_counter()
    response = client.chat.completions.create(
        model=settings.LLM_CHAT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    choice = response.choices[0]
    content = choice.message.content or ""
    usage = response.usage
    return LLMResult(
        content=content,
        model=response.model or settings.LLM_CHAT_MODEL,
        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
        latency_ms=latency_ms,
    )
