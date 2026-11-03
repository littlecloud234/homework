import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("courses", "0001_initial"),
        ("knowledge", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
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
                    "title",
                    models.CharField(blank=True, max_length=120, verbose_name="标题"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversations",
                        to="courses.course",
                        verbose_name="课程",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversations",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "会话",
                "verbose_name_plural": "会话",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="Message",
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
                    "role",
                    models.CharField(
                        choices=[
                            ("user", "学生"),
                            ("assistant", "助手"),
                            ("system", "系统"),
                        ],
                        max_length=20,
                        verbose_name="角色",
                    ),
                ),
                ("content", models.TextField(verbose_name="内容")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ok", "正常"),
                            ("refused", "拒答"),
                            ("error", "错误"),
                        ],
                        default="ok",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                (
                    "model_name",
                    models.CharField(blank=True, max_length=128, verbose_name="模型"),
                ),
                (
                    "prompt_tokens",
                    models.PositiveIntegerField(default=0, verbose_name="输入 token"),
                ),
                (
                    "completion_tokens",
                    models.PositiveIntegerField(default=0, verbose_name="输出 token"),
                ),
                (
                    "latency_ms",
                    models.PositiveIntegerField(default=0, verbose_name="耗时(ms)"),
                ),
                (
                    "retrieval_debug",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="检索调试信息"
                    ),
                ),
                (
                    "needs_review",
                    models.BooleanField(default=False, verbose_name="待人工复核"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="qa.conversation",
                        verbose_name="会话",
                    ),
                ),
            ],
            options={
                "verbose_name": "消息",
                "verbose_name_plural": "消息",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="Citation",
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
                    "document_title",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="文档标题快照"
                    ),
                ),
                (
                    "rank",
                    models.PositiveSmallIntegerField(verbose_name="引用编号"),
                ),
                ("score", models.FloatField(default=0.0, verbose_name="相似度")),
                ("quote", models.TextField(blank=True, verbose_name="引用原文")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "chunk",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="citations",
                        to="knowledge.documentchunk",
                        verbose_name="引用片段",
                    ),
                ),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="citations",
                        to="qa.message",
                        verbose_name="回答",
                    ),
                ),
            ],
            options={
                "verbose_name": "引用",
                "verbose_name_plural": "引用",
                "ordering": ["rank"],
            },
        ),
        migrations.CreateModel(
            name="Feedback",
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
                    "rating",
                    models.SmallIntegerField(
                        choices=[(1, "有用"), (-1, "没用")], verbose_name="评价"
                    ),
                ),
                (
                    "comment",
                    models.CharField(blank=True, max_length=1000, verbose_name="备注"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedbacks",
                        to="qa.message",
                        verbose_name="回答",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="qa_feedbacks",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "反馈",
                "verbose_name_plural": "反馈",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="UnansweredQuestion",
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
                ("question", models.TextField(verbose_name="问题")),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("no_context", "无相关资料"),
                            ("low_score", "相关度不足"),
                            ("user_thumbs_down", "用户点踩"),
                            ("out_of_scope", "超出课程范围"),
                        ],
                        max_length=32,
                        verbose_name="原因",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "待处理"),
                            ("resolved", "已处理"),
                            ("ignored", "忽略"),
                        ],
                        default="open",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "resolved_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="处理时间"),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="unanswered_questions",
                        to="courses.course",
                        verbose_name="课程",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="unanswered_questions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="提问人",
                    ),
                ),
            ],
            options={
                "verbose_name": "待办问题",
                "verbose_name_plural": "待办问题",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(
                fields=["user", "course"], name="idx_conversation_user_course"
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["conversation", "created_at"], name="idx_message_conversation"
            ),
        ),
        migrations.AddIndex(
            model_name="unansweredquestion",
            index=models.Index(
                fields=["course", "status"], name="idx_unanswered_course_status"
            ),
        ),
        migrations.AddConstraint(
            model_name="citation",
            constraint=models.UniqueConstraint(
                fields=("message", "chunk"), name="uniq_message_chunk_citation"
            ),
        ),
        migrations.AddConstraint(
            model_name="feedback",
            constraint=models.UniqueConstraint(
                fields=("message", "user"), name="uniq_message_user_feedback"
            ),
        ),
    ]
