"""教师待办问题池的写入逻辑：去重，并允许已处理问题再次出现时重新打开。"""
from ..models import UnansweredQuestion


def record_unanswered(*, course, user, question: str, reason: str) -> UnansweredQuestion:
    item = (
        UnansweredQuestion.objects.filter(course=course, question=question)
        .order_by("-created_at")
        .first()
    )
    if item is None:
        return UnansweredQuestion.objects.create(
            course=course,
            user=user,
            question=question,
            reason=reason,
        )

    # 已处理的问题再次出现时重新打开；教师明确“忽略”的问题不强行打扰。
    if item.status == UnansweredQuestion.Status.RESOLVED:
        item.status = UnansweredQuestion.Status.OPEN
        item.reason = reason
        item.resolved_at = None
        item.save(update_fields=["status", "reason", "resolved_at"])
    return item
