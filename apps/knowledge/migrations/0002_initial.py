import apps.knowledge.models
import django.db.models.deletion
import pgvector.django
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0001_initial"),
        ("knowledge", "0001_enable_vector"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="文档标题")),
                (
                    "file",
                    models.FileField(
                        blank=True,
                        max_length=100,
                        upload_to=apps.knowledge.models.course_document_path,
                        verbose_name="原始文件",
                    ),
                ),
                (
                    "raw_text",
                    models.TextField(blank=True, verbose_name="直接录入文本"),
                ),
                (
                    "source_type",
                    models.CharField(
                        choices=[
                            ("syllabus", "课程大纲"),
                            ("slides", "课件"),
                            ("textbook", "教材节选"),
                            ("lab", "实验指导"),
                            ("faq", "常见问题"),
                            ("exam", "习题/答案"),
                            ("other", "其他"),
                        ],
                        default="other",
                        max_length=20,
                        verbose_name="来源类型",
                    ),
                ),
                (
                    "version",
                    models.CharField(default="v1", max_length=32, verbose_name="版本"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("uploaded", "已上传"),
                            ("processing", "解析中"),
                            ("ready", "可检索"),
                            ("failed", "解析失败"),
                            ("archived", "已归档"),
                        ],
                        default="uploaded",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                (
                    "checksum",
                    models.CharField(blank=True, max_length=64, verbose_name="SHA-256"),
                ),
                (
                    "effective_from",
                    models.DateField(blank=True, null=True, verbose_name="生效日期"),
                ),
                (
                    "effective_to",
                    models.DateField(blank=True, null=True, verbose_name="失效日期"),
                ),
                (
                    "metadata",
                    models.JSONField(blank=True, default=dict, verbose_name="扩展元数据"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="courses.course",
                        verbose_name="课程",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="uploaded_documents",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="上传人",
                    ),
                ),
            ],
            options={
                "verbose_name": "课程文档",
                "verbose_name_plural": "课程文档",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DocumentChunk",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("seq", models.PositiveIntegerField(verbose_name="块序号")),
                (
                    "heading",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="所属标题"
                    ),
                ),
                ("content", models.TextField(verbose_name="片段内容")),
                (
                    "char_count",
                    models.PositiveIntegerField(default=0, verbose_name="字符数"),
                ),
                (
                    "embedding",
                    pgvector.django.VectorField(
                        blank=True,
                        dimensions=1024,
                        null=True,
                        verbose_name="向量",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(blank=True, default=dict, verbose_name="扩展元数据"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chunks",
                        to="courses.course",
                        verbose_name="课程",
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chunks",
                        to="knowledge.document",
                        verbose_name="文档",
                    ),
                ),
            ],
            options={
                "verbose_name": "文档片段",
                "verbose_name_plural": "文档片段",
                "ordering": ["document_id", "seq"],
            },
        ),
        migrations.CreateModel(
            name="IngestionJob",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "等待中"),
                            ("running", "执行中"),
                            ("succeeded", "成功"),
                            ("failed", "失败"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                ("message", models.TextField(blank=True, verbose_name="信息")),
                (
                    "chunk_count",
                    models.PositiveIntegerField(default=0, verbose_name="片段数"),
                ),
                (
                    "started_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "finished_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ingestion_jobs",
                        to="knowledge.document",
                        verbose_name="文档",
                    ),
                ),
            ],
            options={
                "verbose_name": "解析任务",
                "verbose_name_plural": "解析任务",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="document",
            index=models.Index(
                fields=["course", "status"], name="idx_document_course_status"
            ),
        ),
        migrations.AddIndex(
            model_name="documentchunk",
            index=models.Index(fields=["course"], name="idx_chunk_course"),
        ),
        migrations.AddConstraint(
            model_name="documentchunk",
            constraint=models.UniqueConstraint(
                fields=("document", "seq"), name="uniq_document_chunk_seq"
            ),
        ),
    ]
