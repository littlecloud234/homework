"""Embedding 服务。默认走 OpenAI 兼容接口，可切换到本地 bge-m3 服务。"""
import logging

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


def _client() -> OpenAI:
    if not settings.EMBEDDING_API_KEY:
        raise RuntimeError(
            "未配置 EMBEDDING_API_KEY。请填写 SiliconFlow 等兼容服务的密钥，"
            "或将 EMBEDDING_BASE_URL 指向本地推理服务并设置占位密钥。"
        )
    return OpenAI(
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL,
        timeout=settings.LLM_TIMEOUT,
        max_retries=2,
    )


def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """批量向量化，保持输入顺序，并校验维度。"""
    if not texts:
        return []

    client = _client()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=batch,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        for item in ordered:
            vector = list(item.embedding)
            if len(vector) != settings.EMBEDDING_DIM:
                raise ValueError(
                    f"Embedding 维度不匹配：配置为 {settings.EMBEDDING_DIM}，"
                    f"实际为 {len(vector)}。请同步修改 EMBEDDING_DIM 并重建向量。"
                )
            vectors.append(vector)
    return vectors
