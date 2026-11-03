from django.contrib import admin

from .models import Document, DocumentChunk, IngestionJob


@admin.action(description="重新解析所选文档（异步入队）")
def reingest_documents(modeladmin, request, queryset):
    from .tasks import ingest_document_task

    for document in queryset:
        ingest_document_task.delay(document.id)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "course",
        "source_type",
        "version",
        "status",
        "uploaded_by",
        "created_at",
    )
    list_filter = ("status", "source_type", "course")
    search_fields = ("title", "course__code", "course__title")
    autocomplete_fields = ("course", "uploaded_by")
    readonly_fields = ("checksum", "created_at", "updated_at")
    actions = [reingest_documents]
    list_select_related = ("course", "uploaded_by")

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        # 文档创建后不允许改课程，否则冗余的 chunk.course 会与文档归属不一致。
        if obj:
            fields.append("course")
        return fields

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        content_changed = not change or any(
            field in form.changed_data for field in ("file", "raw_text")
        )
        if content_changed:
            obj.status = Document.Status.UPLOADED
            obj.checksum = obj.compute_checksum()
            obj.save(update_fields=["status", "checksum", "updated_at"])


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "seq", "heading", "char_count", "created_at")
    list_filter = ("course",)
    search_fields = ("document__title", "content")
    exclude = ("embedding",)
    list_select_related = ("document", "course")


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "status", "chunk_count", "started_at", "finished_at")
    list_filter = ("status",)
    search_fields = ("document__title",)
    readonly_fields = ("document", "status", "message", "chunk_count", "started_at", "finished_at", "created_at")
    list_select_related = ("document",)

    def has_add_permission(self, request):
        return False
