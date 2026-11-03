from django.conf import settings
from django.db import models

from apps.courses.models import Course


class Conversation(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name="课程",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name="用户",
    )
    title = models.CharField(max_length=120, blank=True, verbose_name="标题")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "会话"
        verbose_name_plural = "会话"
        indexes = [
            models.Index(fields=["user", "course"], name="idx_conversation_user_course"),
        ]

    def __str__(self):
        return self.title or f"会话 {self.pk}"


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "学生"
        ASSISTANT = "assistant", "助手"
        SYSTEM = "system", "系统"

    class Status(models.TextChoices):
        OK = "ok", "正常"
        REFUSED = "refused", "拒答"
        ERROR = "error", "错误"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="会话",
    )
    role = models.CharField(max_length=20, choices=Role.choices, verbose_name="角色")
    content = models.TextField(verbose_name="内容")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OK,
        verbose_name="状态",
    )
    model_name = models.CharField(max_length=128, blank=True, verbose_name="模型")
    prompt_tokens = models.PositiveIntegerField(default=0, verbose_name="输入 token")
    completion_tokens = models.PositiveIntegerField(default=0, verbose_name="输出 token")
    latency_ms = models.PositiveIntegerField(default=0, verbose_name="耗时(ms)")
    retrieval_debug = models.JSONField(default=dict, blank=True, verbose_name="检索调试信息")
    needs_review = models.BooleanField(default=False, verbose_name="待人工复核")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "消息"
        verbose_name_plural = "消息"
        indexes = [
            models.Index(fields=["conversation", "created_at"], name="idx_message_conversation"),
        ]

    def __str__(self):
        return f"{self.conversation_id} · {self.role}"


class Citation(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="citations",
        verbose_name="回答",
    )
    chunk = models.ForeignKey(
        "knowledge.DocumentChunk",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="citations",
        verbose_name="引用片段",
    )
    # 快照：文档重新解析会删除旧 chunk，引用仍可用于审计与展示。
    document_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="文档标题快照",
    )
    rank = models.PositiveSmallIntegerField(verbose_name="引用编号")
    score = models.FloatField(default=0.0, verbose_name="相似度")
    quote = models.TextField(blank=True, verbose_name="引用原文")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["rank"]
        verbose_name = "引用"
        verbose_name_plural = "引用"
        constraints = [
            models.UniqueConstraint(
                fields=["message", "chunk"],
                name="uniq_message_chunk_citation",
            )
        ]

    def __str__(self):
        return f"{self.message_id} -> chunk {self.chunk_id}"


class Feedback(models.Model):
    class Rating(models.IntegerChoices):
        HELPFUL = 1, "有用"
        NOT_HELPFUL = -1, "没用"

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="feedbacks",
        verbose_name="回答",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="qa_feedbacks",
        verbose_name="用户",
    )
    rating = models.SmallIntegerField(choices=Rating.choices, verbose_name="评价")
    comment = models.CharField(max_length=1000, blank=True, verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "反馈"
        verbose_name_plural = "反馈"
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user"],
                name="uniq_message_user_feedback",
            )
        ]

    def __str__(self):
        return f"{self.message_id} · {self.rating}"


class UnansweredQuestion(models.Model):
    class Reason(models.TextChoices):
        NO_CONTEXT = "no_context", "无相关资料"
        LOW_SCORE = "low_score", "相关度不足"
        USER_THUMBS_DOWN = "user_thumbs_down", "用户点踩"
        OUT_OF_SCOPE = "out_of_scope", "超出课程范围"

    class Status(models.TextChoices):
        OPEN = "open", "待处理"
        RESOLVED = "resolved", "已处理"
        IGNORED = "ignored", "忽略"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="unanswered_questions",
        verbose_name="课程",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unanswered_questions",
        verbose_name="提问人",
    )
    question = models.TextField(verbose_name="问题")
    reason = models.CharField(max_length=32, choices=Reason.choices, verbose_name="原因")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name="状态",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="处理时间")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "待办问题"
        verbose_name_plural = "待办问题"
        indexes = [
            models.Index(fields=["course", "status"], name="idx_unanswered_course_status"),
        ]

    def __str__(self):
        return self.question[:60]
