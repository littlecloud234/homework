import hashlib

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from pgvector.django import VectorField

from apps.courses.models import Course


def course_document_path(instance, filename):
    return f"courses/{instance.course_id}/documents/{filename}"


class Document(models.Model):
    """教师上传的课程资料。原始文件与纯文本二选一。"""

    class SourceType(models.TextChoices):
        SYLLABUS = "syllabus", "课程大纲"
        SLIDES = "slides", "课件"
        TEXTBOOK = "textbook", "教材节选"
        LAB = "lab", "实验指导"
        FAQ = "faq", "常见问题"
        EXAM = "exam", "习题/答案"
        OTHER = "other", "其他"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "已上传"
        PROCESSING = "processing", "解析中"
        READY = "ready", "可检索"
        FAILED = "failed", "解析失败"
        ARCHIVED = "archived", "已归档"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="课程",
    )
    title = models.CharField(max_length=255, verbose_name="文档标题")
    file = models.FileField(
        upload_to=course_document_path,
        blank=True,
        verbose_name="原始文件",
    )
    raw_text = models.TextField(blank=True, verbose_name="直接录入文本")
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.OTHER,
        verbose_name="来源类型",
    )
    version = models.CharField(max_length=32, default="v1", verbose_name="版本")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
        verbose_name="状态",
    )
    checksum = models.CharField(max_length=64, blank=True, verbose_name="SHA-256")
    effective_from = models.DateField(null=True, blank=True, verbose_name="生效日期")
    effective_to = models.DateField(null=True, blank=True, verbose_name="失效日期")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="扩展元数据")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
        verbose_name="上传人",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "课程文档"
        verbose_name_plural = "课程文档"
        indexes = [
            models.Index(fields=["course", "status"], name="idx_document_course_status"),
        ]

    def __str__(self):
        return f"{self.course.code} · {self.title}"

    def clean(self):
        super().clean()
        if not self.file and not (self.raw_text or "").strip():
            raise ValidationError("请上传文件或填写直接录入文本。")

    def compute_checksum(self) -> str:
        """对“实际会被解析的内容”计算 SHA-256。

        与 extractors 的优先级保持一致：有文件时以文件为准，否则使用直接录入文本。
        """
        digest = hashlib.sha256()
        if self.file:
            try:
                self.file.open("rb")
                for chunk in self.file.chunks():
                    digest.update(chunk)
            finally:
                self.file.close()
        elif self.raw_text:
            digest.update(self.raw_text.encode("utf-8"))
        return digest.hexdigest()


class DocumentChunk(models.Model):
    """检索最小单元。course 冗余存储，确保检索时能强制课程隔离。"""

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
        verbose_name="文档",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="chunks",
        verbose_name="课程",
    )
    seq = models.PositiveIntegerField(verbose_name="块序号")
    heading = models.CharField(max_length=255, blank=True, verbose_name="所属标题")
    content = models.TextField(verbose_name="片段内容")
    char_count = models.PositiveIntegerField(default=0, verbose_name="字符数")
    embedding = VectorField(
        dimensions=settings.EMBEDDING_DIM,
        null=True,
        blank=True,
        verbose_name="向量",
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name="扩展元数据")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document_id", "seq"]
        verbose_name = "文档片段"
        verbose_name_plural = "文档片段"
        constraints = [
            models.UniqueConstraint(
                fields=["document", "seq"],
                name="uniq_document_chunk_seq",
            )
        ]
        indexes = [
            models.Index(fields=["course"], name="idx_chunk_course"),
        ]

    def __str__(self):
        return f"{self.document.title} #{self.seq}"


class IngestionJob(models.Model):
    """一次文档解析入库任务，失败原因可追溯。"""

    class Status(models.TextChoices):
        PENDING = "pending", "等待中"
        RUNNING = "running", "执行中"
        SUCCEEDED = "succeeded", "成功"
        FAILED = "failed", "失败"

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="ingestion_jobs",
        verbose_name="文档",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="状态",
    )
    message = models.TextField(blank=True, verbose_name="信息")
    chunk_count = models.PositiveIntegerField(default=0, verbose_name="片段数")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "解析任务"
        verbose_name_plural = "解析任务"

    def __str__(self):
        return f"{self.document_id} · {self.status}"
