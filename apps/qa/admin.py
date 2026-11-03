from django.contrib import admin
from django.utils import timezone

from .models import Citation, Conversation, Feedback, Message, UnansweredQuestion


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("role", "status", "content", "model_name", "latency_ms", "created_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class CitationInline(admin.TabularInline):
    model = Citation
    extra = 0
    fields = ("rank", "chunk", "document_title", "score", "quote")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "user", "title", "created_at", "updated_at")
    list_filter = ("course",)
    search_fields = ("title", "user__username", "user__display_name")
    inlines = [MessageInline]
    list_select_related = ("course", "user")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "role",
        "status",
        "needs_review",
        "model_name",
        "latency_ms",
        "created_at",
    )
    list_filter = ("role", "status", "needs_review", "model_name")
    search_fields = ("content",)
    readonly_fields = (
        "conversation",
        "role",
        "content",
        "status",
        "model_name",
        "prompt_tokens",
        "completion_tokens",
        "latency_ms",
        "retrieval_debug",
        "needs_review",
        "created_at",
    )
    inlines = [CitationInline]
    list_select_related = ("conversation",)

    def has_add_permission(self, request):
        return False


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "user", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("user__username", "comment")
    list_select_related = ("message", "user")


@admin.action(description="将所选问题标记为已处理")
def mark_resolved(modeladmin, request, queryset):
    queryset.update(
        status=UnansweredQuestion.Status.RESOLVED,
        resolved_at=timezone.now(),
    )


@admin.action(description="将所选问题标记为忽略")
def mark_ignored(modeladmin, request, queryset):
    queryset.update(status=UnansweredQuestion.Status.IGNORED)


@admin.register(UnansweredQuestion)
class UnansweredQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "question", "reason", "status", "created_at")
    list_filter = ("course", "status", "reason")
    search_fields = ("question",)
    actions = [mark_resolved, mark_ignored]
    list_select_related = ("course", "user")
