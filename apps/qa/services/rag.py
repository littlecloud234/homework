"""RAG 主流程：检索 -> 阈值判断 -> 生成 -> 引用落库。

大模型只参与“基于资料组织答案”，不参与权限、拒答阈值和引用真实性判断。
"""
import logging
import re

from django.conf import settings
from pgvector.django import CosineDistance

from apps.knowledge.models import Document, DocumentChunk

from ..models import Citation, Conversation, Message, UnansweredQuestion
from .embeddings import embed_texts
from .llm import chat_completion
from .prompts import REFUSAL_TEMPLATE, build_messages
from .queue import record_unanswered

logger = logging.getLogger(__name__)

CITATION_RE = re.compile(r"\[(\d{1,2})\]")
ERROR_TEXT = "抱歉，回答生成暂时失败，请稍后再试，或把问题提交给任课教师。"
MODEL_REFUSAL_MARKERS = (
    "根据现有课程资料无法确定",
    "无法找到足够依据",
    "现有课程资料不足",
)


def retrieve(
    course_id: int,
    query: str,
    top_k: int | None = None,
    min_score: float | None = None,
):
    """课程范围内向量检索。

    返回 ([(chunk, score)], best_score)。best_score 用于区分“没有任何资料”
    与“有资料但相关度不足”，两者会进入不同的教师待办分类。
    """
    top_k = top_k or settings.RETRIEVAL_TOP_K
    min_score = settings.RETRIEVAL_SCORE_THRESHOLD if min_score is None else min_score

    query_vector = embed_texts([query])[0]
    candidates = list(
        DocumentChunk.objects.filter(
            # 以文档归属为权威，chunk.course 只作为冗余索引字段。
            document__course_id=course_id,
            document__status=Document.Status.READY,
            embedding__isnull=False,
        )
        .select_related("document")
        .annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[:top_k]
    )
    if not candidates:
        return [], None

    scored = [(chunk, 1.0 - float(chunk.distance)) for chunk in candidates]
    results = [(chunk, score) for chunk, score in scored if score >= min_score]
    return results, max(score for _, score in scored)


def answer_question(
    *,
    course,
    user,
    question: str,
    conversation: Conversation | None = None,
) -> Message:
    conversation = conversation or Conversation.objects.create(
        course=course,
        user=user,
        title=question[:80],
    )
    user_message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=question,
    )

    history = _recent_history(conversation, exclude_id=user_message.id)

    try:
        sources, best_score = retrieve(course.id, question)
    except Exception:  # noqa: BLE001 - 对外返回友好错误，内部保留堆栈
        logger.exception("检索失败 course_id=%s", course.id)
        return _save_error(conversation)

    if not sources:
        reason = (
            UnansweredQuestion.Reason.LOW_SCORE
            if best_score is not None
            else UnansweredQuestion.Reason.NO_CONTEXT
        )
        message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            status=Message.Status.REFUSED,
            content=REFUSAL_TEMPLATE.format(course_title=course.title),
            retrieval_debug={
                "reason": reason.value,
                "best_score": round(best_score, 4) if best_score is not None else None,
            },
        )
        record_unanswered(course=course, user=user, question=question, reason=reason)
        _touch(conversation)
        return message

    try:
        messages, context_count = build_messages(course, question, sources, history)
        result = chat_completion(messages)
        if not result.content.strip():
            raise ValueError("模型返回空内容")
    except Exception:  # noqa: BLE001
        logger.exception(
            "生成失败 course_id=%s conversation_id=%s", course.id, conversation.id
        )
        return _save_error(conversation)

    parsed_ranks = sorted({int(value) for value in CITATION_RE.findall(result.content)})
    context_sources = sources[:context_count]
    valid_ranks = [rank for rank in parsed_ranks if 1 <= rank <= len(context_sources)]
    has_invalid_citations = parsed_ranks != valid_ranks
    model_refused = _looks_like_refusal(result.content)
    needs_review = has_invalid_citations or (not valid_ranks and not model_refused)

    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=result.content,
        status=Message.Status.REFUSED if model_refused else Message.Status.OK,
        model_name=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_ms=result.latency_ms,
        needs_review=needs_review,
        retrieval_debug={
            "threshold": settings.RETRIEVAL_SCORE_THRESHOLD,
            "sources": _sources_debug(sources),
            "context_sources": context_count,
            "parsed_ranks": parsed_ranks,
            "cited_ranks": valid_ranks,
            "has_invalid_citations": has_invalid_citations,
            "model_refusal": model_refused,
            "needs_review": needs_review,
        },
    )
    citations = _build_citations(message, valid_ranks, context_sources)
    message.retrieval_debug["citation_count"] = len(citations)
    message.save(update_fields=["retrieval_debug"])

    if model_refused:
        record_unanswered(
            course=course,
            user=user,
            question=question,
            reason=UnansweredQuestion.Reason.LOW_SCORE,
        )

    _touch(conversation)
    return message


def _looks_like_refusal(content: str) -> bool:
    """识别模型自己判断“资料不足”的短回答，避免把它当成正常答案。"""
    compact = re.sub(r"\s+", "", content)
    if len(compact) > 300:
        return False
    return any(marker in compact for marker in MODEL_REFUSAL_MARKERS)


def _recent_history(
    conversation: Conversation,
    *,
    exclude_id: int | None = None,
    limit: int = 6,
) -> list[dict]:
    queryset = conversation.messages.filter(
        role__in=[Message.Role.USER, Message.Role.ASSISTANT]
    )
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    messages = queryset.order_by("-created_at")[:limit]
    return [
        {"role": item.role, "content": item.content}
        for item in reversed(list(messages))
    ]


def _sources_debug(sources) -> list[dict]:
    return [
        {
            "rank": rank,
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "document_title": chunk.document.title,
            "score": round(score, 4),
        }
        for rank, (chunk, score) in enumerate(sources, start=1)
    ]


def _build_citations(message: Message, ranks: list[int], sources) -> list[Citation]:
    citations = []
    for rank in ranks:
        if not 1 <= rank <= len(sources):
            continue
        chunk, score = sources[rank - 1]
        citations.append(
            Citation(
                message=message,
                chunk=chunk,
                document_title=chunk.document.title,
                rank=rank,
                score=score,
                quote=chunk.content[:240],
            )
        )
    if citations:
        Citation.objects.bulk_create(citations)
    return citations


def _save_error(conversation: Conversation) -> Message:
    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        status=Message.Status.ERROR,
        content=ERROR_TEXT,
    )
    _touch(conversation)
    return message


def _touch(conversation: Conversation) -> None:
    conversation.save(update_fields=["updated_at"])
